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


def get_node(state: dict, abs_path: str) -> dict | None:
    """絶対パスのノードを返す。存在しない/途中がディレクトリでなければ None。"""
    node = root_node(state)
    for seg in segments(abs_path):
        if node.get("type") != "dir":
            return None
        node = node.get("children", {}).get(seg)
        if node is None:
            return None
    return node


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


def can_read(node: dict) -> bool:
    """所有者の読み取りビット（mode[0]=='r'）を検査する。"""
    return node.get("mode", "rw-r--r--")[0] == "r"


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
