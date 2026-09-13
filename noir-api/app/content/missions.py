"""Mission カタログ（Mission1〜22）。

出典: docs/Mission参照ファイル.md。title は英語名、title_ja は画面表示名。
allowed_commands は各 Mission の必須コマンド + 共通の基本操作（ls/cd/cat/pwd/echo/git）。
詳細正規表現・初期FS は実装時に本 MissionDef を拡張する（設計指示書 § 11 / § 5）。

**プレイ順序と id の関係（重要）**: `MissionDef.id` は「安定した事件番号」であり、
プレイ順序そのものではない。**プレイ順序は `_DEFS` リストの並び順**で決まる。
Mission23〜28（後日、中盤〜終盤に挿入予定）は既存 Mission を採番し直さずに
`_DEFS` の途中へ挿入できるようにするための設計で、`id == プレイ順序` という
前提はどこにも置かない。`all_missions()` は常に `_DEFS` の並び順（= プレイ順序）で
返す。ある Mission の「直前/直後の Mission」を知りたいときは
`previous_mission_id()` / `next_mission_id()` を使うこと（`mission_id - 1` /
`mission_id + 1` のような id 演算をしない）。
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
# ヒントが指す inner/ に実行権限のない封印解除スクリプト unseal.sh（chmod +x で解錠）。
# immutable=False で配置し、P2-01 の can_exec 特例（immutable=True は実行可）を
# 適用させない — このため sh 実行には明示的な chmod +x が必須になる。
# （旧: inner/case_file.sh をロックしていたが、統合ワールドでは case_file.sh が
#  /root に動的合成される（P3-04）ため、実行権限パズルの対象を unseal.sh に移した。
#  2026-09-13）
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
                        "The inner room waits at /root/vault/inner.\n"
                        "The seal script there will not run until it is\n"
                        "granted permission to execute.",
                        "---------",
                        immutable=False,
                    ),
                    "inner": {
                        "type": "dir",
                        "children": {
                            "unseal.sh": _mode_file(
                                "# vault seal release — archivist only\n"
                                'echo "SEAL RELEASED: room B-2"\n'
                                'echo "EVIDENCE TAG: ORCHID-7"\n',
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
    "tail -n 5 /root/informant_trail/journal.log",
    "grep PIER /root/informant_trail/journal.log",
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
# 統合ワールドでは Mission21 解放時に progress.release_missions が探偵自身の
# バケットへ上書きする（本人の道具箱が盗まれる、が筋書き）。
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
        "公園で猫ファイルを find で探し出し、机の報告書（/root/desk/report.txt）に絶対パスと状態を書いて完了する。",
        ["find", "grep", "awk", "sort", "uniq"],
        # 判定は judge.py の Mission2 専用ロジック（find 使用・机の報告書
        # /root/desk/report.txt の絶対パス記載・STATUS 記載）で行うため
        # expected_script_patterns は空にする（誤答メッセージを個別化するため）。
        # 読み方（cat/grep）は絶対パスでも cd 後の相対パスでも自由（P3-08e）。
        initial_filesystem=_MISSION2_FS,
        initial_current_path="/root/park",
        hints=[
            "ゴール: catinfo.txt を find で見つけ、机の report.txt（/root/desk/report.txt）にその絶対パスと STATUS の値を書き、sh case_file.sh → git push する。",
            'find /root/park -name catinfo.txt で場所が分かる。中身は cat で読む。報告書は机に置く: echo "/root/park/swing/catinfo.txt STATUS: stray" > /root/desk/report.txt のように絶対パス（/ から）を含める。',
            'find /root/park -name catinfo.txt（名前で探す）→ cat /root/park/swing/catinfo.txt（読む）→ echo "/root/park/swing/catinfo.txt STATUS: stray" > /root/desk/report.txt（机に報告書を書く）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m "cat"（セーブ）→ git push（提出）',
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "依頼は迷い猫。名前はマイク、黒。公園（park）で最後に見られたらしい。\n玄関を出て、公園へ向かわないと！"},
            {"id": "park", "when": "after", "line": r"^(cd|ls) /root/park", "text": "ベンチ、噴水、遊具……区画が多い。当てずっぽうに歩けば日が暮れる。名前で探す（find）のが探偵の仕事、のはず。"},
            {"id": "found", "when": "after", "line": r"^find ", "output": r"catinfo\.txt", "text": "出た！ 猫の記録は遊具（swing）の傍。"},
            {"id": "read", "when": "after", "line": r"^cat .*catinfo\.txt", "text": "STATUS: stray——野良か。机（desk）に戻って、報告書（report.txt）を書かないと。\n書く場所は `/` から始まる住所で。「swing の傍」じゃ、誰も辿り着けない。"},
            {"id": "desk", "when": "after", "line": r"^(cd|ls) /root/desk", "text": "机の上。ここに report.txt を作って、猫の居場所（`/` からの住所）と状態（STATUS）を書き込む——echo で流し込めばいい、はず。"},
            {"id": "wrote", "when": "after", "line": r"^echo .*> /root/desk/report\.txt", "text": "報告書ができた。中身を確かめたら（cat）、事件ファイル（case_file.sh）で確認しておくか。"},
            {"id": "fail_report", "when": "after", "line": r"^sh .*case_file\.sh", "output": "report not found", "text": "報告書が無い、と言われた。机（/root/desk）に report.txt を作らないと。"},
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
        hints=[
            "ゴール: /root/wiretap_room/tape.log で一番多く出てくる TEL: 番号を grep | sort | uniq -c のパイプで数え、echo \"TEL: 000-0000\" で報告して sh case_file.sh → git push する。",
            "wc -l tape.log で行数、head tape.log で行の形（TEL: 番号 / NOTE: 雑音）を見る。grep TEL tape.log | sort | uniq -c | sort -n で番号ごとの回数が並ぶ（最後の行が最多）。報告は echo \"TEL: 555-0000\" の書式。",
            "cd /root/wiretap_room（盗聴室へ）→ wc -l tape.log（分量を見る）→ head tape.log（形を見る）→ grep TEL tape.log | sort | uniq -c | sort -n（番号を絞る→並べる→数える→回数順）→ echo \"TEL: <最多の番号>\"（報告）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"tape\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "押収した盗聴テープ。盗聴室（wiretap_room）に tape.log として置いてある。\n犯人が繰り返し掛けていた番号——それさえ分かれば、あとは本部の仕事。"},
            {"id": "count", "when": "after", "line": r"^wc ", "text": "数えるほどの行数でも、本物のテープなら何万行にもなる。目で読む癖は、今のうちに捨てたほうがいい。"},
            {"id": "flood", "when": "after", "line": r"^cat [^|]*tape\.log\s*$", "text": "流れていくだけで何も残らない。欲しいのは番号だけ——絞り込む道具（grep）があったはず。"},
            {"id": "shape", "when": "after", "line": r"^(head|tail) ", "text": "TEL: の行と、NOTE: の雑音。形は揃っている。形が揃っているなら、機械に数えさせられる。"},
            {"id": "filtered", "when": "after", "line": r"^grep [^|]*$", "output": "TEL:", "text": "番号だけになった。だが同じ番号が散らばっている……数えるなら、並べて（sort）からまとめる（uniq）。管（|）で繋げば一気に流せるはず。"},
            {"id": "counted", "when": "after", "line": r"uniq\s+-c", "text": "回数が付いた！ 一番多い番号——それが犯人の相手のはず。報告書に TEL: の形で書き出す。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "突き返された。集計（uniq -c）の証跡と、番号の報告（TEL: 000-0000）——両方要る。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "これで行ける。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "何万行のテープより、数えた一行のほうが重い。\n——管（パイプ）で道具を繋ぐ。探偵の第二の目、なのかもしれない。"},
        ],
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
            r"sh\s+.*unseal\.sh",
        ],
        initial_filesystem=_MISSION5_FS,
        hints=[
            "ゴール: /root/vault の読めないファイルを chmod +r で読み、奥の部屋 /root/vault/inner の unseal.sh を chmod +x してから sh で実行し、sh case_file.sh → git push する。",
            "ls -l /root/vault で刻印（rwx）を見る。--------- は鍵が全部無い状態。読む鍵は chmod +r <ファイル>、実行の鍵は chmod +x <ファイル>。実行は sh <ファイル>。",
            "ls -l /root/vault（刻印を見る）→ chmod +r /root/vault/locked_evidence.txt（読む鍵）→ cat /root/vault/locked_evidence.txt（奥の部屋を知る）→ ls -l /root/vault/inner → chmod +x /root/vault/inner/unseal.sh（実行の鍵）→ sh /root/vault/inner/unseal.sh（封印解除）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"vault\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "資料室（vault）に封印された証拠がある。鍵は三種類——読む、書く、実行する。\n刻印（rwx）が読めれば、どの鍵が抜かれているかも分かるはず。"},
            {"id": "inspect", "when": "after", "line": r"^ls -l", "output": "---------", "text": "---------……九つの刻印が全部空。鍵がひとつも無い。読むには、読む鍵（r）を付け直す（chmod +r）しかない。"},
            {"id": "denied_read", "when": "after", "line": r"^cat .*locked_evidence", "output": "permission denied", "text": "読めない。当然か——鍵が無いのだから。"},
            {"id": "unlocked_read", "when": "after", "line": r"^chmod .*locked_evidence", "text": "刻印が変わった。これで読めるはず。"},
            {"id": "inner", "when": "after", "line": r"^cat .*locked_evidence", "output": "inner room", "text": "奥の部屋（inner）を指している。封印を解く仕掛けは、許可が無いと動かない、と。"},
            {"id": "denied_exec", "when": "after", "line": r"^sh .*unseal", "output": "permission denied", "text": "動かない。実行の鍵（x）が無い……付けるなら chmod +x。"},
            {"id": "unsealed", "when": "after", "line": r"^sh .*unseal", "output": "SEAL RELEASED", "text": "封印が解けた！ 事件ファイルで確認して、本部へ。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "まだ足りない。読む鍵（+r）、実行の鍵（+x）、そして封印解除（sh unseal.sh）——三つとも通したか……。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "資料室は開いた。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "rwx の九文字は鍵の刻印だった。読めない・開けない・動かない——三つとも、鍵が無いだけのこと。"},
        ],
    ),
    MissionDef(
        6, "Shadow Process", "盗聴器を止めろ",
        "ps で不審プロセスを見つけ、裏取りしてから kill する。",
        ["ps", "kill", "grep"],
        # 判定は judge.py の Mission6 専用ロジック（processes に listener_x が
        # 残っていないか）で行うため expected_script_patterns は空にする。
        initial_filesystem=_MISSION6_FS,
        initial_processes=_MISSION6_PROCESSES,
        hints=[
            "ゴール: ps aux で動いているプロセスを見て、盗聴プログラム listener_x の PID を kill で止め、sh case_file.sh → git push する。clock / mailbox / heater は止めない。",
            "ps aux で一覧（PID と名前）。怪しい名前の PID は cat /proc/<PID>/cmdline で実体を裏取りできる。止めるのは kill <PID>。正規のプロセスを kill すると警告が出る（失敗にはならない）。",
            "ps aux（名簿を見る）→ cat /proc/666/cmdline（実体を確かめる）→ kill 666（盗聴器を止める）→ sh case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"bug\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "事務所の空気がおかしい。誰かに聞かれている……盗聴プログラムが動いているはず。\n名簿（ps）を見て、止める（kill）。ただし時計や郵便受けを止めたら、事務所が回らなくなる。"},
            {"id": "roster", "when": "after", "line": r"^ps\b", "output": "listener_x", "text": "clock、mailbox、heater……それに listener_x。聞き耳（listener）を立てている名前が、ひとつだけ紛れている。"},
            {"id": "verify", "when": "after", "line": r"^cat /proc/666/cmdline", "text": "/tmp/.hidden/listener_x --tap……隠しフォルダから盗聴（tap）。これで確信、のはず。"},
            {"id": "wrong_kill", "when": "after", "line": r"^kill ", "output": "legitimate process", "text": "しまった、それは事務所の正規の住人!? ……幸い止まってはいない。よく見てから撃たないと。"},
            {"id": "killed", "when": "after", "line": r"^kill 666", "output": "terminated", "text": "静かになった。盗聴器は止まったはず。事件ファイルで確認して、本部へ。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "still running", "text": "まだ聞かれている。名簿（ps）をもう一度……。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "盗聴器は沈黙した。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "事務所に静けさが戻った。プロセスは目に見えない住人——名簿を読めれば、追い出せる。"},
        ],
    ),
    MissionDef(
        7, "Inside the Machine", "機械の胸の内",
        "/proc を読み、偽装プロセスの正体を暴いて起訴・停止する。",
        ["ps", "kill", "grep", "free", "uptime"],
        # 判定は judge.py の Mission7 専用ロジック（/proc 裏取り・偽装 cmdline 報告・
        # 停止済みの 3 点）で行うため expected_script_patterns は空にする。
        initial_filesystem=_MISSION7_FS,
        initial_processes=_MISSION7_PROCESSES,
        hints=[
            "ゴール: ps aux の名簿では見抜けない偽装プロセス（名前は clock、PID 923）を /proc/923/status と /proc/923/cmdline で裏取りし、本当の起動コマンドを echo で報告してから kill 923 し、sh case_file.sh → git push する。",
            "ls /proc で PID の部屋が並ぶ。cat /proc/<PID>/status で名前（Name）、cat /proc/<PID>/cmdline で本当の起動コマンドが分かる。報告は echo \"<cmdline の中身>\"。止めるのは kill <PID>。",
            "ps aux（名簿）→ ls /proc（原本の部屋）→ cat /proc/923/status（名乗り）→ cat /proc/923/cmdline（持ち物＝本当のコマンド）→ echo \"/tmp/.fake/exfil --send\"（起訴状に書く）→ kill 923（停止）→ sh case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"impostor\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "また潜入者がいる、と本部から。だが今回は止める前に「起訴」しろ、と。\n誰が、何を、どうやって——機械は胸の内（/proc）に全部書いているはず。"},
            {"id": "roster", "when": "after", "line": r"^ps\b", "text": "mailbox、heater、clock。見慣れた名前ばかり……。だが名簿は名乗った名前を写すだけ。名前は誰でも名乗れる。"},
            {"id": "proc", "when": "after", "line": r"^ls /proc", "text": "番号（PID）の部屋が並んでいる。名簿の原本はここ、ということか。"},
            {"id": "status", "when": "after", "line": r"^cat /proc/923/status", "text": "Name: clock……身分証は本物に見える。だが、持ち物はどうだ？"},
            {"id": "cmdline", "when": "after", "line": r"^cat /proc/923/cmdline", "text": "/tmp/.fake/exfil --send——時計のふりをして、外へ送っている（exfil）！ これが起訴状の中身になる。"},
            {"id": "body", "when": "after", "line": r"^(cat /proc/(meminfo|cpuinfo|uptime)|free|uptime)\b", "text": "この建物（PC）の身体検査。free も uptime も、結局ここを読んでいるだけ、なのかもしれない。"},
            {"id": "judge_no_proc", "when": "after", "line": r"^sh .*case_file\.sh", "output": "check /proc", "text": "起訴には証拠が要る。/proc の中——status か cmdline を見てからだ。"},
            {"id": "judge_no_report", "when": "after", "line": r"^sh .*case_file\.sh", "output": "real command", "text": "偽装の実体——起動コマンドそのものを、報告に書き写さないと。"},
            {"id": "judge_running", "when": "after", "line": r"^sh .*case_file\.sh", "output": "still running", "text": "起訴状は揃った。あとは止めるだけ（kill）。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "起訴状は本部へ。記録して送る。"},
            {"id": "clear", "when": "clear", "text": "名簿（ps）は名乗った名前を写すだけ。持ち物（/proc）は嘘をつけない。\n——コマンドの向こう側も、ただのファイルだった。"},
        ],
    ),
    MissionDef(
        8, "Master of Disguise", "変装潜入",
        "合言葉を見つけ su で barman になり、権限付きファイルを読む。",
        ["su", "whoami", "exit"],
        # 判定は judge.py の Mission8 専用ロジック（su barman・whoami・秘密ファイル
        # 閲覧・detective への復帰の4点）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION8_FS,
        hints=[
            "ゴール: /root/bar/back/ledger.txt は barman しか読めない。su barman で変装し、whoami で確認してから読み、exit で detective に戻って sh case_file.sh → git push する。",
            "cat /root/bar/hint.txt に合言葉（やり方）がある。su barman で barman になり、whoami で今の自分を確かめる。読み終えたら exit で元に戻る（戻らないと判定が通らない）。",
            "cat /root/bar/hint.txt（合言葉）→ su barman（変装）→ whoami（今の自分を確認）→ cat /root/bar/back/ledger.txt（台帳を読む）→ exit（自分に戻る）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"disguise\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "酒場（bar）の裏に、barman しか読めない台帳があるらしい。合言葉は店のどこかに。\n変装して読む——そして、必ず自分に戻る。"},
            {"id": "denied", "when": "after", "line": r"^cat .*ledger", "output": "ermission denied", "text": "読めない。この台帳は barman のもの……俺のままでは駄目、ということか。"},
            {"id": "hint", "when": "after", "line": r"^cat .*hint\.txt", "text": "合言葉が出た。su barman——barman になれ、と。"},
            {"id": "disguised", "when": "after", "line": r"^su barman", "text": "変装完了……のはず。プロンプトが変わった。今の自分が誰か、確かめておく（whoami）。"},
            {"id": "whoami", "when": "after", "line": r"^whoami", "output": "barman", "text": "barman だ。今なら台帳が読めるはず。"},
            {"id": "ledger", "when": "after", "line": r"^cat .*ledger", "output": "SUSPECT", "text": "SUSPECT: Nico Faro——容疑者の名前。控えたら、変装を解いて（exit）自分に戻る。"},
            {"id": "judge_no_su", "when": "after", "line": r"^sh .*case_file\.sh", "output": "become barman", "text": "台帳は barman にしか読めない。店の中にヒント（hint.txt）があるはず。"},
            {"id": "judge_no_whoami", "when": "after", "line": r"^sh .*case_file\.sh", "output": "confirm who you are", "text": "変装したなら、今の自分を確かめる（whoami）癖を付けろ、と。"},
            {"id": "judge_unread", "when": "after", "line": r"^sh .*case_file\.sh", "output": "still unread", "text": "台帳（/root/bar/back/ledger.txt）をまだ読んでいない。"},
            {"id": "judge_still_barman", "when": "after", "line": r"^sh .*case_file\.sh", "output": "own identity", "text": "まだ barman のまま!? 報告は自分の名前でしないと。exit で戻る。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "自分に戻った。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "変装は解いた。誰かになれる力より、今の自分が誰かを確かめる癖のほうが、探偵を長生きさせる。"},
        ],
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
        hints=[
            "ゴール: /root/evidence_locker/evidence.dat を file で正体を確かめながら tar → unzip と開封し、最深部の final_clue.txt の CODE: を echo で報告して sh case_file.sh → git push する。",
            "file <ファイル> で中身の種類が分かる（gzip compressed data なら tar -xzf <ファイル>、Zip archive data なら unzip <ファイル>）。展開は今いるディレクトリに出るので cd /root/evidence_locker してから。",
            "cd /root/evidence_locker → file evidence.dat（正体: gzip）→ tar -xzf evidence.dat（開封）→ file sealed.zip（正体: Zip）→ unzip sealed.zip（開封）→ cat final_clue.txt（コードを読む）→ echo \"CODE: NOIR-1948\"（報告）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"unsealed\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "押収品は証拠保管庫（evidence_locker）に。evidence.dat——拡張子はそう名乗っているが、当てにならない。\n鑑識（file）にかけながら、一枚ずつ開けていく。"},
            {"id": "sniff", "when": "after", "line": r"^file .*evidence\.dat", "output": "gzip", "text": "gzip compressed data——.dat の皮を被った圧縮包み。tar で解く（tar -xzf）。"},
            {"id": "not_archive", "when": "after", "line": r"^(tar|unzip|gunzip) ", "output": "invalid input", "text": "包みじゃない物を無理に開けても壊すだけ。先に鑑識（file）だ。"},
            {"id": "peeled", "when": "after", "line": r"^tar .*-x", "output": r"^$", "text": "一枚剥けた。中から出てきた物も、また鑑識にかける。"},
            {"id": "zip", "when": "after", "line": r"^file .*sealed\.zip", "output": "Zip", "text": "今度は Zip。包みが違えば道具も違う（unzip）。"},
            {"id": "unzipped", "when": "after", "line": r"^unzip ", "output": r"^$", "text": "最深部が見えた。"},
            {"id": "clue", "when": "after", "line": r"^cat .*final_clue", "output": "CODE:", "text": "CODE: NOIR-1948——封印の芯。報告に写す。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "突き返された。tar の展開、unzip の展開、コードの報告——どれかが記録に無い。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "封印は全部解けた。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "拡張子は名札にすぎない。中身は鑑識でしか分からない。\n——包みを剥がすたび、一歩ずつ近づいていた。"},
        ],
    ),
    MissionDef(
        10, "The Forged Letter", "改ざんされた遺言状",
        "diff で改ざん箇所を特定し、sed で原本どおりに復元する。",
        ["diff", "sed"],
        # 判定は judge.py の Mission10 専用ロジック（diff 実行 + submitted.txt が
        # original.txt と完全一致）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION10_FS,
        hints=[
            "ゴール: /root/will_office の original.txt（原本）と submitted.txt（写し）を diff で比べ、違う 1 文字を sed で直して submitted.txt に書き戻し、sh case_file.sh → git push する。",
            "diff original.txt submitted.txt で違う行が < > で出る（違いは数字の 0 と英字の O）。sed 's/間違い/正しい/' submitted.txt > submitted.txt で置き換えて書き戻す。直した後にもう一度 diff で差分が消えたか確かめる。",
            "cd /root/will_office → diff original.txt submitted.txt（違いを見る: 2 行目の $50000 と $5O000）→ sed 's/5O000/50000/' submitted.txt > submitted.txt（置換して書き戻す）→ diff original.txt submitted.txt（差分なしを確認）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"will\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "遺言状の写し（submitted.txt）が原本（original.txt）と違う、と遺族が言う。遺言事務所（will_office）に両方ある。\n目で見比べて分からないなら、機械に比べさせる（diff）。"},
            {"id": "diff", "when": "after", "line": r"^diff ", "output": "AMOUNT", "text": "2c2……2 行目。$50000 と $5O000——ゼロとオーの一文字。人の目では絶対に見つからない差。"},
            {"id": "sed_screen", "when": "after", "line": r"^sed [^>]*$", "output": "AMOUNT", "text": "画面に直った文が出ただけ。ファイルはまだ古いまま——書き戻す（> ファイル）必要がある、はず。"},
            {"id": "sed_write", "when": "after", "line": r"^sed .*>", "text": "置き換えて書き戻した。もう一度 diff で確かめる。"},
            {"id": "judge_no_diff", "when": "after", "line": r"^sh .*case_file\.sh", "output": "run diff", "text": "直す前に、何が違うかを機械に言わせろ（diff）、と。"},
            {"id": "judge_mismatch", "when": "after", "line": r"^sh .*case_file\.sh", "output": "does not match", "text": "まだ一致していない。置換の指定（s/前/後/）と書き戻し先を見直す。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "写しは原本に戻った。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "ゼロとオー。人の目が誤魔化される一文字を、diff は一行で指した。——比べる道具を持て。"},
        ],
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
        hints=[
            "ゴール: /root/scraps/pieces.txt の「番号:本文」の断片を sort で番号順に並べ、cut で本文だけ取り出し、全文を 1 行に繋げて echo で報告して sh case_file.sh → git push する。",
            "sort /root/scraps/pieces.txt で番号順に並ぶ。cut -d: -f2 で「:」区切りの 2 列目（本文）だけ残る。パイプで繋げば sort … | cut -d: -f2。報告は echo \"全文\"（3 片を空白で繋げた 1 行）。",
            "cat /root/scraps/pieces.txt（断片を見る）→ sort /root/scraps/pieces.txt | cut -d: -f2（並べて番号を剥がす）→ echo \"MIDNIGHT AT THE OLD PIER BRING THE LEDGER ALONE\"（全文を報告）→ sh case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"note\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "切り裂かれた脅迫状。断片（scraps）には番号が振ってあるが、順番はばらばららしい。\n並べ替えて（sort）、番号を剥がして（cut）、全文を復元する。"},
            {"id": "pieces", "when": "after", "line": r"^cat .*pieces", "text": "3:ALONE、1:MIDNIGHT……番号:本文の形。番号順に並べれば読めるはず。"},
            {"id": "sorted", "when": "after", "line": r"^sort [^|]*$", "text": "並んだ。あとは番号（コロンの前）を剥がす——cut -d: -f2。"},
            {"id": "cut", "when": "after", "line": r"\| *cut ", "text": "MIDNIGHT AT THE OLD PIER / BRING THE LEDGER / ALONE——脅迫状の全文。一行に繋げて報告する。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "突き返された。sort、cut（か paste）、そして全文——三つ揃って初めて復元になる。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "脅迫状は元の形に戻った。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "三片なら手でも並べられた。百片なら？ 道具の価値は、数が増えたときに分かる。"},
        ],
    ),
    # --- ここに Mission23〜25 相当（git-team 編。id は既存と衝突しない新規採番）を
    #     挿入予定。_DEFS の並び順がそのままプレイ順序になる（このコメント直下 =
    #     Mission11 の直後・Mission12 の直前）。---
    MissionDef(
        12, "Ghost Line", "幽霊回線を追え",
        "dig で IP を割り出し、ping で生存確認して ssh で突入する。",
        ["dig", "host", "ping", "ss", "ssh", "exit", "grep"],
        # 判定は judge.py の Mission12 専用ロジック（dig→ping→ssh の出現順序 +
        # remote 証拠閲覧 + 黒幕名報告）で行うため expected_script_patterns は空。
        # 現場（/den 以下）は SSH_HOSTS["ghost.example"] に定義（local FS 不要）。
        hints=[
            "ゴール: dig ghost.example → ping ghost.example → ssh ghost.example の順に実行し、接続先の /den/evidence/orders.txt を読んで BOSS: の名前を echo で報告、exit で戻って sh case_file.sh → git push する。",
            "dig <ホスト> で IP、ping <ホスト> で生存確認、ss -tln で開いているポート、ssh <ホスト> で接続。判定は dig → ping → ssh の順番を見る。証拠は接続先の /den/evidence/orders.txt。報告は echo \"BOSS: 名前\"。事務所へ戻るのは exit。",
            "dig ghost.example（住所）→ ping ghost.example（生存）→ ss -tln（開いた扉）→ ssh ghost.example（突入）→ cat /den/evidence/orders.txt（証拠）→ echo \"BOSS: Selene Vance\"（報告）→ exit（帰還）→ sh case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"ghost\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "犯人は「ghost」と呼ばれるサーバーから指示を出している。\n住所を割り出し（dig）、生きているか確かめ（ping）、それから踏み込む（ssh）。順番を守れ——調べてから、踏み込む。"},
            {"id": "resolved", "when": "after", "line": r"^(dig|host) ", "output": r"10\.66\.6\.6", "text": "10.66.6.6——幽霊の住所が割れた。"},
            {"id": "no_host", "when": "after", "line": r"^(dig|host|ping) ", "output": "Host not found", "text": "名前が引けない。綴りは ghost.example のはず。"},
            {"id": "alive", "when": "after", "line": r"^ping ", "output": "bytes from", "text": "返事がある。生きている。"},
            {"id": "ports", "when": "after", "line": r"^ss\b", "text": "開いている扉（ポート）も見えた。準備は整った、はず。"},
            {"id": "breach", "when": "after", "line": r"^ssh (ghost\.example|10\.66\.6\.6)", "text": "踏み込んだ。ここは巣（/den）。証拠（evidence）を探す。"},
            {"id": "orders", "when": "after", "line": r"^cat .*orders\.txt", "output": "BOSS:", "text": "BOSS: Selene Vance——黒幕の名前。報告に書いて、回線を切って（exit）帰る。"},
            {"id": "judge_order", "when": "after", "line": r"^sh .*case_file\.sh", "output": "investigate before", "text": "順番が違う、と。dig → ping → ssh。調べてから踏み込む。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "証拠（orders.txt）を読んで、黒幕の名前を報告に書いたか……。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "黒幕の名は本部へ。記録して送る。"},
            {"id": "clear", "when": "clear", "text": "住所を引き、生存を確かめ、踏み込む。捜査の手順は、ネットワークの手順でもあった。"},
        ],
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
        hints=[
            "ゴール: crontab -l で予定表を見て、危険なジョブ（/tmp/.dark/broadcast.sh）が動く曜日と時刻を読み解き、echo \"FRIDAY 00:00\" の書式で報告して sh case_file.sh → git push する。",
            "crontab -l の各行は「分 時 日 月 曜日 コマンド」。曜日は 0=日曜 … 5=金曜 6=土曜（/root/crontab_room/hint.txt に書式の説明がある）。0 0 * * 5 なら毎週金曜 00:00。報告は echo \"曜日 時:分\"（英語の曜日・24 時間表記）。",
            "crontab -l（予定表）→ cat /root/crontab_room/hint.txt（書式の読み方）→ echo \"FRIDAY 00:00\"（危険ジョブの発動日時を報告）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"cron\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "サーバーに時限装置（cron）が仕掛けられた。予定表（crontab -l）を見て、危険なジョブが動く日時を割り出す。\n五つの数字の読み方は、部屋（crontab_room）の hint.txt にあるはず。"},
            {"id": "table", "when": "after", "line": r"^crontab -l", "text": "三行。0 0 * * 5 /tmp/.dark/broadcast.sh……隠しフォルダの「放送」。分・時・日・月・曜日——最後の 5 が曜日、のはず。"},
            {"id": "format", "when": "after", "line": r"^cat .*hint\.txt", "text": "曜日: 5 は金曜。0 0 は 0 時 0 分。——金曜の深夜 0 時。"},
            {"id": "date", "when": "after", "line": r"^date\b", "text": "今日の日付。発動までどれだけある？"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "報告の書式は FRIDAY 00:00。予定表を見た証跡（crontab -l）も要る。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "発動日時は割れた。記録して本部へ。処理班が間に合う。"},
            {"id": "clear", "when": "clear", "text": "五つの数字は時限装置の目盛りだった。読めれば、止められる。"},
        ],
    ),
    MissionDef(
        14, "Hall of Mirrors", "鏡の館",
        "ls -l と file でシンボリックリンクを見抜き、実体の絶対パスを特定する。",
        ["ls", "file"],
        # 判定は judge.py の Mission14 専用ロジック（report の echo 行に実体の
        # 絶対パスがあるか。リンクパスのみの報告は不合格）で行う。
        initial_filesystem=_MISSION14_FS,
        hints=[
            "ゴール: /root/mirror_hall の deed_*.txt はどれも案内板（シンボリックリンク）。ls -l と file で辿って実体のファイルの絶対パスを突き止め、それを echo で報告して sh case_file.sh → git push する。",
            "ls -l /root/mirror_hall で「名前 -> 行き先」の矢印が出る（矢印付きはリンク）。file <パス> は symbolic link to … と教えてくれる。矢印を辿って、矢印の無いファイル（ASCII text）に着いたらそれが実体。報告は echo \"実体の絶対パス\"（リンクのパスを書くと突き返される）。",
            "ls -l /root/mirror_hall（矢印を見る）→ file /root/mirror_hall/deed_a.txt（symbolic link to deed_b）→ file /root/mirror_hall/deed_b.txt（symbolic link to vault/real_deed.txt）→ file /root/mirror_hall/vault/real_deed.txt（ASCII text = 実体）→ cat /root/mirror_hall/vault/real_deed.txt → echo \"/root/mirror_hall/vault/real_deed.txt\"（報告）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"deed\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "鏡の館（mirror_hall）。権利書（deed）が何枚もあるが、本物は一枚だけらしい。\n残りは鏡——どこかを映しているだけ。映しているなら、映している先があるはず。"},
            {"id": "arrows", "when": "after", "line": r"^ls -l .*mirror_hall", "output": "->", "text": "矢印（->）。deed_a は deed_b を、deed_b は vault の中を指している。矢印の付いた名前は案内板（リンク）で、本体じゃない。"},
            {"id": "link", "when": "after", "line": r"^file .*deed_[abc]", "output": "symbolic link", "text": "鑑識も言っている——symbolic link。案内板だ。矢印の先へ。"},
            {"id": "real", "when": "after", "line": r"^file .*real_deed", "output": "ASCII text", "text": "ASCII text——矢印が無い。ここが本物。住所は `/` からの絶対パスで控える。"},
            {"id": "through_mirror", "when": "after", "line": r"^cat .*deed_[abc]", "output": "DEED:", "text": "読める……が、これは鏡越しに見ているだけ。報告に書くのは鏡の場所じゃなく、本物の場所のはず。"},
            {"id": "judge_mirror", "when": "after", "line": r"^sh .*case_file\.sh", "output": "only a mirror", "text": "「それは鏡だ」と突き返された。案内板の住所じゃなく、実体の住所を。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "実体の絶対パスを echo で報告したか……。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "本物の在処が判った。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "鏡は何枚あっても、本物は一枚。矢印を辿り切る癖——それが鏡の館の出口だった。"},
        ],
    ),
    MissionDef(
        15, "The Informant's Trail", "情報屋の足取り",
        "history とログから操作を再現し、情報屋の行き先を突き止める。",
        ["history", "tail", "grep"],
        # 判定は judge.py の Mission15 専用ロジック（informant_history の再現 +
        # 行き先の報告）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION15_FS,
        informant_history=_MISSION15_HISTORY,
        hints=[
            "ゴール: history に残った情報屋の操作 2 行をそのまま打ち直し、journal.log から行き先（PIER 13）を突き止めて echo \"PIER 13\" で報告、sh case_file.sh → git push する。",
            "history で情報屋が打ったコマンドが番号付きで出る。判定は「同じコマンドを一字一句そのまま」実行したかを見る（tail -n 5 … と grep PIER …）。行き先は grep の結果の行に書いてある。",
            "history（足取り）→ tail -n 5 /root/informant_trail/journal.log（末尾 5 行）→ grep PIER /root/informant_trail/journal.log（行き先）→ echo \"PIER 13\"（報告）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"trail\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "情報屋が消えた。机の端末には、最後に打った操作の履歴（history）が残っているらしい。\n同じ操作をなぞれば、同じ場所に辿り着くはず。"},
            {"id": "history", "when": "after", "line": r"^history\b", "output": "journal", "text": "二行。tail で末尾を読み、grep で PIER を探している……行き先は journal.log の中か。同じ手順を、同じ言葉で。"},
            {"id": "tail", "when": "after", "line": r"^tail .*journal", "text": "最後の足取り。倉庫、そして「note left」——置き手紙。"},
            {"id": "pier", "when": "after", "line": r"^grep PIER .*journal", "output": "PIER 13", "text": "PIER 13——13 番桟橋。情報屋はここへ向かった。報告に書く。"},
            {"id": "judge_retrace", "when": "after", "line": r"^sh .*case_file\.sh", "output": "exact steps", "text": "「足取りをそのままなぞれ」と。履歴（history）の二行を、一字一句同じに。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "行き先（PIER 13）を報告に書いたか……。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "足取りは掴んだ。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "打った言葉は履歴に残る。残るなら、なぞれる——それが history の使い道、なのかもしれない。"},
        ],
    ),
    MissionDef(
        16, "The Great Sweep", "一斉捜索令状",
        "glob と引用符で対象を絞り込み、空白入りファイル名も開封する。",
        ["find", "grep"],
        # 判定は judge.py の Mission16 専用ロジック（数字 glob 使用 + 引用符付き
        # cat 成功 + コード報告）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION16_FS,
        initial_current_path="/root/warehouse",
        hints=[
            "ゴール: /root/warehouse の大量の case_*.txt を glob（case_[0-9].txt）で絞り込み、空白入りの \"top secret.txt\" を引用符付きで開いて CODE: を echo で報告、sh case_file.sh → git push する。",
            "ls case_* は全部並んで見づらい。ls case_[0-9].txt なら 1 桁番号だけに絞れる（判定はこの [0-9] の使用を見る）。空白入りの名前は cat \"top secret.txt\" のように引用符で囲む（囲まないと 2 つの名前に分かれて file not found）。",
            "cd /root/warehouse → ls case_*（多すぎる）→ ls case_[0-9].txt（数字 1 桁だけ）→ cat \"top secret.txt\"（引用符で開く）→ echo \"CODE: 4821-VESPER\"（報告）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"sweep\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "一斉捜索令状が下りた。倉庫（warehouse）には事件簿が山ほどある——全部開ける時間は無い。\n名前の形で絞る（glob）。それと、空白の入った名前には気をつけろ、と先輩が言っていた気がする。"},
            {"id": "too_many", "when": "after", "line": r"^ls .*case_\*", "text": "……多すぎる。* は全部を拾う。もっと狭い網——[0-9] なら数字一文字だけのはず。"},
            {"id": "narrowed", "when": "after", "line": r"\[0-9\]", "text": "九件に絞れた。網の目を選べば、山も一握りになる。"},
            {"id": "split_name", "when": "after", "line": r"^cat top secret", "output": "not found", "text": "見つからない!? ……空白で名前が二つに割れている。引用符（\"\"）で一つに束ねないと。"},
            {"id": "opened", "when": "after", "line": r'^cat "top secret', "output": "CODE:", "text": "開いた。CODE: 4821-VESPER——令状の本命。報告に写す。"},
            {"id": "judge_glob", "when": "after", "line": r"^sh .*case_file\.sh", "output": "glob pattern", "text": "「網を絞れ」と。case_[0-9].txt のような形で。"},
            {"id": "judge_unopened", "when": "after", "line": r"^sh .*case_file\.sh", "output": "unopened file", "text": "本命をまだ開けていない。空白入りの名前は引用符で。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "コード（CODE: …）を報告に写したか……。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "捜索完了。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "* は全部、[0-9] は一文字。網の目を選ぶのは探偵の仕事で、空白は引用符で束ねる——名前の扱いも、捜査のうち。"},
        ],
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
        hints=[
            "ゴール: /root/contracts の copy_1〜5.txt を md5sum で指紋照合し、ledger.txt の原本ハッシュと一致しない 1 通（copy_4）を見つけて echo で報告、sh case_file.sh → git push する。",
            "md5sum <ファイル> でファイルの指紋（ハッシュ）が出る。複数まとめて md5sum copy_*.txt でもよい。cat ledger.txt の ORIGINAL MD5 と見比べ、違う 1 通が改ざん版。diff copy_1.txt copy_4.txt で何が違うかも分かる。報告は echo \"copy_4 …\"。",
            "cd /root/contracts → cat ledger.txt（原本の指紋）→ md5sum copy_*.txt（5 通の指紋）→ diff copy_1.txt copy_4.txt（違いを見る）→ echo \"copy_4 was tampered\"（報告）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"fingerprint\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "契約書の写しが五通（contracts）。どれも同じに見えるが、一通だけ書き換えられているらしい。\n目で見比べても無駄だった事件を思い出す。指紋（ハッシュ）を採るしかない。"},
            {"id": "ledger", "when": "after", "line": r"^cat .*ledger", "output": "MD5", "text": "台帳に原本の指紋がある。これと照合すれば、偽物は自分から名乗り出るはず。"},
            {"id": "fingerprint", "when": "after", "line": r"^md5sum ", "text": "指紋が出た。同じ中身なら同じ指紋——一文字でも違えば、まるで別人の指紋になる。"},
            {"id": "diff", "when": "after", "line": r"^diff .*copy_", "output": "interest", "text": "0% と O%。ゼロとオー——また、あの一文字か。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "指紋採取（md5sum）の証跡と、偽物の名前（copy_4）の報告——両方要る。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "偽物は割れた。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "指紋は嘘をつかない。ファイルが本物かどうかは、見た目ではなくハッシュで決まる——ダウンロードした物も、同じこと。"},
        ],
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
        hints=[
            "ゴール: /root/archive を grep -r で探すと読めないファイルの雑音（permission denied）が混ざる。2>/dev/null で雑音を捨てて目撃証言を読み、PLATE: の番号を echo で報告して sh case_file.sh → git push する。",
            "エラーは 2 番の管（標準エラー出力）を流れる。コマンドの末尾に 2>/dev/null を付けるとエラーだけ捨てられる（判定はこれの使用を見る）。grep -r \"witness\" /root/archive 2>/dev/null で証言のファイルだけが残る。",
            "grep -r \"witness\" /root/archive（雑音混じり）→ grep -r \"witness\" /root/archive 2>/dev/null（雑音を捨てる）→ cat /root/archive/witness_note.txt（証言を読む）→ echo \"PLATE: NX-4471\"（報告）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"static\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "資料庫（archive）のどこかに目撃証言（witness）がある。だが庫内は封印ファイルだらけで、探すたびに「読めない」の雑音が鳴る。\n雑音と声は、別々の管を通っているはず。"},
            {"id": "static", "when": "after", "line": r"^grep -r [^2]*$", "output": "permission denied", "text": "雑音だらけ。だが声も混ざっている……。エラーは 2 番の管（2>）。管ごと排水溝（/dev/null）へ流せないか。"},
            {"id": "silence", "when": "after", "line": r"2>\s*/dev/null", "text": "静かになった。残ったのは声だけ。"},
            {"id": "witness", "when": "after", "line": r"^cat .*witness_note", "output": "PLATE:", "text": "黒い車、ナンバー NX-4471。報告に写す。"},
            {"id": "status", "when": "after", "line": r"^echo \$\?", "text": "直前のコマンドの成否（$?）。0 なら成功、それ以外は失敗——これも 2 番の管の仲間、なのかもしれない。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "雑音を捨てた証跡（2>/dev/null）と、ナンバーの報告（PLATE: …）——両方要る。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "声は拾った。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "出力には管が二本ある。声（1）と雑音（2）。雑音の管だけ塞げば、声ははっきり聞こえる。"},
        ],
    ),
    MissionDef(
        19, "The Detective's Playbook", "捜査手順書を書け",
        "変数と if を使ったシェルスクリプトを自作し、実行して判定する。",
        ["sh", "grep"],
        # 判定は judge.py の Mission19 専用ロジック（patrol.sh 実行 + FOUND 出力 +
        # 自作スクリプトに変数定義と if を含む）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION19_FS,
        hints=[
            "ゴール: /root/precinct_desk/sample.sh を手本に、変数と if を使った自作スクリプト /root/precinct_desk/patrol.sh を echo で書き、chmod +x して sh で実行し FOUND を出してから sh case_file.sh → git push する。",
            "スクリプトは echo '行' > patrol.sh（1 行目）、echo '行' >> patrol.sh（2 行目以降）で組み立てる。中身は 変数=値 / if grep -q \"$変数\" evidence.txt; then / echo \"FOUND\" / fi の 4 行。evidence.txt に出てくる名前（Sam）を変数に入れる。$ を含む行はシングルクォートで囲む。",
            "cd /root/precinct_desk → cat sample.sh（手本）→ cat evidence.txt（探す名前）→ echo 'TARGET=Sam' > patrol.sh → echo 'if grep -q \"$TARGET\" evidence.txt; then' >> patrol.sh → echo '  echo \"FOUND\"' >> patrol.sh → echo 'fi' >> patrol.sh → cat patrol.sh（確認）→ chmod +x patrol.sh → sh patrol.sh（FOUND が出る）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"playbook\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "今日から書く側だ。今まで実行するだけだった手順（sh）を、後輩のために手順書として残す。\n署の机（precinct_desk）に見本（sample.sh）と証拠（evidence.txt）がある。"},
            {"id": "sample", "when": "after", "line": r"^cat .*sample\.sh", "text": "変数に言葉を入れて（KEYWORD=）、それを探させ（grep -q）、見つかったら告げる（echo FOUND）。四行で一つの捜査手順、ということか。"},
            {"id": "evidence", "when": "after", "line": r"^cat .*evidence\.txt", "text": "Sam Whitfield——探す名前はこれ。手順書には名前を変数に入れて渡す。"},
            {"id": "first_line", "when": "after", "line": r"^echo .*> *[^>]*patrol\.sh", "text": "一行目を書いた。続きは >> で足していく（> だと上書きで消える）。"},
            {"id": "review", "when": "after", "line": r"^cat .*patrol\.sh", "text": "読み返す。変数、if、echo FOUND、fi——見本と同じ形になっているか。"},
            {"id": "denied", "when": "after", "line": r"^sh .*patrol\.sh", "output": "permission denied", "text": "動かない。実行の鍵（chmod +x）——資料室で覚えたやつだ。"},
            {"id": "found", "when": "after", "line": r"^sh .*patrol\.sh", "output": "FOUND", "text": "FOUND！ 自分で書いた手順が、自分の代わりに証拠を見つけた。"},
            {"id": "not_found", "when": "after", "line": r"^sh .*patrol\.sh", "output": r"^$", "text": "何も言わない……見つからなかった、ということ。変数の名前か、探すファイルの場所を見直す。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "手順書に変数と if が入っていて、実行して FOUND が出たか——echo FOUND を直書きしただけでは通らない。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "手順書は本物になった。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "case_file.sh も、誰かが書いた手順書だった。実行する側から書く側へ——黒い画面は、書けば動く。"},
        ],
    ),
    MissionDef(
        20, "Map of the City", "この街の地図",
        "FHS（/etc, /var/log, /home, /tmp）を巡り、黒幕の住民登録を探す。",
        ["grep", "tail"],
        # 判定は judge.py の Mission20 専用ロジック（/etc・/var/log・/tmp・/home の
        # 4区画探索 + 黒幕名報告）で行うため expected_script_patterns は空。
        initial_filesystem=_MISSION20_FS,
        hints=[
            "ゴール: /etc・/var/log・/tmp・/home の 4 区画をそれぞれ ls / cat / tail / grep のどれかで調べ、黒幕のユーザー名（/home の下の名前）を echo で報告して sh case_file.sh → git push する。",
            "ls / で街の全体図。設定は /etc（cat /etc/hosts, /etc/passwd）、出来事は /var/log（tail /var/log/entry.log）、消し忘れは /tmp（ls -a /tmp で隠しファイル）、住民は /home（ls /home）。判定は 4 区画すべてを覗いたかを見る。報告は echo \"ユーザー名\"。",
            "ls /（全体図）→ cat /etc/hosts（市役所）→ tail /var/log/entry.log（公文書館: 誰がどこへ）→ cat /tmp/.forgotten（ゴミ捨て場の消し忘れ）→ ls /home/mr_black（住宅街）→ echo \"mr_black\"（報告）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"map\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "事務所を出て、街へ。この街（Linux）には決まった区画がある——設定は市役所（/etc）、出来事は公文書館（/var/log）、住民は住宅街（/home）、消したい物はゴミ捨て場（/tmp）。\n黒幕の住民登録は、どこかにあるはず。"},
            {"id": "map", "when": "after", "line": r"^ls /\s*$", "text": "街の全体図。bin は道具街、etc は市役所、home は住宅街……名前は看板だ。"},
            {"id": "etc", "when": "after", "line": r"^(cat|ls|grep|tail) .*/etc", "text": "市役所の台帳。名簿（passwd）には住民の名前と家（/home/…）が並んでいる。"},
            {"id": "log", "when": "after", "line": r"^(cat|tail|grep) .*/var/log", "output": "unknown", "text": "23:55、正体不明の誰かが /home/mr_black へ向かった——公文書館は出来事を全部残している。"},
            {"id": "tmp", "when": "after", "line": r"^(cat|ls|grep|tail) .*/tmp", "text": "ゴミ捨て場。ドットで始まる名前は隠しファイル——消し忘れは、いつもここにある。"},
            {"id": "home", "when": "after", "line": r"^(cat|ls|grep|tail) .*/home", "text": "住宅街。mr_black の家に住民登録がある。名前を報告に書く。"},
            {"id": "judge_map", "when": "after", "line": r"^sh .*case_file\.sh", "output": "map is incomplete", "text": "地図がまだ埋まっていない、と。/etc、/var/log、/tmp、/home——四つ全部を覗いたか。"},
            {"id": "judge_fail", "when": "after", "line": r"^sh .*case_file\.sh", "output": "pattern mismatch", "text": "黒幕のユーザー名を報告に書いたか……。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "住民登録は押さえた。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "新しい道具は一つも使わなかった。街の区画を知っているだけで、辿り着けた。\n——次に本物の黒い画面を開いたとき、そこは知っている街のはず。"},
        ],
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
        hints=[
            "ゴール: 壊された PATH（道具箱の場所リスト）を echo $PATH で確認し、export PATH=/usr/local/bin:/usr/bin:/bin で直して grep か find を成功させ、壊されていた値（/tmp/.stolen）を echo で報告して sh case_file.sh → git push する。",
            "grep が command not found でも道具は消えていない。echo $PATH（または printenv PATH）で今の値が見える。絶対パスなら動く: /bin/cat /root/toolbox_room/hint.txt。which grep で在処も分かる。直すのは export PATH=/usr/local/bin:/usr/bin:/bin。報告は echo \"壊されていた値\"。",
            "echo $PATH（壊れた値 /tmp/.stolen を見る）→ /bin/cat /root/toolbox_room/hint.txt（絶対パスで手掛かりを読む）→ which grep（道具の在処）→ export PATH=/usr/local/bin:/usr/bin:/bin（復旧）→ grep TOOL /root/toolbox_room/hint.txt（道具が戻った）→ echo \"/tmp/.stolen\"（報告）→ sh case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m \"toolbox\"（セーブ）→ git push（提出）",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "事務所に戻ると異変が起きていた。grep も find も「そんな道具は知らない」と言う。\n盗まれたのは道具じゃない——道具箱の場所リスト（PATH）のはず。"},
            {"id": "gone", "when": "after", "line": r"^(grep|find|cat|ls)\b", "output": "command not found", "text": "……道具が無い。いや、無いのは道具じゃなく、探す場所のリストのほうだ。今のリストを見る（echo $PATH）。"},
            {"id": "path", "when": "after", "line": r"^(echo \$PATH|printenv PATH)", "output": "stolen", "text": "/tmp/.stolen——リストが丸ごと書き換えられている。道具街（/bin）が無ければ、名前で呼んでも誰も来ない。"},
            {"id": "abs", "when": "after", "line": r"^/bin/", "text": "住所で直接呼べば動く。道具はまだ道具街にある——リストが破られただけ、で確定。"},
            {"id": "which", "when": "after", "line": r"^(which|type) ", "output": "/bin/", "text": "在処は /bin。ならリストに /bin を戻せばいい（export PATH=…）。"},
            {"id": "restored", "when": "after", "line": r"^export PATH=", "text": "リストを書き戻した。道具を呼んでみる。"},
            {"id": "sh_gone", "when": "after", "line": r"^sh ", "output": "command not found", "text": "事件ファイルすら開けない——sh も道具のひとつ、ということか。住所で呼ぶ（/bin/sh）手もあるが、先にリストを直すほうが早い。"},
            {"id": "judge_broken", "when": "after", "line": r"^(/bin/)?sh .*case_file\.sh", "output": "PATH is still broken", "text": "まだリストが壊れたまま、と。export PATH=/usr/local/bin:/usr/bin:/bin。"},
            {"id": "judge_fail", "when": "after", "line": r"^(/bin/)?sh .*case_file\.sh", "output": "pattern mismatch", "text": "直した後に道具（grep か find）を一度使ったか。壊されていた値（/tmp/.stolen）を報告に書いたか……。"},
            {"id": "judge_pass", "when": "after", "line": r"^(/bin/)?sh .*case_file\.sh", "output": "all checks passed", "text": "道具箱は取り戻した。記録して本部へ。"},
            {"id": "clear", "when": "clear", "text": "コマンドは魔法じゃなく、リスト（PATH）の中の住所から呼ばれる道具だった。\n——「そんなコマンドは知らない」と言われたら、まずリストを疑え。"},
        ],
    ),
    # --- ここに Mission26〜28 相当（server 編。id は既存と衝突しない新規採番）を
    #     挿入予定。_DEFS の並び順がそのままプレイ順序になる（このコメント直下 =
    #     Mission21 の直後・Mission22（最終事件）の直前）。---
    MissionDef(
        22, "Case Closed", "最終事件 — すべてを繋げろ",
        "学んだ全技術を関所として突破し、黒幕の名を本部に提出する。",
        ["find", "ssh", "exit", "chmod", "grep", "sort", "uniq", "tar", "md5sum", "sh"],
        # 判定は judge.py の Mission22 専用ロジック（8関所を直列検査。欠けた関所を
        # "Warning: checkpoint <n> incomplete" で示す）で行うため
        # expected_script_patterns は空。
        initial_filesystem=_MISSION22_FS,
        # 最終事件のヒントは 1 段階目のみ（Mission参照 § 22「もう教えることはない」）。
        hints=[
            "ゴール: これまでの技術を 8 つの関所の順に通す — ① find で /root/clues の鍵（*.key）を探す ② ssh ghost.example で証拠を読み exit ③ chmod +r で /root/vault/locked.txt を読む ④ grep | sort | uniq -c で /root/logs/calls.log を集計 ⑤ tar -xf で /root/clues/evidence.tar を開く ⑥ md5sum で中身を照合 ⑦ 変数と if の自作 sh で FOUND を出す ⑧ 黒幕の名前を echo で報告 — そして sh case_file.sh → git push。",
        ],
        story_beats=[
            {"id": "start", "when": "start", "text": "全部の事件が、一人に繋がっていた。手がかり（clues）、資料室（vault）、通話記録（logs）——これまでの道具を全部使って、黒幕の名を本部に出す。\nもう教えてくれる先輩はいない。"},
            {"id": "key", "when": "after", "line": r"^find ", "output": r"\.key", "text": "鍵が見つかった。中身は……回線の宛先か。"},
            {"id": "orders", "when": "after", "line": r"^cat .*orders\.txt", "output": "BOSS:", "text": "また、この名前。全部の糸がここへ戻ってくる。"},
            {"id": "burner", "when": "after", "line": r"^cat .*locked\.txt", "output": "burner", "text": "使い捨ての番号。通話記録（calls.log）で裏を取る——回数を数えれば、嘘は消える。"},
            {"id": "counted", "when": "after", "line": r"uniq\s+-c", "text": "最頻出の番号が、資料室の番号と一致した。"},
            {"id": "note", "when": "after", "line": r"^cat .*final_note", "text": "S.V.——署名入りの走り書き。本物かどうかは、指紋（md5sum）で決める。"},
            {"id": "verdict", "when": "after", "line": r"^sh .*\.sh", "output": "FOUND", "text": "手順書が「FOUND」と告げた。自分の書いた判定が、自分の推理を裏付けた。"},
            {"id": "checkpoint", "when": "after", "line": r"^sh .*case_file\.sh", "output": "checkpoint", "text": "関所が一つ抜けている、と。番号の順に——find、ssh、chmod、パイプ集計、tar、md5sum、自作 sh、報告。"},
            {"id": "judge_pass", "when": "after", "line": r"^sh .*case_file\.sh", "output": "all checks passed", "text": "八つの関所、すべて通った。記録して——最後の push だ。"},
            {"id": "clear", "when": "clear", "text": "黒幕の名は本部へ届いた。事件は閉じた。\n——ここでやったことは全部、本物の黒い画面でそのまま通じる。理解すれば、怖くない。"},
        ],
    ),
]

MISSIONS: dict[int, MissionDef] = {m.id: m for m in _DEFS}


def get_mission(mission_id: int) -> MissionDef | None:
    return MISSIONS.get(mission_id)


def all_missions() -> list[MissionDef]:
    """Mission 一覧をプレイ順序（= `_DEFS` の並び順）で返す。

    `id` 順ではない点に注意（`id` は安定した事件番号であり並び順ではない）。
    """
    return list(_DEFS)


def mission_index(mission_id: int) -> int:
    """プレイ順序での 0-based 位置。未知の mission_id は ValueError。"""
    for i, mission in enumerate(_DEFS):
        if mission.id == mission_id:
            return i
    raise ValueError(f"unknown mission_id: {mission_id}")


def first_mission_id() -> int:
    """プレイ順序で最初の Mission の id。"""
    return _DEFS[0].id


def previous_mission_id(mission_id: int) -> int | None:
    """プレイ順序で1つ前の Mission の id（先頭 Mission なら None）。"""
    index = mission_index(mission_id)
    return _DEFS[index - 1].id if index > 0 else None


def next_mission_id(mission_id: int) -> int | None:
    """プレイ順序で1つ後の Mission の id（末尾 Mission なら None）。"""
    index = mission_index(mission_id)
    return _DEFS[index + 1].id if index + 1 < len(_DEFS) else None


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
#   - judge.py `_MISSION10_ORIGINAL_PATH` / `_MISSION10_SUBMITTED_PATH` は
#     /root/will_office/original.txt・submitted.txt に追随済み（Phase F）。
#   - judge.py `_MISSION19_SCRIPT_PATH`（プレイヤーが作る patrol.sh の置き場）は
#     /root/precinct_desk/patrol.sh に追随済み（Phase F）。
#   - `_MISSION15_HISTORY`（情報屋の履歴）→ /root/informant_trail/journal.log（対応済み。Phase F）
# Mission10 以外は Mission 別 FS がまだ現役のためここでは変更しない（world 内の文章・
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
