"""仮想ファイルシステムのパス解決・ノード操作（一元化ヘルパー）。

`filesystem` は「/」直下の子ノード map（例: {"root": {...}}）。「/」自体は暗黙で、
その children が `filesystem` そのもの（同一オブジェクト）を指すため、そこへの追加・
削除は state に反映される。実 OS には一切触れない（設計指示書 § 0.5）。
"""

from datetime import datetime, timezone


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


# --- 動的 case_file.sh（Part5 P3-03/P3-04）---
# 統合ワールドでは `case_file.sh` は常に `/root/case_file.sh` の1本（設計は
# `context/04_task_backlog.md` Part5 背景節・P3-03参照）。`_build_world_fs()`
# （app/content/missions.py）は静的マージ時にどの Mission の `case_file.sh` も
# 深さを問わず除外しており、`filesystem` JSON には保存しない。/proc と同じく
# 読み取り時に動的生成する（全 Mission で本文は同一の定型文なので、アクティブ
# Mission に応じた内容分岐は不要）。旧 Mission 単位フローの state は元々この
# パスに実ノードを持つため、この生成には到達しない（_walk が先に実ノードを返す）。
_DYNAMIC_CASE_FILE_PATH = "/root/case_file.sh"
_CASE_FILE_TEXT = "# 事件ファイル: sh case_file.sh で判定する\n"


def _dynamic_case_file_node() -> dict:
    return _proc_file(_CASE_FILE_TEXT)


def can_traverse(node: dict, current_user: str = "detective") -> bool:
    """ディレクトリの通過（cd で入る・ls/find で降りる等）権限を検査する。

    `mode` が未設定なら常に許可する（デフォルト開放ポリシー。ファイル用
    `can_exec` の「immutable なら常に許可」＝デフォルト閉鎖とは別物。Part5
    P3-04。既存 22 Mission 分のディレクトリノードは mode 未設定のため無影響）。
    設定されている場合は実行ビット（idx 2=owner, 8=other）を見る（`can_read` と
    同じく owner/other の二値判定。グループ概念は持たない）。
    """
    mode = node.get("mode")
    if mode is None:
        return True
    owner = node.get("owner", "detective")
    idx = 2 if current_user == owner else 8
    return mode[idx] == "x"


def _walk(node: dict, segs: list[str], current_user: str) -> dict | None:
    for seg in segs:
        if node.get("type") != "dir":
            return None
        # 子へ降りる前に「現在地」ディレクトリの通過権限を検査する（Part5 P3-04）。
        # 末端（探索対象そのもの）はここではチェックしない — cd 等の呼び出し側が
        # 個別に検査する（見えない/触れない演出を「存在しない」に統一するため）。
        if not can_traverse(node, current_user):
            return None
        node = node.get("children", {}).get(seg)
        if node is None:
            return None
    return node


def get_node(state: dict, abs_path: str) -> dict | None:
    """絶対パスのノードを返す。存在しない/途中がディレクトリでなければ None。

    `/proc` 配下は processes テーブルから動的生成する（読み取り専用）。
    `/root/case_file.sh` も filesystem 内に実ノードが無ければ動的生成する
    （統合ワールドの静的マージが除外しているため。旧 Mission 単位フローは
    実ノードを持つのでこの分岐には到達しない）。
    経路上の未解放ディレクトリ（Part5 P3-04）を通過する場合も None（見えない/
    触れない演出。存在しないのと同じ扱い）。末端ノード自身の通過権限は
    呼び出し側（cmd_cd 等）が個別に検査する。
    """
    current_user = state.get("current_user", "detective")
    segs = segments(abs_path)
    if segs and segs[0] == "proc":
        return _walk(_proc_root(state), segs[1:], current_user)
    node = _walk(root_node(state), segs, current_user)
    if node is None and abs_path == _DYNAMIC_CASE_FILE_PATH:
        return _dynamic_case_file_node()
    return node


def get_parent(state: dict, abs_path: str) -> tuple[dict | None, str | None]:
    """(親ディレクトリノード, 末端名) を返す。

    親が無い/ディレクトリでなければ (None, name)。親ディレクトリ自身が未解放
    （Part5 P3-04）の場合も (None, name)（そこへの書き込み系コマンド — touch /
    mkdir / redirect 等 — は get_parent だけがゲートを担うため、ここで完結させる）。
    """
    segs = segments(abs_path)
    if not segs:
        return None, None
    parent = get_node(state, "/" + "/".join(segs[:-1]))
    if parent is None or parent.get("type") != "dir":
        return None, segs[-1]
    current_user = state.get("current_user", "detective")
    if not can_traverse(parent, current_user):
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
