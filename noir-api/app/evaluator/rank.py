"""探偵ランク（設計指示書 § 8 レベル表 / § 11 ゲーム機能 1）。

ランク＝これまでに解放されたコマンドの最高レベル。Mission クリアで新しいコマンドが
解放されて最高レベルが上がったとき、`rank_up` イベント（§ 7）で辞令を出す。
純粋関数・state を変更しない。解放済みコマンドの算出は `complete.mission_commands`
（Mission の allowed_commands の和。history/clear 等の基本操作は数えない）と共有する。
"""

from app.evaluator import complete

# 設計指示書 § 8「レベル分け」の表そのまま（ランク名はフロントの辞令・ヘッダー表示にも使う）。
RANK_NAMES: dict[int, str] = {
    1: "見習い探偵",
    2: "新米探偵",
    3: "捜査員",
    4: "分析官",
    5: "情報屋",
    6: "監視者",
    7: "潜入捜査官",
    8: "証拠管理官",
    9: "追跡者",
    10: "主任探偵",
    11: "参謀",
}

_LEVELS: dict[int, tuple[str, ...]] = {
    1: ("ls", "cd", "pwd", "touch", "mkdir", "cat", "echo", "clear"),
    2: ("less", "history"),
    3: ("grep", "find", "sort", "uniq", "egrep", "fgrep"),
    4: ("awk",),
    5: ("head", "tail", "wc", "cut", "paste", "tr", "sed", "diff", "nl", "tee", "xargs"),
    6: ("ps", "top", "kill", "pgrep", "jobs", "free", "uptime"),
    7: ("chmod", "chown", "umask", "su", "whoami", "id", "who"),
    8: (
        "cp", "mv", "tar", "gzip", "gunzip", "zip", "unzip", "ln", "file",
        "which", "locate", "du", "df", "md5sum", "sha256sum", "stat",
    ),
    9: ("ping", "ip", "ss", "dig", "host", "hostname", "traceroute"),
    10: (
        "crontab", "at", "date", "cal", "systemctl", "journalctl", "uname", "env", "alias",
        "export", "unset", "printenv", "type",
    ),
    11: ("sh", "test", "read", "basename", "dirname", "seq"),
}
COMMAND_LEVEL: dict[str, int] = {
    cmd: level for level, cmds in _LEVELS.items() for cmd in cmds
}


def level_of(commands: list[str]) -> int:
    """コマンド群の最高レベル（表に無いもの＝ssh/git/exit 等は Level 1 扱い）。"""
    return max((COMMAND_LEVEL.get(c, 1) for c in commands), default=1)


def rank_of(state: dict) -> dict:
    """`{"level": n, "name": "..."}`。hello / result の state summary に載せる。"""
    level = level_of(complete.mission_commands(state))
    return {"level": level, "name": RANK_NAMES.get(level, "")}


def rank_up_event(before: dict, after: dict) -> dict | None:
    """クリア前後の state を比べ、ランクが上がっていれば `rank_up` イベントの中身を返す。

    `unlocked` は新しく解放されたコマンド（ランクが変わらない解放は辞令を出さない）。
    """
    prev_cmds = set(complete.mission_commands(before))
    next_cmds = complete.mission_commands(after)
    prev_level = level_of(sorted(prev_cmds))
    next_level = level_of(next_cmds)
    if next_level <= prev_level:
        return None
    return {
        "type": "event",
        "name": "rank_up",
        "level": next_level,
        "rank_name": RANK_NAMES.get(next_level, ""),
        "from_level": prev_level,
        "from_rank_name": RANK_NAMES.get(prev_level, ""),
        "unlocked": [c for c in next_cmds if c not in prev_cmds],
    }
