"""Mission カタログ（Mission1〜22）。

出典: docs/Mission参照ファイル.md。title は英語名、title_ja は画面表示名。
allowed_commands は各 Mission の必須コマンド + 共通の基本操作（ls/cd/cat/pwd/echo/git）。
詳細正規表現・初期FS は実装時に本 MissionDef を拡張する（設計指示書 § 11 / § 5）。
"""

from dataclasses import dataclass, field

# 全 Mission 共通で使える基本操作（ナビゲーション + 疑似 Git ワークフロー）。
BASE_COMMANDS = ["ls", "cd", "cat", "pwd", "echo", "git"]


def _mode_file(content: str, mode: str, *, immutable: bool = False) -> dict:
    return {
        "type": "file",
        "content": content,
        "mode": mode,
        "owner": "detective",
        "mtime": "2026-01-01T00:00:00Z",
        "immutable": immutable,
    }


def _file(content: str, *, immutable: bool = False) -> dict:
    return _mode_file(content, "rw-r--r--", immutable=immutable)


# Mission1 の初期 FS: 机の名刺 + 判定スクリプト。
_MISSION1_FS = {
    "root": {
        "type": "dir",
        "children": {
            "desk": {
                "type": "dir",
                "children": {
                    "businesscard.txt": _file("NAME: ???\nROLE: detective", immutable=True),
                },
            },
            "case_file.sh": _file("# 事件ファイル: sh case_file.sh で判定する\n", immutable=True),
        },
    }
}


# Mission2 の初期 FS: 公園（park）に猫情報ファイル + デコイ。swing に本命。
# 初期 current_path=/root/park なので、find で swing 配下の catinfo.txt を探し、
# 絶対パスで cat/grep して STATUS を読み取る導線。
_MISSION2_FS = {
    "root": {
        "type": "dir",
        "children": {
            "park": {
                "type": "dir",
                "children": {
                    "swing": {
                        "type": "dir",
                        "children": {
                            "catinfo.txt": _file(
                                "NAME: Mike\n"
                                "COLOR: black\n"
                                "STATUS: stray\n"
                                "LAST_SEEN: swing",
                                immutable=True,
                            ),
                        },
                    },
                    "fountain": {
                        "type": "dir",
                        "children": {
                            "note.txt": _file("just water here", immutable=True),
                        },
                    },
                    "bench": {
                        "type": "dir",
                        "children": {
                            "trash.txt": _file("empty can", immutable=True),
                        },
                    },
                    "case_file.sh": _file(
                        "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
                    ),
                },
            },
        },
    }
}


# Mission4 の盗聴ログ: 電話番号を出現頻度差をつけて散らす。最頻出 = 正解。
# grep TEL | sort | uniq -c | sort で最頻番号を割り出す導線（実際は数万行想定）。
_MISSION4_ANSWER = "555-0142"
_MISSION4_COUNTS = {
    _MISSION4_ANSWER: 9,  # 最頻出（正解）
    "555-0199": 5,
    "555-0007": 3,
    "555-0250": 2,
    "555-0333": 1,
}


def _mission4_tape() -> str:
    groups = [[num] * count for num, count in _MISSION4_COUNTS.items()]
    scattered: list[str] = []
    # ラウンドロビンで散らし、sort 前提の集計を体感させる（決定的）。
    while any(groups):
        for g in groups:
            if g:
                scattered.append(g.pop())
    # 発信番号の記録（grep TEL | sort | uniq -c で頻度集計できるよう番号のみの行）。
    lines = [f"TEL: {num}" for num in scattered]
    # TEL を含まないノイズ行（grep で除外される）。
    lines += [f"NOTE: heartbeat seq={i}" for i in range(10)]
    return "\n".join(lines)


_MISSION4_FS = {
    "root": {
        "type": "dir",
        "children": {
            "tape.log": _file(_mission4_tape(), immutable=True),
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


# Mission5 の初期 FS: /root/vault/ に閲覧不可のヒントファイル（chmod +r で解錠）。
# ヒントが指す inner/ に実行権限のない case_file.sh（chmod +x で解錠）。
# immutable=False で配置し、P2-01 の can_exec 特例（immutable=True は実行可）を
# 適用させない — このため sh 実行には明示的な chmod +x が必須になる。
_MISSION5_FS = {
    "root": {
        "type": "dir",
        "children": {
            "vault": {
                "type": "dir",
                "children": {
                    "locked_evidence.txt": _mode_file(
                        "SEALED EVIDENCE ROOM\n"
                        "This file is locked. Use chmod +r to read it.\n"
                        "The inner room waits at /root/vault/inner.",
                        "---------",
                        immutable=False,
                    ),
                    "inner": {
                        "type": "dir",
                        "children": {
                            "case_file.sh": _mode_file(
                                "# 事件ファイル: sh case_file.sh で判定する\n",
                                "rw-r--r--",
                                immutable=False,
                            ),
                        },
                    },
                },
            },
        },
    }
}


# Mission6 のプロセステーブル: 正規プロセス（clock/mailbox/heater, protected）に
# 紛れ込んだ盗聴プログラム listener_x（pid 666）。protected の kill は判定側で
# 拒否せず kill コマンド側で「削除しない」形で汎用的に処理する。
_MISSION6_PROCESSES = [
    {"pid": 100, "name": "clock", "user": "root", "cmdline": "/usr/sbin/clockd", "state": "S", "protected": True},
    {"pid": 101, "name": "mailbox", "user": "root", "cmdline": "/usr/sbin/mailboxd", "state": "S", "protected": True},
    {"pid": 102, "name": "heater", "user": "root", "cmdline": "/usr/sbin/heaterd", "state": "S", "protected": True},
    {"pid": 666, "name": "listener_x", "user": "root", "cmdline": "/tmp/.hidden/listener_x --tap", "state": "S", "protected": False},
]

_MISSION6_FS = {
    "root": {
        "type": "dir",
        "children": {
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


# Mission7 のプロセステーブル: 正規プロセスに紛れ、名前だけ "clock" を騙る侵入者
# （実体は cmdline "/tmp/.fake/exfil --send"）。ps の名簿だけでは見抜けず、
# /proc/<PID>/cmdline まで裏取りして初めて正体が割れる（タイトル通りの「胸の内」）。
_MISSION7_PROCESSES = [
    {"pid": 201, "name": "mailbox", "user": "root", "cmdline": "/usr/sbin/mailboxd", "state": "S", "protected": True},
    {"pid": 202, "name": "heater", "user": "root", "cmdline": "/usr/sbin/heaterd", "state": "S", "protected": True},
    {"pid": 923, "name": "clock", "user": "root", "cmdline": "/tmp/.fake/exfil --send", "state": "S", "protected": False},
]

_MISSION7_FS = {
    "root": {
        "type": "dir",
        "children": {
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


def _owner_file(content: str, mode: str, owner: str) -> dict:
    return {
        "type": "file",
        "content": content,
        "mode": mode,
        "owner": owner,
        "mtime": "2026-01-01T00:00:00Z",
        "immutable": False,
    }


# Mission8 の初期 FS: bar/ にヒント（誰でも読める）+ barman だけが読める台帳。
# 合言葉探しは「ヒントの発見体験」として実装し、su 自体はパスワード検証なしで
# 成功させる（判定は su barman・whoami・秘密ファイル閲覧・detective への復帰の
# 4 点で担保する。judge.py の Mission8 専用ロジック）。
_MISSION8_FS = {
    "root": {
        "type": "dir",
        "children": {
            "bar": {
                "type": "dir",
                "children": {
                    "hint.txt": _owner_file(
                        "The barman keeps a ledger nobody else may read.\n"
                        "Become him: su barman\n"
                        "The ledger waits at /root/bar/back/ledger.txt",
                        "rw-r--r--",
                        "detective",
                    ),
                    "back": {
                        "type": "dir",
                        "children": {
                            "ledger.txt": _owner_file(
                                "SUSPECT: Nico Faro\n"
                                "LAST SEEN: back room, midnight",
                                "rw-------",
                                "barman",
                            ),
                        },
                    },
                    "case_file.sh": _file(
                        "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
                    ),
                },
            },
        },
    }
}


def _archive_file(archive_type: str, archive_content: dict) -> dict:
    node = _file("", immutable=True)
    node["archive_type"] = archive_type
    node["archive_content"] = archive_content
    return node


# Mission9 の初期 FS: 拡張子は当てにならない（evidence.dat の実体は tar.gz）。
# evidence.dat（tar.gz）→ sealed.zip（zip）→ final_clue.txt の3層アーカイブ。
_MISSION9_FINAL_CLUE = _file("CODE: NOIR-1948", immutable=True)
_MISSION9_SEALED_ZIP = _archive_file("zip", {"final_clue.txt": _MISSION9_FINAL_CLUE})
_MISSION9_EVIDENCE = _archive_file("tar.gz", {"sealed.zip": _MISSION9_SEALED_ZIP})

_MISSION9_FS = {
    "root": {
        "type": "dir",
        "children": {
            "evidence.dat": _MISSION9_EVIDENCE,
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


# Mission10 の初期 FS: original.txt（正本、immutable）と submitted.txt
# （1文字だけ改ざんされた写し。"0" と "O" — 目視では見つけにくい）。
_MISSION10_FS = {
    "root": {
        "type": "dir",
        "children": {
            "original.txt": _file(
                "PAY TO: THE ORPHANAGE\nAMOUNT: $50000\nSIGNED: J. Whitfield",
                immutable=True,
            ),
            "submitted.txt": _file(
                "PAY TO: THE ORPHANAGE\nAMOUNT: $5O000\nSIGNED: J. Whitfield",
                immutable=False,
            ),
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


# Mission11 の初期 FS: シャッフル済みタグ付き断片（glob 非依存の導線。P2-08）。
# sort でタグ順に並び替え、cut -d: -f2 で本文を取り出す。
_MISSION11_FS = {
    "root": {
        "type": "dir",
        "children": {
            "scraps": {
                "type": "dir",
                "children": {
                    "pieces.txt": _file(
                        "3:ALONE\n1:MIDNIGHT AT THE OLD PIER\n2:BRING THE LEDGER",
                        immutable=True,
                    ),
                },
            },
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


@dataclass(frozen=True)
class MissionDef:
    id: int
    title: str
    title_ja: str
    description: str
    # 必須コマンド（BASE_COMMANDS と重複しない Mission 固有分）。
    extra_commands: list[str] = field(default_factory=list)
    # case_file.sh 判定用の正規表現（command_log の各行に対して評価。AND / 順不同 /
    # 大小文字区別あり。設計指示書 § 9）。空 = 詳細未確定（実装時に確定）。
    expected_script_patterns: list[str] = field(default_factory=list)
    # 初期仮想FS（設計指示書 § 4 の filesystem スキーマ）。None は空の /root のみ。
    # Mission ごとの詳細 FS は順次ここに追加する。
    initial_filesystem: dict | None = None
    # 初期カレントディレクトリ（Mission参照ファイル § 1 のテンプレ）。None は /root。
    initial_current_path: str | None = None
    # 初期仮想プロセステーブル（ps/kill・/proc の対象）。None は空（デフォルト）。
    initial_processes: list[dict] | None = None

    @property
    def allowed_commands(self) -> list[str]:
        seen: dict[str, None] = {}
        for cmd in [*BASE_COMMANDS, *self.extra_commands]:
            seen.setdefault(cmd, None)
        return list(seen)


_DEFS: list[MissionDef] = [
    MissionDef(
        1, "Edit Business Card", "名刺を編集せよ",
        "机上の名刺ファイルにユーザー名を書き込み、疑似 git push まで完了する。",
        # case_file.sh は「捜査タスクの証跡」を判定する（§ 9 の判定例と同様）。
        # git add/commit/push は case_file.sh の後に走る手順のため regex ではなく
        # git コマンド側で構造的に強制する（commit は staged 必須 / push は
        # case_checked 必須。設計指示書 § 10 の判定フロー）。
        expected_script_patterns=[
            r"^cat\s+/root/desk/businesscard\.txt$",
            r"^echo\s+.+\s*>\s+/root/desk/businesscard\.txt$",
        ],
        initial_filesystem=_MISSION1_FS,
    ),
    MissionDef(
        2, "Park Cat Search", "公園の猫を探せ",
        "公園で猫ファイルを絶対パスで探索し、条件を満たして完了する。",
        ["find", "grep", "awk", "sort", "uniq"],
        # 判定は judge.py の Mission2 専用ロジック（find 使用・絶対パス・STATUS 抽出）で
        # 行うため expected_script_patterns は空にする（誤答メッセージを個別化するため）。
        initial_filesystem=_MISSION2_FS,
        initial_current_path="/root/park",
    ),
    MissionDef(
        3, "Amusement Park Bomb", "遊園地の爆弾",
        "ssh で遊園地に接続し、ヒントを集めて解除コードを特定する。",
        ["ssh", "exit", "find", "grep", "awk", "sort", "uniq"],
        # ssh amusement_park 接続後、/gate のヒントから Code/Wire/Height を読み取り、
        # echo で記録する（Mission1 と同じ「証跡=echo 行」方式）。汎用 AND-regex 判定。
        expected_script_patterns=[
            r"Code: [A-Z0-9]{4,}",
            r"Wire: (red|blue|yellow)",
            r"Height: [0-9]+",
        ],
    ),
    MissionDef(
        4, "Wiretap Tape", "盗聴テープを解析せよ",
        "数万行のログをパイプで捌き、最頻出の電話番号を特定する。",
        ["grep", "sort", "uniq", "wc", "head", "tail"],
        # クリア条件: uniq -c を含むパイプ集計の実行 + 正解番号の記述（Mission参照 § 4）。
        expected_script_patterns=[
            r"uniq\s+-c",
            rf"TEL: {_MISSION4_ANSWER}",
        ],
        initial_filesystem=_MISSION4_FS,
    ),
    MissionDef(
        5, "The Locked Vault", "開かずの資料室",
        "パーミッションを読み解き、chmod で証拠と case_file.sh を解錠する。",
        ["ls", "chmod"],
        # クリア条件: chmod +r（ヒント解錠）と chmod +x（case_file.sh 解錠）の
        # 2 系統が command_log に存在すること（Mission参照 § 5「2回以上」）。
        expected_script_patterns=[
            r"chmod\s+\+?r",
            r"chmod\s+\+?x",
        ],
        initial_filesystem=_MISSION5_FS,
    ),
    MissionDef(
        6, "Shadow Process", "盗聴器を止めろ",
        "ps で不審プロセスを見つけ、裏取りしてから kill する。",
        ["ps", "kill", "grep"],
        # 判定は judge.py の Mission6 専用ロジック（processes に listener_x が
        # 残っていないか）で行うため expected_script_patterns は空にする。
        initial_filesystem=_MISSION6_FS,
        initial_processes=_MISSION6_PROCESSES,
    ),
    MissionDef(
        7, "Inside the Machine", "機械の胸の内",
        "/proc を読み、偽装プロセスの正体を暴いて起訴・停止する。",
        ["ps", "kill", "grep", "free", "uptime"],
        # 判定は judge.py の Mission7 専用ロジック（/proc 裏取り・偽装 cmdline 報告・
        # 停止済みの 3 点）で行うため expected_script_patterns は空にする。
        initial_filesystem=_MISSION7_FS,
        initial_processes=_MISSION7_PROCESSES,
    ),
    MissionDef(
        8, "Master of Disguise", "変装潜入",
        "合言葉を見つけ su で barman になり、権限付きファイルを読む。",
        ["su", "whoami", "exit"],
        # 判定は judge.py の Mission8 専用ロジック（su barman・whoami・秘密ファイル
        # 閲覧・detective への復帰の4点）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION8_FS,
    ),
    MissionDef(
        9, "Sealed Evidence", "封印された証拠品",
        "file で正体を確かめながら、多重アーカイブを開封して手がかりを得る。",
        ["file", "tar", "gunzip", "unzip"],
        # クリア条件: tar 展開 / unzip 展開 / 最深部コードの記述（Mission参照 § 9）。
        expected_script_patterns=[
            r"tar\s+-x",
            r"unzip\s+",
            r"CODE: NOIR-1948",
        ],
        initial_filesystem=_MISSION9_FS,
    ),
    MissionDef(
        10, "The Forged Letter", "改ざんされた遺言状",
        "diff で改ざん箇所を特定し、sed で原本どおりに復元する。",
        ["diff", "sed"],
        # 判定は judge.py の Mission10 専用ロジック（diff 実行 + submitted.txt が
        # original.txt と完全一致）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION10_FS,
    ),
    MissionDef(
        11, "Torn Note", "切り裂かれた脅迫状",
        "断片ファイルを sort/cut/paste で並べ替え、全文を復元する。",
        ["sort", "cut", "paste"],
        # クリア条件: sort 実行 + cut/paste 実行 + 復元全文の記述（Mission参照 § 11）。
        expected_script_patterns=[
            r"\bsort\b",
            r"\b(cut|paste)\b",
            r"MIDNIGHT AT THE OLD PIER BRING THE LEDGER ALONE",
        ],
        initial_filesystem=_MISSION11_FS,
    ),
    MissionDef(
        12, "Ghost Line", "幽霊回線を追え",
        "dig で IP を割り出し、ping で生存確認して ssh で突入する。",
        ["dig", "host", "ping", "ss", "ssh", "exit", "grep"],
    ),
    MissionDef(
        13, "Midnight Broadcast", "深夜0時の犯行予告",
        "cron 書式を解読し、危険な時限ジョブだけを解除する。",
        ["crontab", "date", "grep"],
    ),
    MissionDef(
        14, "Hall of Mirrors", "鏡の館",
        "ls -l と file でシンボリックリンクを見抜き、実体の絶対パスを特定する。",
        ["ls", "file"],
    ),
    MissionDef(
        15, "The Informant's Trail", "情報屋の足取り",
        "history とログから操作を再現し、情報屋の行き先を突き止める。",
        ["history", "tail", "grep"],
    ),
    MissionDef(
        16, "The Great Sweep", "一斉捜索令状",
        "glob と引用符で対象を絞り込み、空白入りファイル名も開封する。",
        ["find", "grep"],
    ),
    MissionDef(
        17, "Fingerprint", "指紋は嘘をつかない",
        "md5sum で契約書コピーを照合し、改ざんされた1通を特定する。",
        ["md5sum", "sha256sum", "diff", "sort"],
    ),
    MissionDef(
        18, "Silence in the Static", "雑音の中の声",
        "2>/dev/null でエラーを捨て、必要な出力だけを取り出す。",
        ["grep", "find"],
    ),
    MissionDef(
        19, "The Detective's Playbook", "捜査手順書を書け",
        "変数と if を使ったシェルスクリプトを自作し、実行して判定する。",
        ["sh", "grep"],
    ),
    MissionDef(
        20, "Map of the City", "この街の地図",
        "FHS（/etc, /var/log, /home, /tmp）を巡り、黒幕の住民登録を探す。",
        ["grep", "tail"],
    ),
    MissionDef(
        21, "The Missing Toolbox", "消えた道具箱",
        "汚染された PATH を診断し、export で復旧して道具（コマンド）を取り戻す。",
        ["printenv", "export", "unset", "which", "type", "grep", "find"],
    ),
    MissionDef(
        22, "Case Closed", "最終事件 — すべてを繋げろ",
        "学んだ全技術を関所として突破し、黒幕の名を本部に提出する。",
        ["find", "ssh", "exit", "chmod", "grep", "sort", "uniq", "tar", "md5sum", "sh"],
    ),
]

MISSIONS: dict[int, MissionDef] = {m.id: m for m in _DEFS}


def get_mission(mission_id: int) -> MissionDef | None:
    return MISSIONS.get(mission_id)


def all_missions() -> list[MissionDef]:
    return [MISSIONS[i] for i in sorted(MISSIONS)]
