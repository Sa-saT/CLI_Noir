"""Mission カタログ（Mission1〜22）。

出典: docs/Mission参照ファイル.md。title は英語名、title_ja は画面表示名。
allowed_commands は各 Mission の必須コマンド + 共通の基本操作（ls/cd/cat/pwd/echo/git）。
詳細正規表現・初期FS は実装時に本 MissionDef を拡張する（設計指示書 § 11 / § 5）。

`_build_world_fs()`（Part5 P3-03）は 22 Mission分の `_MISSIONn_FS` を1つの永続統合
ワールド filesystem へ合成する。既存の `MissionDef.initial_filesystem` は
Mission 単位の旧フロー（`app/ws/terminal.py::build_initial_state`）が P3-09/P3-10の
カットオーバーまで引き続き使うため、一切変更しない（合成は新規に別領域を組み立てるだけ。
`context/04_task_backlog.md` Part5 参照）。
"""

import copy
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
    # 統合ワールド（Part5）でこの Mission が所有する絶対パス（ディレクトリ）。
    # 未解放時はこのディレクトリの mode が "---------"/owner "system" になり、
    # 直前 Mission クリアで解放される（`app/evaluator/progress.py::advance_mission`）。
    # 空 = FS を持たない Mission（remote 限定・process テーブルのみ等）。
    owned_paths: list[str] = field(default_factory=list)

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
            "まず机(desk)を調べ、名刺ファイルの場所を確認しよう。",
            "名刺にはあなたのユーザー名を書き込む必要があります。",
            "編集後は git add -> git commit -m -> git push の順で進めよう。",
        ],
        owned_paths=["/root/desk"],
    ),
    MissionDef(
        2, "Park Cat Search", "公園の猫を探せ",
        "公園で猫ファイルを絶対パスで探索し、条件を満たして完了する。",
        ["find", "grep", "awk", "sort", "uniq"],
        # 判定は judge.py の Mission2 専用ロジック（find 使用・絶対パス・STATUS 抽出）で
        # 行うため expected_script_patterns は空にする（誤答メッセージを個別化するため）。
        initial_filesystem=_MISSION2_FS,
        initial_current_path="/root/park",
        hints=[
            "公園は広い。当てずっぽうで歩き回っても日が暮れるだけだ。的を絞る道具を使え。",
            "find を使え。猫の情報ファイルは、遊具の近くのどこかに眠っている。",
            "find /root/park -name catinfo.txt — 見つけたら絶対パスで読み、STATUS の欄まで報告書に書き写せ。",
        ],
        owned_paths=["/root/park"],
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
            "遊園地の門の向こうに、答えはある。だがここからじゃ届かない。回線を繋げ。",
            "ssh amusement_park で門(gate)まで踏み込め。中の設備を一つずつ find と cat で洗え。",
            "ssh amusement_park のあと find . -type f で3つの手がかりを探し、cat で読んだ Code / Wire / Height を echo で報告書に書き出せ。",
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
        owned_paths=["/root/wiretap_room"],
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
        owned_paths=["/root/vault"],
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
        owned_paths=["/root/bar"],
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
        owned_paths=["/root/evidence_locker"],
    ),
    MissionDef(
        10, "The Forged Letter", "改ざんされた遺言状",
        "diff で改ざん箇所を特定し、sed で原本どおりに復元する。",
        ["diff", "sed"],
        # 判定は judge.py の Mission10 専用ロジック（diff 実行 + submitted.txt が
        # original.txt と完全一致）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION10_FS,
        owned_paths=["/root/will_office"],
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
        owned_paths=["/root/scraps"],
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
        owned_paths=["/root/crontab_room"],
    ),
    MissionDef(
        14, "Hall of Mirrors", "鏡の館",
        "ls -l と file でシンボリックリンクを見抜き、実体の絶対パスを特定する。",
        ["ls", "file"],
        # 判定は judge.py の Mission14 専用ロジック（report の echo 行に実体の
        # 絶対パスがあるか。リンクパスのみの報告は不合格）で行う。
        initial_filesystem=_MISSION14_FS,
        owned_paths=["/root/mirror_hall"],
    ),
    MissionDef(
        15, "The Informant's Trail", "情報屋の足取り",
        "history とログから操作を再現し、情報屋の行き先を突き止める。",
        ["history", "tail", "grep"],
        # 判定は judge.py の Mission15 専用ロジック（informant_history の再現 +
        # 行き先の報告）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION15_FS,
        informant_history=_MISSION15_HISTORY,
        owned_paths=["/root/informant_trail"],
    ),
    MissionDef(
        16, "The Great Sweep", "一斉捜索令状",
        "glob と引用符で対象を絞り込み、空白入りファイル名も開封する。",
        ["find", "grep"],
        # 判定は judge.py の Mission16 専用ロジック（数字 glob 使用 + 引用符付き
        # cat 成功 + コード報告）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION16_FS,
        initial_current_path="/root/warehouse",
        owned_paths=["/root/warehouse"],
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
        owned_paths=["/root/contracts"],
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
        owned_paths=["/root/archive"],
    ),
    MissionDef(
        19, "The Detective's Playbook", "捜査手順書を書け",
        "変数と if を使ったシェルスクリプトを自作し、実行して判定する。",
        ["sh", "grep"],
        # 判定は judge.py の Mission19 専用ロジック（patrol.sh 実行 + FOUND 出力 +
        # 自作スクリプトに変数定義と if を含む）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION19_FS,
        owned_paths=["/root/precinct_desk"],
    ),
    MissionDef(
        20, "Map of the City", "この街の地図",
        "FHS（/etc, /var/log, /home, /tmp）を巡り、黒幕の住民登録を探す。",
        ["grep", "tail"],
        # 判定は judge.py の Mission20 専用ロジック（/etc・/var/log・/tmp・/home の
        # 4区画探索 + 黒幕名報告）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION20_FS,
        owned_paths=["/home/mr_black"],
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
        owned_paths=["/root/toolbox_room"],
    ),
    MissionDef(
        22, "Case Closed", "最終事件 — すべてを繋げろ",
        "学んだ全技術を関所として突破し、黒幕の名を本部に提出する。",
        ["find", "ssh", "exit", "chmod", "grep", "sort", "uniq", "tar", "md5sum", "sh"],
        # 判定は judge.py の Mission22 専用ロジック（8関所を直列検査。欠けた関所を
        # "Warning: checkpoint <n> incomplete" で示す）で行うため
        # expected_script_patterns は空。
        initial_filesystem=_MISSION22_FS,
        owned_paths=["/root/clues", "/root/logs"],
    ),
]

MISSIONS: dict[int, MissionDef] = {m.id: m for m in _DEFS}


def get_mission(mission_id: int) -> MissionDef | None:
    return MISSIONS.get(mission_id)


def all_missions() -> list[MissionDef]:
    return [MISSIONS[i] for i in sorted(MISSIONS)]


# --- 永続統合ワールド FS（Part5 P3-03）---
# 裸置きだった約7Mission分のファイルを専用サブディレクトリへ移設する（命名は
# context/04_task_backlog.md Part5 P3-03 で確定した案）。
_WORLD_RELOCATIONS: dict[int, dict[str, list[str]]] = {
    4: {"tape.log": ["wiretap_room", "tape.log"]},
    9: {"evidence.dat": ["evidence_locker", "evidence.dat"]},
    10: {
        "original.txt": ["will_office", "original.txt"],
        "submitted.txt": ["will_office", "submitted.txt"],
    },
    13: {"hint.txt": ["crontab_room", "hint.txt"]},
    15: {"journal.log": ["informant_trail", "journal.log"]},
    19: {
        "sample.sh": ["precinct_desk", "sample.sh"],
        "evidence.txt": ["precinct_desk", "evidence.txt"],
    },
    21: {"hint.txt": ["toolbox_room", "hint.txt"]},
}

# root 直下で複数 Mission が同じディレクトリ名を意図的に共有し、上書きではなく
# 加算マージするディレクトリ（vault = Mission5 の元祖 + Mission22 のコールバック）。
# 汎用衝突解決アルゴリズムにはしない（意図しない衝突を握りつぶさないため）。ここに
# 無い名前が root 直下で複数 Mission から定義されたら `_merge_root_children` が
# ValueError を送出する。
_ADDITIVE_MERGE_DIRS: dict[str, set[int]] = {"vault": {5, 22}}

# 常時公開の FHS システムディレクトリ（Mission20 が定義するが、この4つは Mission20
# 未解放でも常に traverse 可能。`/home/mr_black` だけ Mission20 専用にゲートする。
# Mission20の矛盾解消: 設計指示書 § 5 / Part5 背景節を参照）。
_PUBLIC_FHS_DIRS = ("etc", "var", "tmp", "bin")

_LOCKED_MODE = "---------"
_LOCKED_OWNER = "system"
_OPEN_MODE = "rwxr-xr-x"
_OPEN_OWNER = "detective"


def _merge_children_additive(dest: dict, name: str, src_children: dict) -> None:
    """dest[name] のディレクトリ children に src_children を加算マージする。

    キーが衝突したら例外を送出する（意図しない上書きを握りつぶさないため）。
    """
    node = dest.setdefault(name, {"type": "dir", "children": {}})
    for key, value in src_children.items():
        if key in node["children"]:
            raise ValueError(
                f"world FS additive merge collision: '{name}/{key}' defined twice"
            )
        node["children"][key] = value


def _place_relocated(dest: dict, dest_segments: list[str], node: dict) -> None:
    """dest（world root children）に dest_segments で示すサブパスへ node を配置する。"""
    cur = dest
    for seg in dest_segments[:-1]:
        cur = cur.setdefault(seg, {"type": "dir", "children": {}})["children"]
    leaf = dest_segments[-1]
    if leaf in cur:
        raise ValueError(f"world FS relocation collision at {'/'.join(dest_segments)}")
    cur[leaf] = node


def _strip_case_file_sh(node: dict) -> None:
    """node 配下から `case_file.sh` を再帰的に除去する（in-place）。

    Mission によって `case_file.sh` の配置深さが異なる（例: Mission1 は
    `/root/case_file.sh` 直下、Mission2 は `/root/park/case_file.sh`、Mission5 は
    `/root/vault/inner/case_file.sh`）ため、トップレベルのキー名だけでは除外し切れない。
    P3-04 が `/root/case_file.sh` をアクティブ Mission から動的生成する方式に
    置き換えるため、静的マージからは深さを問わず全除外する（/proc と同じ扱い）。
    """
    if node.get("type") != "dir":
        return
    children = node.get("children", {})
    children.pop("case_file.sh", None)
    for child in children.values():
        _strip_case_file_sh(child)


def _merge_root_children(world_root_children: dict, mission: MissionDef) -> None:
    """mission の initial_filesystem["root"]["children"] を world の /root 直下へ合成する。

    `case_file.sh` は深さを問わず全 Mission で除外する（`_strip_case_file_sh` 参照）。
    """
    fs_dict = mission.initial_filesystem
    if fs_dict is None:
        return
    root_children = fs_dict.get("root", {}).get("children", {})
    relocations = _WORLD_RELOCATIONS.get(mission.id, {})
    for name, raw_node in root_children.items():
        if name == "case_file.sh":
            continue
        node = copy.deepcopy(raw_node)
        _strip_case_file_sh(node)
        if name in relocations:
            _place_relocated(world_root_children, relocations[name], node)
            continue
        if name in _ADDITIVE_MERGE_DIRS:
            if mission.id not in _ADDITIVE_MERGE_DIRS[name]:
                raise ValueError(
                    f"Mission{mission.id} defines additive-merge dir '{name}' but is "
                    "not listed in _ADDITIVE_MERGE_DIRS — add it explicitly if this "
                    "shared directory is intentional."
                )
            _merge_children_additive(world_root_children, name, node.get("children", {}))
            continue
        if name in world_root_children:
            raise ValueError(
                f"world FS root collision: '{name}' defined by more than one Mission "
                f"(latest: Mission{mission.id}). Add it to _WORLD_RELOCATIONS or "
                "_ADDITIVE_MERGE_DIRS if this is intentional."
            )
        world_root_children[name] = node


def _merge_top_level(world: dict, mission: MissionDef) -> None:
    """root 以外のトップレベルキー（Mission20 の FHS: etc/var/tmp/home/bin）を合成する。"""
    fs_dict = mission.initial_filesystem
    if fs_dict is None:
        return
    for top_key, top_node in fs_dict.items():
        if top_key == "root":
            continue
        if top_node.get("type") != "dir":
            raise ValueError(f"unexpected non-dir top-level FS key '{top_key}'")
        node = copy.deepcopy(top_node)
        _strip_case_file_sh(node)
        _merge_children_additive(world, top_key, node.get("children", {}))


def _resolve_world_node(world: dict, abs_path: str) -> dict:
    """world（filesystem 形式の dict）から絶対パスのノードを取得する。

    `app/evaluator/fs.py` の `get_node` と同じ「先頭セグメントが / 直下のトップレベル
    キー」規約（`root_node` 参照）だが、権限ゲート機構（P3-04）より前に world 構築時点
    で使う軽量版のため fs.py には依存しない。
    """
    segs = [p for p in abs_path.split("/") if p]
    if not segs:
        raise ValueError("owned_paths: empty path")
    node = world.get(segs[0])
    if node is None:
        raise ValueError(f"owned_paths references missing top-level node: {abs_path}")
    for seg in segs[1:]:
        node = node.get("children", {}).get(seg)
        if node is None:
            raise ValueError(f"owned_paths references missing node: {abs_path}")
    return node


# Mission20 の /etc/hosts は最初から ghost.example 行を持たない（Mission12 の dig
# 発見体験を守るため。Part5 背景節「Mission20(FHS)の矛盾」）。Mission12 解放時に
# `app/evaluator/progress.py::advance_mission`（P3-05）がこの行を追記する。
GHOST_HOSTS_LINE = "10.66.6.6 ghost.example"


def _hide_ghost_hosts_line(world: dict) -> None:
    etc = world.get("etc")
    if etc is None:
        return
    hosts = etc.get("children", {}).get("hosts")
    if hosts is None:
        return
    lines = [ln for ln in hosts["content"].split("\n") if ln != GHOST_HOSTS_LINE]
    hosts["content"] = "\n".join(lines)


def _apply_initial_lock_state(world: dict) -> None:
    """各 Mission 区画の初期 mode/owner を設定する（Part5 P3-03 項目5）。

    デフォルトは未解放（locked: mode="---------" owner="system"）。Mission1 の区画と
    常時公開 FHS システムディレクトリだけ最初から open。以降の Mission 解放時の
    書き換えは `app/evaluator/progress.py::advance_mission`（P3-05）が行う。
    """
    for mission in all_missions():
        for path in mission.owned_paths:
            node = _resolve_world_node(world, path)
            is_open_from_start = mission.id == 1
            node["mode"] = _OPEN_MODE if is_open_from_start else _LOCKED_MODE
            node["owner"] = _OPEN_OWNER if is_open_from_start else _LOCKED_OWNER

    for fhs_key in _PUBLIC_FHS_DIRS:
        if fhs_key in world:
            world[fhs_key]["mode"] = _OPEN_MODE
            world[fhs_key]["owner"] = _OPEN_OWNER
    if "home" in world:
        world["home"]["mode"] = _OPEN_MODE
        world["home"]["owner"] = _OPEN_OWNER
    # /root 自体は全 Mission 共通の拠点として常時公開する。
    world["root"]["mode"] = _OPEN_MODE
    world["root"]["owner"] = _OPEN_OWNER


def _build_world_fs() -> dict:
    """22 Mission分の初期FSを1つの永続統合ワールド filesystem へ合成する。

    既存の `MissionDef.initial_filesystem`／`_MISSIONn_FS` は変更しない
    （Mission単位の旧フローが P3-09/P3-10 のカットオーバーまで使い続けるため）。
    呼び出しごとに独立した dict を返す（呼び出し側で書き換えても他へ影響しない）。
    """
    world: dict = {"root": {"type": "dir", "children": {}}}
    for mission in all_missions():
        _merge_root_children(world["root"]["children"], mission)
        _merge_top_level(world, mission)
    _hide_ghost_hosts_line(world)
    _apply_initial_lock_state(world)
    return world


# インポート時に一度構築し、リロケーション漏れ・意図しない衝突を即座に検出する
# （fail-fast。Part5 P3-03 検証項目）。呼び出し側は都度 `_build_world_fs()` を
# 呼んで独立した dict を得る。
_build_world_fs()
