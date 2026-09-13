# Mission参照ファイル（Agent用）

各 Mission の仕様を Agent が参照する基準書。  
確定情報は固定値で記載し、未確定は最小限だけ残す。

---

## 0. 共通ルール（確定）

- MVP: Mission1〜3（Mission4〜22 は Phase2。§ 5 参照）
- 判定: 正規表現ベース / 順不同許容 / 大小文字区別あり
- 不正コマンド時: エラーメッセージ表示のみ（即失敗にしない）
- 疑似 Git: `git add -> git commit -m "<msg>" -> git push` 順序必須
- `git commit` = ゲームセーブ（1 Mission 中に何度でも可。再開時にセーブ選択可）
- `git push` = クリア判定（最新 commit の状態で合否判定）
- commit 履歴はプレイ全体で 1 本（Mission 遷移で消去しない）。push が通った commit は印付きで、再開するとクリア直後から
- commit message: 1 文字以上（MVP はパターン制約なし）
- 実 Git 連携なし（内部 `git_state` で判定）
- エラーメッセージは `設計指示書.md` § 12 を正とする
- コマンド仕様は `バックエンド_コマンド機能仕様.md` を正とする
- 場面画像はカレントディレクトリに紐付く（`DESIGN.md` § 1 が正）。Mission 定義は `presentation.scene_images`（場所キー → 画像・最長一致）を持つ
- Mission クリア時に**現場実習カード**（設計指示書 § 11 機能11）を表示する。文面は各 Mission の実装時に確定（安全な読み取り系コマンド限定）
- **エラー図鑑 / やらかし体験室 / ご褒美コマンド**（設計指示書 § 11 機能9・10・12）は Mission 非依存の共通機能。Mission 側での個別定義は不要

---

## 1. Mission共通テンプレート（推奨初期値）

### A. 基本情報
- mission_id: `1..22`
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
- 場面画像: `presentation.scene_images`（場所キー → 画像。current_path の最長一致で解決。`DESIGN.md` § 1）
  - Mission 既定 1 枚 = `mission{n}.png`（ルートに紐付け・フォールバック）+ 意味のある場所ごとの任意追加
- 説明文: ミッション目的 + 主要コマンド + 完了条件を 3 行で表示
- クリア演出: フェード + "Mission Complete!" + 次 Mission 導線
- クリア演出後: 現場実習カード表示（§ 0 参照。文面は実装時確定）

---

### 独り言（story_beats）とヒントの共通仕様（2026-09-13 確定）

- **独り言 = ストーリーで誘導**。探偵本人の一人称・話者ラベル無し。断定を避ける（「〜のはず」）。「!」「!?」は可。1 beat ≤ 2 行。各 beat はその Mission で一度だけ発火
- **ヒント = 直接的なゴール説明**。1: ゴール / 2: 必要コマンドと書式 / 3: コマンド列 + 各コマンドの簡易説明。ペナルティなし
- トリガー語彙（`MissionDef.story_beats` の `when`）:
  - `start`: Mission がアクティブになって最初（hello / 前 Mission クリア直後）
  - `after`: 実行後。`line`（`resolved_line` への正規表現。`paths` があれば `"<argv0> <path>"` にも当てる）+ 任意の `output`（出力全文への正規表現）+ 任意の `remote`（ssh 中か）
  - `clear`: `git push` 成功時
  - `stall`（フロント側・共通文言）: 無操作 60 秒 or 連続エラー 3 回。「……手が止まっている。焦らなくていい。ヒントを見るのは恥じゃない。」+ ヒントボタンを光らせる

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
- ヒント（2026-09-13 改訂: 直接的なゴール説明）:
  - 1: `ゴール: /root/desk/businesscard.txt に自分の名前を書き込み、sh case_file.sh で確認 → git add → git commit -m → git push で提出する。`
  - 2: `名刺は cat で読む。書き換えは echo "NAME: 名前" > businesscard.txt（上書き）。エディタ（vi 等）は無い。`
  - 3: `cat businesscard.txt（中身を読む）→ echo "NAME: 名前" > businesscard.txt（上書きで書き込む）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m "done"（セーブ）→ git push（提出）`
- 独り言（story_beats）:

| id | when | 条件 | 文言 |
|---|---|---|---|
| start | start | — | 雨の月曜。依頼人は俺の名刺を一瞥して言った——名前が無い、と。<br>……確か、机（desk）の上に置きっぱなしのはず。 |
| desk | after | line `^(cd\|ls) /root/desk` | 名刺ファイルが一枚。中身、確かめておかないと。 |
| read | after | line `^cat /root/desk/businesscard\.txt` | NAME: ???……我ながら間抜けな名刺。名前を書き込まないと話にならない。 |
| no_editor | after | line `^(vi\|vim\|nano\|emacs)\b` output `command not allowed` | この事務所にまともなエディタは無い……。書き込むなら echo で流し込む（`>`）しかないか。 |
| wrote | after | line `^echo .*> /root/desk/businesscard\.txt` | これでいい。名前の入った名刺。<br>本部に出す前に、事件ファイル（case_file.sh）で確認しておくか。 |
| judge_pass | after | line `^sh .*case_file\.sh` output `all checks passed` | 確認は通った！ あとは記録して本部へ——add、commit、そして push。 |
| judge_fail | after | line `^sh .*case_file\.sh` output `pattern mismatch` | 事件ファイルが突き返された!? 何か足りない……名刺をもう一度読み直してみるか。 |
| push_fail | after | line `^git push` output `requirements not met` | 本部が受け付けない……。確認（sh case_file.sh）を通してから、記録し直さないと駄目らしい。 |
| clear | clear | — | 名刺が本部に届いた。これで俺の名前は、この街の帳簿に載ったはず。<br>——今やったことは、本物の黒い画面でもそのまま通じる。 |

---

## 3. Mission2（Park Cat Search）

### 確定
- 目的: 公園で猫ファイルを find で探し出し、机の報告書（`/root/desk/report.txt`）に絶対パスと状態を書いて `case_file.sh` を完了する
- 報告書の置き場（2026-09-13 確定）: `/root/desk/report.txt`。判定は履歴ではなくこのファイルの**中身**を読む（find 使用だけは履歴）。Mission1 の名刺と同じ机に戻らせる導線で、「公園で調べて机で書く」流れにする
- 完了には疑似 `git push` 成功を含む
- 猫ファイル: `catinfo.txt`（配置: `/root/park/swing/catinfo.txt`）
- 必須コマンド: `find`, `cat`, `grep`
- 任意（加点）: `awk`, `sort`, `uniq`
- 誤答パターン:
  - 報告書ファイル無し: `Error: report not found — write /root/desk/report.txt`
  - 報告書に絶対パス未記述: `Error: absolute path required — report the path from /`
  - 猫情報キー不足: `Error: required cat status not found`
  - `find` 未使用: `Warning: use find to locate clues`
- ヒント（2026-09-13 改訂: 直接的なゴール説明）:
  - 1: `ゴール: catinfo.txt を find で見つけ、机の report.txt（/root/desk/report.txt）にその絶対パスと STATUS の値を書き、sh case_file.sh → git push する。`
  - 2: `find /root/park -name catinfo.txt で場所が分かる。中身は cat で読む。報告書は机に置く: echo "/root/park/swing/catinfo.txt STATUS: stray" > /root/desk/report.txt のように絶対パス（/ から）を含める。`
  - 3: `find /root/park -name catinfo.txt（名前で探す）→ cat /root/park/swing/catinfo.txt（読む）→ echo "/root/park/swing/catinfo.txt STATUS: stray" > /root/desk/report.txt（机に報告書を書く）→ sh /root/case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m "cat"（セーブ）→ git push（提出）`
- 独り言（story_beats）:

| id | when | 条件 | 文言 |
|---|---|---|---|
| start | start | — | 依頼は迷い猫。名前はマイク、黒。公園（park）で最後に見られたらしい。<br>玄関を出て、公園へ向かわないと！ |
| park | after | line `^(cd\|ls) /root/park` | ベンチ、噴水、遊具……区画が多い。当てずっぽうに歩けば日が暮れる。名前で探す（find）のが探偵の仕事、のはず。 |
| found | after | line `^find ` output `catinfo\.txt` | 出た！ 猫の記録は遊具（swing）の傍。 |
| read | after | line `^cat .*catinfo\.txt` | STATUS: stray——野良か。机（desk）に戻って、報告書（report.txt）を書かないと。<br>書く場所は `/` から始まる住所で。「swing の傍」じゃ、誰も辿り着けない。 |
| desk | after | line `^(cd\|ls) /root/desk` | 机の上。ここに report.txt を作って、猫の居場所（`/` からの住所）と状態（STATUS）を書き込む——echo で流し込めばいい、はず。 |
| wrote | after | line `^echo .*> /root/desk/report\.txt` | 報告書ができた。中身を確かめたら（cat）、事件ファイル（case_file.sh）で確認しておくか。 |
| fail_report | after | line `^sh .*case_file\.sh` output `report not found` | 報告書が無い、と言われた。机（/root/desk）に report.txt を作らないと。 |
| fail_abs | after | line `^sh .*case_file\.sh` output `absolute path required` | 突き返された!? 住所が途中から……`/` から書き直さないと。 |
| fail_status | after | line `^sh .*case_file\.sh` output `cat status not found` | 状態が抜けている。STATUS の欄を報告に写さないと。 |
| fail_find | after | line `^sh .*case_file\.sh` output `use find` | 歩き回って見つけたのはいいが、次からは find で絞ろう。この公園より広い場所も来るはず。 |
| judge_pass | after | line `^sh .*case_file\.sh` output `all checks passed` | これで報告になる。記録して、本部へ。 |
| clear | clear | — | 猫は遊具の下で丸くなっていた。住所が正確なら、誰でも同じ場所へ辿り着ける——それが絶対パス、というやつか。 |
- 絶対パスの扱い（2026-09-07 確定 / P3-08e）: 読み方は自由（`cd` してから相対パスで読んでも実 Linux と同じ意味なので合格）。絶対パスが必須なのは報告書（`/root/desk/report.txt`）に書く一行のみ。「報告書に `swing/catinfo.txt` と書いても、読んだ人がどの swing か辿れない」という絶対パスの存在理由そのものを体験させるための課題指定である。

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
- ヒント（2026-09-13 改訂: 直接的なゴール説明）:
  - 1: `ゴール: ssh amusement_park で接続し、園内の 3 ファイルから Code: / Wire: / Height: を読み取って echo で書き出し、sh case_file.sh → git push する。`
  - 2: `接続後は find . -type f で 3 ファイルを列挙し cat で読む。報告は echo "Code: XXXX" のように「キー: 値」の書式で 3 行。事務所へ戻るのは exit。`
  - 3: `ssh amusement_park（接続）→ find . -type f（ファイル列挙）→ cat booth/manual.txt / cat ferris/wiring.txt / cat sign/notice.txt（Code・Wire・Height を読む）→ echo "Code: ...", echo "Wire: ...", echo "Height: ..."（報告 3 行）→ sh case_file.sh（判定）→ git add .（記録対象に載せる）→ git commit -m "bomb"（セーブ）→ git push（提出）`
- 独り言（story_beats）:

| id | when | 条件 | 文言 |
|---|---|---|---|
| start | start | — | 電話の声は震えていた。遊園地に爆弾が仕掛けられた、解除コードは園内の設備に散らばっている、と。<br>ここからじゃ届かない。回線を繋いで（ssh）、門（amusement_park）まで踏み込まないと！ |
| no_host | after | line `^ssh ` output `Host not found` | 回線が繋がらない……。宛先の綴り、合っているか？ |
| connected | after | line `^ssh amusement_park` | 繋がった。ここは門の前（/gate）。プロンプトの色が変わった——今は向こう側にいる、ということか。 |
| survey | after | line `^(ls\|find)\b` remote | 案内所（booth）、観覧車（ferris）、看板（sign）……設備は三つ。手がかりも三つのはず。 |
| code | after | line `^cat .*manual\.txt` remote | Code が出た！ 控えておこう。 |
| wire | after | line `^cat .*wiring\.txt` remote | 切る線の色。間違えたら終わり……。 |
| height | after | line `^cat .*notice\.txt` remote | 身長制限……これが最後の数字か？ |
| no_way_back | after | line `^cd /root` output `directory not found` remote | ここは向こう側。事務所へ戻るなら回線を切る（exit）しかない、はず。 |
| judge_fail | after | line `^sh .*case_file\.sh` output `pattern mismatch` | まだ揃っていない!? Code、Wire、Height——三つとも報告に書いたか……。 |
| judge_pass | after | line `^sh .*case_file\.sh` output `all checks passed` | 三つ揃った！ 記録して本部へ。処理班が待っている。 |
| clear | clear | — | 観覧車が止まった。回線を切って（exit）、事務所へ戻ろう。<br>——ssh は、遠くの機械を自分の机にする道具、なのかもしれない。 |

---

## 5. Mission4〜22（Phase2・概要確定）

概要・フロー・クリア条件方針は確定。`expected_script_patterns` の詳細正規表現は各 Mission の実装時に確定する（Mission2/3 と同じ運用）。Mission22 を最終章とし、4〜21 は独立性を保つ（順序の入れ替えが可能）。
（2026-07-08: Mission7「機械の胸の内」/proc と Mission21「消えた道具箱」PATH を追加し番号を振り直した。旧 7〜19 → 8〜20、旧 20 → 22）

### Mission4: Wiretap Tape「盗聴テープを解析せよ」
- 学習テーマ: パイプ・リダイレクト（Level 5）
- あらすじ: 押収した盗聴記録（数万行のログ）に、犯人が繰り返し連絡していた電話番号が埋もれている。全部読むのは不可能だ。流れ作業で捌け。
- フロー: `wc -l tape.log`（分量に絶望する演出）→ `head`/`tail` で構造把握 → `grep "TEL" tape.log | sort | uniq -c | sort` で最頻出番号を特定 → report → 疑似 git push
- 必須: `grep`, パイプ, `sort`, `uniq`（`wc`, `head`, `tail` は加点）
- クリア条件: `uniq\s+-c` を含むパイプ行の実行 + 正解番号 `TEL: [0-9]{3}-[0-9]{4}` の記述
- ゲーム性: 「cat では読み切れない」体験そのものがパズル。パイプの必要性を強制的に体感させる
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）
- 2026-09-13 改訂: tape.log を 266 行（TEL 233 行 + 雑音）にし、正解 555-0142（41 回）と桁違いの似た番号（555-0124 38 回・555-0412・555-0141・555-0143 …）を混ぜて目視で数えられない量にした。開始の独り言で「盗聴室へ行って tape.log を確かめる」と誘導する

### Mission5: The Locked Vault「開かずの資料室」
- 学習テーマ: パーミッション（Level 7）
- あらすじ: 重要証拠には鍵（権限）がかかっている。読めない・開けない・実行できない、3種類の鍵を使い分けろ。
- フロー: `ls -l` で `----------` を確認 → `chmod +r` で閲覧解錠 → ヒントから奥の部屋 `/root/vault/inner` へ → 実行権限のない封印解除スクリプト `unseal.sh` を発見 → `chmod +x` → `sh unseal.sh` で封印解除 → `sh /root/case_file.sh` でクリア（2026-09-13: 統合ワールドでは `case_file.sh` が `/root` に動的合成されるため、実行権限パズルの対象を `inner/case_file.sh` から `inner/unseal.sh` へ移した）
- 必須: `ls -l`, `chmod`, `cat`
- クリア条件: `chmod +r` と `chmod +x` の両系統 + `sh …unseal.sh` の成功が command_log にあること
- ゲーム性: `rwx` 表示を「鍵の刻印」として読み解く。数値モード（`chmod 644`）での解錠は加点
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission6: Shadow Process「盗聴器を止めろ」
- 学習テーマ: プロセス管理（Level 6）
- あらすじ: 事務所に盗聴プログラムが仕掛けられている。動いているプロセスの正体を突き止めて止めろ。ただし時計やポストを止めるな。
- フロー: `ps aux` で一覧 → 正規プロセス（`clock`, `mailbox`, `heater`）に混ざる `listener_x` を発見 → 裏取り（`cat /proc/<PID>/cmdline` で実体を確認。2026-07-08 具体化）→ `kill <PID>`
- 必須: `ps`, `kill`
- クリア条件: 正しい PID への kill 実行 + `mission_flags.bug_removed = true`
- ゲーム性: 「間違い探し」。正規プロセスを kill すると警告 + 巻き戻し（即失敗にしない）。裏取りせず勘で kill すると正解でも減点。/proc での裏取りは加点（深掘りは Mission7）
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission7: Inside the Machine「機械の胸の内」（2026-07-08 追加）
- 学習テーマ: /proc 疑似ファイルシステム・プロセス鑑識（Level 6 / LPIC 101.1・103.5）
- あらすじ: また潜入者だ。だが今度は止める前に「起訴」する。誰が・何を・どうやって動かしているのか — 機械は胸の内（`/proc`）に全部書いてある。読み方を知る者だけが読める。
- フロー: 相棒が「`ps` が見せる名簿の原本は `/proc` にある」と明かす → `ls /proc` で PID の部屋が並ぶ → `cat /proc/<PID>/status` で偽名（Name）と身元（Uid）を確認 → `cat /proc/<PID>/cmdline` で実際の起動コマンドを暴く → `cat /proc/meminfo`・`/proc/cpuinfo` で「この建物（PC）の身体検査」→ 証拠を揃えて report → `kill <PID>`
- 必須: `ls /proc`, `cat /proc/<PID>/status` または `cmdline`
- クリア条件: 対象 PID の status/cmdline 閲覧フラグ + 起動コマンド（偽装名との不一致）の記述一致 + kill 成功
- ゲーム性: 「名簿（ps）と持ち物検査（/proc）」の二段推理。プロセス名は `clock` でも cmdline は別物、という偽装トリック。`free`/`uptime` が実は `/proc/meminfo`・`/proc/uptime` を読んでいるタネ明かしで「コマンドの向こう側もただのファイル」を体感させる
- 備考: `/proc` は仮想プロセステーブルから動的生成・読み取り専用（設計指示書 § 4）
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission8: Master of Disguise「変装潜入」
- 学習テーマ: ユーザー切替（Level 7）
- あらすじ: 容疑者「barman」しか読めないファイルがある。合言葉（パスワード）は店のどこかに。変装して読め。
- フロー: `cat` で `Permission denied` を体験 → 店内探索で合言葉発見 → `su barman` → `whoami` で確認 → 目的ファイル閲覧 → `exit` で自分に戻る
- 必須: `su`, `whoami`, `cat`, `exit`
- クリア条件: barman 状態での対象ファイル閲覧 + 元ユーザーへの復帰
- ゲーム性: 「今の自分は誰か」の確認習慣。exit で戻る構造が Mission3 の ssh/exit と対になり反復学習になる
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission9: Sealed Evidence「封印された証拠品」
- 学習テーマ: アーカイブ・鑑識（Level 8）
- あらすじ: 押収品はマトリョーシカのように何重にも封印されている。拡張子は当てにならない。鑑識（file）にかけながら開封しろ。
- フロー: `file evidence.dat`（実体は tar.gz と判明）→ `tar -xzf` → 出てきたファイルをまた `file` → `unzip` → … → 最深部の手がかり入手
- 必須: `file`, `tar`, `gunzip` または `unzip`
- クリア条件: 最深部ファイルの `cat` 実行 + 記載コードの report 転記
- ゲーム性: 開封のたびに一歩近づく「発掘」感。「拡張子ではなく file で確かめる」鉄則のパズル化
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission10: The Forged Letter「改ざんされた遺言状」
- 学習テーマ: 差分・置換（Level 5）
- あらすじ: 遺言状の原本と写しのどこかが書き換えられている。差分を見つけ、写しを原本どおりに直せ。
- フロー: `diff original.txt submitted.txt` で改ざん行を特定 → `sed 's/…/…/'` で復元 → report へ
- 必須: `diff`, `sed`
- クリア条件: diff 実行 + sed による正しい置換 + 復元後ファイルの一致判定
- ゲーム性: 目視では見つからない1文字差（`0` と `O`）を仕込む
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission11: Torn Note「切り裂かれた脅迫状」
- 学習テーマ: テキスト整形（Level 5）
- あらすじ: 細切れにされた脅迫状の断片ファイルを並べ替え、貼り合わせて全文を復元しろ。
- フロー: `ls` で断片確認 → `cat piece_*` で把握 → `sort` で行順復元 → `cut` / `paste` で整形 → 全文を report へ
- 必須: `sort`, `cut` または `paste`
- クリア条件: 復元済み全文の正規表現一致
- ゲーム性: 手作業でも解けるが sort/cut なら圧倒的に速い、という「道具の価値」の体験
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission12: Ghost Line「幽霊回線を追え」
- 学習テーマ: ネットワーク追跡（Level 9）
- あらすじ: 犯人は通称「ghost」というサーバーから指示を出している。住所（IP）を割り出し、生存を確認し、突入せよ。
- フロー: `dig ghost.example` → `ping` で生存確認 → `ss` で開いている扉確認 → `ssh` → remote 内で証拠収集 → `exit`
- 必須: `dig`（または `host`）, `ping`, `ssh`, `exit`
- クリア条件: dig → ping → ssh の順序実行 + remote 内の証拠ファイル閲覧
- ゲーム性: 「調べてから踏み込む」実務手順が捜査手順そのものとして機能する
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission13: Midnight Broadcast「深夜0時の犯行予告」
- 学習テーマ: cron・時刻書式（Level 10）
- あらすじ: 犯人はサーバーに時限装置（cron ジョブ）を仕掛けた。`0 0 * * 5` を解読し、正しいジョブだけを解除しろ。
- フロー: `crontab -l` → 5フィールド書式の解読（ヒント: `man 5 crontab`）→ 危険ジョブ特定 → 解除 → 解除時刻を report へ
- 必須: `crontab -l`, `cat`, `date`
- クリア条件: 正しいジョブの特定（発動日時の記述一致）+ 解除フラグ
- ゲーム性: LPIC 頻出の cron 書式が、暗記ではなく時限爆弾の解読体験として定着する
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission14: Hall of Mirrors「鏡の館」
- 学習テーマ: リンク・実体判定（Level 8）
- あらすじ: 保管庫は「鏡の館」。同名ファイルのほとんどは案内板（シンボリックリンク）で、実体は1つだけ。本物を見つけ出せ。
- フロー: `ls -l` で `->` 表示を読む → `file` で `symbolic link` 判定 → 実体を特定して閲覧 → 実体の絶対パスを report へ
- 必須: `ls -l`, `file`
- クリア条件: 実体ファイルの絶対パス記述（リンクのパスは不正解）
- ゲーム性: 推理がそのまま `ls -l` の読解訓練になる。Mission2 の絶対パス学習の応用編
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission15: The Informant's Trail「情報屋の足取り」
- 学習テーマ: 履歴・ログ監視（Level 5〜6）
- あらすじ: 失踪した情報屋の端末に操作履歴が残っている。最後に何を調べ、どこへ向かったのか。足取りを再現しろ。
- フロー: `history`（情報屋の履歴を閲覧する演出）→ `tail journal.log` → 履歴どおりに再実行 → 行き先を突き止める
- 必須: `history`, `tail`, `grep`
- クリア条件: 履歴再現（同一コマンド列の実行）+ 行き先の記述一致
- ゲーム性: 「他人の履歴から意図を推理する」= コマンド理解の総復習。履歴が攻略チャートになるメタ構造
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission16: The Great Sweep「一斉捜索令状」
- 学習テーマ: ワイルドカード・引用符（概念）
- あらすじ: 数百の押収ファイルのうち、令状が許すのは「`case_` で始まり数字1桁」だけ。範囲をパターンで指定しろ。犯人は空白入りファイル名 `top secret.txt` で目くらましを残している。
- フロー: `ls case_*`（多すぎる）→ `ls case_[0-9].txt` で絞る → 一括調査 → `cat top secret.txt` が失敗 → `cat "top secret.txt"` で開封
- 必須: glob（`*` `?` `[...]`）の使用、引用符付きパス
- クリア条件: glob パターン使用 + 引用符付きファイルの閲覧 + 発見コードの記述
- ゲーム性: 「令状の範囲＝パターン」。空白入りファイル名は引用符を知らないと物理的に開けない
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission17: Fingerprint「指紋は嘘をつかない」
- 学習テーマ: チェックサム・真正性検証（Level 8）
- あらすじ: 見た目が完全に同一な契約書コピー5通のうち1通だけ改ざんされている。ファイルの「指紋」で照合しろ。
- フロー: `cat copy_*.txt`（全部同じに見える）→ 台帳の原本ハッシュと `md5sum copy_*.txt` を突き合わせ → 不一致の1通を特定 → `diff` で箇所確認 → report
- 必須: `md5sum`（または `sha256sum`）, `cat`（`diff`, `sort` は加点）
- クリア条件: md5sum 実行 + 改ざんファイル名と改ざん箇所の記述一致
- ゲーム性: 「1文字違えば指紋は別物」というハッシュの性質を推理トリックに使う。Mission10 の発展形
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission18: Silence in the Static「雑音の中の声」
- 学習テーマ: 標準エラー・リダイレクト・終了コード（概念）
- あらすじ: 老朽アーカイブサーバーは探索のたびに大量のエラー（雑音）を吐く。雑音だけをシュレッダーに流せ。
- フロー: `grep -r "witness" /archive` → `Permission denied` の雑音で画面が埋まる → `2>/dev/null` で声だけ残す → 手がかり入手 → `echo $?` で成否確認の練習
- 必須: `2>/dev/null` を含む実行（`echo $?` は加点）
- クリア条件: `2>\s*/dev/null` パターンの実行 + 手がかりの記述
- ゲーム性: 「出力には2本の管がある」を雑音と声で可視化。雑音の絶望→1記号で静寂、のカタルシス
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission19: The Detective's Playbook「捜査手順書を書け」
- 学習テーマ: シェルスクリプト基礎（Level 11）
- あらすじ: 手作業でやってきた「証拠確認→判定→報告」を、後輩のために手順書（スクリプト）に書き起こせ。今まで実行するだけだった `case_file.sh`、今日からは書く側だ。
- フロー: `cat sample.sh` で見本を読む → `echo` で自作 `patrol.sh` を作成（変数定義 + `if grep -q "$TARGET" file; then echo "FOUND"; fi`）→ `sh patrol.sh` → `FOUND` 出力確認
- 必須: `sh`, 変数定義と `$変数` 参照, `if` 文
- クリア条件: 変数定義 + if 文を含むスクリプトの作成と実行成功
- ゲーム性: 「実行する側→書く側」への視点逆転。for 文で複数ファイル巡回は加点
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission20: Map of the City「この街の地図」
- 学習テーマ: FHS・実 Linux のディレクトリ構成（概念）
- あらすじ: 舞台は「本物の Linux の街」へ。設定は市役所（`/etc`）、出来事は公文書館（`/var/log`）、住民は住宅街（`/home`）、消したいものはゴミ捨て場（`/tmp`）。黒幕の住民登録を探し出せ。
- フロー: `ls /` で全体図 → `cat /etc/hosts` → `/var/log/entry.log` を `tail`/`grep` で調査 → `/tmp` の消し忘れ → `/home/<黒幕>` を特定
- 必須: `ls`, `cd`, `cat`, `grep`, `tail`
- クリア条件: `/etc` `/var/log` `/tmp` `/home` の4区画探索フラグ + 黒幕ユーザー名の記述一致
- ゲーム性: 新コマンドゼロ・知識だけで解く「地理」の回。クリア後に実機を開いた時「知っている街」になっている
- 備考: FHS 版の仮想FSマップが必要（既存の探偵事務所マップとは別レイアウト）
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission21: The Missing Toolbox「消えた道具箱」（2026-07-08 追加）
- 学習テーマ: 環境変数・PATH（Level 10 / LPIC 103.1）
- あらすじ: 事務所に戻ると異変が起きていた。`grep` も `find` も「そんな道具は知らない」と言う。道具が盗まれたのか？ いや — 盗まれたのは道具ではなく、**道具箱の場所リスト（PATH）**だ。
- フロー: `grep …` が `command not found`（開幕の異常事態）→ 相棒「道具は消えていない。リストが破られただけだ」→ `echo $PATH`（または `printenv PATH`）で汚染された値を確認 → `/bin/ls` の絶対パス実行で「道具はまだそこにある」ことを裏取り → `which` / `type` でコマンドの在処を確認 → `export PATH=/usr/local/bin:/usr/bin:/bin` で復旧 → `grep` 再実行成功 → 犯人が残した偽 PATH 文字列を report
- 必須: `echo $PATH` または `printenv`, `export PATH=…`, 復旧後のコマンド実行成功
- クリア条件: PATH 復旧フラグ（`env_vars.PATH` の正常値一致）+ 復旧後の allowlist コマンド成功 + 偽 PATH 値の記述一致
- ゲーム性: 「コマンドが打てない」異常事態そのものが謎。絶対パス実行という抜け道が「PATH = コマンド探索経路」の意味を裏から証明する。Mission20（街の地図）の「/bin = 道具街」の比喩をそのまま回収
- 備考: 統合ワールドでは Mission21 解放時（Mission20 クリアの `git push`）に `release_missions` が**探偵自身**の `env_vars["detective"]["PATH"]` を汚染値 `/tmp/.stolen` に上書きする（2026-09-13 確定。2026-08-12 の「別アカウントに閉じ込めて su で入る」案は、Mission が順番制で他 Mission へ波及しないこと・「自分の道具箱が盗まれる」筋書きと LPIC の学び（自分の環境の PATH を直す）に一致することから、本人の環境を汚す方式へ変更）。`unset` の体験は加点要素
- 独り言（story_beats）・3 段階ヒント: 2026-09-13 起草済み（文言は `noir-api/app/content/missions.py` の `hints` / `story_beats` が正。Mission1〜3 と同じ文体規約）

### Mission22: Case Closed「最終事件 — すべてを繋げろ」
- 学習テーマ: 総合演習（Level 1〜11 の複合・卒業試験）
- あらすじ: 全事件は一人の黒幕に繋がっていた。local と複数 remote を行き来し、権限を解除し、ログをパイプで捌き、最終証拠の真正性をハッシュで確かめ、黒幕の名を本部に提出せよ。
- フロー: 学んだ技術を関所として配置（find → dig/ssh → chmod → grep|sort|uniq → tar → md5sum → 自作スクリプトで最終判定 → 報告）
- 必須: `find`, `ssh`, `chmod`, パイプ, `tar`, `md5sum`, `sh`（自作）, 疑似 git 一式
- クリア条件: 全関所フラグの達成 + 黒幕名の正規表現一致 + git push
- ゲーム性: ヒントは1段階目のみ（相棒が「もう教えることはない」）。クリア時に「実PCでも同じことができる」エピローグを表示し、実機・LPIC 受験への導線とする
- 独り言（story_beats）・ヒント: 2026-09-13 起草済み。ヒントは 1 段階（8 関所の順序を示すゴール説明）のみ（文言は `noir-api/app/content/missions.py` が正）

---

## 5b. 追加エピソード（2026-09-13 確定・実装済み）

ユーザー要望（2026-09-13 デモプレイ後）: ① 中盤に **チーム内で共有するための git 操作**（ブランチ・マージ・PR・
レビュー）の Mission を追加 ② 後半に **サーバー知識**（オンプレ・クラウド共通）の Mission を追加。以下は推論した設計案。

### 5b-1. 全体の置き方

- **事件番号（id）は 23〜28 で固定、並び順は別に持つ**: 全 Mission に `order`（捜査の順番）を持たせ、一覧・解放判定・
  `case_file.sh` の動的合成は `order` 順、id は変えない。探偵の事件番号は受理順なので、時系列で #23 が #12 と #13 の
  間に来ても物語上おかしくない。既存 Mission の id・ドキュメント・テスト・区画表（`_MISSION_AREAS`）を一切触らずに済む
  （対案: 13〜22 を 16〜28 に振り直す。ドキュメント・テスト・DB 上の `mission_progress` の移行が要り、採らない）
- 配置: **git 編 = Mission11「切り裂かれた脅迫状」の後**（テキスト編集と save/push を十分こなした中盤）、
  **サーバー編 = Mission21「消えた道具箱」の後・Mission22 最終事件の前**（FHS と PATH を知ったあと。最終事件は最後のまま）
- 疑似 Git の原則（commit=セーブ / push=クリア判定）は**据え置き**。ブランチ・マージ・PR は「捜査中の作業」として
  Mission の課題にし、クリアは従来どおり `sh case_file.sh → git add → git commit → git push`。判定は command_log と
  `git_state` の枝の状態で行う
- ブランチが管理する範囲は **`/root/team_desk` 配下だけ**（実 git のリポジトリと同じく、世界全体ではなく作業ディレクトリ）。
  `git checkout` はこの配下だけを枝のスナップショットに差し替える（進捗・他区画は不変）
- PR は **`gh`（GitHub CLI）の擬似実装**で扱う（実在のツール。`gh pr create` / `gh pr view` / `gh pr merge`）。本部の
  レビューはルールで生成し、`gh pr view` に "Changes requested" / "Approved" として現れる。GitHub そのものの UI は再現しない

### 5b-2. git 編（3 本。Level 4〜5 相当。新コマンド: `git branch/checkout/merge/log/diff`、`gh`）

#### Mission23: Branching Leads「分岐する捜査線」
- 学習テーマ: ブランチ（並行する捜査線を分ける）
- あらすじ: 本部から「本筋の調書（main）は汚すな。仮説は別の線で追え」と通達。港（harbor）の線を別ブランチで追う
- 舞台: `/root/team_desk/`（`case_notes.txt`・`suspects.txt`。初期ブランチ `main`）
- フロー: `git branch`（今いる枝）→ `git checkout -b lead/harbor`（枝を切る）→ `echo … >> case_notes.txt`（港の線を書く）→
  `git add . && git commit`（枝にセーブ）→ `git checkout main`（本筋へ戻ると追記が**消えている**体験）→ `git log`（枝ごとの
  履歴）→ `git merge lead/harbor`（本筋に取り込む。競合なし fast-forward）→ `sh case_file.sh` → push
- クリア条件: `checkout -b` で枝を切った + その枝で commit + `main` へ `merge` 済み（`git_state.branches["main"]` の内容に
  港の追記がある）
- ゲーム性: 「枝を切り替えると机の上の書類が入れ替わる」を目で見る。checkout で追記が消える瞬間が学び

#### Mission24: Conflicting Statements「食い違う調書」
- 学習テーマ: マージ競合の解決
- あらすじ: 相棒（不採用の相棒キャラではなく同僚探偵 "Reed"）が同じ調書の同じ行を別の内容で書いていた。枝
  `reed/statement` を取り込むと競合する
- 舞台: `/root/team_desk/statement.txt`。事前に枝 `reed/statement`（同じ行を「目撃時刻 23:50」と主張）を仕込む。
  main 側は「23:10」。分岐点（base）では時刻が `[time unconfirmed]` なので、両側が同じ行を埋めた＝三方マージが競合する
- フロー: `git merge reed/statement` → `CONFLICT (content): Merge conflict in statement.txt` → `cat statement.txt` で
  `<<<<<<< HEAD` / `=======` / `>>>>>>> reed/statement` を読む → 証拠（`/root/team_desk/cctv.log` に 23:50 の記録）で
  正しい側を選ぶ → `sed`/`echo` で目印を消して一本化 → `git add statement.txt` → `git commit`（マージ確定）
- クリア条件: 競合マーカーが無い + 正しい時刻（23:50）が残っている + マージ commit がある
- 誤答: マーカーが残ったまま → `Error: unresolved conflict markers in statement.txt` / 間違った側を残す →
  `Warning: the statement contradicts cctv.log`
- ゲーム性: 「機械は勝手に決めない。決めるのは証拠を読んだ探偵」

#### Mission25: The Pull Request「本部への送付状」
- 学習テーマ: PR とレビュー（共有・指摘・修正・承認・マージ）
- あらすじ: 調書を本部の主任（reviewer: "Chief Morgan"）に送る。突き返されたら直して再送
- フロー: `git checkout -b report/harbor` → 報告書 `report.txt` を書く → commit → `gh pr create --title "Harbor case"
  --body "…"` → `#12 opened` → `gh pr view 12` → レビュー **"Changes requested: 証拠は絶対パスで引用しろ / 容疑者名を
  suspects.txt と一致させろ"** → 修正 → commit → `gh pr view 12` → **"Approved"** → `gh pr merge 12` → main に取り込まれる
  → `sh case_file.sh` → push
- レビューのルール（判定と同じロジックで生成）: report.txt に `/root/team_desk/cctv.log` の絶対パス引用があるか /
  suspects.txt にある名前が含まれるか。両方満たすまで Changes requested
- クリア条件: PR 作成 → 指摘後の追加 commit → Approved → merge 済み
- ゲーム性: 「一発で通らない」を前提にしたループ。実務の PR の手触り

### 5b-3. サーバー編（3 本。Level 9〜10 相当。新コマンド: `systemctl status/stop`、`journalctl -u`、`df -h`、`du -sh`、
`uname -a`、`hostname`、`ip a`、`cat /etc/os-release`。予約済みホスト `archive_node`（オンプレ）と `corp_server`（クラウド）を使う）

#### Mission26: The Machine That Never Sleeps「眠らない機械」（オンプレ）
- 学習テーマ: 資源と稼働（uptime / free / df / du）、サービスとログ（systemctl / journalctl）— オンプレ・クラウド共通
- あらすじ: 署の地下にある保管サーバー（archive_node）が夜中に止まりかける。現地（ssh）で診る
- 舞台: `ssh archive_node`（初期 `/srv`）。`df -h` で `/var` が 98%、`du -sh /var/log/*` で `spool.log` が肥大、
  `systemctl status archive-indexer` が `failed`、`journalctl -u archive-indexer` に "No space left on device"
- フロー: `uptime` → `free` → `df -h`（満杯）→ `du -sh /var/log/*`（犯人のログ）→ `systemctl status` → `journalctl -u` →
  原因（ログ肥大でディスク満杯 → サービス停止）を report → `exit`
- クリア条件: df・du・systemctl・journalctl の 4 手 + 肥大ファイルのパスと "No space left" の報告
- ゲーム性: 「機械が止まる理由は、だいたい満腹か過労」。オンプレでもクラウドでも同じ診断手順

#### Mission27: The Witness in the Clouds「雲の上の証人」（クラウド）
- 学習テーマ: クラウド VM の身元（メタデータ）と公開面（ポート）— `curl` は mock API 限定なので
  `curl http://169.254.169.254/latest/meta-data/instance-id` を疑似実装
- あらすじ: 本部が借りているクラウドの機械（corp_server）に、誰かが勝手に扉（ポート）を開けた
- 舞台: `ssh corp_server`（初期 `/opt/app`）。`hostname` / `cat /etc/os-release` / `ip a`（プライベート IP）/
  メタデータ（instance-id・region）/ `ss -tln` に見慣れない `:4444` / `systemctl status backdoor-relay` → `systemctl stop`
- フロー: `hostname` → `curl …/instance-id`（この機械の身元）→ `ip a` → `ss -tln`（開いた扉）→ `systemctl status`（正体）→
  `journalctl -u`（いつから）→ `systemctl stop backdoor-relay` → `ss -tln`（閉じた）→ report → `exit`
- クリア条件: instance-id とポート番号の報告 + 該当サービスの停止 + 正規サービス（`app-web`）を止めていない
- ゲーム性: オンプレとの違いは「身元をメタデータで確かめる」だけ。中身は同じ Linux

#### Mission28: Two Sites「二つの拠点」（オンプレ × クラウド）
- 学習テーマ: 同じ OS・違う運用（バックアップの往復、時刻・cron・ハッシュ）
- あらすじ: オンプレの夜間バックアップがクラウドへ届いていない。両方に入って突き合わせる
- フロー: `ssh archive_node` → `crontab -l`（02:00 の backup ジョブ）→ `ls -l /srv/backup/`（今日の分が無い）→
  `journalctl -u backup`（"ssh: connect to corp_server port 22: Connection refused"）→ `exit` → `ssh corp_server` →
  `systemctl status sshd`（止まっている）→ `systemctl start sshd` → `ls -l /var/backups/`・`md5sum`（前回分の照合）→
  `uname -a`・`cat /etc/os-release` を両方で比べる → report → `exit`
- クリア条件: 両ホストへの ssh + 原因（sshd 停止）の特定と復旧 + 両拠点の OS 情報の報告
- ゲーム性: 「同じ Linux が二か所にある」ことの実感。オンプレ／クラウドの区別は置き場所の違いでしかない

### 5b-3b. Mission29: Under Duress「消せ、と男は言った」（やらかし体験室。2026-09-13 ユーザー案で確定・実装）
- 学習テーマ: `rm -rf` と `dd` が本当に何をするか（denylist の理由を体験で理解する）
- あらすじ: 深夜、港の報告書（Mission25）で名指しした Nico Faro が事務所に押し入り、捜査室（team_desk）と証拠ディスクの消去を強要する。探偵は机の下で予備の機械（SANDBOX）に繋ぎ替え、要求どおり消してみせる。男は満足して去る
- 配置: プレイ順序で Mission25 の直後（PR で名指しした因果）。区画は持たない（Mission23 の `/root/team_desk` と Mission5/22 の `/root/vault` を舞台にする）
- 機構: `MissionDef.sandbox=True`。解放時に `sandbox.enter`（filesystem を退避）、クリア時に `sandbox.leave`（戻す）。退避中だけ `rm`/`dd` が通る。`rm` は消した名前を一行ずつ出す（演出）。`dd if=/dev/zero of=/dev/sdb` は `/root/vault` の中身を空にする
- クリア条件: `/root/team_desk` を `rm -r` で消した + `dd` 実行 + `ls` で確認。誤答: `Warning: the team desk is still there (rm -rf)` / `Warning: the evidence disk is not wiped (dd)`
- ゲーム性: 「消えていく名前」を自分の手で流す。`rm -rf /root` までやっても `case_file.sh` は動的合成なので詰まない

### 5b-4. 実装メモ（2026-09-13 実装済み。機構は `docs/バックエンド_コマンド機能仕様.md` § 5b/5c、判定は `judge.py` 23〜28、コンテンツは `missions.py`）
- `git_state` に `branches: {name: {"tree": <team_desk のスナップショット>, "head": commit_id}}` と `current_branch` を追加。
  `git checkout` は `/root/team_desk` 配下だけ差し替え。`merge` は行単位の三方比較（同じ行が両側で異なれば競合マーカー）
- `gh` を registry に追加（`pr create` / `pr view` / `pr merge`）。レビュー本文は Mission の `review_rules` から生成
- サーバー編は `SSH_HOSTS` に `archive_node` / `corp_server` を追加し、`services`（systemctl/journalctl 用の仮想
  サービス表）・`disk`（df/du 用の使用量表）・`metadata`（curl mock）を remote 定義に持たせる。`systemctl stop/start` は
  仮想サービス表の状態を書き換えるだけ（`rm` 禁止と同じ思想で `disable`/`mask` は不採用）
- LPIC 対応: サーバー編は 101.3（systemd）・102.6/104（ディスク）・109（ネットワーク）・107.2（cron）。git 編は LPIC 外
  （設計指示書 § 11「PC への理解」の範囲として採用）

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
