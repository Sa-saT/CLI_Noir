"""allowlist / denylist（設計指示書 § 8 の決定版）。

判定順序: denylist → allowlist → 実行。allowlist 外・denylist は
`Error: command not allowed`（§ 12）。
"""

ALLOWLIST: set[str] = {
    # Level 1〜4（MVP）
    "ls", "cd", "pwd",
    "touch", "mkdir", "cat", "less",
    "echo", "history", "clear",
    "grep", "find", "sort", "uniq", "awk",
    "egrep", "fgrep",
    "ssh", "exit",
    "git",
    "chmod", "chown", "curl",
    # Level 5: テキスト処理・パイプ
    "head", "tail", "wc", "cut", "paste", "tr", "sed", "diff", "nl", "tee", "xargs",
    # Level 6: プロセス
    "ps", "top", "kill", "pgrep", "jobs", "free", "uptime",
    # Level 7: 権限・ユーザー
    "umask", "su", "whoami", "id", "who",
    # Level 8: ファイル管理・アーカイブ・鑑識
    "cp", "mv",
    "tar", "gzip", "gunzip", "zip", "unzip", "ln", "file",
    "which", "locate", "du", "df", "md5sum", "sha256sum", "stat",
    # Level 9: ネットワーク
    "ping", "ip", "ss", "dig", "host", "hostname", "traceroute",
    # Level 10: システム管理・自動化
    "crontab", "at", "date", "cal", "systemctl", "journalctl", "uname", "env", "alias",
    "export", "unset", "printenv", "type",
    # Level 11: シェルスクリプト基礎
    "sh", "test", "read", "basename", "dirname", "seq",
    # 全レベル共通
    "man", "apropos", "whatis",
    # ご褒美コマンド
    "cowsay", "figlet",
}

DENYLIST: set[str] = {
    "rm", "sudo", "shutdown",
    "poweroff", "reboot",
    "telnet", "ftp", "wget",
    "nc", "dd", "mkfs",
}
