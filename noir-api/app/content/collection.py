"""隠しファイル収集（設計指示書 § 11 ゲーム機能 5。2026-09-13 実装）。

各 Mission の区画に `.` で始まる隠しファイルを 1 つずつ置く。`ls -a` で見つけ、`cat` で読むと
「回想」として集まり、集めると背景ストーリー（探偵の名前が名刺から消えていた理由）が
読める。ご褒美コマンド（機能 12）はこの収集数で解放する（app/evaluator/rewards.py）。

ファイルは「世界の住人が書いた文書」として書く（AUTHORING_GUIDE § 4）。ここでは
元相棒 R. の手帳の切れ端という体裁。順番（no）は物語の時系列。
"""

# path → {"no", "title", "text"}。path は統合ワールドの絶対パス（区画の中）。
FRAGMENTS: dict[str, dict] = {
    "/root/desk/.old_photo_note": {"no": 1, "title": "写真の裏", "text": (
        "R. の手帳より——\n"
        "写真の裏に書いておく。三年前の冬、相棒の名前が本部の帳簿から消えた。\n"
        "本人はまだ気づいていない。名刺から名前が消えるのは、その次だ。"
    )},
    "/root/park/.bench_carving": {"no": 2, "title": "ベンチの彫り跡", "text": (
        "ベンチの裏に彫ってあった。「S.V. was here」\n"
        "港の猫の事件のずっと前から、あの女はこの街を歩いている。"
    )},
    "/root/wiretap_room/.reel_label": {"no": 3, "title": "リールのラベル", "text": (
        "テープの箱の底にラベル。「Reel 7 — do not index」\n"
        "誰かが本部の記録係に、索引を付けるなと命じている。消えた名前は、索引から消えた名前だ。"
    )},
    "/root/vault/.archivist_memo": {"no": 4, "title": "記録係のメモ", "text": (
        "資料室の記録係が辞める前に残したメモ。\n"
        "「削除依頼は正規の書式で来た。署名は本部長代理。だが筆跡は女のものだった」"
    )},
    "/root/bar/.coaster": {"no": 5, "title": "コースターの走り書き", "text": (
        "barman のコースターに鉛筆で。「探偵の名前を買う客がいる。高値で」\n"
        "名前は売り物になる。消してから、売る。"
    )},
    "/root/evidence_locker/.tag_stub": {"no": 6, "title": "荷札の半券", "text": (
        "封印箱の荷札の半券。差出人欄は空白、受取人は「S. Vance」\n"
        "封印を何重にもしたのは、開ける手間で諦めさせるためだったのか。"
    )},
    "/root/will_office/.clerk_diary": {"no": 7, "title": "書記の日記", "text": (
        "遺言事務所の書記の日記。「ゼロとオーの差し替えを頼まれた。相場の十倍で」\n"
        "一文字の改ざんは、あの女の手口の癖だ。"
    )},
    "/root/scraps/.envelope": {"no": 8, "title": "封筒の消印", "text": (
        "脅迫状の封筒。消印は港の郵便局、差出日は名前が消えた翌日。\n"
        "R. は書いている。「脅迫状は最初から、相棒に宛てたものだった」"
    )},
    "/root/crontab_room/.wall_scratch": {"no": 9, "title": "壁の引っ掻き傷", "text": (
        "時計の裏の壁に「0 0 * * 5」——金曜 0 時。\n"
        "帳簿から名前を消す処理も、金曜 0 時の時限装置で流されていた。"
    )},
    "/root/mirror_hall/.frame_back": {"no": 10, "title": "額縁の裏", "text": (
        "鏡の額縁の裏に写真。若い日の S.V. と、まだ名前のあった相棒が並んでいる。\n"
        "R. の字で「二人は同じ事務所にいた」。"
    )},
    "/root/informant_trail/.pier_ticket": {"no": 11, "title": "桟橋の切符", "text": (
        "13 番桟橋の乗船券。半券に「Vance / one-way」\n"
        "情報屋が消えた桟橋で、あの女も一度、街を出ている。"
    )},
    "/root/toolbox_room/.receipt": {"no": 12, "title": "工具屋の領収書", "text": (
        "道具箱の底に領収書。品名「PATH リスト書換え依頼」、支払人 S.V.\n"
        "道具を盗む必要は無い。場所リストを壊せば、探偵は何も出来なくなる。"
    )},
    "/root/clues/.last_page": {"no": 13, "title": "手帳の最後のページ", "text": (
        "R. の手帳、最後のページ。\n"
        "「名前を消したのは、相棒に街を出て欲しかったから。私は止められなかった。\n"
        " だが名刺に名前を書き戻す方法だけは、教えておいた。echo と、リダイレクト」"
    )},
}

TOTAL = len(FRAGMENTS)


def is_fragment(abs_path: str) -> bool:
    return abs_path in FRAGMENTS
