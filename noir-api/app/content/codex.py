"""捜査道具図鑑 / エラー図鑑（設計指示書 § 11 ゲーム機能 2・10。2026-09-13 実装）。

- 道具図鑑: 正常実行したコマンド名を `state["codex"]["commands"]` に登録する。実 PC での
  意味とゲーム内の意味の並記はフロント（`noir-client/app/utils/commandCatalog.ts`）が持つ。
- エラー図鑑: 遭遇したエラーを「捜査資料」として `state["codex"]["errors"]` に登録する。
  翻訳文（探偵の独り言と同じ文体）はここ `ERROR_ENTRIES` が正で、設計指示書 § 12 の
  一覧と 1:1 に対応する。§ 12 に無い実コマンド風の文言（`rm: …` 等）も、遭遇しうる
  ものは載せる。

図鑑の表示は Mission 画面の scene 上のレイヤー（独り言の一つ奥。DESIGN.md § 5）。
"""

# key: エラー行の先頭一致で判定する（長いものから順に試す）。
ERROR_ENTRIES: list[dict] = [
    {"key": "Error: command not allowed", "title": "その道具は持ち出せない", "text": "この事務所の許可リスト（allowlist）に無いか、禁じられた道具（denylist）。実機なら動くものもあるが、ここでは意図して封じてある。"},
    {"key": "Error: command not found", "title": "道具の在処が分からない", "text": "道具箱の場所リスト（PATH）にその道具の置き場が無い、というだけ。道具が消えたわけじゃない。`echo $PATH` と `which` で確かめる。"},
    {"key": "Error: invalid input", "title": "書き方が違う", "text": "引数や記号の並びが道具の期待と違う。道具のせいにする前に、書式を疑う。`man <道具>` が手引き。"},
    {"key": "Error: path not found", "title": "その住所に建物は無い", "text": "指したパスの途中か末尾が存在しない。`ls` で今いる場所を、`pwd` で住所を確かめる。"},
    {"key": "Error: file not found", "title": "その名前のファイルは無い", "text": "綴り、大文字小文字、そして今いる場所。空白入りの名前は引用符で束ねないと二つに割れる。"},
    {"key": "Error: directory not found", "title": "その部屋は無い", "text": "`cd` の先が存在しない。相対パスなら今いる場所から数え直す。`/` から書けば迷わない。"},
    {"key": "Error: directory already exists", "title": "もうその部屋はある", "text": "`mkdir` の先に同名の物がある。上書きはしない——それが安全側。"},
    {"key": "Error: invalid pattern", "title": "網の編み方が違う", "text": "正規表現として読めない。`[` を開いたら閉じる、特別な記号はエスケープする。"},
    {"key": "Error: pattern mismatch", "title": "報告が合っていない（致命）", "text": "事件ファイルが要求する形と一致しない。ヒントの書式どおりに、もう一度。"},
    {"key": "Warning: pattern mismatch", "title": "報告が合っていない", "text": "判定は通らなかったが、失敗ではない。足りない手順か、報告の書式を見直す合図。"},
    {"key": "Error: permission denied", "title": "鍵が無い", "text": "読む・書く・実行する——どれかの鍵（rwx）が無い。`ls -l` で刻印を見て、必要なら `chmod` か、持ち主になる（su）。"},
    {"key": "Permission denied", "title": "鍵が無い", "text": "読む・書く・実行する——どれかの鍵（rwx）が無い。`ls -l` で刻印を見て、必要なら `chmod` か、持ち主になる（su）。"},
    {"key": "Host not found", "title": "その宛先は地図に無い", "text": "ホスト名の綴り違いか、まだ回線が開いていない。`dig` で住所（IP）を引けるかから確かめる。"},
    {"key": "Error: remote not connected", "title": "回線が繋がっていない", "text": "向こう側のファイルを触るには、先に `ssh` で回線を繋ぐ。"},
    {"key": "Error: nothing to commit", "title": "記録に載せるものが無い", "text": "セーブ（commit）の前に、記録対象に載せる（`git add`）。順番が逆だと空振りする。"},
    {"key": "Error: commit message required", "title": "メモ無しのセーブは受け付けない", "text": "`git commit -m \"何をしたか\"`。未来の自分への手紙だと思って一言。"},
    {"key": "Error: push not allowed before commit", "title": "セーブしていない物は出せない", "text": "本部へ出す（push）のは、記録した（commit）もの。`git add` → `git commit` → `git push` の順。"},
    {"key": "Error: mission requirements not met", "title": "本部が受け付けない", "text": "判定（`sh case_file.sh`）を通したセーブでないと出せない。判定 → add → commit → push。"},
    {"key": "Error: unresolved conflict markers", "title": "機械のメモが残っている", "text": "`<<<<<<<` `=======` `>>>>>>>` はマージが残した目印。どちらを採るか決めて、目印ごと消す。"},
    {"key": "Error: you have unmerged files", "title": "マージが途中", "text": "競合を直して `git add` → `git commit` で確定してから次へ。"},
    {"key": "Error: commit your changes before switching branches", "title": "机の上を片付けてから", "text": "枝を切り替えると机の中身が入れ替わる。未セーブの変更は先に commit。"},
    {"key": "Error: pull request", "title": "送付状の状態が違う", "text": "承認（Approved）されていない PR は merge できない。`gh pr view` で指摘を読む。"},
    {"key": "Error: no such process", "title": "その番号の住人はいない", "text": "PID を打ち間違えたか、もう止まっている。`ps aux` で名簿を見直す。"},
    {"key": "Warning: you stopped a legitimate process", "title": "正規の住人を止めた", "text": "kill は名簿を見てから。裏取り（`/proc/<PID>/cmdline`）をしてから撃つ。"},
    {"key": "curl: (6) Could not resolve host", "title": "その宛先は名前が引けない", "text": "この事務所の curl は模擬 API（メタデータ）専用。外の世界には繋がらない。"},
    {"key": "curl: (7) Failed to connect", "title": "メタデータの窓口が無い", "text": "169.254.169.254 はクラウドの機械の中からしか見えない住所。事務所からは繋がらない。"},
    {"key": "rm: cannot remove", "title": "rm が断った", "text": "ディレクトリは `-r` が要る／その名前は無い。rm は確認も取り消しも無い道具——断られた方が幸運。"},
    {"key": "dd: ", "title": "dd が断った", "text": "`if=`（元）と `of=`（先）が要る。先を間違えれば本物のディスクが無になる道具。"},
    {"key": "Unit ", "title": "そのサービスは登録が無い", "text": "`systemctl status <名前>` の名前が違う。`ss -tln` や `journalctl` から名前を拾う。"},
    {"key": "merge: ", "title": "その枝は無い", "text": "`git branch` で枝の名前を確かめる。"},
]

_KEYS_LONGEST_FIRST = sorted(ERROR_ENTRIES, key=lambda e: -len(e["key"]))


def error_entry_for(line: str) -> dict | None:
    """出力行に対応する図鑑エントリ（先頭一致）。無ければ None。"""
    for entry in _KEYS_LONGEST_FIRST:
        if line.startswith(entry["key"]):
            return entry
    return None
