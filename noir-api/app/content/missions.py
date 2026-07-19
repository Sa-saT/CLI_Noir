"""Mission カタログ（Mission1〜22）。

出典: docs/Mission参照ファイル.md。title は英語名、title_ja は画面表示名。
allowed_commands は各 Mission の必須コマンド + 共通の基本操作（ls/cd/cat/pwd/echo/git）。
詳細正規表現・初期FS は実装時に本 MissionDef を拡張する（設計指示書 § 11 / § 5）。
"""

from dataclasses import dataclass, field

# 全 Mission 共通で使える基本操作（ナビゲーション + 疑似 Git ワークフロー）。
BASE_COMMANDS = ["ls", "cd", "cat", "pwd", "echo", "git"]


def _file(content: str, *, immutable: bool = False) -> dict:
    return {
        "type": "file",
        "content": content,
        "mode": "rw-r--r--",
        "owner": "detective",
        "mtime": "2026-01-01T00:00:00Z",
        "immutable": immutable,
    }


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
    ),
    MissionDef(
        5, "The Locked Vault", "開かずの資料室",
        "パーミッションを読み解き、chmod で証拠と case_file.sh を解錠する。",
        ["ls", "chmod"],
    ),
    MissionDef(
        6, "Shadow Process", "盗聴器を止めろ",
        "ps で不審プロセスを見つけ、裏取りしてから kill する。",
        ["ps", "kill", "grep"],
    ),
    MissionDef(
        7, "Inside the Machine", "機械の胸の内",
        "/proc を読み、偽装プロセスの正体を暴いて起訴・停止する。",
        ["ps", "kill", "grep", "free", "uptime"],
    ),
    MissionDef(
        8, "Master of Disguise", "変装潜入",
        "合言葉を見つけ su で barman になり、権限付きファイルを読む。",
        ["su", "whoami", "exit"],
    ),
    MissionDef(
        9, "Sealed Evidence", "封印された証拠品",
        "file で正体を確かめながら、多重アーカイブを開封して手がかりを得る。",
        ["file", "tar", "gunzip", "unzip"],
    ),
    MissionDef(
        10, "The Forged Letter", "改ざんされた遺言状",
        "diff で改ざん箇所を特定し、sed で原本どおりに復元する。",
        ["diff", "sed"],
    ),
    MissionDef(
        11, "Torn Note", "切り裂かれた脅迫状",
        "断片ファイルを sort/cut/paste で並べ替え、全文を復元する。",
        ["sort", "cut", "paste"],
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
