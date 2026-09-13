"""Tab 補完（設計指示書 § 7 補完フレーム / DESIGN.md § 10-4）。

フロントは仮想 FS を知らないため、`complete` フレームで受けた行とカーソル位置から
サーバーが候補を返す。純粋関数・state を変更しない。

補完の種類（bash と同じ考え方）:
  - パイプ段の先頭の単語 → コマンド名（解放済みのものだけ。未解放は候補に出さない）
  - `git ` の直後 → サブコマンド（status / add / commit / push）
  - それ以外 → パス（current_path 基準。権限ゲートで見えない区画は候補に出さない）

`replace_from` は行内の置換開始位置（bash と同じく、パスは最後の `/` 以降の
1 セグメントだけを置き換える）。候補にはディレクトリなら末尾 `/` を付ける。
"""

from app.content.missions import BASE_COMMANDS, all_missions, mission_index
from app.evaluator import fs, progress
from app.evaluator.allowlist import ALLOWLIST
from app.evaluator.registry import get_command

_GIT_SUBCOMMANDS = ["add", "commit", "push", "status"]
# Mission の allowed_commands に載らないが最初から使えるシェルの基本操作
_ALWAYS_AVAILABLE = ["history", "clear", "exit"]
# 単語の区切り（空白 + シェルの演算子）。引用符の中は _current_word が別扱いする。
_SEPARATORS = " \t|;<>&"


def mission_commands(state: dict) -> list[str]:
    """解放済み Mission の allowed_commands の和（BASE + 捜査中までの各 Mission の extra）。

    探偵ランク（app/evaluator/rank.py）はこれの最高レベルで決まる。
    """
    active = progress.active_mission_id(state["mission_progress"])
    # 「まだ手を付けていない Mission」の判定は id の大小ではなく _DEFS の並び順
    # （プレイ順序）で行う（Mission23 以降の挿入で id とプレイ順序がずれるため）。
    active_index = mission_index(active) if active is not None else None
    names: dict[str, None] = {cmd: None for cmd in BASE_COMMANDS}
    for i, mission in enumerate(all_missions()):
        if active_index is not None and i > active_index:
            continue
        for cmd in mission.extra_commands:
            names.setdefault(cmd, None)
    return list(names)


def released_commands(state: dict) -> list[str]:
    """今のプレイヤーが打てるコマンド名（補完候補）。

    mission_commands + 最初から使える基本操作。allowlist に無いもの・evaluator
    未実装のものは候補に出さない（打っても動かないため）。
    """
    names = [*mission_commands(state), *_ALWAYS_AVAILABLE]
    return sorted(
        {n for n in names if n in ALLOWLIST and get_command(n) is not None}
    )


def _open_quote_index(before: str) -> int | None:
    """カーソルが引用符の中にあるなら、その開き引用符の位置を返す。"""
    quote: str | None = None
    opened: int | None = None
    for i, ch in enumerate(before):
        if quote is None and ch in ('"', "'"):
            quote, opened = ch, i
        elif ch == quote:
            quote, opened = None, None
    return opened


def _current_word(before: str) -> tuple[int, str, bool]:
    """カーソル前の文字列から、補完対象の単語の開始位置・本文・先頭単語かを返す。

    引用符の中なら（`cat "top sec`）開き引用符の直後から単語とみなす（空白を含む
    名前を補完できるように。bash と同じ）。
    """
    opened = _open_quote_index(before)
    if opened is not None:
        start = opened + 1
        head = before[:opened].rstrip()
        return start, before[start:], head == "" or head[-1] in "|;&"
    start = len(before)
    while start > 0 and before[start - 1] not in _SEPARATORS:
        start -= 1
    word = before[start:]
    # 直前の非空白トークンを探して「段の先頭か」を判定する
    head = before[:start].rstrip()
    is_first = head == "" or head[-1] in "|;&"
    return start, word, is_first


def _previous_token(before: str, start: int) -> str:
    head = before[:start].rstrip()
    if not head or head[-1] in "|;&":
        return ""
    tail = len(head)
    i = tail
    while i > 0 and head[i - 1] not in _SEPARATORS:
        i -= 1
    return head[i:tail]


def _path_candidates(state: dict, word: str) -> tuple[list[str], int]:
    """パス補完。戻り値は (候補, 単語内での置換開始オフセット)。"""
    slash = word.rfind("/")
    dir_part = word[: slash + 1] if slash >= 0 else ""
    prefix = word[slash + 1 :]
    base = fs.normalize(state["current_path"], dir_part or ".")
    node = fs.get_node(state, base)
    if node is None or node.get("type") != "dir":
        return [], slash + 1
    children = fs.effective_children(state, base, node)
    current_user = state.get("current_user", "detective")
    names: list[str] = []
    for name in sorted(children):
        if not name.startswith(prefix):
            continue
        # 隠しファイルは明示的に "." から打ち始めたときだけ（bash と同じ）
        if name.startswith(".") and not prefix.startswith("."):
            continue
        child = children[name]
        if child.get("type") == "dir":
            if not fs.can_traverse(child, current_user):
                continue  # 未解放区画は見えない
            names.append(name + "/")
        else:
            names.append(name)
    return names, slash + 1


def complete(state: dict, line: str, cursor: int) -> tuple[list[str], int]:
    """候補と置換開始位置（行内オフセット）を返す。候補が無ければ候補は空リスト。"""
    cursor = max(0, min(cursor, len(line)))
    before = line[:cursor]
    start, word, is_first = _current_word(before)

    if is_first:
        prefix = word
        candidates = [c for c in released_commands(state) if c.startswith(prefix)]
        return candidates, start

    previous = _previous_token(before, start)
    if previous == "git":
        return [c for c in _GIT_SUBCOMMANDS if c.startswith(word)], start

    names, offset = _path_candidates(state, word)
    return names, start + offset
