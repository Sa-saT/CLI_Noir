"""MVP コマンド実装（純粋関数）。

各コマンドは `(state, argv, stdin_lines) -> (stdout_lines, new_state)`。state は engine が
deepcopy 済みを渡すので、その場で書き換えて返してよい。実 OS には触れない
（glob=fnmatch / 正規表現=re。設計指示書 § 0.5）。エラーは CommandError で送出する。
"""

import copy
import fnmatch
import re
from datetime import datetime

from app.evaluator import fs
from app.evaluator.errors import CommandError
from app.evaluator.judge import run_case_file
from app.evaluator.registry import command

def _rfile(content: str) -> dict:
    """remote FS 用のファイルノード（読み取り専用ヒント）。"""
    return {
        "type": "file",
        "content": content,
        "mode": "r--r--r--",
        "owner": "park",
        "mtime": "2026-01-01T00:00:00Z",
        "immutable": True,
    }


# ssh 接続先（設計指示書 § 5）。filesystem は接続時にスタックへ退避して差し替える。
# amusement_park は Mission3 専用。/gate 配下のヒントから Code/Wire/Height を読み取り、
# echo で記録する（判定は judge の汎用 AND-regex。証跡=echo 行）。
SSH_HOSTS: dict[str, dict] = {
    "amusement_park": {
        "initial_path": "/gate",
        "filesystem": {
            "gate": {
                "type": "dir",
                "children": {
                    "booth": {
                        "type": "dir",
                        "children": {
                            "manual.txt": _rfile(
                                "DEFUSE MANUAL\n"
                                "Enter the code printed on the panel.\n"
                                "Code: K3Y9"
                            ),
                        },
                    },
                    "ferris": {
                        "type": "dir",
                        "children": {
                            "wiring.txt": _rfile(
                                "WIRING DIAGRAM\n"
                                "Three wires: red / blue / yellow.\n"
                                "Cut the correct one -> Wire: blue"
                            ),
                        },
                    },
                    "sign": {
                        "type": "dir",
                        "children": {
                            "notice.txt": _rfile(
                                "SAFETY NOTICE\n"
                                "Ride limit for this gate.\n"
                                "Height: 180"
                            ),
                        },
                    },
                    "decoy": {
                        "type": "dir",
                        "children": {
                            "junk.txt": _rfile("popcorn receipts, nothing useful"),
                        },
                    },
                    "case_file.sh": _rfile("# 事件ファイル: sh case_file.sh で判定する\n"),
                },
            }
        },
    },
}


def _content_lines(node: dict) -> list[str]:
    content = node.get("content", "")
    if content == "":
        return []
    return content.split("\n")


def _read_input(state: dict, files: list[str], stdin: list[str]) -> list[str]:
    """ファイル引数があればその内容を連結、無ければ stdin を入力行として返す。

    cat/grep/sort/uniq/wc/head/tail/cut のファイル読み取りをここに集約し、
    権限検査（mode の所有者読み取りビット）も一箇所で行う。
    """
    if not files:
        return list(stdin)
    lines: list[str] = []
    for f in files:
        node = fs.get_node(state, fs.normalize(state["current_path"], f))
        if not fs.is_file(node):
            raise CommandError("Error: file not found")
        if not fs.can_read(node):
            raise CommandError("Error: permission denied")
        lines.extend(_content_lines(node))
    return lines


def _flag_chars(argv: list[str]) -> set[str]:
    """`-rn` のような連結ブールフラグを文字集合へ展開する（数値付きは対象外）。"""
    chars: set[str] = set()
    for a in argv[1:]:
        if a.startswith("-") and len(a) > 1 and not a[1].isdigit():
            chars.update(a[1:])
    return chars


def _operands(argv: list[str]) -> list[str]:
    """オプションでない引数（ファイル名等）。単独の `-`（stdin）は除く。"""
    return [a for a in argv[1:] if not a.startswith("-")]


def _format_mtime(mtime: str) -> str:
    try:
        dt = datetime.fromisoformat(mtime.replace("Z", "+00:00"))
    except ValueError:
        return mtime
    return dt.strftime("%b %d %H:%M")


def _ls_long_line(name: str, node: dict) -> str:
    is_dir = node.get("type") == "dir"
    mode = node.get("mode", "rw-r--r--")
    perm = ("d" if is_dir else "-") + mode
    owner = node.get("owner", "detective")
    size = 0 if is_dir else len(node.get("content", ""))
    date = _format_mtime(node.get("mtime", "2026-01-01T00:00:00Z"))
    return f"{perm} 1 {owner} {owner} {size:>6} {date} {name}"


# --- ナビゲーション ---
@command("ls")
def cmd_ls(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    flags = _flag_chars(argv)
    long = "l" in flags
    operands = _operands(argv)
    target = operands[0] if operands else state["current_path"]
    abs_path = fs.normalize(state["current_path"], target)
    node = fs.get_node(state, abs_path)
    if node is None:
        raise CommandError("Error: path not found")

    if fs.is_file(node):
        name = fs.segments(abs_path)[-1] if fs.segments(abs_path) else abs_path
        return ([_ls_long_line(name, node)] if long else [name]), state

    names = sorted(node.get("children", {}).keys())
    if not long:
        return names, state
    return [_ls_long_line(n, node["children"][n]) for n in names], state


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
    if fs.is_proc_path(abs_path):
        raise CommandError("Permission denied")
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
    if fs.is_proc_path(abs_path):
        raise CommandError("Permission denied")
    if fs.get_node(state, abs_path) is not None:
        raise CommandError("Error: directory already exists")
    parent, name = fs.get_parent(state, abs_path)
    if parent is None:
        raise CommandError("Error: path not found")
    parent["children"][name] = fs.new_dir()
    return [], state


def _mode_from_numeric(spec: str) -> str:
    """`644` 等の数値モードを 9 文字の rwx 表現へ変換する。"""
    bits = ""
    for digit in spec:
        n = int(digit)
        bits += ("r" if n & 4 else "-") + ("w" if n & 2 else "-") + ("x" if n & 1 else "-")
    return bits


_CHMOD_CLASS_OFFSET = {"u": 0, "g": 3, "o": 6}


def _apply_symbolic_mode(mode: str, spec: str) -> str:
    """`+r` / `u+x` / `-w` 等のシンボリックモードを既存 mode に適用する。

    クラス接頭辞（u/g/o）省略時は全クラス（設計: Mission参照ファイルの
    「u/g/o 接頭辞は省略可=全クラス」に対応）。
    """
    m = re.fullmatch(r"([ugoa]*)([+-])([rwx]+)", spec)
    if not m:
        raise CommandError("Error: invalid input")
    classes, op, perms = m.groups()
    target_classes = {"u", "g", "o"} if not classes or "a" in classes else set(classes)

    mode_chars = list(mode)
    for cls in target_classes:
        offset = _CHMOD_CLASS_OFFSET[cls]
        for i, p in enumerate("rwx"):
            if p in perms:
                mode_chars[offset + i] = p if op == "+" else "-"
    return "".join(mode_chars)


@command("chmod")
def cmd_chmod(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = argv[1:]
    if len(operands) < 2:
        raise CommandError("Error: invalid input")

    spec, *paths = operands
    for path in paths:
        abs_path = fs.normalize(state["current_path"], path)
        node = fs.get_node(state, abs_path)
        if node is None:
            raise CommandError("Error: path not found")
        current_mode = node.get("mode", "rw-r--r--")
        if re.fullmatch(r"[0-7]{3}", spec):
            node["mode"] = _mode_from_numeric(spec)
        else:
            node["mode"] = _apply_symbolic_mode(current_mode, spec)
    return [], state


@command("cat", "less")
def cmd_cat(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    files = _operands(argv)
    return _read_input(state, files, stdin), state


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

    lines = _read_input(state, files, stdin)

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


# --- テキスト処理（Level 5） ---
def _num_key(line: str) -> float:
    """行頭の数値を取り出す（sort -n 用）。数値が無ければ 0。"""
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", line)
    return float(m.group(1)) if m else 0.0


@command("sort")
def cmd_sort(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    flags = _flag_chars(argv)
    lines = _read_input(state, _operands(argv), stdin)

    if "n" in flags:
        result = sorted(lines, key=_num_key, reverse="r" in flags)
    else:
        result = sorted(lines, reverse="r" in flags)

    if "u" in flags:  # sort -u: 連続重複を除去
        deduped: list[str] = []
        for ln in result:
            if not deduped or deduped[-1] != ln:
                deduped.append(ln)
        result = deduped
    return result, state


@command("uniq")
def cmd_uniq(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    flags = _flag_chars(argv)
    lines = _read_input(state, _operands(argv), stdin)

    # 隣接する重複のみをまとめる（実 uniq と同じ。事前 sort 前提）。
    groups: list[list] = []  # [line, count]
    for ln in lines:
        if groups and groups[-1][0] == ln:
            groups[-1][1] += 1
        else:
            groups.append([ln, 1])

    count_flag = "c" in flags
    dup_only = "d" in flags
    out: list[str] = []
    for ln, count in groups:
        if dup_only and count < 2:
            continue
        out.append(f"{count:7d} {ln}" if count_flag else ln)
    return out, state


@command("wc")
def cmd_wc(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    flags = _flag_chars(argv)
    files = _operands(argv)
    lines = _read_input(state, files, stdin)

    n_lines = len(lines)
    n_words = sum(len(ln.split()) for ln in lines)
    n_bytes = len("\n".join(lines))

    parts: list[int] = []
    if "l" in flags:
        parts.append(n_lines)
    if "w" in flags:
        parts.append(n_words)
    if "c" in flags:
        parts.append(n_bytes)
    if not parts:  # 無指定は行/語/バイトを併記
        parts = [n_lines, n_words, n_bytes]

    text = " ".join(str(p) for p in parts)
    if len(files) == 1:
        text = f"{text} {files[0]}"
    return [text], state


def _parse_n(argv: list[str], default: int = 10) -> tuple[int, list[str]]:
    """head/tail の `-n N` / `-N` と入力ファイルを解釈する。"""
    n = default
    files: list[str] = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "-n":
            i += 1
            if i < len(argv):
                try:
                    n = int(argv[i])
                except ValueError as exc:
                    raise CommandError("Error: invalid input") from exc
        elif re.fullmatch(r"-\d+", a):
            n = int(a[1:])
        elif not a.startswith("-"):
            files.append(a)
        i += 1
    return n, files


@command("head")
def cmd_head(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    n, files = _parse_n(argv)
    lines = _read_input(state, files, stdin)
    return lines[:n], state


@command("tail")
def cmd_tail(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    n, files = _parse_n(argv)
    lines = _read_input(state, files, stdin)
    return (lines[-n:] if n > 0 else []), state


def _parse_ranges(spec: str, maxn: int) -> list[int]:
    """cut の LIST（`1` / `1,3` / `1-3` / `2-` / `-3`）を 1 始まりの位置列へ。"""
    indices: list[int] = []
    for part in spec.split(","):
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            start = int(a) if a else 1
            end = int(b) if b else maxn
            indices.extend(range(start, end + 1))
        else:
            indices.append(int(part))
    return indices


@command("cut")
def cmd_cut(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    delim = "\t"
    field_spec: str | None = None
    char_spec: str | None = None
    files: list[str] = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "-d":
            i += 1
            delim = argv[i] if i < len(argv) else "\t"
        elif a.startswith("-d"):
            delim = a[2:]
        elif a == "-f":
            i += 1
            field_spec = argv[i] if i < len(argv) else None
        elif a.startswith("-f"):
            field_spec = a[2:]
        elif a == "-c":
            i += 1
            char_spec = argv[i] if i < len(argv) else None
        elif a.startswith("-c"):
            char_spec = a[2:]
        elif not a.startswith("-"):
            files.append(a)
        i += 1

    if field_spec is None and char_spec is None:
        raise CommandError("Error: invalid input")

    lines = _read_input(state, files, stdin)
    out: list[str] = []
    try:
        for ln in lines:
            if char_spec is not None:
                idxs = _parse_ranges(char_spec, len(ln))
                out.append("".join(ln[j - 1] for j in idxs if 1 <= j <= len(ln)))
            elif delim not in ln:  # 区切りが無い行はそのまま（GNU cut 既定）
                out.append(ln)
            else:
                fields = ln.split(delim)
                idxs = sorted({j for j in _parse_ranges(field_spec, len(fields))})
                out.append(delim.join(fields[j - 1] for j in idxs if 1 <= j <= len(fields)))
    except ValueError as exc:
        raise CommandError("Error: invalid input") from exc
    return out, state


# --- プロセス管理（Level 6） ---
@command("ps")
def cmd_ps(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    processes = state.get("processes", [])
    lines = ["USER       PID STAT COMMAND"]
    for p in processes:
        lines.append(f"{p['user']:<10} {p['pid']:>3} {p.get('state', 'S'):<4} {p['cmdline']}")
    return lines, state


@command("kill")
def cmd_kill(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 2:
        raise CommandError("Error: invalid input")
    try:
        pid = int(argv[1])
    except ValueError as exc:
        raise CommandError("Error: invalid input") from exc

    processes = state.get("processes", [])
    idx = next((i for i, p in enumerate(processes) if p["pid"] == pid), None)
    if idx is None:
        raise CommandError("Error: no such process")

    if processes[idx].get("protected", False):
        # 正規プロセスは削除しない（間違い探し。即失敗にせず警告で巻き戻す）。
        return ["Warning: you stopped a legitimate process"], state

    del processes[idx]
    return [f"[{pid}] terminated"], state


@command("free")
def cmd_free(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    # /proc/meminfo と同じ定数から算出する（「ps/free も /proc を読んでいる」の
    # タネ明かし。Mission7）。
    total = fs.PROC_MEM_TOTAL_KB
    used = fs.PROC_MEM_USED_KB
    free_kb = total - used
    header = "              total        used        free"
    row = f"Mem:     {total:>10} {used:>10} {free_kb:>10}"
    return [header, row], state


@command("uptime")
def cmd_uptime(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    seconds = fs.PROC_UPTIME_SECONDS
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return [f"up {hours} hours, {minutes} minutes"], state


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
    if not fs.can_exec(node):
        raise CommandError("Error: permission denied")

    basename = fs.segments(abs_path)[-1]
    if basename == "case_file.sh":
        return run_case_file(state)
    # 汎用スクリプト（変数 / if / for）の実行は Mission19 実装時に対応する。
    return [], state
