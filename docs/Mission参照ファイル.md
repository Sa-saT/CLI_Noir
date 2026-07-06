# Mission参照ファイル（Agent用）

各 Mission の仕様を Agent が参照する基準書。  
確定情報は固定値で記載し、未確定は最小限だけ残す。

---

## 0. 共通ルール（確定）

- MVP: Mission1〜3（Mission4〜20 は Phase2。§ 5 参照）
- 判定: 正規表現ベース / 順不同許容 / 大小文字区別あり
- 不正コマンド時: エラーメッセージ表示のみ（即失敗にしない）
- 疑似 Git: `git add -> git commit -m "<msg>" -> git push` 順序必須
- `git commit` = ゲームセーブ（1 Mission 中に何度でも可。再開時にセーブ選択可）
- `git push` = クリア判定（最新 commit の状態で合否判定）
- 次 Mission 遷移時、前 Mission のクリア前 commit は全消去
- commit message: 1 文字以上（MVP はパターン制約なし）
- 実 Git 連携なし（内部 `git_state` で判定）
- エラーメッセージは `設計指示書.md` § 12 を正とする
- コマンド仕様は `バックエンド_コマンド機能仕様.md` を正とする

---

## 1. Mission共通テンプレート（推奨初期値）

### A. 基本情報
- mission_id: `1..20`
- title: `Mission名（英語） + 画面表示名（日本語）`
- 学習テーマ: `基本操作 / 検索 / remote操作 / 正規表現 / 疑似Git`
- 想定プレイ時間: `10〜25分`
- 難易度: `1〜5`

### B. 初期状態
- current_path: `Mission1=/root, Mission2=/root/park, Mission3=remote接続後に/gate`
- local / remote: `Mission1,2=local / Mission3=local開始→sshでremote`
- 初期FS: `設計指示書.md § 5 の local構造 + Mission専用ヒントファイル`
- 初期 `git_state`: `staged=[] / committed=false / pushed=false`

### C. 判定仕様
- `expected_script_patterns`: 正規表現配列
- AND/OR: 基本 AND（全パターン一致必須）。必要時のみ OR グループ追加
- `case_file.sh` 採点対象: コマンド実行ログ + 生成/編集ファイル内容 + git_state
- 不一致時: `Warning: pattern mismatch`（致命時は `Error: pattern mismatch`）

### D. 失敗/例外
- 想定エラー: `file not found / path not found / invalid pattern / command not allowed`
- ヒント: 3 段階（方向性 → 具体コマンド → ほぼ答え）
- リトライ: 失敗理由表示 → ヒント表示 → 再実行

### E. UI/演出
- 背景画像: `mission{n}.png`
- 説明文: ミッション目的 + 主要コマンド + 完了条件を 3 行で表示
- クリア演出: フェード + "Mission Complete!" + 次 Mission 導線

---

## 2. Mission1（Edit Business Card）

### 確定
- 目的: 名刺ファイルにユーザー名を書き込み、`case_file.sh` 判定後に疑似 `git push` まで完了する
- 想定コマンド: `ls`, `cd`, `cat`, `echo`, `git status/add/commit/push`
- 進行条件: 疑似 Git ワークフロー成功まで
- 名刺ファイル: `/root/desk/businesscard.txt`
- `case_file.sh` の正規表現:
  - `^cat\\s+/root/desk/businesscard\\.txt$`
  - `^echo\\s+.+\\s*>\\s+/root/desk/businesscard\\.txt$`
  - `^git\\s+add\\s+.+$`
  - `^git\\s+commit\\s+-m\\s+.+$`
  - `^git\\s+push$`
- ヒント:
  - 1: `まず机(desk)を調べ、名刺ファイルの場所を確認しよう。`
  - 2: `名刺にはあなたのユーザー名を書き込む必要があります。`
  - 3: `編集後は git add -> git commit -m -> git push の順で進めよう。`

---

## 3. Mission2（Park Cat Search）

### 確定
- 目的: 公園で猫ファイルを探索し、絶対パス・状態を満たした `case_file.sh` で完了する
- 完了には疑似 `git push` 成功を含む
- 猫ファイル: `catinfo.txt`（配置: `/root/park/swing/catinfo.txt`）
- 必須コマンド: `find`, `cat`, `grep`
- 任意（加点）: `awk`, `sort`, `uniq`
- 誤答パターン:
  - 絶対パス未記述: `Error: absolute path required`
  - 猫情報キー不足: `Error: required cat status not found`
  - `find` 未使用: `Warning: use find to locate clues`

---

## 4. Mission3（Amusement Park Bomb）

### 確定
- 目的: remote（遊園地）でヒント収集し、正規表現条件を満たす `case_file.sh` で完了する
- `ssh amusement_park` で接続 → 初期ディレクトリ `/gate`
- local へ戻る: `exit` のみ（`cd` 不可）
- 接続エラー: `Host not found` / `Permission denied`
- 必須: `ssh amusement_park` → `find` → `cat/grep` → `case_file.sh` → 疑似 `git push`
- 任意: `awk`, `sort`, `uniq`
- 必須正規表現キー:
  - `Code: [A-Z0-9]{4,}`
  - `Wire: (red|blue|yellow)`
  - `Height: [0-9]+`

---

## 5. Mission4〜20（Phase2・概要確定）

概要・フロー・クリア条件方針は確定。`expected_script_patterns` の詳細正規表現は各 Mission の実装時に確定する（Mission2/3 と同じ運用）。Mission20 を最終章とし、4〜19 は独立性を保つ（順序の入れ替えが可能）。

### Mission4: Wiretap Tape「盗聴テープを解析せよ」
- 学習テーマ: パイプ・リダイレクト（Level 5）
- あらすじ: 押収した盗聴記録（数万行のログ）に、犯人が繰り返し連絡していた電話番号が埋もれている。全部読むのは不可能だ。流れ作業で捌け。
- フロー: `wc -l tape.log`（分量に絶望する演出）→ `head`/`tail` で構造把握 → `grep "TEL" tape.log | sort | uniq -c | sort` で最頻出番号を特定 → report → 疑似 git push
- 必須: `grep`, パイプ, `sort`, `uniq`（`wc`, `head`, `tail` は加点）
- クリア条件: `uniq\s+-c` を含むパイプ行の実行 + 正解番号 `TEL: [0-9]{3}-[0-9]{4}` の記述
- ゲーム性: 「cat では読み切れない」体験そのものがパズル。パイプの必要性を強制的に体感させる

### Mission5: The Locked Vault「開かずの資料室」
- 学習テーマ: パーミッション（Level 7）
- あらすじ: 重要証拠には鍵（権限）がかかっている。読めない・開けない・実行できない、3種類の鍵を使い分けろ。
- フロー: `ls -l` で `----------` を確認 → `chmod +r` で閲覧解錠 → ヒントから次の部屋へ → 実行権限のない `case_file.sh` を発見 → `chmod +x` → 実行してクリア
- 必須: `ls -l`, `chmod`, `cat`
- クリア条件: `chmod\s+\+?[rx]` 系パターン2回以上 + case_file 実行成功
- ゲーム性: `rwx` 表示を「鍵の刻印」として読み解く。数値モード（`chmod 644`）での解錠は加点

### Mission6: Shadow Process「盗聴器を止めろ」
- 学習テーマ: プロセス管理（Level 6）
- あらすじ: 事務所に盗聴プログラムが仕掛けられている。動いているプロセスの正体を突き止めて止めろ。ただし時計やポストを止めるな。
- フロー: `ps aux` で一覧 → 正規プロセス（`clock`, `mailbox`, `heater`）に混ざる `listener_x` を発見 → 裏取り → `kill <PID>`
- 必須: `ps`, `kill`
- クリア条件: 正しい PID への kill 実行 + `mission_flags.bug_removed = true`
- ゲーム性: 「間違い探し」。正規プロセスを kill すると警告 + 巻き戻し（即失敗にしない）。裏取りせず勘で kill すると正解でも減点

### Mission7: Master of Disguise「変装潜入」
- 学習テーマ: ユーザー切替（Level 7）
- あらすじ: 容疑者「barman」しか読めないファイルがある。合言葉（パスワード）は店のどこかに。変装して読め。
- フロー: `cat` で `Permission denied` を体験 → 店内探索で合言葉発見 → `su barman` → `whoami` で確認 → 目的ファイル閲覧 → `exit` で自分に戻る
- 必須: `su`, `whoami`, `cat`, `exit`
- クリア条件: barman 状態での対象ファイル閲覧 + 元ユーザーへの復帰
- ゲーム性: 「今の自分は誰か」の確認習慣。exit で戻る構造が Mission3 の ssh/exit と対になり反復学習になる

### Mission8: Sealed Evidence「封印された証拠品」
- 学習テーマ: アーカイブ・鑑識（Level 8）
- あらすじ: 押収品はマトリョーシカのように何重にも封印されている。拡張子は当てにならない。鑑識（file）にかけながら開封しろ。
- フロー: `file evidence.dat`（実体は tar.gz と判明）→ `tar -xzf` → 出てきたファイルをまた `file` → `unzip` → … → 最深部の手がかり入手
- 必須: `file`, `tar`, `gunzip` または `unzip`
- クリア条件: 最深部ファイルの `cat` 実行 + 記載コードの report 転記
- ゲーム性: 開封のたびに一歩近づく「発掘」感。「拡張子ではなく file で確かめる」鉄則のパズル化

### Mission9: The Forged Letter「改ざんされた遺言状」
- 学習テーマ: 差分・置換（Level 5）
- あらすじ: 遺言状の原本と写しのどこかが書き換えられている。差分を見つけ、写しを原本どおりに直せ。
- フロー: `diff original.txt submitted.txt` で改ざん行を特定 → `sed 's/…/…/'` で復元 → report へ
- 必須: `diff`, `sed`
- クリア条件: diff 実行 + sed による正しい置換 + 復元後ファイルの一致判定
- ゲーム性: 目視では見つからない1文字差（`0` と `O`）を仕込む

### Mission10: Torn Note「切り裂かれた脅迫状」
- 学習テーマ: テキスト整形（Level 5）
- あらすじ: 細切れにされた脅迫状の断片ファイルを並べ替え、貼り合わせて全文を復元しろ。
- フロー: `ls` で断片確認 → `cat piece_*` で把握 → `sort` で行順復元 → `cut` / `paste` で整形 → 全文を report へ
- 必須: `sort`, `cut` または `paste`
- クリア条件: 復元済み全文の正規表現一致
- ゲーム性: 手作業でも解けるが sort/cut なら圧倒的に速い、という「道具の価値」の体験

### Mission11: Ghost Line「幽霊回線を追え」
- 学習テーマ: ネットワーク追跡（Level 9）
- あらすじ: 犯人は通称「ghost」というサーバーから指示を出している。住所（IP）を割り出し、生存を確認し、突入せよ。
- フロー: `dig ghost.example` → `ping` で生存確認 → `ss` で開いている扉確認 → `ssh` → remote 内で証拠収集 → `exit`
- 必須: `dig`（または `host`）, `ping`, `ssh`, `exit`
- クリア条件: dig → ping → ssh の順序実行 + remote 内の証拠ファイル閲覧
- ゲーム性: 「調べてから踏み込む」実務手順が捜査手順そのものとして機能する

### Mission12: Midnight Broadcast「深夜0時の犯行予告」
- 学習テーマ: cron・時刻書式（Level 10）
- あらすじ: 犯人はサーバーに時限装置（cron ジョブ）を仕掛けた。`0 0 * * 5` を解読し、正しいジョブだけを解除しろ。
- フロー: `crontab -l` → 5フィールド書式の解読（ヒント: `man 5 crontab`）→ 危険ジョブ特定 → 解除 → 解除時刻を report へ
- 必須: `crontab -l`, `cat`, `date`
- クリア条件: 正しいジョブの特定（発動日時の記述一致）+ 解除フラグ
- ゲーム性: LPIC 頻出の cron 書式が、暗記ではなく時限爆弾の解読体験として定着する

### Mission13: Hall of Mirrors「鏡の館」
- 学習テーマ: リンク・実体判定（Level 8）
- あらすじ: 保管庫は「鏡の館」。同名ファイルのほとんどは案内板（シンボリックリンク）で、実体は1つだけ。本物を見つけ出せ。
- フロー: `ls -l` で `->` 表示を読む → `file` で `symbolic link` 判定 → 実体を特定して閲覧 → 実体の絶対パスを report へ
- 必須: `ls -l`, `file`
- クリア条件: 実体ファイルの絶対パス記述（リンクのパスは不正解）
- ゲーム性: 推理がそのまま `ls -l` の読解訓練になる。Mission2 の絶対パス学習の応用編

### Mission14: The Informant's Trail「情報屋の足取り」
- 学習テーマ: 履歴・ログ監視（Level 5〜6）
- あらすじ: 失踪した情報屋の端末に操作履歴が残っている。最後に何を調べ、どこへ向かったのか。足取りを再現しろ。
- フロー: `history`（情報屋の履歴を閲覧する演出）→ `tail journal.log` → 履歴どおりに再実行 → 行き先を突き止める
- 必須: `history`, `tail`, `grep`
- クリア条件: 履歴再現（同一コマンド列の実行）+ 行き先の記述一致
- ゲーム性: 「他人の履歴から意図を推理する」= コマンド理解の総復習。履歴が攻略チャートになるメタ構造

### Mission15: The Great Sweep「一斉捜索令状」
- 学習テーマ: ワイルドカード・引用符（概念）
- あらすじ: 数百の押収ファイルのうち、令状が許すのは「`case_` で始まり数字1桁」だけ。範囲をパターンで指定しろ。犯人は空白入りファイル名 `top secret.txt` で目くらましを残している。
- フロー: `ls case_*`（多すぎる）→ `ls case_[0-9].txt` で絞る → 一括調査 → `cat top secret.txt` が失敗 → `cat "top secret.txt"` で開封
- 必須: glob（`*` `?` `[...]`）の使用、引用符付きパス
- クリア条件: glob パターン使用 + 引用符付きファイルの閲覧 + 発見コードの記述
- ゲーム性: 「令状の範囲＝パターン」。空白入りファイル名は引用符を知らないと物理的に開けない

### Mission16: Fingerprint「指紋は嘘をつかない」
- 学習テーマ: チェックサム・真正性検証（Level 8）
- あらすじ: 見た目が完全に同一な契約書コピー5通のうち1通だけ改ざんされている。ファイルの「指紋」で照合しろ。
- フロー: `cat copy_*.txt`（全部同じに見える）→ 台帳の原本ハッシュと `md5sum copy_*.txt` を突き合わせ → 不一致の1通を特定 → `diff` で箇所確認 → report
- 必須: `md5sum`（または `sha256sum`）, `cat`（`diff`, `sort` は加点）
- クリア条件: md5sum 実行 + 改ざんファイル名と改ざん箇所の記述一致
- ゲーム性: 「1文字違えば指紋は別物」というハッシュの性質を推理トリックに使う。Mission9 の発展形

### Mission17: Silence in the Static「雑音の中の声」
- 学習テーマ: 標準エラー・リダイレクト・終了コード（概念）
- あらすじ: 老朽アーカイブサーバーは探索のたびに大量のエラー（雑音）を吐く。雑音だけをシュレッダーに流せ。
- フロー: `grep -r "witness" /archive` → `Permission denied` の雑音で画面が埋まる → `2>/dev/null` で声だけ残す → 手がかり入手 → `echo $?` で成否確認の練習
- 必須: `2>/dev/null` を含む実行（`echo $?` は加点）
- クリア条件: `2>\s*/dev/null` パターンの実行 + 手がかりの記述
- ゲーム性: 「出力には2本の管がある」を雑音と声で可視化。雑音の絶望→1記号で静寂、のカタルシス

### Mission18: The Detective's Playbook「捜査手順書を書け」
- 学習テーマ: シェルスクリプト基礎（Level 11）
- あらすじ: 手作業でやってきた「証拠確認→判定→報告」を、後輩のために手順書（スクリプト）に書き起こせ。今まで実行するだけだった `case_file.sh`、今日からは書く側だ。
- フロー: `cat sample.sh` で見本を読む → `echo` で自作 `patrol.sh` を作成（変数定義 + `if grep -q "$TARGET" file; then echo "FOUND"; fi`）→ `sh patrol.sh` → `FOUND` 出力確認
- 必須: `sh`, 変数定義と `$変数` 参照, `if` 文
- クリア条件: 変数定義 + if 文を含むスクリプトの作成と実行成功
- ゲーム性: 「実行する側→書く側」への視点逆転。for 文で複数ファイル巡回は加点

### Mission19: Map of the City「この街の地図」
- 学習テーマ: FHS・実 Linux のディレクトリ構成（概念）
- あらすじ: 舞台は「本物の Linux の街」へ。設定は市役所（`/etc`）、出来事は公文書館（`/var/log`）、住民は住宅街（`/home`）、消したいものはゴミ捨て場（`/tmp`）。黒幕の住民登録を探し出せ。
- フロー: `ls /` で全体図 → `cat /etc/hosts` → `/var/log/entry.log` を `tail`/`grep` で調査 → `/tmp` の消し忘れ → `/home/<黒幕>` を特定
- 必須: `ls`, `cd`, `cat`, `grep`, `tail`
- クリア条件: `/etc` `/var/log` `/tmp` `/home` の4区画探索フラグ + 黒幕ユーザー名の記述一致
- ゲーム性: 新コマンドゼロ・知識だけで解く「地理」の回。クリア後に実機を開いた時「知っている街」になっている
- 備考: FHS 版の仮想FSマップが必要（既存の探偵事務所マップとは別レイアウト）

### Mission20: Case Closed「最終事件 — すべてを繋げろ」
- 学習テーマ: 総合演習（Level 1〜11 の複合・卒業試験）
- あらすじ: 全事件は一人の黒幕に繋がっていた。local と複数 remote を行き来し、権限を解除し、ログをパイプで捌き、最終証拠の真正性をハッシュで確かめ、黒幕の名を本部に提出せよ。
- フロー: 学んだ技術を関所として配置（find → dig/ssh → chmod → grep|sort|uniq → tar → md5sum → 自作スクリプトで最終判定 → 報告）
- 必須: `find`, `ssh`, `chmod`, パイプ, `tar`, `md5sum`, `sh`（自作）, 疑似 git 一式
- クリア条件: 全関所フラグの達成 + 黒幕名の正規表現一致 + git push
- ゲーム性: ヒントは1段階目のみ（相棒が「もう教えることはない」）。クリア時に「実PCでも同じことができる」エピローグを表示し、実機・LPIC 受験への導線とする

---

## 6. Agent 出力フォーマット（固定）

```md
# Mission{n}: <title>

## 目的
## 初期状態
## 必須コマンド
## expected_script_patterns
## クリア条件
## 失敗条件/エラー文言
## テストケース（正常系 / 異常系）
```

---

## 7. Agent 参照優先順位

1. `設計指示書.md`（全体方針・API・エラー定義・開発フロー）
2. `Mission参照ファイル.md`（本ファイル。Mission詳細）
3. `バックエンド_コマンド機能仕様.md`（コマンド実装詳細）
4. `環境構築手順.md`（セットアップ手順）
