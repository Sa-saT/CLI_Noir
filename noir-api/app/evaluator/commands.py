"""MVP コマンド実装（純粋関数）。

各コマンドは `(state, argv, stdin_lines) -> (stdout_lines, new_state)`。state は engine が
deepcopy 済みを渡すので、その場で書き換えて返してよい。実 OS には触れない
（glob=fnmatch / 正規表現=re。設計指示書 § 0.5）。エラーは CommandError で送出する。
"""

import copy
import difflib
import fnmatch
import hashlib
import re
from datetime import datetime

from app.content.missions import get_mission
from app.evaluator import fs, progress, script
from app.evaluator.allowlist import ALLOWLIST, DENYLIST
from app.evaluator.env import env_for
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
        "required_mission_id": 3,
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
    # ghost.example は Mission12 専用（設計指示書 § 5 で未定だった接続先を確定。
    # 2026-07-20）。/den 配下に黒幕の指示書 + デコイ。dig で判明する IP でも
    # 接続できるよう別名登録する。
    "ghost.example": {
        "required_mission_id": 12,
        "initial_path": "/den",
        "filesystem": {
            "den": {
                "type": "dir",
                "children": {
                    "evidence": {
                        "type": "dir",
                        "children": {
                            "orders.txt": _rfile(
                                "BOSS: Selene Vance\n"
                                "ORDERS: silence the informant before midnight"
                            ),
                            "decoy.txt": _rfile("routine chatter, nothing useful"),
                        },
                    },
                    "case_file.sh": _rfile("# 事件ファイル: sh case_file.sh で判定する\n"),
                },
            }
        },
    },
    # サーバー編（Mission26〜28。バックエンド_コマンド機能仕様 § 5c、2026-09-13 確定）。
    # Mission26/27/28 はまだ _DEFS に無いため required_mission_id は未来の id を指す
    # （cmd_ssh 側で「未知 mission_id = 未解放」として扱うので、実装が揃うまでは
    # 誰も到達できない予約済みホストとして安全に存在できる）。
    "archive_node": {
        "required_mission_id": 26,
        "initial_path": "/srv",
        "hostname": "archive-node-01",
        "uname": (
            "Linux archive-node-01 6.1.0-18-amd64 #1 SMP Debian 6.1.76-1 x86_64 GNU/Linux"
        ),
        "disk": [
            {"fs": "/dev/sda1", "size": "40G", "used": "12G", "avail": "26G", "pct": 32,
             "mount": "/"},
            {"fs": "/dev/sdb1", "size": "20G", "used": "19.6G", "avail": "400M", "pct": 98,
             "mount": "/var"},
        ],
        "sizes": {
            "/var/log/spool.log": "17G",
            "/var/log/syslog": "220M",
            "/var/log/auth.log": "12M",
        },
        "ip": [{"iface": "eth0", "addr": "192.168.10.5/24"}],
        "metadata": None,
        "cron_jobs": [
            {"schedule": "0 2 * * *", "command": "/usr/local/bin/backup.sh",
             "malicious": False},
            {"schedule": "*/30 * * * *", "command": "/usr/bin/healthcheck.sh",
             "malicious": False},
        ],
        "services": {
            "archive-indexer": {
                "state": "failed",
                "description": "Archive indexer",
                "port": None,
                "journal": [
                    "Mar 03 02:14:05 archive-node-01 archive-indexer[812]: "
                    "indexing /srv/backup",
                    "Mar 03 02:14:07 archive-node-01 archive-indexer[812]: "
                    "write /var/lib/index/db: No space left on device",
                    "Mar 03 02:14:07 archive-node-01 systemd[1]: "
                    "archive-indexer.service: Failed with result 'exit-code'.",
                ],
            },
            "sshd": {
                "state": "active",
                "description": "OpenSSH server",
                "port": 22,
                "journal": [
                    "Mar 03 02:00:00 archive-node-01 sshd[900]: "
                    "Server listening on 0.0.0.0 port 22.",
                ],
            },
            "backup": {
                "state": "active",
                "description": "Nightly backup sync",
                "port": None,
                "journal": [
                    "Mar 03 02:00:01 archive-node-01 backup: "
                    "starting nightly sync to corp_server",
                    "Mar 03 02:00:02 archive-node-01 backup: "
                    "ssh: connect to host corp_server port 22: Connection refused",
                    "Mar 03 02:00:02 archive-node-01 backup: sync failed",
                ],
            },
        },
        "filesystem": {
            "srv": {
                "type": "dir",
                "children": {
                    "backup": {
                        "type": "dir",
                        "children": {
                            "backup-2026-09-11.tar.gz": _rfile("BACKUP PLACEHOLDER 2026-09-11"),
                            "backup-2026-09-12.tar.gz": _rfile("BACKUP PLACEHOLDER 2026-09-12"),
                        },
                    },
                    "case_file.sh": _rfile("# 事件ファイル: sh case_file.sh で判定する\n"),
                },
            },
            "var": {
                "type": "dir",
                "children": {
                    "log": {
                        "type": "dir",
                        "children": {
                            "spool.log": _rfile(
                                "spool: queued job 4471 for corp_server\n"
                                "spool: queued job 4472 for corp_server\n"
                                "spool: disk write failed: No space left on device"
                            ),
                            "syslog": _rfile(
                                "Mar 03 02:00:00 archive-node-01 systemd[1]: "
                                "Started Archive indexer."
                            ),
                            "auth.log": _rfile(
                                "Mar 03 02:00:00 archive-node-01 sshd[900]: "
                                "Accepted publickey for park"
                            ),
                        },
                    },
                },
            },
            "etc": {
                "type": "dir",
                "children": {
                    "os-release": _rfile(
                        'PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\n'
                        'NAME="Debian GNU/Linux"\n'
                        'VERSION_ID="12"'
                    ),
                },
            },
        },
    },
    "corp_server": {
        "required_mission_id": 27,
        "initial_path": "/opt/app",
        "hostname": "corp-web-01",
        "uname": "Linux corp-web-01 6.8.0-31-generic #31-Ubuntu SMP x86_64 GNU/Linux",
        "disk": [
            {"fs": "/dev/sda1", "size": "40G", "used": "16G", "avail": "22G", "pct": 41,
             "mount": "/"},
        ],
        "sizes": {
            "/var/log/app.log": "340M",
            "/var/backups": "1.8G",
        },
        "ip": [{"iface": "eth0", "addr": "10.0.3.17/24"}],
        "metadata": {
            "instance-id": "i-0f3e9a7c2b1d4e5f6",
            "region": "ap-northeast-1",
            "local-ipv4": "10.0.3.17",
            "instance-type": "t3.small",
        },
        "cron_jobs": [
            {"schedule": "0 3 * * *", "command": "/usr/bin/certbot renew", "malicious": False},
        ],
        "services": {
            "app-web": {
                "state": "active",
                "description": "Company web app",
                "port": 8080,
                "journal": [
                    "Mar 03 03:00:00 corp-web-01 app-web[500]: listening on 0.0.0.0:8080",
                ],
            },
            "sshd": {
                "state": "failed",
                "description": "OpenSSH server",
                "port": 22,
                "journal": [
                    "Mar 03 03:00:01 corp-web-01 sshd: "
                    "/etc/ssh/sshd_config: line 12: Bad configuration option",
                    "Mar 03 03:00:01 corp-web-01 systemd[1]: "
                    "sshd.service: Failed with result 'exit-code'.",
                ],
            },
            "backdoor-relay": {
                "state": "active",
                "description": "relay",
                "port": 4444,
                "journal": [
                    "Mar 03 03:00:02 corp-web-01 relay: listening on 0.0.0.0:4444",
                    "Mar 03 03:00:02 corp-web-01 relay: forwarding to 10.66.6.6",
                ],
            },
        },
        "filesystem": {
            "opt": {
                "type": "dir",
                "children": {
                    "app": {
                        "type": "dir",
                        "children": {
                            "app.py": _rfile("# app placeholder\n"),
                            "README.txt": _rfile("Company web app.\n"),
                            "case_file.sh": _rfile("# 事件ファイル: sh case_file.sh で判定する\n"),
                        },
                    },
                },
            },
            "var": {
                "type": "dir",
                "children": {
                    "backups": {
                        "type": "dir",
                        "children": {
                            "backup-2026-09-11.tar.gz": _rfile("BACKUP PLACEHOLDER 2026-09-11"),
                            "backup-2026-09-12.tar.gz": _rfile("BACKUP PLACEHOLDER 2026-09-12"),
                        },
                    },
                    "log": {
                        "type": "dir",
                        "children": {
                            "app.log": _rfile("app: started on :8080\napp: healthy"),
                        },
                    },
                },
            },
            "etc": {
                "type": "dir",
                "children": {
                    "os-release": _rfile(
                        'PRETTY_NAME="Ubuntu 24.04 LTS"\nNAME="Ubuntu"\nVERSION_ID="24.04"'
                    ),
                },
            },
        },
    },
}
SSH_HOSTS["10.66.6.6"] = SSH_HOSTS["ghost.example"]


def current_host_def(state: dict) -> dict | None:
    """remote_mode 中の接続先ホスト定義（`SSH_HOSTS[ssh_host]`）を返す。local なら None。"""
    if not state.get("remote_mode"):
        return None
    return SSH_HOSTS.get(state.get("ssh_host"))


def service_state(state: dict, host: str, name: str) -> dict | None:
    """`host` の `services[name]` に `state["remote_services"][host][name]`
    （`systemctl start/stop/restart` の記録）を重ねたサービス定義を返す。
    ホスト自体、またはそのサービス名が無ければ None。
    """
    host_info = SSH_HOSTS.get(host)
    if host_info is None:
        return None
    base = host_info.get("services", {}).get(name)
    if base is None:
        return None
    merged = dict(base)
    merged.update(state.get("remote_services", {}).get(host, {}).get(name, {}))
    return merged


def _content_lines(node: dict) -> list[str]:
    content = node.get("content", "")
    if content == "":
        return []
    return content.split("\n")


def _read_input(state: dict, files: list[str], stdin: list[str]) -> list[str]:
    """ファイル引数があればその内容を連結、無ければ stdin を入力行として返す。

    cat/grep/sort/uniq/wc/head/tail/cut のファイル読み取りをここに集約し、
    シンボリックリンクの解決と権限検査（current_user と owner に基づく
    読み取りビット）も一箇所で行う。
    """
    if not files:
        return list(stdin)
    current_user = state.get("current_user", "detective")
    lines: list[str] = []
    for f in files:
        node = fs.get_node(state, fs.normalize(state["current_path"], f))
        if fs.is_link(node):
            node = fs.resolve_link(state, node)
        if not fs.is_file(node):
            raise CommandError("Error: file not found")
        if not fs.can_read(node, current_user):
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
    node_type = node.get("type")
    prefix = {"dir": "d", "link": "l"}.get(node_type, "-")
    mode = node.get("mode", "rwxrwxrwx" if node_type == "link" else "rw-r--r--")
    perm = prefix + mode
    owner = node.get("owner", "detective")
    if node_type == "link":
        size = len(node.get("target", ""))
        label = f"{name} -> {node.get('target', '')}"
    elif node_type == "dir":
        size = 0
        label = name
    else:
        size = len(node.get("content", ""))
        label = name
    date = _format_mtime(node.get("mtime", "2026-01-01T00:00:00Z"))
    return f"{perm} 1 {owner} {owner} {size:>6} {date} {label}"


# --- ナビゲーション ---
@command("ls")
def cmd_ls(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    flags = _flag_chars(argv)
    long = "l" in flags
    operands = _operands(argv)
    # 複数ターゲット対応（glob 展開で `ls case_*` が複数ファイル名になるため）。
    targets = operands if operands else [state["current_path"]]
    current_user = state.get("current_user", "detective")

    out: list[str] = []
    for target in targets:
        abs_path = fs.normalize(state["current_path"], target)
        node = fs.get_node(state, abs_path)
        if node is None:
            raise CommandError("Error: path not found")

        if fs.is_file(node) or fs.is_link(node):
            name = fs.segments(abs_path)[-1] if fs.segments(abs_path) else abs_path
            out.append(_ls_long_line(name, node) if long else name)
        else:
            # 統合ワールドの動的合成エントリ（/root/case_file.sh 等）を含めた
            # 実効的な children から列挙する（P3-04b）。
            children = fs.effective_children(state, abs_path, node)
            # 通行権限（P3-04a）を通らない子ディレクトリは一覧から除外する。
            names = sorted(
                n for n, child in children.items() if fs.can_traverse(child, current_user)
            )
            if long:
                out.extend(_ls_long_line(n, children[n]) for n in names)
            else:
                out.extend(names)
    return out, state


def home_dir(state: dict) -> str:
    """現在のコンテキスト（local/remote）での $HOME 相当パスを返す。

    ssh 接続中は env_vars["HOME"] が local のまま（cmd_ssh は env_vars を退避・
    差し替えしないため）なので、接続先のログインディレクトリ（initial_path）を
    使う。引数無し `cd` と engine の `~` 展開が共用する（UX-01a）。
    """
    if state.get("remote_mode"):
        host_info = SSH_HOSTS.get(state.get("ssh_host"))
        return host_info["initial_path"] if host_info is not None else "/"
    return env_for(state).get("HOME", "/root")


@command("cd")
def cmd_cd(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    show_path = False
    if len(argv) < 2:
        # 引数無し cd は $HOME へ移動する（実 bash と同じ挙動。P3-07 / BUG-02）。
        target = home_dir(state)
    elif argv[1] == "-":
        # `cd -` は OLDPWD へ戻り、実 bash と同じく移動先を 1 行表示する（UX-01a）。
        oldpwd = env_for(state).get("OLDPWD")
        if oldpwd is None:
            raise CommandError("Error: directory not found")
        target = oldpwd
        show_path = True
    else:
        target = argv[1]
    abs_path = fs.normalize(state["current_path"], target)
    node = fs.get_node(state, abs_path)
    # 解決先ディレクトリ自身のゲート（P3-04a）は fs.get_node が見る。
    if not fs.is_dir(node):
        raise CommandError("Error: directory not found")
    env_for(state)["OLDPWD"] = state["current_path"]
    state["current_path"] = abs_path
    return ([abs_path] if show_path else []), state


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
    # $VAR/$? の展開は engine.evaluate() が呼び出し前に一括で行う（P2-18）。
    return [" ".join(argv[1:])], state


@command("clear")
def cmd_clear(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    # 表示制御はフロント側の責務。evaluator は state を変えない。
    return [], state


@command("history")
def cmd_history(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    # Mission15 は「情報屋の履歴」を演出として見せるため MissionDef.informant_history
    # があればそれを優先する。無ければ実 bash と同じく自分の操作履歴（command_log）を
    # `%5d  cmd` 書式で表示する（UX-01a）。実行中の history 自身は engine が成功後に
    # append するためまだ command_log に無く、含めない。
    mission_id = progress.active_mission_id(state["mission_progress"])
    mission = get_mission(mission_id) if mission_id else None
    informant_history = mission.informant_history if mission else None
    if informant_history:
        return [f"{i + 1}  {cmd}" for i, cmd in enumerate(informant_history)], state
    command_log = state.get("command_log", [])
    return [f"{i + 1:5d}  {cmd}" for i, cmd in enumerate(command_log)], state


# --- 検索 ---
def _walk_files(state: dict, abs_dir: str):
    """ディレクトリ配下の全ファイル（symlink は辿らず素通し）を再帰列挙する。

    通行権限（P3-04a）を通らない子ディレクトリはスキップする（降りない・列挙しない）。
    """
    node = fs.get_node(state, abs_dir)
    if not fs.is_dir(node):
        return
    current_user = state.get("current_user", "detective")
    for name in sorted(node.get("children", {}).keys()):
        child = node["children"][name]
        if fs.is_dir(child) and not fs.can_traverse(child, current_user):
            continue
        child_path = fs.normalize(abs_dir, name)
        if fs.is_dir(child):
            yield from _walk_files(state, child_path)
        else:
            yield child_path


@command("grep", "egrep", "fgrep")
def cmd_grep(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    name = argv[0]
    flags = {a for a in argv[1:] if a.startswith("-")}
    positional = [a for a in argv[1:] if not a.startswith("-")]
    if not positional:
        raise CommandError("Error: invalid input")

    pattern, targets = positional[0], positional[1:]
    fixed = name == "fgrep" or "-F" in flags
    ignorecase = "-i" in flags
    invert = "-v" in flags
    recursive = "-r" in flags or "-R" in flags

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

    if recursive:
        if not targets:
            raise CommandError("Error: invalid input")
        current_user = state.get("current_user", "detective")
        matched: list[str] = []
        stderr = state.setdefault("_stderr", [])
        for target in targets:
            abs_start = fs.normalize(state["current_path"], target)
            for file_path in _walk_files(state, abs_start):
                node = fs.get_node(state, file_path)
                if fs.is_link(node):
                    node = fs.resolve_link(state, node)
                if not fs.is_file(node):
                    continue
                if not fs.can_read(node, current_user):
                    stderr.append(f"Error: permission denied: {file_path}")
                    continue
                for ln in _content_lines(node):
                    if bool(regex.search(ln)) != invert:
                        matched.append(f"{file_path}:{ln}")
        return warning + matched, state

    lines = _read_input(state, targets, stdin)

    matched = [ln for ln in lines if bool(regex.search(ln)) != invert]

    if "-q" in flags:
        # 出力を捨てマッチ有無だけを終了ステータスで伝える（if 条件での利用を想定。
        # Mission19）。マッチ無しは CommandError にして evaluate() の失敗パスへ乗せる。
        if not matched:
            raise CommandError("Error: no match")
        return [], state

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
    current_user = state.get("current_user", "detective")

    def walk(path: str, n: dict) -> None:
        basename = fs.segments(path)[-1] if fs.segments(path) else path
        if name_glob is None or fnmatch.fnmatch(basename, name_glob):
            results.append(path)
        if fs.is_dir(n):
            for child_name in sorted(n.get("children", {})):
                child = n["children"][child_name]
                # 通行権限（P3-04a）を通らない子ディレクトリへは降りない・出力もしない。
                if fs.is_dir(child) and not fs.can_traverse(child, current_user):
                    continue
                child_path = "/" + "/".join([*fs.segments(path), child_name])
                walk(child_path, child)

    walk(abs_start, node)
    return results, state


# --- アーカイブ・鑑識（Level 8） ---
# アーカイブは file ノードに任意キー "archive_type"（"tar"|"tar.gz"|"zip"|"gzip"）と
# "archive_content" を持たせて表現する。拡張子ではなく file コマンドで実体を確かめる
# 設計（Mission9）。gzip は単一ファイルの中身ノードそのもの、tar/zip は
# {name: node, ...} の展開後エントリ集合。

_FILE_DESCRIPTIONS = {
    "tar.gz": "gzip compressed data",
    "gzip": "gzip compressed data",
    "zip": "Zip archive data",
    "tar": "POSIX tar archive",
}


@command("file")
def cmd_file(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    label = operands[0]
    abs_path = fs.normalize(state["current_path"], label)
    node = fs.get_node(state, abs_path)
    if node is None:
        raise CommandError("Error: path not found")
    if fs.is_dir(node):
        return [f"{label}: directory"], state
    if fs.is_link(node):
        return [f"{label}: symbolic link to {node.get('target', '')}"], state
    desc = _FILE_DESCRIPTIONS.get(node.get("archive_type"), "ASCII text")
    return [f"{label}: {desc}"], state


def _extract_into_cwd(state: dict, archive_content: dict) -> None:
    cwd = fs.get_node(state, state["current_path"])
    if not fs.is_dir(cwd):
        raise CommandError("Error: path not found")
    for name, node in archive_content.items():
        cwd["children"][name] = copy.deepcopy(node)


@command("ln")
def cmd_ln(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    args = argv[1:]
    if "-s" not in args:
        raise CommandError("Error: invalid input")
    operands = [a for a in args if a != "-s"]
    if len(operands) != 2:
        raise CommandError("Error: invalid input")

    target, link_name = operands
    abs_target = fs.normalize(state["current_path"], target)
    abs_link = fs.normalize(state["current_path"], link_name)
    if fs.get_node(state, abs_link) is not None:
        raise CommandError("Error: path already exists")
    parent, name = fs.get_parent(state, abs_link)
    if parent is None:
        raise CommandError("Error: path not found")
    parent["children"][name] = fs.new_link(abs_target)
    return [], state


@command("tar")
def cmd_tar(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    flags = [a for a in argv[1:] if a.startswith("-")]
    operands = _operands(argv)
    if not operands or not flags:
        raise CommandError("Error: invalid input")
    flag_letters = flags[0].lstrip("-")
    if "x" not in flag_letters or "f" not in flag_letters:
        raise CommandError("Error: invalid input")

    abs_path = fs.normalize(state["current_path"], operands[0])
    node = fs.get_node(state, abs_path)
    if not fs.is_file(node):
        raise CommandError("Error: file not found")
    if node.get("archive_type") not in ("tar", "tar.gz"):
        raise CommandError("Error: invalid input")

    _extract_into_cwd(state, node.get("archive_content", {}))
    return [], state


@command("unzip")
def cmd_unzip(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    abs_path = fs.normalize(state["current_path"], operands[0])
    node = fs.get_node(state, abs_path)
    if not fs.is_file(node):
        raise CommandError("Error: file not found")
    if node.get("archive_type") != "zip":
        raise CommandError("Error: invalid input")

    _extract_into_cwd(state, node.get("archive_content", {}))
    return [], state


@command("gunzip")
def cmd_gunzip(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    abs_path = fs.normalize(state["current_path"], operands[0])
    node = fs.get_node(state, abs_path)
    if not fs.is_file(node):
        raise CommandError("Error: file not found")
    if node.get("archive_type") != "gzip":
        raise CommandError("Error: invalid input")

    parent, name = fs.get_parent(state, abs_path)
    if parent is None:
        raise CommandError("Error: path not found")
    new_name = name[:-3] if name.endswith(".gz") else f"{name}.out"
    del parent["children"][name]
    parent["children"][new_name] = copy.deepcopy(node["archive_content"])
    return [], state


def _hash_files(state: dict, files: list[str], algo: str) -> list[str]:
    """md5sum/sha256sum 共通実装。content の実ハッシュを hashlib で計算する
    （標準ライブラリなので実 OS 非依存の設計原則に適合）。"""
    if not files:
        raise CommandError("Error: invalid input")
    out: list[str] = []
    for f in files:
        node = fs.get_node(state, fs.normalize(state["current_path"], f))
        if fs.is_link(node):
            node = fs.resolve_link(state, node)
        if not fs.is_file(node):
            raise CommandError("Error: file not found")
        digest = hashlib.new(algo, node.get("content", "").encode()).hexdigest()
        out.append(f"{digest}  {f}")
    return out


@command("md5sum")
def cmd_md5sum(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    return _hash_files(state, _operands(argv), "md5"), state


@command("sha256sum")
def cmd_sha256sum(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    return _hash_files(state, _operands(argv), "sha256"), state


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


@command("paste")
def cmd_paste(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    delim = "\t"
    files: list[str] = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "-d":
            i += 1
            delim = argv[i] if i < len(argv) else "\t"
        elif a.startswith("-d"):
            delim = a[2:]
        elif not a.startswith("-"):
            files.append(a)
        i += 1

    if not files:
        return list(stdin), state

    columns = [_read_input(state, [f], []) for f in files]
    max_len = max(len(c) for c in columns)
    out: list[str] = []
    for row in range(max_len):
        parts = [col[row] if row < len(col) else "" for col in columns]
        out.append(delim.join(parts))
    return out, state


@command("tr")
def cmd_tr(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    args = argv[1:]
    delete_flag = "-d" in args
    operands = [a for a in args if not a.startswith("-")]

    if delete_flag:
        if not operands:
            raise CommandError("Error: invalid input")
        to_delete = set(operands[0])
        return ["".join(ch for ch in ln if ch not in to_delete) for ln in stdin], state

    if len(operands) != 2 or len(operands[0]) != len(operands[1]):
        raise CommandError("Error: invalid input")
    table = str.maketrans(operands[0], operands[1])
    return [ln.translate(table) for ln in stdin], state


def _diff_range(start: int, end: int) -> str:
    """diff の範囲表記（1始まり）。単一行は "N"、複数行は "N,M"。"""
    if end - start <= 1:
        return str(start + 1)
    return f"{start + 1},{end}"


def _classic_diff(a_lines: list[str], b_lines: list[str]) -> list[str]:
    """古典 diff 形式（"NcM" / "< " / "---" / "> "）で差分を返す。同一なら []。"""
    sm = difflib.SequenceMatcher(None, a_lines, b_lines, autojunk=False)
    out: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            out.append(f"{_diff_range(i1, i2)}c{_diff_range(j1, j2)}")
            out.extend(f"< {ln}" for ln in a_lines[i1:i2])
            out.append("---")
            out.extend(f"> {ln}" for ln in b_lines[j1:j2])
        elif tag == "delete":
            out.append(f"{_diff_range(i1, i2)}d{j1}")
            out.extend(f"< {ln}" for ln in a_lines[i1:i2])
        elif tag == "insert":
            out.append(f"{i1}a{_diff_range(j1, j2)}")
            out.extend(f"> {ln}" for ln in b_lines[j1:j2])
    return out


@command("diff")
def cmd_diff(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if len(operands) != 2:
        raise CommandError("Error: invalid input")
    a_lines = _read_input(state, [operands[0]], [])
    b_lines = _read_input(state, [operands[1]], [])
    return _classic_diff(a_lines, b_lines), state


_SED_PATTERN = re.compile(r"^s/(.*)/(.*)/(g)?$")


@command("sed")
def cmd_sed(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    m = _SED_PATTERN.match(operands[0])
    if not m:
        raise CommandError("Error: invalid input")
    old, new, flag_g = m.group(1), m.group(2), m.group(3)

    lines = _read_input(state, operands[1:], stdin)
    count = 0 if flag_g else 1
    try:
        return [re.sub(old, new, ln, count=count) for ln in lines], state
    except re.error as exc:
        raise CommandError("Error: invalid input") from exc


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


# --- ネットワーク（Level 9） ---
# 静的なホスト表（設計指示書 § 5。ghost.example は Mission12 実装時に確定）。
NET_HOSTS: dict[str, str] = {
    "ghost.example": "10.66.6.6",
    "archive_node": "192.168.10.5",
    "corp_server": "10.0.3.17",
}


def _resolve_ip(target: str) -> str | None:
    if target in NET_HOSTS:
        return NET_HOSTS[target]
    if target in NET_HOSTS.values():
        return target
    return None


@command("dig")
def cmd_dig(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    host = operands[0]
    ip = _resolve_ip(host)
    if ip is None:
        raise CommandError("Host not found")
    return [
        ";; ANSWER SECTION:",
        f"{host}.\t300\tIN\tA\t{ip}",
    ], state


@command("host")
def cmd_host(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    target = operands[0]
    ip = _resolve_ip(target)
    if ip is None:
        raise CommandError("Host not found")
    return [f"{target} has address {ip}"], state


@command("ping")
def cmd_ping(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    target = operands[0]
    ip = _resolve_ip(target)
    if ip is None:
        raise CommandError("Host not found")
    return [
        f"PING {target} ({ip}): 56 data bytes",
        f"64 bytes from {ip}: icmp_seq=0 ttl=64 time=0.5 ms",
        f"64 bytes from {ip}: icmp_seq=1 ttl=64 time=0.4 ms",
        "--- ping statistics ---",
        "2 packets transmitted, 2 packets received, 0% packet loss",
    ], state


@command("ss")
def cmd_ss(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    header = "Netid  State   Local Address:Port   Peer Address:Port"
    host_def = current_host_def(state)
    if host_def is None:
        return [header, "tcp    LISTEN  0.0.0.0:22           0.0.0.0:*"], state
    host = state["ssh_host"]
    rows = [header]
    for name in host_def.get("services", {}):
        merged = service_state(state, host, name)
        if merged is not None and merged.get("state") == "active" and merged.get("port"):
            rows.append(f"tcp    LISTEN  0.0.0.0:{merged['port']}           0.0.0.0:*")
    return rows, state


# --- 自動化（Level 10） ---
@command("crontab")
def cmd_crontab(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    # 閲覧のみ対応（rm 禁止と同じ方針で書き込み系は実装しない。解除は
    # judge 側で「正解ジョブの発動日時を報告」できたかどうかで判定する）。
    if "-l" not in argv[1:]:
        raise CommandError("Error: invalid input")
    host_def = current_host_def(state)
    jobs = host_def.get("cron_jobs", []) if host_def is not None else state.get("cron_jobs", [])
    if not jobs:
        return ["no crontab for detective"], state
    return [f"{j['schedule']} {j['command']}" for j in jobs], state


# --- サーバー編の基盤（Level 12。バックエンド_コマンド機能仕様 § 5c） ---
_LOCAL_UNAME = "Linux office 6.1.0-18-amd64 #1 SMP x86_64 GNU/Linux"
_METADATA_URL_PREFIX = "http://169.254.169.254/latest/meta-data/"
_SYSTEMCTL_ACTIONS = {"status", "start", "stop", "restart"}
_SYSTEMCTL_SINCE = "Thu 2026-01-01 00:00:00 UTC"
_JOURNAL_BEGIN = "-- Logs begin at Thu 2026-01-01 00:00:00 UTC --"


@command("hostname")
def cmd_hostname(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    host_def = current_host_def(state)
    name = host_def["hostname"] if host_def is not None else "office"
    return [name], state


@command("uname")
def cmd_uname(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    flags = _flag_chars(argv)
    host_def = current_host_def(state)
    full = host_def["uname"] if host_def is not None else _LOCAL_UNAME
    if "a" in flags:
        return [full], state
    # -a 無しはカーネル名（先頭トークン `Linux`）のみ。
    return [full.split(" ", 1)[0]], state


def _df_row(row: dict) -> str:
    return (
        f"{row['fs']:<14} {row['size']:>5} {row['used']:>5} {row['avail']:>5} "
        f"{row['pct']:>3}% {row['mount']}"
    )


@command("df")
def cmd_df(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    host_def = current_host_def(state)
    rows = host_def["disk"] if host_def is not None else [
        {"fs": "/dev/sda1", "size": "40G", "used": "9G", "avail": "31G", "pct": 23, "mount": "/"},
    ]
    header = "Filesystem     Size  Used Avail Use% Mounted on"
    return [header, *[_df_row(row) for row in rows]], state


def _content_size(node: dict) -> int:
    if node.get("type") != "dir":
        return len(node.get("content", ""))
    return sum(_content_size(child) for child in node.get("children", {}).values())


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    unit = "B"
    for candidate in ("K", "M", "G"):
        if size < 1024:
            break
        size /= 1024
        unit = candidate
    if unit == "B":
        return f"{int(size)}{unit}"
    return f"{size:.1f}{unit}"


@command("du")
def cmd_du(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    host_def = current_host_def(state)
    sizes = host_def.get("sizes", {}) if host_def is not None else {}
    lines: list[str] = []
    for target in operands:
        abs_path = fs.normalize(state["current_path"], target)
        human = sizes.get(abs_path)
        if human is None:
            node = fs.get_node(state, abs_path)
            if node is None:
                raise CommandError("Error: path not found")
            human = _human_size(_content_size(node))
        lines.append(f"{human}\t{target}")
    return lines, state


def _ip_lines(ifaces: list[dict]) -> list[str]:
    lines: list[str] = []
    for idx, item in enumerate(ifaces, start=1):
        iface = item["iface"]
        is_lo = iface == "lo"
        flags = "LOOPBACK,UP,LOWER_UP" if is_lo else "BROADCAST,MULTICAST,UP,LOWER_UP"
        mtu = 65536 if is_lo else 1500
        scope = "host" if is_lo else "global"
        lines.append(f"{idx}: {iface}: <{flags}> mtu {mtu}")
        lines.append(f"    inet {item['addr']} scope {scope} {iface}")
    return lines


@command("ip")
def cmd_ip(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands or operands[0] not in ("a", "addr"):
        raise CommandError("Error: invalid input")
    host_def = current_host_def(state)
    if host_def is not None:
        ifaces = [{"iface": "lo", "addr": "127.0.0.1/8"}, *host_def.get("ip", [])]
    else:
        ifaces = [
            {"iface": "lo", "addr": "127.0.0.1/8"},
            {"iface": "eth0", "addr": "10.0.0.2/24"},
        ]
    return _ip_lines(ifaces), state


def _systemctl_status_lines(svc: str, merged: dict) -> list[str]:
    lines = [f"● {svc}.service - {merged.get('description', svc)}"]
    state_value = merged.get("state", "inactive")
    if state_value == "active":
        lines.append(f"   Active: active (running) since {_SYSTEMCTL_SINCE}")
    elif state_value == "failed":
        lines.append("   Active: failed (Result: exit-code)")
    else:
        lines.append(f"   Active: inactive (dead) since {_SYSTEMCTL_SINCE}")
    lines.extend(merged.get("journal", [])[-3:])
    return lines


@command("systemctl")
def cmd_systemctl(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if len(operands) < 2 or operands[0] not in _SYSTEMCTL_ACTIONS:
        raise CommandError("Error: invalid input")
    action, svc = operands[0], operands[1]

    if action != "status":
        # start/stop/restart はサーバーでだけ触れる（事務所には触れるサービスが無い）。
        if not state.get("remote_mode"):
            raise CommandError("Error: command not allowed")
        host = state["ssh_host"]
        host_info = SSH_HOSTS[host]
        if svc not in host_info.get("services", {}):
            raise CommandError(f"Unit {svc}.service could not be found.")
        overrides = state.setdefault("remote_services", {}).setdefault(host, {})
        new_state_value = "inactive" if action == "stop" else "active"
        overrides[svc] = {**overrides.get(svc, {}), "state": new_state_value}
        return [], state

    host = state.get("ssh_host") if state.get("remote_mode") else None
    merged = service_state(state, host, svc) if host else None
    if merged is None:
        raise CommandError(f"Unit {svc}.service could not be found.")
    return _systemctl_status_lines(svc, merged), state


@command("journalctl")
def cmd_journalctl(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    tokens = argv[1:]
    svc: str | None = None
    n: int | None = None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "-u" and i + 1 < len(tokens):
            svc = tokens[i + 1]
            i += 2
            continue
        if tok == "-n" and i + 1 < len(tokens) and tokens[i + 1].isdigit():
            n = int(tokens[i + 1])
            i += 2
            continue
        raise CommandError("Error: invalid input")
    if svc is None:
        raise CommandError("Error: invalid input")

    host = state.get("ssh_host") if state.get("remote_mode") else None
    merged = service_state(state, host, svc) if host else None
    if merged is None:
        raise CommandError(f"Unit {svc}.service could not be found.")
    journal = merged.get("journal", [])
    if n is not None:
        journal = journal[-n:] if n > 0 else []
    return [_JOURNAL_BEGIN, *journal], state


def _url_host(url: str) -> str:
    without_scheme = url.split("://", 1)[-1]
    return without_scheme.split("/", 1)[0]


@command("curl")
def cmd_curl(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    url = operands[0]
    if not url.startswith(_METADATA_URL_PREFIX):
        raise CommandError(f"curl: (6) Could not resolve host: {_url_host(url)}")

    host_def = current_host_def(state)
    metadata = host_def.get("metadata") if host_def is not None else None
    if metadata is None:
        raise CommandError("curl: (7) Failed to connect to 169.254.169.254 port 80")

    key = url[len(_METADATA_URL_PREFIX):]
    if key == "":
        return sorted(metadata.keys()), state
    if key not in metadata:
        raise CommandError("404 - Not Found")
    return [str(metadata[key])], state


@command("date")
def cmd_date(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    return ["Thu Jan  1 00:00:00 UTC 2026"], state


# --- 環境変数（Level 10。Mission21） ---
_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


@command("export")
def cmd_export(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 2:
        raise CommandError("Error: invalid input")
    m = _ASSIGN.match(argv[1])
    if not m:
        raise CommandError("Error: invalid input")
    env_for(state)[m.group(1)] = m.group(2)
    return [], state


@command("unset")
def cmd_unset(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 2:
        raise CommandError("Error: invalid input")
    env_for(state).pop(argv[1], None)
    return [], state


@command("printenv")
def cmd_printenv(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    env_vars = env_for(state)
    operands = _operands(argv)
    if not operands:
        return [f"{k}={v}" for k, v in env_vars.items()], state
    return [env_vars[k] for k in operands if k in env_vars], state


@command("which")
def cmd_which(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    name = operands[0]
    if name in DENYLIST or name not in ALLOWLIST:
        raise CommandError("Error: command not allowed")
    return [f"/bin/{name}"], state


@command("type")
def cmd_type(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    operands = _operands(argv)
    if not operands:
        raise CommandError("Error: invalid input")
    name = operands[0]
    if name in DENYLIST or name not in ALLOWLIST:
        raise CommandError("Error: command not allowed")
    return [f"{name} is /bin/{name}"], state


# --- SSH / remote ---
@command("ssh")
def cmd_ssh(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 2:
        raise CommandError("Error: invalid input")
    host = argv[1]
    info = SSH_HOSTS.get(host)
    if info is None:
        raise CommandError("Host not found")
    # 未解放 Mission のホストは存在自体を隠す（同じ文言の Host not found で返す）。
    # サーバー編（archive_node/corp_server）は _DEFS にまだ無い mission_id を指すことが
    # あるため、status_for が ValueError（unknown mission_id）を投げるケースも「未解放」
    # として扱う（Mission 実装が揃うまでは誰も到達できない予約済みホストのまま）。
    required_mission_id = info.get("required_mission_id")
    if required_mission_id is not None:
        try:
            locked = progress.status_for(required_mission_id, state["mission_progress"]) == "locked"
        except ValueError:
            locked = True
        if locked:
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
    # su での変装復帰を優先する（ssh の remote 離脱とスタックが独立しているため、
    # 変装中に ssh していても su の復帰が先に処理される）。
    user_stack = state.get("_user_stack", [])
    if user_stack:
        state["current_user"] = user_stack.pop()
        return [], state

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


# --- ユーザー切替（Level 7） ---
_UID_MAP = {"root": 0, "detective": 1000}


@command("su")
def cmd_su(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 2:
        raise CommandError("Error: invalid input")
    stack = state.setdefault("_user_stack", [])
    stack.append(state.get("current_user", "detective"))
    state["current_user"] = argv[1]
    return [], state


@command("whoami")
def cmd_whoami(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    return [state.get("current_user", "detective")], state


@command("id")
def cmd_id(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    user = state.get("current_user", "detective")
    uid = _UID_MAP.get(user, 1001)
    return [f"uid={uid}({user}) gid={uid}({user})"], state


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

    # 汎用スクリプト（変数 / if / for。Mission19）。
    out_lines, new_state = script.run_script(state, node.get("content", ""))
    if "FOUND" in out_lines:
        progress.flags(new_state)["script_found"] = True
    return out_lines, new_state
