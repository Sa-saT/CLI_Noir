"""仮想ファイルシステムのパス解決・ノード操作（一元化ヘルパー）。

`filesystem` は「/」直下の子ノード map（例: {"root": {...}}）。「/」自体は暗黙で、
その children が `filesystem` そのもの（同一オブジェクト）を指すため、そこへの追加・
削除は state に反映される。実 OS には一切触れない（設計指示書 § 0.5）。
"""

from datetime import datetime, timezone

from app.content.missions import CASE_FILE_NAME, get_mission
from app.evaluator import progress


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize(current_path: str, path: str) -> str:
    """current_path を基準に path（絶対/相対/`.`/`..`）を絶対パスへ正規化する。"""
    if path.startswith("/"):
        base: list[str] = []
    else:
        base = [p for p in current_path.split("/") if p]
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if base:
                base.pop()
        else:
            base.append(part)
    return "/" + "/".join(base)


def segments(abs_path: str) -> list[str]:
    return [p for p in abs_path.split("/") if p]


def root_node(state: dict) -> dict:
    """「/」を表す合成ディレクトリノード（children は filesystem 本体を参照）。"""
    return {"type": "dir", "children": state["filesystem"]}


# --- 疑似 /proc（設計指示書 § 4）---
# filesystem JSON には保存せず、読み取り時に processes テーブルから動的生成する
# 読み取り専用ツリー。「ps も /proc を読んでいる」タネ明かし（Mission7）用に
# free/uptime コマンドと同じ定数を参照させ、出力を整合させる。
PROC_MEM_TOTAL_KB = 8_192_000
PROC_MEM_USED_KB = 2_048_000
PROC_UPTIME_SECONDS = 132345.67

_PROC_CPUINFO = (
    "processor\t: 0\n"
    "vendor_id\t: NoirVirtual\n"
    "model name\t: Virtual CPU @ 2.40GHz"
)


def _proc_file(content: str) -> dict:
    return {
        "type": "file",
        "content": content,
        "mode": "r--r--r--",
        "owner": "root",
        "mtime": "2026-01-01T00:00:00Z",
        "immutable": True,
    }


def _proc_meminfo_text() -> str:
    free_kb = PROC_MEM_TOTAL_KB - PROC_MEM_USED_KB
    return (
        f"MemTotal:       {PROC_MEM_TOTAL_KB} kB\n"
        f"MemFree:        {free_kb} kB\n"
        f"MemUsed:        {PROC_MEM_USED_KB} kB"
    )


def _proc_pid_dir(p: dict) -> dict:
    uid = 0 if p.get("user") == "root" else 1000
    status = f"Name:\t{p['name']}\nState:\t{p.get('state', 'S')} (sleeping)\nUid:\t{uid}"
    return {
        "type": "dir",
        "children": {
            "status": _proc_file(status),
            "cmdline": _proc_file(p["cmdline"]),
        },
    }


def _proc_root(state: dict) -> dict:
    children = {str(p["pid"]): _proc_pid_dir(p) for p in state.get("processes", [])}
    children["cpuinfo"] = _proc_file(_PROC_CPUINFO)
    children["meminfo"] = _proc_file(_proc_meminfo_text())
    children["uptime"] = _proc_file(f"{PROC_UPTIME_SECONDS} 0.00")
    return {"type": "dir", "children": children}


def is_proc_path(abs_path: str) -> bool:
    segs = segments(abs_path)
    return bool(segs) and segs[0] == "proc"


# --- 統合ワールドの動的 case_file.sh（P3-04b）---
# 疑似 /proc と同じ方針: filesystem JSON には保存せず、読み取り時に
# mission_progress から動的生成する。Mission 別 state（filesystem に静的な
# case_file.sh を持つ・mission_progress を持たない）とは "mission_progress"
# キーの有無で区別し、移行期の両立を保つ。
WORLD_CASE_FILE_DIR = "/root"
WORLD_CASE_FILE_PATH = f"{WORLD_CASE_FILE_DIR}/{CASE_FILE_NAME}"


def _synth_case_file_node(state: dict) -> dict | None:
    """統合ワールドのアクティブ Mission から `/root/case_file.sh` を合成する。

    `mission_progress` が無い（＝Mission 別 state）場合や、全 Mission クリア済み
    （アクティブ Mission が無い）場合は None を返し、呼び出し側に通常のファイル
    探索へフォールバックさせる。
    """
    mission_progress = state.get("mission_progress")
    if mission_progress is None:
        return None
    mission_id = progress.active_mission_id(mission_progress)
    if mission_id is None:
        return None
    mission = get_mission(mission_id)
    if mission is None:
        return None
    content = (
        "# 事件ファイル: sh case_file.sh で判定する\n"
        f"# 捜査中の事件: {mission.title_ja}\n"
        f"# {mission.description}\n"
    )
    return new_file(content, immutable=True)


def is_dynamic_path(state: dict, abs_path: str) -> bool:
    """読み取り時に合成される（`filesystem` に実体を持たない）パスか。

    疑似 `/proc` と統合ワールドの `case_file.sh` が該当する。書き込み系は実体が
    無いため黙って握り潰されてしまうので、呼び出し側はこれを見て明示的に拒否する。
    """
    if is_proc_path(abs_path):
        return True
    return abs_path == WORLD_CASE_FILE_PATH and _synth_case_file_node(state) is not None


def effective_children(state: dict, abs_path: str, node: dict) -> dict:
    """ディレクトリノードの実効的な children（動的合成エントリを含む）を返す。

    `ls` 等の列挙系コマンドはこの関数経由で children を取得すること。合成結果は
    `state["filesystem"]` には一切書き戻さない（読み取り専用のスナップショット）。
    """
    children = node.get("children", {})
    if abs_path == WORLD_CASE_FILE_DIR:
        synth = _synth_case_file_node(state)
        if synth is not None:
            children = {**children, CASE_FILE_NAME: synth}
    return children


def _walk(node: dict, segs: list[str], current_user: str = "detective") -> dict | None:
    for seg in segs:
        if node.get("type") != "dir":
            return None
        # 子へ降りる前に通行権限を検査する（P3-04a）。拒否は「存在しない」と同じ扱い。
        if not can_traverse(node, current_user):
            return None
        node = node.get("children", {}).get(seg)
        if node is None:
            return None
    # 経路の途中だけでなく、解決済みノード自身のゲートも検査する。ここが無いと
    # 「/root/park を直接指定した ls/cat/touch/mkdir/...」がゲートを素通りしてしまう
    # （get_parent 等が「経路の最後の1つ手前まで」を get_node に渡す形で親を解決するため）。
    if node is not None and not can_traverse(node, current_user):
        return None
    return node


def get_node(state: dict, abs_path: str) -> dict | None:
    """絶対パスのノードを返す。存在しない/途中がディレクトリでなければ None。

    途中のディレクトリ、および解決済みノード自身が `can_traverse` を拒否した場合も
    None（見えない/触れない演出）。`/proc` 配下は processes テーブルから動的生成する
    読み取り専用ツリーで、権限ゲートの対象外のため素通しする。
    """
    segs = segments(abs_path)
    if segs and segs[0] == "proc":
        return _walk(_proc_root(state), segs[1:])
    if abs_path == WORLD_CASE_FILE_PATH:
        synth = _synth_case_file_node(state)
        if synth is not None:
            return synth
        # mission_progress を持たない state（Mission 別 state）は合成しない。
        # 通常探索へフォールスルーし、静的に配置された case_file.sh を返す。
    current_user = state.get("current_user", "detective")
    return _walk(root_node(state), segs, current_user)


def get_parent(state: dict, abs_path: str) -> tuple[dict | None, str | None]:
    """(親ディレクトリノード, 末端名) を返す。親が無い/ディレクトリでなければ (None, name)。"""
    segs = segments(abs_path)
    if not segs:
        return None, None
    parent = get_node(state, "/" + "/".join(segs[:-1]))
    if parent is None or parent.get("type") != "dir":
        return None, segs[-1]
    return parent, segs[-1]


def is_dir(node: dict | None) -> bool:
    return node is not None and node.get("type") == "dir"


def is_file(node: dict | None) -> bool:
    return node is not None and node.get("type") == "file"


def is_link(node: dict | None) -> bool:
    return node is not None and node.get("type") == "link"


def resolve_link(state: dict, node: dict | None, *, max_hops: int = 10) -> dict | None:
    """symlink を実体まで辿る（多段リンク対応）。循環・未解決なら None を返す。"""
    hops = 0
    while node is not None and node.get("type") == "link" and hops < max_hops:
        node = get_node(state, node.get("target", ""))
        hops += 1
    return node


def can_read(node: dict, current_user: str = "detective") -> bool:
    """読み取り権限を検査する。current_user がファイルの owner と一致すれば
    所有者ビット（mode[0]）、一致しなければその他ビット（mode[6]）を見る
    （グループは概念として持たないため owner/other の二値で判定する）。
    """
    mode = node.get("mode", "rw-r--r--")
    owner = node.get("owner", "detective")
    idx = 0 if current_user == owner else 6
    return mode[idx] == "r"


def can_exec(node: dict) -> bool:
    """実行ビットを検査する。デフォルト配置ファイル（immutable）は特例で常に許可
    （Mission1〜4 の case_file.sh は mode に x を持たないため）。Mission 側で
    この特例を外したい場合は immutable=False で配置する（例: Mission5）。
    """
    if node.get("immutable", False):
        return True
    return "x" in node.get("mode", "rw-r--r--")


def can_traverse(node: dict, current_user: str = "detective") -> bool:
    """ディレクトリの通行権限（列挙・cd・再帰探索で子へ降りる）を検査する（P3-04a）。

    mode 未設定は常に True（デフォルト開放ポリシー）。`can_exec` の「immutable
    以外はデフォルト閉鎖」とは意図的に別物: 既存 22 Mission 分のディレクトリノードは
    mode を持たないため、この関数の追加は無影響でなければならない。mode を持つのは
    Part5 統合ワールド（`app/content/missions.py` の `OPEN_DIR_MODE`/`LOCKED_DIR_MODE`）
    の未解放区画だけ。
    dir 以外のノードは常に True（呼び出し側が type を意識せず呼べるようにするため）。
    owner 一致なら owner 側の x ビット（mode[2]）、不一致なら other 側の x ビット
    （mode[8]）を見る（`can_read` と同じ owner/other 二値の考え方）。
    """
    if node.get("type") != "dir":
        return True
    mode = node.get("mode")
    if mode is None:
        return True
    owner = node.get("owner", "detective")
    idx = 0 if current_user == owner else 6
    return mode[idx + 2] == "x"


def new_file(content: str = "", *, immutable: bool = False) -> dict:
    return {
        "type": "file",
        "content": content,
        "mode": "rw-r--r--",
        "owner": "detective",
        "mtime": now_iso(),
        "immutable": immutable,
    }


def new_dir() -> dict:
    return {"type": "dir", "children": {}}


def new_link(target: str) -> dict:
    return {
        "type": "link",
        "target": target,
        "mode": "rwxrwxrwx",
        "owner": "detective",
        "mtime": now_iso(),
    }
