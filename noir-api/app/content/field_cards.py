"""現場実習カード（設計指示書 § 11 ゲーム機能 11。2026-09-13 実装）。

Mission クリア時に「同じことを君の本物の PC でやってみろ」と渡すテキストカード。
対象は**読み取り系の安全なコマンドだけ**（破壊的操作・書き込みは載せない。echo も
リダイレクト無し）。ターミナルの開き方（macOS / Windows）はフロント側の共通文。

各カード: {"lead": 一言, "steps": [{"cmd": 実機で打つ行, "note": 何が見えるか}], "caution": 任意の注意}
"""

FIELD_CARDS: dict[int, dict] = {
    1: {"lead": "名刺の代わりに、自分の家（ホーム）を覗く。", "steps": [
        {"cmd": "pwd", "note": "今いる場所。ログイン直後はホームディレクトリ"},
        {"cmd": "ls", "note": "家にある物の一覧。ゲームの desk に相当する"},
        {"cmd": "cat ~/.bashrc", "note": "無ければ ~/.zshrc。読むだけ。設定ファイルは普通のテキスト"},
    ]},
    2: {"lead": "find で自分の PC の中から名前で探す。", "steps": [
        {"cmd": "find ~ -name \"*.txt\"", "note": "ホーム以下の .txt を全部。多すぎたら Ctrl+C で止める"},
        {"cmd": "find ~ -name \"*.pdf\" | head", "note": "先頭だけ見る。パイプはここでも同じ"},
    ], "caution": "出てくるのは絶対パス。それが「誰でも辿り着ける住所」"},
    3: {"lead": "ssh は相手が要る。今は道具の在処だけ確かめる。", "steps": [
        {"cmd": "which ssh", "note": "実機にも同じ道具がある"},
        {"cmd": "ssh -V", "note": "バージョン表示。繋がずに終わる"},
    ]},
    4: {"lead": "行数を数え、絞って、数える。", "steps": [
        {"cmd": "wc -l ~/.bash_history", "note": "無ければ ~/.zsh_history。自分が打った履歴の行数"},
        {"cmd": "history | grep ls | wc -l", "note": "ls を何回打ったか。管を繋ぐ"},
        {"cmd": "history | awk '{print $2}' | sort | uniq -c | sort -n | tail", "note": "自分が一番使う道具のランキング"},
    ]},
    5: {"lead": "刻印（rwx）を読む。", "steps": [
        {"cmd": "ls -l ~", "note": "先頭 10 文字が鍵の刻印"},
        {"cmd": "ls -l /etc/passwd", "note": "誰でも読めるが、書けるのは root だけ"},
        {"cmd": "ls -ld /root", "note": "たいてい入れない部屋。それが権限"},
    ], "caution": "chmod は自分で作ったファイルにだけ。システムの物には触らない"},
    6: {"lead": "名簿（ps）を見る。止めない。", "steps": [
        {"cmd": "ps aux | head", "note": "本物の名簿。見慣れない名前が並ぶ"},
        {"cmd": "ps aux | wc -l", "note": "動いている住人の数"},
    ], "caution": "kill は自分で起動した物にだけ。分からなければ打たない"},
    7: {"lead": "機械の胸の内を読む（Linux なら）。", "steps": [
        {"cmd": "cat /proc/cpuinfo | head", "note": "Linux のみ。macOS には /proc が無い（sysctl -n machdep.cpu.brand_string）"},
        {"cmd": "cat /proc/meminfo | head -3", "note": "free が読んでいる元"},
        {"cmd": "ls /proc | head", "note": "PID の部屋"},
    ]},
    8: {"lead": "今の自分が誰か。", "steps": [
        {"cmd": "whoami", "note": "ログインしている自分"},
        {"cmd": "id", "note": "番号（uid）と所属（groups）"},
    ], "caution": "su / sudo は今日は打たない。変装は責任が伴う"},
    9: {"lead": "鑑識（file）は拡張子を信じない。", "steps": [
        {"cmd": "file ~/*", "note": "ホームの物の正体。ディレクトリ・テキスト・画像"},
        {"cmd": "file /bin/ls", "note": "道具そのものも鑑識にかけられる"},
    ]},
    10: {"lead": "比べる道具を持て。", "steps": [
        {"cmd": "diff <(echo a) <(echo b)", "note": "1 行の違いを diff が指す（bash/zsh）"},
        {"cmd": "echo 5O000 | sed 's/O/0/'", "note": "画面で置換。ファイルは変わらない"},
    ]},
    11: {"lead": "並べて、切り出す。", "steps": [
        {"cmd": "ls | sort", "note": "名前順"},
        {"cmd": "cat /etc/passwd | cut -d: -f1 | head", "note": "区切り文字で列を切る。住民の名前だけ"},
    ]},
    12: {"lead": "調べてから、踏み込まない（今日は調べるだけ）。", "steps": [
        {"cmd": "dig example.com", "note": "住所を引く（無ければ nslookup example.com）"},
        {"cmd": "ping -c 3 example.com", "note": "3 回だけ。生きているか"},
    ]},
    13: {"lead": "時限装置の予定表を読む。", "steps": [
        {"cmd": "crontab -l", "note": "自分の予定表。無ければ no crontab と出るだけ"},
        {"cmd": "date", "note": "今"},
        {"cmd": "cal", "note": "今月"},
    ]},
    14: {"lead": "矢印を辿る。", "steps": [
        {"cmd": "ls -l /usr/bin | grep '\\->' | head", "note": "本物の案内板（symlink）"},
        {"cmd": "readlink -f /usr/bin/python3", "note": "無ければ file /usr/bin/python3。矢印の先の実体"},
    ]},
    15: {"lead": "自分の足取りを読む。", "steps": [
        {"cmd": "history | tail -n 20", "note": "最後の 20 手"},
        {"cmd": "history | grep cd", "note": "どこへ行ったか"},
    ]},
    16: {"lead": "網の目を選ぶ。", "steps": [
        {"cmd": "ls /etc/*.conf", "note": "* は全部"},
        {"cmd": "ls /dev/tty[0-9]", "note": "[0-9] は一文字（Linux）"},
        {"cmd": "ls \"$HOME\"", "note": "空白が入るかもしれない物は引用符で束ねる"},
    ]},
    17: {"lead": "指紋を採る。", "steps": [
        {"cmd": "md5sum /etc/hostname", "note": "macOS は md5 /etc/hosts"},
        {"cmd": "sha256sum /etc/hostname", "note": "macOS は shasum -a 256 /etc/hosts。ダウンロードした物の照合にも同じ手"},
    ]},
    18: {"lead": "雑音の管だけ塞ぐ。", "steps": [
        {"cmd": "ls /root", "note": "たいてい Permission denied（雑音）"},
        {"cmd": "ls /root 2>/dev/null", "note": "雑音が消える"},
        {"cmd": "echo $?", "note": "直前の成否。0 以外は失敗"},
    ]},
    19: {"lead": "書けば動く。", "steps": [
        {"cmd": "echo 'echo FOUND' > /tmp/patrol.sh && sh /tmp/patrol.sh", "note": "/tmp に 1 行の手順書。自分の家の外には書かない"},
        {"cmd": "cat /tmp/patrol.sh", "note": "手順書もただのテキスト"},
    ]},
    20: {"lead": "知っている街のはず。", "steps": [
        {"cmd": "ls /", "note": "全体図。etc / var / home / tmp / bin"},
        {"cmd": "cat /etc/hosts", "note": "市役所の台帳"},
        {"cmd": "ls /var/log | head", "note": "公文書館（macOS は /var/log も同じ）"},
    ]},
    21: {"lead": "道具箱のリストを読む。", "steps": [
        {"cmd": "echo $PATH", "note": "道具箱の場所リスト"},
        {"cmd": "which ls", "note": "ls の在処"},
        {"cmd": "type cd", "note": "cd は組み込み（builtin）"},
    ], "caution": "export PATH=… は打たない（打つなら新しいターミナルを開いて試す。閉じれば元に戻る）"},
    22: {"lead": "全部、本物の黒い画面でそのまま通じる。", "steps": [
        {"cmd": "find ~ -name \"*.txt\" | head", "note": "探す"},
        {"cmd": "ls -l ~ | head", "note": "鍵を読む"},
        {"cmd": "history | awk '{print $2}' | sort | uniq -c | sort -n | tail -3", "note": "数える"},
        {"cmd": "md5sum /etc/hostname", "note": "指紋（macOS: md5 /etc/hosts）"},
    ]},
    23: {"lead": "枝を切って戻る（git があれば）。", "steps": [
        {"cmd": "git --version", "note": "無ければここまで。入れるなら公式サイトから"},
        {"cmd": "git branch", "note": "リポジトリの中で。今の枝に *"},
        {"cmd": "git log --oneline | head", "note": "履歴は枝ごと"},
    ]},
    24: {"lead": "競合の目印を知っている。", "steps": [
        {"cmd": "git status", "note": "マージ中なら Unmerged paths と出る"},
        {"cmd": "grep -rn '<<<<<<<' . | head", "note": "残った目印を探す網"},
    ]},
    25: {"lead": "送付状（PR）は GitHub の画面か gh で。", "steps": [
        {"cmd": "gh --version", "note": "GitHub CLI。無ければ Web の Pull requests タブが同じ物"},
        {"cmd": "gh pr list", "note": "リポジトリの中で。開いている送付状"},
    ]},
    26: {"lead": "機械の診察はこの三つから。", "steps": [
        {"cmd": "uptime", "note": "どれだけ起きているか"},
        {"cmd": "df -h", "note": "満腹度（macOS も同じ）"},
        {"cmd": "du -sh ~/* 2>/dev/null | sort -h | tail", "note": "家の中で一番重い物"},
    ]},
    27: {"lead": "扉と身分証。", "steps": [
        {"cmd": "hostname", "note": "名札"},
        {"cmd": "ss -tln", "note": "開いている扉（macOS は netstat -an | grep LISTEN）"},
        {"cmd": "ip a", "note": "住所（macOS は ifconfig）"},
    ], "caution": "systemctl stop は自分で入れたサービスにだけ。169.254.169.254 はクラウドの中からしか見えない"},
    28: {"lead": "同じ Linux が何か所にあっても、診かたは同じ。", "steps": [
        {"cmd": "cat /etc/os-release", "note": "OS の名札（macOS は sw_vers）"},
        {"cmd": "uname -a", "note": "カーネル"},
        {"cmd": "journalctl -u ssh -n 5", "note": "Linux のみ。sshd の日誌（権限が要るかも）"},
    ]},
    29: {"lead": "これは実機ではやらない。", "steps": [
        {"cmd": "ls -la ~", "note": "消す代わりに、隠しファイル（. で始まる）まで全部見る"},
        {"cmd": "man rm", "note": "何をする道具か、手引きで読む。q で閉じる"},
    ], "caution": "rm と dd は予備の機械で一度見た。本物では、消す前に必ず ls で相手を確かめる"},
}
