"""`man` = 捜査ハンドブック（設計指示書 § 11 ゲーム機能 6。2026-09-13 実装）。

実 man と同じ節構成（NAME / SYNOPSIS / DESCRIPTION / OPTIONS）に、ゲーム内の意味
（IN THIS OFFICE）と SEE ALSO を添える。「困ったら man」の実務習慣づけが目的なので、
DESCRIPTION は**実機での意味**を書き、ゲーム限定の知識は IN THIS OFFICE に分ける。
未収録は実 man と同じく `No manual entry for <name>`。

各エントリ: name, section(既定 1), summary(NAME 行), synopsis, description(行リスト),
options([(flag, 説明)]), office(行リスト), see_also([name...])
"""

MANPAGES: dict[str, dict] = {
    "ls": {"summary": "ディレクトリの中身を一覧する", "synopsis": "ls [-a] [-l] [パス...]",
           "description": ["指定したディレクトリ（省略時はカレント）にあるファイル・ディレクトリの名前を並べる。", "`.` で始まる隠しファイルは -a を付けないと出ない。"],
           "options": [("-a", "隠しファイル（`.` 始まり）と `.` `..` も出す"), ("-l", "詳細表示。先頭 10 文字が権限の刻印（rwx）、持ち主、大きさ、更新日時")],
           "office": ["今いる部屋の手がかりを見回す。隠された物（回想）は -a で。"], "see_also": ["cd", "pwd", "find"]},
    "cd": {"summary": "作業ディレクトリを移動する", "synopsis": "cd [パス]",
           "description": ["パスへ移動する。省略時はホーム、`-` は直前にいた場所へ。`..` は一つ上。"],
           "options": [], "office": ["部屋を移る。ssh 中は事務所（/root）へは戻れない——回線を切る（exit）。"], "see_also": ["ls", "pwd"]},
    "pwd": {"summary": "今いる場所の絶対パスを表示する", "synopsis": "pwd", "description": ["カレントディレクトリを `/` から始まる住所で表示する。"], "options": [], "office": ["迷ったら打つ。プロンプトにも出ているが、報告に書く住所はこれで確かめる。"], "see_also": ["cd", "ls"]},
    "cat": {"summary": "ファイルの中身を表示する", "synopsis": "cat ファイル...", "description": ["ファイルを先頭から最後まで画面に流す。複数指定すると連結して流す。"], "options": [], "office": ["証拠を読む。長い物は head / tail / grep で絞る。"], "see_also": ["head", "tail", "less", "grep"]},
    "less": {"summary": "ファイルをページ送りで読む", "synopsis": "less ファイル", "description": ["長いファイルを 1 画面ずつ読む。実機では q で終了、/ で検索。"], "options": [], "office": ["ここでは cat と同じく全文を出す。"], "see_also": ["cat", "head", "tail"]},
    "head": {"summary": "先頭の数行を表示する", "synopsis": "head [-n 行数] ファイル", "description": ["既定は先頭 10 行。"], "options": [("-n N", "先頭 N 行")], "office": ["テープの形を見るのに使う。全部読まない癖。"], "see_also": ["tail", "cat"]},
    "tail": {"summary": "末尾の数行を表示する", "synopsis": "tail [-n 行数] ファイル", "description": ["既定は末尾 10 行。実機の -f は追記をライブで追う。"], "options": [("-n N", "末尾 N 行")], "office": ["日誌の最新を見る。情報屋の足取りはここに残る。"], "see_also": ["head", "journalctl"]},
    "echo": {"summary": "文字列を表示する", "synopsis": "echo 文字列 [> ファイル | >> ファイル]", "description": ["引数をそのまま出力する。`> ファイル` で上書き保存、`>> ファイル` で末尾に追記。`$変数` は展開される（シングルクォート内は展開しない）。"], "options": [], "office": ["報告書を書く道具。エディタが無いので echo とリダイレクトで作る。"], "see_also": ["cat", "printenv"]},
    "touch": {"summary": "空のファイルを作る（更新日時を更新する）", "synopsis": "touch ファイル", "description": ["無ければ空ファイルを作り、あれば更新日時だけ今にする。"], "options": [], "office": [], "see_also": ["mkdir", "echo"]},
    "mkdir": {"summary": "ディレクトリを作る", "synopsis": "mkdir ディレクトリ", "description": ["新しいディレクトリ（部屋）を作る。既にあればエラー。"], "options": [], "office": [], "see_also": ["ls", "cd"]},
    "grep": {"summary": "行を検索する", "synopsis": "grep [-r] [-q] パターン [ファイル...]", "description": ["パターン（正規表現）を含む行だけを出す。パイプで受けた入力も検索できる。"], "options": [("-r", "ディレクトリを再帰的に"), ("-q", "出力せず、見つかれば成功（スクリプトの if 用）"), ("-E / egrep", "拡張正規表現")], "office": ["テープから番号だけを抜く。資料庫から証言だけを拾う。"], "see_also": ["find", "sort", "uniq", "sed"]},
    "egrep": {"summary": "grep -E（拡張正規表現）の旧別名", "synopsis": "egrep パターン [ファイル...]", "description": ["実機では非推奨の別名。grep -E を使う。"], "options": [], "office": [], "see_also": ["grep"]},
    "fgrep": {"summary": "grep -F（固定文字列）の旧別名", "synopsis": "fgrep 文字列 [ファイル...]", "description": ["実機では非推奨の別名。grep -F を使う。"], "options": [], "office": [], "see_also": ["grep"]},
    "find": {"summary": "ファイルを名前や種類で探す", "synopsis": "find パス -name パターン | -type f|d", "description": ["パス以下を再帰的に辿り、条件に合う物の**絶対パス**を出す。"], "options": [("-name P", "名前が P（* ? [] はクォートする）"), ("-type f/d", "ファイル / ディレクトリ")], "office": ["公園の猫、倉庫の鍵。名前で探す道具。出てくる住所はそのまま報告に使える。"], "see_also": ["grep", "ls", "file"]},
    "sort": {"summary": "行を並べ替える", "synopsis": "sort [-n] [-r] [-u] [ファイル]", "description": ["行を辞書順に並べる。"], "options": [("-n", "数値順"), ("-r", "逆順"), ("-u", "重複を除く")], "office": ["uniq の前に必ず sort。番号順の断片を並べる。"], "see_also": ["uniq", "cut", "wc"]},
    "uniq": {"summary": "隣り合う重複行をまとめる", "synopsis": "uniq [-c] [ファイル]", "description": ["連続した同じ行を 1 つにする。sort してから使う。"], "options": [("-c", "出現回数を先頭に付ける")], "office": ["最頻出の番号を数える決め手。"], "see_also": ["sort", "grep"]},
    "wc": {"summary": "行数・単語数・文字数を数える", "synopsis": "wc [-l] ファイル", "description": ["既定は行・単語・バイト。"], "options": [("-l", "行数だけ")], "office": ["テープの分量に絶望するための道具。"], "see_also": ["head", "sort"]},
    "cut": {"summary": "行の一部（列）を切り出す", "synopsis": "cut -d 区切り -f 列番号 [ファイル]", "description": ["区切り文字で分けた N 列目だけを出す。"], "options": [("-d C", "区切り文字"), ("-f N", "列番号（1 始まり）")], "office": ["番号:本文 の本文だけ、passwd の名前だけ。"], "see_also": ["paste", "sort", "tr"]},
    "paste": {"summary": "行を横に貼り合わせる", "synopsis": "paste [-d 区切り] ファイル1 ファイル2", "description": ["同じ行番号どうしを並べて 1 行にする。"], "options": [("-d C", "区切り文字（既定はタブ）")], "office": [], "see_also": ["cut"]},
    "tr": {"summary": "文字を置き換える・消す", "synopsis": "tr 集合1 集合2 | tr -d 集合", "description": ["入力の文字を 1 文字ずつ対応表で置き換える。"], "options": [("-d", "指定した文字を消す")], "office": [], "see_also": ["sed"]},
    "sed": {"summary": "行を置換して出力する", "synopsis": "sed 's/前/後/[g]' ファイル [> 出力先]", "description": ["各行で最初の一致を置換（g で全部）。画面に出すだけで元ファイルは変わらない——書き戻すならリダイレクト。"], "options": [], "office": ["ゼロとオーの一文字を直す。"], "see_also": ["diff", "tr", "grep"]},
    "diff": {"summary": "2 つのファイルの違いを示す", "synopsis": "diff ファイル1 ファイル2", "description": ["違う行を `<`（1 側）と `>`（2 側）で示す。同じなら何も出ない。"], "options": [], "office": ["目で見つからない差を機械に言わせる。"], "see_also": ["sed", "md5sum"]},
    "history": {"summary": "打ったコマンドの履歴を表示する", "synopsis": "history", "description": ["番号付きでこれまでのコマンドを並べる。実機では !番号 で再実行できる。"], "options": [], "office": ["情報屋の足取りはここに残っていた。"], "see_also": ["tail"]},
    "clear": {"summary": "画面を消す", "synopsis": "clear", "description": ["Ctrl+L と同じ。"], "options": [], "office": [], "see_also": []},
    "ps": {"summary": "動いているプロセスを一覧する", "synopsis": "ps aux", "description": ["PID・ユーザー・状態・コマンドの名簿。名前は名乗ったもの。"], "options": [("aux", "全ユーザー・全プロセスを詳細に")], "office": ["名簿。裏取りは /proc/<PID>/cmdline。"], "see_also": ["kill", "free", "uptime"]},
    "kill": {"summary": "プロセスに終了を求める", "synopsis": "kill PID", "description": ["指定 PID にシグナル（既定 TERM）を送る。"], "options": [], "office": ["盗聴器を止める。正規の住人を撃つと警告。"], "see_also": ["ps"]},
    "free": {"summary": "メモリの使用量を表示する", "synopsis": "free", "description": ["合計・使用・空き。/proc/meminfo を読んでいる。"], "options": [], "office": [], "see_also": ["uptime", "df"]},
    "uptime": {"summary": "稼働時間と負荷を表示する", "synopsis": "uptime", "description": ["起動からの時間。/proc/uptime を読んでいる。"], "options": [], "office": ["機械の診察の一手目。"], "see_also": ["free", "df"]},
    "chmod": {"summary": "権限（rwx）を変える", "synopsis": "chmod +r|+x|数値 ファイル", "description": ["読む(r)・書く(w)・実行(x) の鍵を付け外しする。数値（644 等）でも指定できる。"], "options": [("+r / +x", "鍵を足す"), ("644, 755", "数値モード")], "office": ["資料室の封印を解く。sh で動かすスクリプトは +x。"], "see_also": ["ls", "su"]},
    "su": {"summary": "別のユーザーになる", "synopsis": "su ユーザー", "description": ["そのユーザーの権限でシェルを開く。戻るのは exit。"], "options": [], "office": ["変装。今の自分は whoami で確かめる。"], "see_also": ["whoami", "id", "exit"]},
    "whoami": {"summary": "今のユーザー名を表示する", "synopsis": "whoami", "description": ["実効ユーザー名。"], "options": [], "office": ["変装したら必ず打つ癖。"], "see_also": ["id", "su"]},
    "id": {"summary": "ユーザー ID とグループを表示する", "synopsis": "id", "description": ["uid・gid・所属グループ。"], "options": [], "office": [], "see_also": ["whoami"]},
    "file": {"summary": "ファイルの種類を判定する", "synopsis": "file ファイル", "description": ["拡張子ではなく中身から種類（テキスト・圧縮・リンク…）を判定する。"], "options": [], "office": ["鑑識。封印の皮を剥ぐ前に必ず。"], "see_also": ["tar", "unzip", "ln"]},
    "tar": {"summary": "アーカイブを展開・作成する", "synopsis": "tar -xzf アーカイブ | tar -xf アーカイブ", "description": ["複数ファイルをまとめた書庫を扱う。"], "options": [("-x", "展開"), ("-z", "gzip 圧縮を解く"), ("-f F", "対象ファイル")], "office": ["展開先は今いる場所。"], "see_also": ["gunzip", "unzip", "file"]},
    "gunzip": {"summary": "gzip 圧縮を解く", "synopsis": "gunzip ファイル.gz", "description": ["1 ファイルの圧縮を解き、.gz を外した名前にする。"], "options": [], "office": [], "see_also": ["tar", "file"]},
    "unzip": {"summary": "zip を展開する", "synopsis": "unzip ファイル.zip", "description": ["今いる場所に展開する。"], "options": [], "office": [], "see_also": ["tar", "file"]},
    "ln": {"summary": "リンクを作る", "synopsis": "ln -s 実体 リンク名", "description": ["-s でシンボリックリンク（案内板）。ls -l で `->` と出る。"], "options": [("-s", "シンボリックリンク")], "office": ["鏡の館の鏡はこれ。"], "see_also": ["file", "ls"]},
    "which": {"summary": "コマンドの在処を表示する", "synopsis": "which コマンド", "description": ["PATH の中から実行ファイルを探して場所を出す。"], "options": [], "office": ["道具箱のどこに道具があるか。"], "see_also": ["type", "printenv"]},
    "type": {"summary": "コマンドの種類を表示する", "synopsis": "type コマンド", "description": ["組み込み（builtin）か、PATH 上のファイルか。"], "options": [], "office": [], "see_also": ["which"]},
    "md5sum": {"summary": "MD5 ハッシュ（指紋）を計算する", "synopsis": "md5sum ファイル...", "description": ["中身が 1 文字でも違えばまったく違う値になる。"], "options": [], "office": ["写しの真贋。ダウンロードした物の照合にも同じ手。"], "see_also": ["sha256sum", "diff"]},
    "sha256sum": {"summary": "SHA-256 ハッシュを計算する", "synopsis": "sha256sum ファイル...", "description": ["md5sum より強い指紋。配布物の照合はこちらが主流。"], "options": [], "office": [], "see_also": ["md5sum"]},
    "ping": {"summary": "相手が生きているか確かめる", "synopsis": "ping ホスト", "description": ["ICMP を送って返事を待つ。"], "options": [], "office": ["踏み込む前の生存確認。"], "see_also": ["dig", "ssh", "ss"]},
    "dig": {"summary": "名前から IP を引く", "synopsis": "dig ホスト名", "description": ["DNS に問い合わせて住所（IP）を得る。"], "options": [], "office": ["幽霊の住所を割る。"], "see_also": ["host", "ping"]},
    "host": {"summary": "名前と IP を引く（簡易）", "synopsis": "host ホスト名", "description": ["dig の簡易版。"], "options": [], "office": [], "see_also": ["dig"]},
    "ss": {"summary": "開いているポート（扉）を一覧する", "synopsis": "ss -tln", "description": ["LISTEN 中の TCP ポートを数値で。"], "options": [("-t", "TCP"), ("-l", "LISTEN のみ"), ("-n", "数値表示")], "office": ["見慣れない扉を探す。"], "see_also": ["systemctl", "ip"]},
    "ip": {"summary": "ネットワークの住所を表示する", "synopsis": "ip a", "description": ["インターフェースごとの IP アドレス。"], "options": [("a / addr", "アドレス一覧")], "office": [], "see_also": ["hostname", "ss"]},
    "hostname": {"summary": "この機械の名前を表示する", "synopsis": "hostname", "description": ["名札。"], "options": [], "office": [], "see_also": ["uname", "ip"]},
    "uname": {"summary": "OS・カーネル情報を表示する", "synopsis": "uname -a", "description": ["カーネル名・ホスト名・版・アーキテクチャ。"], "options": [("-a", "全部")], "office": [], "see_also": ["hostname"]},
    "ssh": {"summary": "別の機械に接続する", "synopsis": "ssh ホスト", "description": ["遠くの機械のシェルを自分の画面に。戻るのは exit。"], "options": [], "office": ["回線を繋ぐ。未解放の宛先は Host not found。"], "see_also": ["exit", "dig", "ping"]},
    "exit": {"summary": "シェル（接続・変装）を抜ける", "synopsis": "exit", "description": ["ssh なら切断、su なら元のユーザーへ。"], "options": [], "office": ["事務所へ戻る唯一の道。"], "see_also": ["ssh", "su"]},
    "crontab": {"summary": "定期実行の予定表を表示する", "synopsis": "crontab -l", "description": ["分 時 日 月 曜日 コマンド の 5 欄 + コマンド。曜日は 0=日 … 6=土。"], "options": [("-l", "一覧")], "office": ["時限装置の目盛り。"], "see_also": ["date", "journalctl"]},
    "date": {"summary": "今の日時を表示する", "synopsis": "date", "description": [], "options": [], "office": [], "see_also": ["crontab"]},
    "export": {"summary": "環境変数を設定する", "synopsis": "export NAME=値", "description": ["以後のコマンドに引き継がれる変数。PATH は道具箱の場所リスト。"], "options": [], "office": ["壊れた PATH を直す。"], "see_also": ["printenv", "unset", "which"]},
    "unset": {"summary": "環境変数を消す", "synopsis": "unset NAME", "description": [], "options": [], "office": [], "see_also": ["export"]},
    "printenv": {"summary": "環境変数を表示する", "synopsis": "printenv [NAME]", "description": ["`echo $NAME` と同じ値が見える。"], "options": [], "office": [], "see_also": ["export", "echo"]},
    "sh": {"summary": "シェルスクリプトを実行する", "synopsis": "sh スクリプト", "description": ["ファイルに書いたコマンド列を上から実行する。変数（NAME=値）、if … then … fi、for が使える。"], "options": [], "office": ["事件ファイル（case_file.sh）の判定もこれ。配置スクリプトは +x してから。"], "see_also": ["chmod", "echo"]},
    "df": {"summary": "ディスクの使用量を区画ごとに表示する", "synopsis": "df -h", "description": ["Use% が 90% を超えたら満腹。"], "options": [("-h", "人間が読める単位")], "office": ["機械が止まる理由の一つ目。"], "see_also": ["du", "uptime"]},
    "du": {"summary": "ディレクトリ・ファイルの大きさを量る", "synopsis": "du -sh パス...", "description": ["何が腹を膨らませているかを探す。"], "options": [("-s", "合計だけ"), ("-h", "人間が読める単位")], "office": [], "see_also": ["df"]},
    "systemctl": {"summary": "サービス（常駐プログラム）を確認・起動・停止する", "synopsis": "systemctl status|start|stop|restart サービス", "description": ["systemd の管理コマンド。status で状態と直近の日誌。"], "options": [], "office": ["サーバーの中でだけ start/stop できる。正規のサービスは止めない。"], "see_also": ["journalctl", "ss", "ps"]},
    "journalctl": {"summary": "サービスの日誌を読む", "synopsis": "journalctl -u サービス [-n 行数]", "description": ["systemd のログ。止まった理由はここに書いてある。"], "options": [("-u S", "サービス S の分だけ"), ("-n N", "末尾 N 行")], "office": [], "see_also": ["systemctl", "tail"]},
    "curl": {"summary": "URL の中身を取得する", "synopsis": "curl URL", "description": ["HTTP で取りに行く。クラウドの中では 169.254.169.254 のメタデータが引ける。"], "options": [], "office": ["この事務所では模擬 API 専用。外には繋がらない。"], "see_also": ["dig"]},
    "git": {"summary": "変更を記録して共有する", "synopsis": "git status|add|commit -m|push|branch|checkout|merge|log|diff", "description": ["実 git: add で記録対象に載せ、commit で履歴に刻み、push で共有先へ。branch/checkout で作業の線を分け、merge で合流。"], "options": [], "office": ["commit＝セーブ、push＝クリア判定（ここだけ実 git と意味が違う）。枝とマージは実 git と同じ。"], "see_also": ["gh"]},
    "gh": {"summary": "GitHub を端末から操作する", "synopsis": "gh pr create --title T [--body B] | gh pr view [n] | gh pr list | gh pr merge [n]", "description": ["Pull Request の作成・閲覧・マージ。"], "options": [], "office": ["本部（主任）への送付状。Approved になるまで merge できない。"], "see_also": ["git"]},
    "rm": {"summary": "ファイル・ディレクトリを削除する", "synopsis": "rm [-r] [-f] パス...", "description": ["確認も取り消しも無い。ディレクトリは -r。"], "options": [("-r", "中身ごと"), ("-f", "確認なし・無くても黙る")], "office": ["この事務所では禁止。予備の機械（Mission29）で一度だけ。"], "see_also": ["dd", "ls"]},
    "dd": {"summary": "ブロック単位でコピー・上書きする", "synopsis": "dd if=元 of=先", "description": ["of= を間違えるとディスクごと無になる。"], "options": [], "office": ["この事務所では禁止。予備の機械で一度だけ。"], "see_also": ["rm"]},
    "cowsay": {"summary": "牛にしゃべらせる", "synopsis": "cowsay 文字列", "description": ["実在する遊びコマンド。実機にも入れられる。"], "options": [], "office": ["隠し実績の報酬。"], "see_also": ["figlet"]},
    "figlet": {"summary": "大きな文字で表示する", "synopsis": "figlet 文字列", "description": ["ASCII アートの見出し。"], "options": [], "office": ["隠し実績の報酬。"], "see_also": ["cowsay"]},
    "man": {"summary": "捜査ハンドブック（マニュアル）を読む", "synopsis": "man [節] コマンド", "description": ["実機の man は q で閉じる。困ったら man。"], "options": [], "office": ["ここでは全文をそのまま出す。"], "see_also": ["apropos", "whatis"]},
    "apropos": {"summary": "キーワードで手引きを探す", "synopsis": "apropos キーワード", "description": ["NAME 行にキーワードを含む項目を一覧する。"], "options": [], "office": [], "see_also": ["man", "whatis"]},
    "whatis": {"summary": "コマンドの一行説明", "synopsis": "whatis コマンド", "description": ["man の NAME 行だけ。"], "options": [], "office": [], "see_also": ["man"]},
}

# セクション付きの特別項目（`man 5 crontab` など）
MANPAGES_BY_SECTION: dict[tuple[str, str], dict] = {
    ("5", "crontab"): {"summary": "cron の予定表の書式", "synopsis": "分 時 日 月 曜日 コマンド",
        "description": ["各欄: 分 0-59 / 時 0-23 / 日 1-31 / 月 1-12 / 曜日 0-7（0 と 7 は日曜）。`*` は毎回、`*/15` は 15 ごと、`1,15` は列挙。", "例: `0 0 * * 5` = 毎週金曜 00:00、`*/15 * * * *` = 15 分ごと。"],
        "options": [], "office": ["深夜 0 時の犯行予告を読むための書式。"], "see_also": ["crontab"]},
}


def render(name: str, page: dict, section: str = "1") -> list[str]:
    head = f"{name.upper()}({section})"
    title = "捜査ハンドブック"
    lines = [f"{head}{title.center(max(1, 60 - 2 * len(head)))}{head}", ""]
    lines += ["NAME", f"       {name} - {page['summary']}", ""]
    lines += ["SYNOPSIS", f"       {page['synopsis']}", ""]
    if page.get("description"):
        lines += ["DESCRIPTION", *[f"       {d}" for d in page["description"]], ""]
    if page.get("options"):
        lines += ["OPTIONS", *[f"       {flag:<12}{desc}" for flag, desc in page["options"]], ""]
    if page.get("office"):
        lines += ["IN THIS OFFICE", *[f"       {d}" for d in page["office"]], ""]
    if page.get("see_also"):
        lines += ["SEE ALSO", "       " + ", ".join(f"{n}(1)" for n in page["see_also"])]
    return lines
