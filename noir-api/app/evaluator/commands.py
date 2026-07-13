"""MVP コマンド実装（純粋関数）。

各コマンドは `(state, argv, stdin_lines) -> (stdout_lines, new_state)`。state は engine が
deepcopy 済みを渡すので、その場で書き換えて返してよい。実 OS には触れない
（glob=fnmatch / 正規表現=re。設計指示書 § 0.5）。エラーは CommandError で送出する。
"""

import copy
import fnmatch
import re

from app.evaluator import fs
from app.evaluator.errors import CommandError
from app.evaluator.judge import run_case_file
from app.evaluator.registry import command

# ssh 接続先（設計指示書 § 5）。filesystem は接続時にスタックへ退避して差し替える。
SSH_HOSTS: dict[str, dict] = {
    "amusement_park": {
        "initial_path": "/gate",
        # Mission3 の詳細 FS は実装時に拡張。現状は入口ディレクトリのみ。
        "filesystem": {"gate": {"type": "dir", "children": {}}},
    },
}


def _content_lines(node: dict) -> list[str]:
    content = node.get("content", "")
    if content == "":
        return []
    return content.split("\n")


# --- ナビゲーション ---
@command("ls")
def cmd_ls(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    target = argv[1] if len(argv) > 1 else state["current_path"]
    abs_path = fs.normalize(state["current_path"], target)
    node = fs.get_node(state, abs_path)
    if node is None:
        raise CommandError("Error: path not found")
    if fs.is_file(node):
        return [fs.segments(abs_path)[-1] if fs.segments(abs_path) else abs_path], state
    return sorted(node.get("children", {}).keys()), state


@command("cd")
def cmd_cd(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 2:
        raise CommandError("Error: invalid input")
    abs_path = fs.normalize(state["current_path"], argv[1])
    node = fs.get_node(state, abs_path)
    if not fs.is_dir(node):
        raise CommandError("Error: directory not found")
    state["current_path"] = abs_path
    return [], state


@command("pwd")
def cmd_pwd(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    return [state["current_path"]], state


# --- ファイル作成・読み取り ---
@command("touch")
def cmd_touch(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 2:
        raise CommandError("Error: invalid input")
    abs_path = fs.normalize(state["current_path"], argv[1])
    node = fs.get_node(state, abs_path)
    if node is not None:
        node["mtime"] = fs.now_iso()
        return [], state
    parent, name = fs.get_parent(state, abs_path)
    if parent is None:
        raise CommandError("Error: path not found")
    parent["children"][name] = fs.new_file()
    return [], state


@command("mkdir")
def cmd_mkdir(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 2:
        raise CommandError("Error: invalid input")
    abs_path = fs.normalize(state["current_path"], argv[1])
    if fs.get_node(state, abs_path) is not None:
        raise CommandError("Error: directory already exists")
    parent, name = fs.get_parent(state, abs_path)
    if parent is None:
        raise CommandError("Error: path not found")
    parent["children"][name] = fs.new_dir()
    return [], state


@command("cat", "less")
def cmd_cat(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    files = [a for a in argv[1:] if not a.startswith("-")]
    if not files:
        return stdin, state
    out: list[str] = []
    for f in files:
        node = fs.get_node(state, fs.normalize(state["current_path"], f))
        if not fs.is_file(node):
            raise CommandError("Error: file not found")
        out.extend(_content_lines(node))
    return out, state


@command("echo")
def cmd_echo(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    return [" ".join(argv[1:])], state


@command("clear", "history")
def cmd_noop(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    # 表示制御・履歴はフロント側の責務。evaluator は state を変えない。
    return [], state


# --- 検索 ---
@command("grep", "egrep", "fgrep")
def cmd_grep(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    name = argv[0]
    flags = {a for a in argv[1:] if a.startswith("-")}
    positional = [a for a in argv[1:] if not a.startswith("-")]
    if not positional:
        raise CommandError("Error: invalid input")

    pattern, files = positional[0], positional[1:]
    fixed = name == "fgrep" or "-F" in flags
    ignorecase = "-i" in flags
    invert = "-v" in flags

    warning: list[str] = []
    if name == "egrep":
        warning = ["egrep: warning: egrep is obsolescent; using grep -E"]
    elif name == "fgrep":
        warning = ["fgrep: warning: fgrep is obsolescent; using grep -F"]

    try:
        regex = re.compile(
            re.escape(pattern) if fixed else pattern,
            re.IGNORECASE if ignorecase else 0,
        )
    except re.error as exc:
        raise CommandError("Error: invalid pattern") from exc

    if files:
        lines: list[str] = []
        for f in files:
            node = fs.get_node(state, fs.normalize(state["current_path"], f))
            if not fs.is_file(node):
                raise CommandError("Error: file not found")
            lines.extend(_content_lines(node))
    else:
        lines = stdin

    matched = [ln for ln in lines if bool(regex.search(ln)) != invert]
    return warning + matched, state


@command("find")
def cmd_find(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    start = argv[1] if len(argv) > 1 and not argv[1].startswith("-") else "."
    name_glob: str | None = None
    if "-name" in argv:
        idx = argv.index("-name")
        if idx + 1 < len(argv):
            name_glob = argv[idx + 1]

    abs_start = fs.normalize(state["current_path"], start)
    node = fs.get_node(state, abs_start)
    if node is None:
        raise CommandError("Error: path not found")

    results: list[str] = []

    def walk(path: str, n: dict) -> None:
        basename = fs.segments(path)[-1] if fs.segments(path) else path
        if name_glob is None or fnmatch.fnmatch(basename, name_glob):
            results.append(path)
        if fs.is_dir(n):
            for child_name in sorted(n.get("children", {})):
                child_path = "/" + "/".join([*fs.segments(path), child_name])
                walk(child_path, n["children"][child_name])

    walk(abs_start, node)
    return results, state


# --- SSH / remote ---
@command("ssh")
def cmd_ssh(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 2:
        raise CommandError("Error: invalid input")
    host = argv[1]
    info = SSH_HOSTS.get(host)
    if info is None:
        raise CommandError("Host not found")
    # 現在（local または上位 remote）の FS とパスを退避してから remote FS を載せる。
    stack = state.setdefault("_fs_stack", [])
    stack.append(
        {
            "filesystem": state["filesystem"],
            "current_path": state["current_path"],
            "remote_mode": state["remote_mode"],
            "ssh_host": state["ssh_host"],
        }
    )
    state["filesystem"] = copy.deepcopy(info["filesystem"])
    state["current_path"] = info["initial_path"]
    state["remote_mode"] = True
    state["ssh_host"] = host
    return [f"Connected to {host}"], state


@command("exit")
def cmd_exit(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    stack = state.get("_fs_stack", [])
    if not stack:
        # local での exit は no-op（ガイド文言）。
        return ["Not connected"], state
    prev = stack.pop()
    state["filesystem"] = prev["filesystem"]
    state["current_path"] = prev["current_path"]
    state["remote_mode"] = prev["remote_mode"]
    state["ssh_host"] = prev["ssh_host"]
    return [], state


# --- スクリプト実行 / Mission 判定 ---
@command("sh")
def cmd_sh(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 2:
        raise CommandError("Error: invalid input")
    abs_path = fs.normalize(state["current_path"], argv[1])
    node = fs.get_node(state, abs_path)
    if not fs.is_file(node):
        raise CommandError("Error: file not found")

    basename = fs.segments(abs_path)[-1]
    if basename == "case_file.sh":
        return run_case_file(state)
    # 汎用スクリプト（変数 / if / for）の実行は Mission19 実装時に対応する。
    return [], state
