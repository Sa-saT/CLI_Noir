"""Mission カタログ（Mission1〜22）。

出典: docs/Mission参照ファイル.md。title は英語名、title_ja は画面表示名。
allowed_commands は各 Mission の必須コマンド + 共通の基本操作（ls/cd/cat/pwd/echo/git）。
詳細正規表現・初期FS は実装時に本 MissionDef を拡張する（設計指示書 § 11 / § 5）。
"""

import copy
from dataclasses import dataclass, field

# 全 Mission 共通で使える基本操作（ナビゲーション + 疑似 Git ワークフロー）。
BASE_COMMANDS = ["ls", "cd", "cat", "pwd", "echo", "git"]

# 判定スクリプトのファイル名。統合ワールド（Part5）では静的配置をやめ、
# アクティブ Mission の内容を /proc と同じ方式で動的生成する（P3-04）。
CASE_FILE_NAME = "case_file.sh"


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


# Mission13 のジョブ表: 金曜0時発動の危険ジョブ + 無害ジョブ2件。
_MISSION13_CRON_JOBS = [
    {"id": 1, "schedule": "0 0 * * 5", "command": "/tmp/.dark/broadcast.sh", "malicious": True},
    {"id": 2, "schedule": "0 6 * * *", "command": "/usr/bin/backup.sh", "malicious": False},
    {"id": 3, "schedule": "*/15 * * * *", "command": "/usr/bin/healthcheck.sh", "malicious": False},
]

_MISSION13_FS = {
    "root": {
        "type": "dir",
        "children": {
            "hint.txt": _file(
                "CRONTAB FORMAT (man 5 crontab)\n"
                "minute hour day month weekday command\n"
                "weekday: 0=Sunday 1=Monday ... 5=Friday 6=Saturday\n"
                "Example: 0 0 * * 5 -> every Friday at 00:00",
                immutable=True,
            ),
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


def _link_file(target: str) -> dict:
    return {
        "type": "link",
        "target": target,
        "mode": "rwxrwxrwx",
        "owner": "detective",
        "mtime": "2026-01-01T00:00:00Z",
    }


# Mission14 の初期 FS: 同名系の案内板（symlink）が多数、実体は1つだけ。
# deed_a -> deed_b -> vault/real_deed.txt（2段リンク）、deed_c -> deed_a（3段）。
_MISSION14_FS = {
    "root": {
        "type": "dir",
        "children": {
            "mirror_hall": {
                "type": "dir",
                "children": {
                    "deed_a.txt": _link_file("/root/mirror_hall/deed_b.txt"),
                    "deed_b.txt": _link_file("/root/mirror_hall/vault/real_deed.txt"),
                    "deed_c.txt": _link_file("/root/mirror_hall/deed_a.txt"),
                    "vault": {
                        "type": "dir",
                        "children": {
                            "real_deed.txt": _file(
                                "DEED: THE OLD LIGHTHOUSE PROPERTY", immutable=True
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


# Mission15: 情報屋の履歴（history が演出として表示）+ journal.log の足跡。
# history どおりに再実行すると行き先（PIER 13）にたどり着く。
_MISSION15_HISTORY = [
    "tail -n 5 /root/journal.log",
    "grep PIER /root/journal.log",
]

_MISSION15_FS = {
    "root": {
        "type": "dir",
        "children": {
            "journal.log": _file(
                "09:00 left the office\n"
                "09:15 stopped at the docks\n"
                "09:40 called an unknown number\n"
                "10:02 bought a one-way ticket\n"
                "10:30 last seen near the warehouse\n"
                "10:45 note left: meet at PIER 13",
                immutable=True,
            ),
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


# Mission16 の初期 FS: warehouse/ に case_1〜case_42.txt を大量配置し、
# glob で絞り込む必要性を体感させる。空白入りファイル名は引用符が必須。
def _mission16_warehouse_children() -> dict:
    children = {
        f"case_{i}.txt": _file(f"routine case file #{i}", immutable=True)
        for i in range(1, 43)
    }
    children["top secret.txt"] = _file("CODE: 4821-VESPER", immutable=True)
    return children


_MISSION16_FS = {
    "root": {
        "type": "dir",
        "children": {
            "warehouse": {
                "type": "dir",
                "children": {
                    **_mission16_warehouse_children(),
                    "case_file.sh": _file(
                        "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
                    ),
                },
            },
        },
    }
}


# Mission17 の初期 FS: 見た目が同一な契約書コピー5通のうち copy_4 のみ
# 1文字改ざん（"0" と "O"）。ledger.txt に原本の実 md5 ハッシュを記載。
_MISSION17_ORIGINAL_TEXT = "Article 7: 0% interest\nSigned by both parties."
_MISSION17_TAMPERED_TEXT = "Article 7: O% interest\nSigned by both parties."
_MISSION17_ORIGINAL_MD5 = "f5826660ac7d8193b17651462cefe538"

_MISSION17_FS = {
    "root": {
        "type": "dir",
        "children": {
            "contracts": {
                "type": "dir",
                "children": {
                    "copy_1.txt": _file(_MISSION17_ORIGINAL_TEXT, immutable=True),
                    "copy_2.txt": _file(_MISSION17_ORIGINAL_TEXT, immutable=True),
                    "copy_3.txt": _file(_MISSION17_ORIGINAL_TEXT, immutable=True),
                    "copy_4.txt": _file(_MISSION17_TAMPERED_TEXT, immutable=True),
                    "copy_5.txt": _file(_MISSION17_ORIGINAL_TEXT, immutable=True),
                    "ledger.txt": _file(
                        f"ORIGINAL MD5: {_MISSION17_ORIGINAL_MD5}", immutable=True
                    ),
                },
            },
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


# Mission18 の初期 FS: /root/archive/ に読めないファイル多数（雑音の元）+
# 読める witness_note.txt（手がかり）。grep -r ... 2>/dev/null で雑音を捨てる。
_MISSION18_FS = {
    "root": {
        "type": "dir",
        "children": {
            "archive": {
                "type": "dir",
                "children": {
                    "sealed_1.txt": _mode_file("classified", "---------", immutable=True),
                    "sealed_2.txt": _mode_file("classified", "---------", immutable=True),
                    "sealed_3.txt": _mode_file("classified", "---------", immutable=True),
                    "witness_note.txt": _file(
                        "local witness report\n"
                        "saw a black car leaving the scene\n"
                        "PLATE: NX-4471",
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


# Mission19 の初期 FS: sample.sh（見本。変数+if+grep -q+echo FOUND の型）+
# evidence.txt（実際の手がかり "Sam" を含む）。プレイヤーは自作 patrol.sh を
# echo リダイレクトで組み立て、sh /root/patrol.sh で実行する。
_MISSION19_FS = {
    "root": {
        "type": "dir",
        "children": {
            "sample.sh": _file(
                "# sample.sh - example: define a variable, then search for it\n"
                'KEYWORD="ExampleWord"\n'
                'if grep -q "$KEYWORD" notes.txt; then\n'
                '  echo "FOUND"\n'
                "fi",
                immutable=True,
            ),
            "evidence.txt": _file(
                "Witness: Sam Whitfield was seen near the pier at midnight.",
                immutable=True,
            ),
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


# Mission20 の初期 FS: 探偵事務所の1階層マップとは別レイアウト（FHS）。
# /etc・/var/log・/tmp・/home の4区画を巡って黒幕（mr_black）の住民登録に辿り着く。
_MISSION20_FS = {
    "root": {
        "type": "dir",
        "children": {
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    },
    "etc": {
        "type": "dir",
        "children": {
            "hosts": _file(
                "127.0.0.1 localhost\n10.66.6.6 ghost.example", immutable=True
            ),
            "passwd": _file(
                "root:x:0:0:root:/root:/bin/sh\n"
                "detective:x:1000:1000:detective:/home/detective:/bin/sh\n"
                "mr_black:x:1001:1001:mr_black:/home/mr_black:/bin/sh",
                immutable=True,
            ),
        },
    },
    "var": {
        "type": "dir",
        "children": {
            "log": {
                "type": "dir",
                "children": {
                    "entry.log": _file(
                        "08:00 detective entered\n"
                        "23:50 unknown entered via side door\n"
                        "23:55 unknown left toward /home/mr_black\n"
                        "00:10 detective entered",
                        immutable=True,
                    ),
                },
            },
        },
    },
    "tmp": {
        "type": "dir",
        "children": {
            ".forgotten": _file(
                "reminder: burn the ledger before sunrise - mr_black",
                immutable=True,
            ),
        },
    },
    "home": {
        "type": "dir",
        "children": {
            "mr_black": {
                "type": "dir",
                "children": {
                    "registration.txt": _file(
                        "RESIDENT: mr_black\nOCCUPATION: unknown", immutable=True
                    ),
                },
            },
        },
    },
    "bin": {"type": "dir", "children": {}},
}


# Mission21 の初期 env_vars: PATH が汚染され allowlist コマンドが軒並み使えない
# （組み込み=echo/export/printenv/which/type 等と絶対パス実行だけが生き残る）。
_MISSION21_BAD_PATH = "/tmp/.stolen"
_MISSION21_GOOD_PATH = "/usr/local/bin:/usr/bin:/bin"
_MISSION21_ENV_VARS = {"PATH": _MISSION21_BAD_PATH, "HOME": "/root"}

_MISSION21_FS = {
    "root": {
        "type": "dir",
        "children": {
            "hint.txt": _file(
                "The tools are not gone. Someone broke the list of where to\n"
                "find them (PATH). Check: echo $PATH or printenv PATH.\n"
                "Trust the absolute path: /bin/ls still works.\n"
                "Recover with: export PATH=/usr/local/bin:/usr/bin:/bin",
                immutable=True,
            ),
            "case_file.sh": _file(
                "# 事件ファイル: sh case_file.sh で判定する\n", immutable=True
            ),
        },
    }
}


# Mission22（最終事件）: これまで学んだ全技術を関所として直列に配置する。
# find → ssh(ghost.example の既存証拠を再利用) → chmod → grep|sort|uniq -c →
# tar → md5sum → 自作 sh → 黒幕名（Mission12 の黒幕 Selene Vance と同一人物）報告 →
# git push。
_MISSION22_CULPRIT = "Selene Vance"
_MISSION22_BURNER = "555-0199"
_MISSION22_NOTE = "NOTE: meet at the pier - S.V."
_MISSION22_NOTE_MD5 = "18567fb6f71f0a1f44814c158a8f7798"

_MISSION22_CALL_COUNTS = {
    _MISSION22_BURNER: 6,  # 最頻出＝vault の手がかりと一致する裏取り対象
    "555-0142": 3,
    "555-0007": 1,
}


def _mission22_calls_log() -> str:
    groups = [[num] * count for num, count in _MISSION22_CALL_COUNTS.items()]
    scattered: list[str] = []
    while any(groups):
        for g in groups:
            if g:
                scattered.append(g.pop())
    return "\n".join(f"TEL: {num}" for num in scattered)


_MISSION22_FS = {
    "root": {
        "type": "dir",
        "children": {
            "clues": {
                "type": "dir",
                "children": {
                    "deep": {
                        "type": "dir",
                        "children": {
                            "access.key": _file(
                                "connect via ssh to ghost.example", immutable=True
                            ),
                        },
                    },
                },
            },
            "vault": {
                "type": "dir",
                "children": {
                    "locked.txt": _mode_file(
                        f"burner number traced to: {_MISSION22_BURNER}",
                        "---------",
                        immutable=False,
                    ),
                },
            },
            "logs": {
                "type": "dir",
                "children": {
                    "calls.log": _file(_mission22_calls_log(), immutable=True),
                },
            },
            "evidence.tar": _archive_file(
                "tar", {"final_note.txt": _file(_MISSION22_NOTE, immutable=True)}
            ),
            "ledger.txt": _file(f"ORIGINAL MD5: {_MISSION22_NOTE_MD5}", immutable=True),
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
    # 初期仮想 cron テーブル（crontab -l の対象）。None は空（デフォルト）。
    initial_cron_jobs: list[dict] | None = None
    # Mission15 専用: history が表示する「情報屋の履歴」（自分の履歴ではない）。
    informant_history: list[str] | None = None
    # 初期環境変数（PATH 汚染等）。None はデフォルト（正常な PATH）。
    initial_env_vars: dict[str, str] | None = None
    # 3段階ヒント（相棒キャラクターの語り。設計指示書 § 11 機能4 / Mission参照 § 1-D）。
    # 空 = 未配線（Mission4〜22 は今回対象外。フロントはボタン自体を非表示にする）。
    hints: list[str] = field(default_factory=list)
    # 進行案内「独り言レイヤー」（STORY-01。Mission参照ファイル § 独り言（story_beats）と
    # ヒントの共通仕様）。各要素: {"id", "when": "start"|"after"|"clear",
    # "text", "line"(任意・正規表現), "output"(任意・正規表現), "remote"(任意・bool)}。
    # 空 = 未配線（Mission4〜22 は今回対象外）。純粋関数側の消費は app/evaluator/story.py。
    story_beats: list[dict] = field(default_factory=list)

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
        hints=[
            "ゴール: /root/desk/businesscard.txt に自分の名前を書き込み、sh case_file.sh で確認 → git add → git commit -m → git push で提出する。",
            '名刺は cat で読む。書き換えは echo "NAME: 名前" > businesscard.txt（上書き）。エディタ（vi 等）は無い。',
            'cat businesscard.txt（中身を読む）→ echo "NAME: 名前" > businesscard.txt（上書きで書き込む）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m "done"（セーブ）→ git push（提出）',
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "雨の月曜。依頼人は俺の名刺を一瞥して言った——名前が無い、と。\n……確か、机（desk）の上に置きっぱなしのはず。"},
            {"id": "desk", "when": "after", "line": r"^(cd|ls) /root/desk", "text": "名刺ファイルが一枚。中身、確かめておかないと。"},
            {"id": "read", "when": "after", "line": r"^cat /root/desk/businesscard\.txt", "text": "NAME: ???……我ながら間抜けな名刺。名前を書き込まないと話にならない。"},
            {"id": "no_editor", "when": "after", "line": r"^(vi|vim|nano|emacs)\b", "output": "command not allowed", "text": "この事務所にまともなエディタは無い……。書き込むなら echo で流し込む（`>`）しかないか。"},
            {"id": "wrote", "when": "after", "line": r"^echo .*> /root/desk/businesscard\.txt", "text": "これでいい。名前の入った名刺。\n本部に出す前に、事件ファイル（case_file.sh）で確認しておくか。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "確認は通った！ あとは記録して本部へ——add、commit、そして push。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "事件ファイルが突き返された!? 何か足りない……名刺をもう一度読み直してみるか。"},
            {"id": "push_fail", "when": "after", "line": r"^git push", "output": "requirements not met", "text": "本部が受け付けない……。確認（sh case_file.sh）を通してから、記録し直さないと駄目らしい。"},
            {"id": "clear", "when": "clear", "text": "名刺が本部に届いた。これで俺の名前は、この街の帳簿に載ったはず。\n——今やったことは、本物の黒い画面でもそのまま通じる。"},
        ],
    ),
    MissionDef(
        2, "Park Cat Search", "公園の猫を探せ",
        "公園で猫ファイルを find で探し出し、報告書に絶対パスと状態を書いて完了する。",
        ["find", "grep", "awk", "sort", "uniq"],
        # 判定は judge.py の Mission2 専用ロジック（find 使用・報告書（echo 行）の
        # 絶対パス記載・STATUS 抽出）で行うため expected_script_patterns は空にする
        # （誤答メッセージを個別化するため）。読み方（cat/grep）は絶対パスでも
        # cd 後の相対パスでも自由（P3-08e）。
        initial_filesystem=_MISSION2_FS,
        initial_current_path="/root/park",
        hints=[
            "ゴール: catinfo.txt を find で見つけ、その絶対パスと STATUS の値を echo で書き出し、sh case_file.sh → git push する。",
            'find /root/park -name catinfo.txt で場所が分かる。中身は cat で読む。報告は echo "/root/park/swing/catinfo.txt STATUS: stray" のように絶対パス（/ から）を含める。',
            'find /root/park -name catinfo.txt（名前で探す）→ cat /root/park/swing/catinfo.txt（読む）→ echo "/root/park/swing/catinfo.txt STATUS: stray" > /root/park/report.txt（報告を書く）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m "cat"（セーブ）→ git push（提出）',
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "依頼は迷い猫。名前はマイク、黒。公園（park）で最後に見られたらしい。\n玄関を出て、公園へ向かわないと！"},
            {"id": "park", "when": "after", "line": r"^(cd|ls) /root/park", "text": "ベンチ、噴水、遊具……区画が多い。当てずっぽうに歩けば日が暮れる。名前で探す（find）のが探偵の仕事、のはず。"},
            {"id": "found", "when": "after", "line": r"^find ", "output": r"catinfo\.txt", "text": "出た！ 猫の記録は遊具（swing）の傍。"},
            {"id": "read", "when": "after", "line": r"^cat .*catinfo\.txt", "text": "STATUS: stray——野良か。依頼人には場所と状態を報告しないと。\n報告書に書く場所は `/` から始まる住所で。「swing の傍」じゃ、誰も辿り着けない。"},
            {"id": "fail_abs", "when": "after", "line": r"^sh .*case_file\.sh", "output": "absolute path required", "text": "突き返された!? 住所が途中から……`/` から書き直さないと。"},
            {"id": "fail_status", "when": "after", "line": r"^sh .*case_file\.sh", "output": "cat status not found", "text": "状態が抜けている。STATUS の欄を報告に写さないと。"},
            {"id": "fail_find", "when": "after", "line": r"^sh .*case_file\.sh", "output": "use find", "text": "歩き回って見つけたのはいいが、次からは find で絞ろう。この公園より広い場所も来るはず。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "これで報告になる。記録して、本部へ。"},
            {"id": "clear", "when": "clear", "text": "猫は遊具の下で丸くなっていた。住所が正確なら、誰でも同じ場所へ辿り着ける——それが絶対パス、というやつか。"},
        ],
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
        hints=[
            "ゴール: ssh amusement_park で接続し、園内の 3 ファイルから Code: / Wire: / Height: を読み取って echo で書き出し、sh case_file.sh → git push する。",
            '接続後は find . -type f で 3 ファイルを列挙し cat で読む。報告は echo "Code: XXXX" のように「キー: 値」の書式で 3 行。事務所へ戻るのは exit。',
            'ssh amusement_park（接続）→ find . -type f（ファイル列挙）→ cat booth/manual.txt / cat ferris/wiring.txt / cat sign/notice.txt（Code・Wire・Height を読む）→ echo "Code: ...", echo "Wire: ...", echo "Height: ..."（報告 3 行）→ sh case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m "bomb"（セーブ）→ git push（提出）',
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "電話の声は震えていた。遊園地に爆弾が仕掛けられた、解除コードは園内の設備に散らばっている、と。\nここからじゃ届かない。回線を繋いで（ssh）、門（amusement_park）まで踏み込まないと！"},
            {"id": "no_host", "when": "after", "line": r"^ssh ", "output": "Host not found", "text": "回線が繋がらない……。宛先の綴り、合っているか？"},
            {"id": "connected", "when": "after", "line": r"^ssh amusement_park", "text": "繋がった。ここは門の前（/gate）。プロンプトの色が変わった——今は向こう側にいる、ということか。"},
            {"id": "survey", "when": "after", "line": r"^(ls|find)\b", "remote": True, "text": "案内所（booth）、観覧車（ferris）、看板（sign）……設備は三つ。手がかりも三つのはず。"},
            {"id": "code", "when": "after", "line": r"^cat .*manual\.txt", "remote": True, "text": "Code が出た！ 控えておこう。"},
            {"id": "wire", "when": "after", "line": r"^cat .*wiring\.txt", "remote": True, "text": "切る線の色。間違えたら終わり……。"},
            {"id": "height", "when": "after", "line": r"^cat .*notice\.txt", "remote": True, "text": "身長制限……これが最後の数字か？"},
            {"id": "no_way_back", "when": "after", "line": r"^cd /root", "output": "directory not found", "remote": True, "text": "ここは向こう側。事務所へ戻るなら回線を切る（exit）しかない、はず。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "まだ揃っていない!? Code、Wire、Height——三つとも報告に書いたか……。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "三つ揃った！ 記録して本部へ。処理班が待っている。"},
            {"id": "clear", "when": "clear", "text": "観覧車が止まった。回線を切って（exit）、事務所へ戻ろう。\n——ssh は、遠くの機械を自分の机にする道具、なのかもしれない。"},
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
        # 判定は judge.py の Mission12 専用ロジック（dig→ping→ssh の出現順序 +
        # remote 証拠閲覧 + 黒幕名報告）で行うため expected_script_patterns は空。
        # 現場（/den 以下）は SSH_HOSTS["ghost.example"] に定義（local FS 不要）。
    ),
    MissionDef(
        13, "Midnight Broadcast", "深夜0時の犯行予告",
        "cron 書式を解読し、危険な時限ジョブだけを解除する。",
        ["crontab", "date", "grep"],
        # クリア条件: crontab -l 実行 + 危険ジョブの発動日時（FRIDAY 00:00）の記述。
        expected_script_patterns=[
            r"crontab\s+-l",
            r"FRIDAY\s+00:00",
        ],
        initial_filesystem=_MISSION13_FS,
        initial_cron_jobs=_MISSION13_CRON_JOBS,
    ),
    MissionDef(
        14, "Hall of Mirrors", "鏡の館",
        "ls -l と file でシンボリックリンクを見抜き、実体の絶対パスを特定する。",
        ["ls", "file"],
        # 判定は judge.py の Mission14 専用ロジック（report の echo 行に実体の
        # 絶対パスがあるか。リンクパスのみの報告は不合格）で行う。
        initial_filesystem=_MISSION14_FS,
    ),
    MissionDef(
        15, "The Informant's Trail", "情報屋の足取り",
        "history とログから操作を再現し、情報屋の行き先を突き止める。",
        ["history", "tail", "grep"],
        # 判定は judge.py の Mission15 専用ロジック（informant_history の再現 +
        # 行き先の報告）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION15_FS,
        informant_history=_MISSION15_HISTORY,
    ),
    MissionDef(
        16, "The Great Sweep", "一斉捜索令状",
        "glob と引用符で対象を絞り込み、空白入りファイル名も開封する。",
        ["find", "grep"],
        # 判定は judge.py の Mission16 専用ロジック（数字 glob 使用 + 引用符付き
        # cat 成功 + コード報告）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION16_FS,
        initial_current_path="/root/warehouse",
    ),
    MissionDef(
        17, "Fingerprint", "指紋は嘘をつかない",
        "md5sum で契約書コピーを照合し、改ざんされた1通を特定する。",
        ["md5sum", "sha256sum", "diff", "sort"],
        # クリア条件: md5sum 実行 + 改ざんファイル名 copy_4 の記述（Mission参照 § 17）。
        expected_script_patterns=[
            r"\bmd5sum\b",
            r"copy_4",
        ],
        initial_filesystem=_MISSION17_FS,
    ),
    MissionDef(
        18, "Silence in the Static", "雑音の中の声",
        "2>/dev/null でエラーを捨て、必要な出力だけを取り出す。",
        ["grep", "find"],
        # クリア条件: 2>/dev/null の実行 + 手がかり（PLATE番号）の記述（Mission参照 § 18）。
        expected_script_patterns=[
            r"2>\s*/dev/null",
            r"PLATE: NX-4471",
        ],
        initial_filesystem=_MISSION18_FS,
    ),
    MissionDef(
        19, "The Detective's Playbook", "捜査手順書を書け",
        "変数と if を使ったシェルスクリプトを自作し、実行して判定する。",
        ["sh", "grep"],
        # 判定は judge.py の Mission19 専用ロジック（patrol.sh 実行 + FOUND 出力 +
        # 自作スクリプトに変数定義と if を含む）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION19_FS,
    ),
    MissionDef(
        20, "Map of the City", "この街の地図",
        "FHS（/etc, /var/log, /home, /tmp）を巡り、黒幕の住民登録を探す。",
        ["grep", "tail"],
        # 判定は judge.py の Mission20 専用ロジック（/etc・/var/log・/tmp・/home の
        # 4区画探索 + 黒幕名報告）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION20_FS,
    ),
    MissionDef(
        21, "The Missing Toolbox", "消えた道具箱",
        "汚染された PATH を診断し、export で復旧して道具（コマンド）を取り戻す。",
        ["printenv", "export", "unset", "which", "type", "grep", "find"],
        # 判定は judge.py の Mission21 専用ロジック（PATH 正常値への復旧 +
        # 復旧後のコマンド成功履歴 + 汚染 PATH 値の報告）で行うため
        # expected_script_patterns は空。
        initial_filesystem=_MISSION21_FS,
        initial_env_vars=_MISSION21_ENV_VARS,
    ),
    MissionDef(
        22, "Case Closed", "最終事件 — すべてを繋げろ",
        "学んだ全技術を関所として突破し、黒幕の名を本部に提出する。",
        ["find", "ssh", "exit", "chmod", "grep", "sort", "uniq", "tar", "md5sum", "sh"],
        # 判定は judge.py の Mission22 専用ロジック（8関所を直列検査。欠けた関所を
        # "Warning: checkpoint <n> incomplete" で示す）で行うため
        # expected_script_patterns は空。
        initial_filesystem=_MISSION22_FS,
    ),
]

MISSIONS: dict[int, MissionDef] = {m.id: m for m in _DEFS}


def get_mission(mission_id: int) -> MissionDef | None:
    return MISSIONS.get(mission_id)


def all_missions() -> list[MissionDef]:
    return [MISSIONS[i] for i in sorted(MISSIONS)]


# =============================================================================
# Part5 P3-03: 永続統合ワールドの仮想FS（_WORLD_FS）
# =============================================================================
# 「22 Mission 分の区画を最初から実体として持ち、未解放はディレクトリ権限で
# 不可視にする」統合ワールド（context/04_task_backlog.md § Part 5）を、既存の
# Mission 別 `initial_filesystem` から機械的に組み立てる。
#
# Mission 別 FS はカットオーバー（P3-10 以降）まで現役なので、ここでは元の dict を
# 一切変更せず deepcopy して変換する。組み立ての規則は 3 つだけ:
#   1. `case_file.sh` は全除外（P3-04 で動的生成に置き換える）
#   2. `/root` 直下の裸置きファイルは Mission 専用サブディレクトリへ移設（_RELOCATIONS）
#   3. 区画の衝突は原則エラー。意図的な相乗りのみ _ADDITIVE_MERGE_PATHS で明示許可


# `/root` 直下に裸置きされていたファイルの移設先（Mission ごと）。
# 移設しないと Mission13 と Mission21 の `hint.txt` のように衝突するうえ、
# ディレクトリ権限ゲート（P3-04）は dir 単位でしか効かず未解放にできない。
_RELOCATIONS: dict[int, dict[str, str]] = {
    4: {"tape.log": "wiretap_room"},
    9: {"evidence.dat": "evidence_locker"},
    10: {"original.txt": "will_office", "submitted.txt": "will_office"},
    13: {"hint.txt": "crontab_room"},
    15: {"journal.log": "informant_trail"},
    19: {"sample.sh": "precinct_desk", "evidence.txt": "precinct_desk"},
    21: {"hint.txt": "toolbox_room"},
    # Mission22 は clues/vault/logs を持つが evidence.tar / ledger.txt が裸置きだった。
    # 最終事件の証拠が Mission1 から丸見えになるため clues/ に収容する。
    22: {"evidence.tar": "clues", "ledger.txt": "clues"},
}

# 移設によりカットオーバー（P3-08/P3-12/P3-13）で追随が要る旧パス参照:
#   - judge.py `_MISSION10_ORIGINAL_PATH` / `_MISSION10_SUBMITTED_PATH`
#     → /root/will_office/original.txt・submitted.txt
#   - judge.py `_MISSION19_SCRIPT_PATH`（プレイヤーが作る patrol.sh の置き場）
#     → /root/precinct_desk/patrol.sh
#   - `_MISSION15_HISTORY`（情報屋の履歴）→ /root/informant_trail/journal.log
# いずれも Mission 別 FS がまだ現役のためここでは変更しない（world 内の文章・
# symlink が指すパスの実在は tests/test_world_fs.py が機械的に検査している）。

# 複数 Mission が同じ場所を共有することを明示的に許可する絶対パス（→ 許可 mission_id）。
# `/root/vault` は Mission5（開かずの資料室）と Mission22（最終事件）の意図的な
# コールバック。ここに無い衝突は設計ミスとして build 時に例外を投げる。
_ADDITIVE_MERGE_PATHS: dict[str, tuple[int, ...]] = {
    "/root/vault": (5, 22),
}

# 各 Mission が所有する区画（ワールド上の絶対パス）。未解放のあいだ不可視にし、
# クリア進行に応じて P3-05 の advance_mission が解放する。ここに載らない Mission
# （3/6/7/12）はローカル FS の区画を持たない（ssh 先・プロセス・cron が舞台）。
_MISSION_AREAS: dict[int, list[str]] = {
    1: ["/root/desk"],
    2: ["/root/park"],
    4: ["/root/wiretap_room"],
    5: ["/root/vault"],
    8: ["/root/bar"],
    9: ["/root/evidence_locker"],
    10: ["/root/will_office"],
    11: ["/root/scraps"],
    13: ["/root/crontab_room"],
    14: ["/root/mirror_hall"],
    15: ["/root/informant_trail"],
    16: ["/root/warehouse"],
    17: ["/root/contracts"],
    18: ["/root/archive"],
    19: ["/root/precinct_desk"],
    # Mission20 の FHS（/etc・/var・/tmp・/bin）は街の常設インフラなので常時公開し、
    # 黒幕の住居だけを被ゲート区画にする（Mission12 の dig 発見体験を潰さないため
    # /etc/hosts の ghost.example 行は別途 P3-05 で追記する）。
    20: ["/home/mr_black"],
    21: ["/root/toolbox_room"],
    22: ["/root/clues", "/root/logs"],
}

# Mission に紐付かず最初から通行できるディレクトリ（探偵の自宅 + 街のインフラ）。
_ALWAYS_OPEN_DIRS = ["/root", "/etc", "/var", "/tmp", "/bin", "/home"]

# ディレクトリ権限ゲート（P3-04）の値。owner が異なると mode の other ビットを
# 見るため、未解放区画は system 所有 + 全ビット無しで不可視になる。
OPEN_DIR_MODE = "rwxr-xr-x"
OPEN_DIR_OWNER = "detective"
LOCKED_DIR_MODE = "---------"
LOCKED_DIR_OWNER = "system"

# Mission12 解放時に /etc/hosts へ追記される行（P3-05）。初期ワールドには含めない。
HOSTS_PATH = "/etc/hosts"
GHOST_HOSTS_LINE = "10.66.6.6 ghost.example"


def _world_dir() -> dict:
    return {"type": "dir", "children": {}}


def _copy_without_case_files(children: dict) -> dict:
    """children を deepcopy しつつ `case_file.sh` を再帰的に取り除く。"""
    out: dict = {}
    for name, node in children.items():
        if name == CASE_FILE_NAME and node.get("type") == "file":
            continue
        if node.get("type") == "dir":
            new_node = {k: copy.deepcopy(v) for k, v in node.items() if k != "children"}
            new_node["children"] = _copy_without_case_files(node.get("children", {}))
            out[name] = new_node
        else:
            out[name] = copy.deepcopy(node)
    return out


def _relocate_root_files(mission_id: int, children: dict) -> dict:
    """`/root` 直下の裸置きファイルを _RELOCATIONS の部屋へ移す。"""
    moves = _RELOCATIONS.get(mission_id, {})
    out = {name: node for name, node in children.items() if name not in moves}
    for name, node in children.items():
        dest = moves.get(name)
        if dest is None:
            continue
        room = out.setdefault(dest, _world_dir())
        if room.get("type") != "dir":
            raise ValueError(f"relocation target /root/{dest} is not a directory")
        if name in room["children"]:
            raise ValueError(f"relocation collision at /root/{dest}/{name}")
        room["children"][name] = node
    return out


def _merge_children(dest: dict, src: dict, mission_id: int, base_path: str) -> None:
    """src の children を dest へマージする。想定外の衝突は例外にする。"""
    for name, node in src.items():
        path = f"{base_path}/{name}"
        if name not in dest:
            dest[name] = node
            continue
        allowed = _ADDITIVE_MERGE_PATHS.get(path, ())
        if (
            mission_id not in allowed
            or dest[name].get("type") != "dir"
            or node.get("type") != "dir"
        ):
            raise ValueError(
                f"world FS conflict at {path} (mission {mission_id}). "
                f"意図した相乗りなら _ADDITIVE_MERGE_PATHS に追加すること"
            )
        _merge_children(dest[name]["children"], node["children"], mission_id, path)


def _node_at(world: dict, abs_path: str) -> dict | None:
    """ワールド（「/」直下の children map）から絶対パスのノードを引く。"""
    node: dict | None = {"type": "dir", "children": world}
    for seg in [s for s in abs_path.split("/") if s]:
        if node is None or node.get("type") != "dir":
            return None
        node = node.get("children", {}).get(seg)
    return node


def _set_dir_gate(world: dict, abs_path: str, *, released: bool) -> None:
    node = _node_at(world, abs_path)
    if node is None or node.get("type") != "dir":
        raise ValueError(f"mission area {abs_path} does not exist in the world FS")
    node["mode"] = OPEN_DIR_MODE if released else LOCKED_DIR_MODE
    node["owner"] = OPEN_DIR_OWNER if released else LOCKED_DIR_OWNER


def _strip_ghost_hosts_line(world: dict) -> None:
    """初期 /etc/hosts から ghost.example 行を落とす（Mission12 で追記される）。"""
    node = _node_at(world, HOSTS_PATH)
    if node is None or node.get("type") != "file":
        return
    lines = [ln for ln in node["content"].split("\n") if GHOST_HOSTS_LINE not in ln]
    node["content"] = "\n".join(lines)


def _build_world_fs() -> dict:
    world: dict = {"root": _world_dir()}
    for mission in all_missions():
        if mission.initial_filesystem is None:
            continue
        pruned = _copy_without_case_files(mission.initial_filesystem)
        root_node = pruned.pop("root", None)
        if root_node is not None:
            relocated = _relocate_root_files(mission.id, root_node.get("children", {}))
            _merge_children(world["root"]["children"], relocated, mission.id, "/root")
        # `/root` 以外（Mission20 の FHS: /etc・/var・/tmp・/bin・/home）。
        _merge_children(world, pruned, mission.id, "")

    _strip_ghost_hosts_line(world)

    for path in _ALWAYS_OPEN_DIRS:
        _set_dir_gate(world, path, released=True)
    first_mission_id = all_missions()[0].id
    for mission_id, paths in _MISSION_AREAS.items():
        for path in paths:
            _set_dir_gate(world, path, released=mission_id == first_mission_id)
    return world


_WORLD_FS = _build_world_fs()


def build_world_filesystem() -> dict:
    """永続統合ワールドの初期 filesystem（毎回まっさらなコピーを返す）。"""
    return copy.deepcopy(_WORLD_FS)


def mission_area_paths(mission_id: int) -> list[str]:
    """その Mission が所有する区画の絶対パス（解放処理 P3-05 が使う）。"""
    return list(_MISSION_AREAS.get(mission_id, []))
