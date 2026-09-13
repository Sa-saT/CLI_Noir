"""やらかし体験室（設計指示書 § 11 ゲーム機能 9。2026-09-13 に Mission29 として採用）。

本編では denylist で禁止している `rm` / `dd` を、**物語上の強要**（犯人に消去を迫られる）
の中で一度だけ本当に実行させる。探偵は犯人の目を盗んで「予備の機械」に繋ぎ替えている
という設定で、Mission 開始時に世界の filesystem を丸ごと退避（backup）し、クリア時
（advance_mission）に戻す。退避中だけ engine が denylist の `rm`/`dd` を通す。

- `state["sandbox"] = {"backup": <filesystem の deepcopy>, "wiped": [...], "dd": bool}`
- 本編の denylist 原則（§ 8）は不変: sandbox が無い state では従来どおり
  `Error: command not allowed`。バイパスは `is_active(state)` の 1 か所だけ。
- commit スナップショット / resume は `sandbox` キーも一緒に保存・復元する
  （退避中のセーブへ戻っても本物の世界が backup に残る）。
"""

import copy

from app.evaluator import fs
from app.evaluator.errors import CommandError
from app.evaluator.registry import command

# sandbox 中だけ許すコマンド（denylist のうち体験させる 2 つ）。
SANDBOX_ONLY = {"rm", "dd"}


def is_active(state: dict) -> bool:
    return bool(state.get("sandbox"))


def enter(state: dict) -> None:
    """世界の filesystem を退避して sandbox を開く（Mission29 解放時のフック）。冪等。"""
    if is_active(state):
        return
    state["sandbox"] = {
        "backup": copy.deepcopy(state["filesystem"]),
        "wiped": [],
        "dd": False,
    }


def leave(state: dict) -> None:
    """退避した filesystem を戻して sandbox を閉じる（クリア時）。何も無ければ no-op。"""
    box = state.pop("sandbox", None)
    if not box:
        return
    state["filesystem"] = box["backup"]
    state["current_path"] = "/root"


@command("rm")
def cmd_rm(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    """`rm [-r|-rf|-f] <path...>`。ディレクトリは -r が要る（実 rm と同じ）。

    engine が sandbox 中にしか dispatch しないため、ここでは sandbox の有無を再検査
    しない（二重の門は `_run_stage` 側に一本化）。
    """
    flags = {ch for tok in argv[1:] if tok.startswith("-") for ch in tok[1:]}
    targets = [tok for tok in argv[1:] if not tok.startswith("-")]
    if not targets:
        raise CommandError("rm: missing operand")
    recursive = "r" in flags or "R" in flags
    out: list[str] = []
    for target in targets:
        abs_path = fs.normalize(state["current_path"], target)
        if fs.is_proc_path(abs_path) or abs_path == fs.WORLD_CASE_FILE_PATH:
            raise CommandError(f"rm: cannot remove '{target}': Permission denied")
        node = fs.get_node(state, abs_path)
        if node is None:
            if "f" in flags:
                continue
            raise CommandError(f"rm: cannot remove '{target}': No such file or directory")
        if node.get("type") == "dir" and not recursive:
            raise CommandError(f"rm: cannot remove '{target}': Is a directory")
        segs = fs.segments(abs_path)
        if not segs:
            # `rm -rf /`: 実機では最近の rm が保護するが、体験室では「全部消える」を見せる
            for name in list(state["filesystem"].keys()):
                out.append(f"removed directory '/{name}'")
                del state["filesystem"][name]
        else:
            parent, name = fs.get_parent(state, abs_path)
            if parent is None:
                raise CommandError(f"rm: cannot remove '{target}': No such file or directory")
            out.extend(_removed_lines(node, abs_path))
            del parent["children"][name]
        state["sandbox"]["wiped"].append(abs_path)
    # 実 rm は黙って消す。-v 相当の行は「消えていく」演出のため常に出す（体験室限定）。
    return out, state


def _removed_lines(node: dict, abs_path: str) -> list[str]:
    if node.get("type") != "dir":
        return [f"removed '{abs_path}'"]
    lines: list[str] = []
    for name, child in sorted(node.get("children", {}).items()):
        lines.extend(_removed_lines(child, f"{abs_path}/{name}"))
    lines.append(f"removed directory '{abs_path}'")
    return lines


@command("dd")
def cmd_dd(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    """`dd if=/dev/zero of=/dev/sdb ...`: 証拠用ディスク（/root/vault にマウントされている
    という設定）をゼロで上書きする。中身は全部消え、空の資料室だけが残る。"""
    opts = dict(tok.split("=", 1) for tok in argv[1:] if "=" in tok)
    src = opts.get("if")
    dst = opts.get("of")
    if src is None or dst is None:
        raise CommandError("dd: missing 'if=' or 'of=' operand")
    if not dst.startswith("/dev/sd"):
        raise CommandError(f"dd: failed to open '{dst}': Permission denied")
    vault = fs.get_node(state, "/root/vault")
    count = 0
    if vault is not None and vault.get("type") == "dir":
        count = len(vault.get("children", {}))
        vault["children"] = {}
    state["sandbox"]["dd"] = True
    return [
        "2048+0 records in",
        "2048+0 records out",
        f"2147483648 bytes (2.1 GB) copied, 4.2 s, 512 MB/s ({count} files lost on {dst})",
    ], state
