# 未完了・未確定の項目

更新日: 2026-07-10

---

## 未着手（実装前に必要）

### 環境構築
- [ ] Nuxt プロジェクト作成（`pnpm create nuxt@latest frontend`）
- [x] FastAPI プロジェクト作成（2026-07-10。`noir-api/` 直下に `docs/環境構築手順.md` § 3-4 のスケルトンを構築。app/{api,ws,evaluator,models} + tests + alembic + settings/main、Python 3.12.8 venv）
- [x] `.env.example` 作成（2026-07-10。`.gitignore`・`requirements.txt` も同時作成）
- [x] API 疎通確認用の最小エンドポイント（2026-07-10。`GET /api/health` → `{"status":"ok"}`。pytest スモーク通過）

### Backend（2026-07-13: 骨格〜MVP 縦切りを実装。`noir-api/`。37 tests green / ruff clean）
- [x] 認証 API 実装（login / refresh / me。PyJWT + bcrypt 直接。SHA256→base64 事前ハッシュで 72 バイト上限回避）
- [x] Mission API 実装（一覧 / 詳細。status=cleared/open/locked を進捗から算出。Mission 定義は `app/content/missions.py` に全22件）
- [x] state API 実装（取得のみ。`/api/missions/{id}/state/`。commits はメタのみ・snapshot 非返却）
- [x] WebSocket エンドポイント実装（auth/hello/resume/exec/result/event。Pydantic 検証・5秒 auth タイムアウト・再接続 state 復元）
- [x] evaluator 実装（denylist→allowlist→registry dispatch→state更新。純粋関数・実OS非依存）
  - 実装済コマンド: ls(+`-l`)/cd/pwd/cat/less/touch/mkdir/echo(+`>``>>`)/grep(egrep/fgrep)/find/ssh/exit/sh/git/clear/history + **sort/uniq/wc/head/tail/cut**（2026-07-20 Level 5 追加）+ **chmod**（2026-07-20 P2-01 で追加）
  - **パイプ `|` 対応済**（2026-07-20。engine でステージ分割・stdin スレッド。リダイレクトは最終段のみ）
  - **権限検査 対応済**（2026-07-20 P2-01・P2-05 で owner 対応に拡張。`fs.can_read(node, current_user)`/`fs.can_exec`。current_user==owner なら所有者ビット、不一致ならその他ビットを検査。読み取り系は `_read_input` に集約し + `Error: permission denied`。`sh` は実行ビット検査。デフォルト配置ファイル（immutable=True）は特例で実行可 — 制限したい Mission は immutable=False で配置）
  - **アーカイブ/鑑識 対応済**（2026-07-20 P2-06。`file`/`tar`/`unzip`/`gunzip`。file ノードに任意キー `archive_type`（tar/tar.gz/zip/gzip）+ `archive_content` を持たせ、拡張子ではなく `file` で実体を判定する設計。tar/unzip は archive_content をカレントディレクトリへ展開・元ファイルは残す、gunzip は .gz を削除して中身に置換）
  - **diff/sed 対応済**（2026-07-20 P2-07。`diff` は `difflib.SequenceMatcher` ベースの古典形式(`NcM`/`<`/`---`/`>`)、`sed` は `s/old/new/` `s/old/new/g` のみ・`old` は正規表現として `re.sub` に渡す）
  - **paste/tr 対応済**（2026-07-20 P2-08。`paste` は複数ファイルを行単位でタブ/`-d`区切り結合、`tr`（stdin専用）は文字変換 `tr a b` / 削除 `tr -d x`）
  - **ネットワーク 対応済**（2026-07-20 P2-09。`dig`/`host`/`ping`/`ss`。静的ホスト表 `NET_HOSTS`（現状 ghost.example のみ）。`ssh` はホスト名/IP どちらでも接続可）
  - **cron 対応済**（2026-07-20 P2-10。state に `cron_jobs` 配列を追加。`crontab -l` は閲覧のみ（rm 禁止と同じ方針で書き込み系は未実装。解除は judge が「正解ジョブの発動日時報告」で判定）、`date` は固定文字列を返す）
  - 未実装（allowlist にはあるが未登録 = `command not allowed`）: awk/md5sum 等 Phase2 コマンド群。`2>`・変数展開・if/for・glob も未対応（§ 0.5 の Phase2）
- [x] 仮想FS モデル / JSON保存（MissionState.data JSON。パス解決は `app/evaluator/fs.py` に一元化。`_fs_stack` で ssh/exit の FS 退避）
- [x] 疑似Git（`app/evaluator/git_ops.py`。commit=snapshot セーブ / push=case_checked 判定 / commits 上限30 / resume でセーブ選択）
- [x] Mission 判定ロジック（`app/evaluator/judge.py`。case_file.sh が expected_script_patterns を command_log に AND 評価）
  - **MVP（Mission1〜3）完成・実プレイ可能**（2026-07-20。Mission2/3 を詳細化）。**Mission4〜13 実装済**（2026-07-20）。**Mission14〜22 の詳細 regex・初期FS は未確定**（下記「Mission4〜22 の詳細化」に含む。Mission1〜13 が実装リファレンス）
  - Mission13「深夜0時の犯行予告」: `cron_jobs`（危険ジョブ "0 0 * * 5 /tmp/.dark/broadcast.sh" + 無害2件）+ man 5 crontab 風ヒント。判定は汎用 AND-regex（`crontab\s+-l` / `FRIDAY\s+00:00` の echo）。テスト `tests/test_mission13.py`（6件）
  - Mission12「幽霊回線を追え」: **ghost.example を確定**（SSH_HOSTS、IP "10.66.6.6" 別名あり。/den/evidence/orders.txt="BOSS: Selene Vance" + デコイ + case_file.sh）。判定は Mission12 専用 judge（command_log 上の dig→ping→ssh **出現順序** + remote 証拠閲覧 + 黒幕名報告。順序不成立は "Warning: investigate before you breach"）。テスト `tests/test_mission12.py`（10件）
  - Mission11「切り裂かれた脅迫状」: /root/scraps/pieces.txt（シャッフル済みタグ付き断片 "3:ALONE" 等。glob 非依存の導線 — P2-13 で glob 対応後も両立）。`sort | cut -d: -f2` でタグ順に本文復元。判定は汎用 AND-regex（`sort` / `cut`か`paste` / 復元全文の echo）。テスト `tests/test_mission11.py`（8件）
  - Mission10「改ざんされた遺言状」: original.txt（正本、immutable）と submitted.txt（1文字改ざん "0"→"O"）。判定は Mission10 専用 judge（diff 実行 + submitted.txt の content が original.txt と完全一致するまで sed で復元されているか）。テスト `tests/test_mission10.py`（9件）
  - Mission9「封印された証拠品」: evidence.dat（archive_type "tar.gz"）→ sealed.zip（"zip"）→ final_clue.txt（"CODE: NOIR-1948"）の3層。`file` は拡張子を見ず archive_type で判定（evidence.dat は .dat 拡張子だが "gzip compressed data" と表示）。判定は汎用 AND-regex（`tar\s+-x` / `unzip\s+` / `CODE: NOIR-1948` の echo）。テスト `tests/test_mission9.py`（7件）
  - Mission8「変装潜入」: **ユーザー切替基盤を新設**（state に `current_user`（既定 "detective"）を追加。`su <user>` で切替、`_user_stack` で退避し `exit` で復帰 — `_fs_stack`（ssh）とは独立管理で、`exit` は user_stack 優先。`whoami`/`id` 追加）。`fs.can_read` を owner 対応に拡張（current_user==owner なら所有者ビット、不一致ならその他ビット）。合言葉はパスワード検証なしで `su barman` が即成功し、bar/back/ledger.txt（owner="barman", mode "rw-------"）で難易度を作る。判定は Mission8 専用 judge（su barman・whoami・秘密ファイル閲覧・detective への復帰の4点）。テスト `tests/test_mission8.py`（7件）
  - Mission5「開かずの資料室」: `_MISSION5_FS`（/root/vault/locked_evidence.txt は mode "---------" → `chmod +r` で解錠 → ヒントが指す inner/case_file.sh は mode "rw-r--r--" だが x 無し・immutable=False → `chmod +x` で解錠）。判定は汎用 AND-regex（`chmod\s+\+?r` / `chmod\s+\+?x`）。P2-01 の権限基盤（can_read/can_exec）の実地検証も兼ねる。テスト `tests/test_mission5.py`（5件）
  - Mission6「盗聴器を止めろ」: **仮想プロセステーブル基盤を新設**（state に `processes` 配列を追加。`.get` 後方互換。`MissionDef.initial_processes` で Mission ごとに上書き）。`ps`/`kill` を実装（kill は `protected: true` のプロセスを削除せず "Warning: you stopped a legitimate process" で巻き戻す汎用設計）。判定は Mission6 専用 judge（processes に listener_x が残っていないか）。テスト `tests/test_mission6.py`（6件）
  - Mission7「機械の胸の内」: **疑似 /proc を実装**（`fs.py` の `get_node` に `/proc` フック。filesystem JSON には保存せず processes テーブルから毎回動的生成・読み取り専用。`/proc/<PID>/status`・`cmdline`・`/proc/cpuinfo`・`meminfo`・`uptime`）。書き込み系（touch/mkdir/リダイレクト）は `/proc` 配下で `Permission denied`（設計指示書 § 4 の文言どおり、他の `Error: ...` 系とは別表記）。`free`/`uptime` は `/proc/meminfo`・`uptime` と同じ定数（`fs.PROC_MEM_TOTAL_KB` 等）から算出し整合を保証。Mission7: 名前 "clock" を騙る侵入者（pid 923, cmdline "/tmp/.fake/exfil --send"）。判定は Mission7 専用 judge（/proc 裏取り → 偽装 cmdline 報告 → 停止、の3段階）。テスト `tests/test_mission7.py`（9件）
  - Mission4「盗聴テープ」: `_MISSION4_FS`（tape.log = 番号のみの発信記録をラウンドロビン散布 + ノイズ、正解=最頻出 555-0142）+ case_file.sh。判定は汎用 AND-regex（`uniq\s+-c` パイプ行 + `TEL: 555-0142` の echo 記録）。`grep TEL|sort|uniq -c|sort` で最頻番号を特定する導線。テスト `tests/test_mission4.py`（5件）
  - Mission2「公園の猫」: 初期 current_path=/root/park、`_MISSION2_FS`（park/swing/catinfo.txt + デコイ）。判定は judge の Mission2 専用ロジック（find使用 / 絶対パス参照 / STATUS抽出の3点、誤答文言を § 3 に一致）。`MissionDef.initial_current_path` フィールドを追加
  - Mission3「遊園地の爆弾」: `ssh amusement_park`→/gate の `SSH_HOSTS` FS にヒント（Code/Wire/Height）+デコイ+case_file.sh を配置。判定は汎用 AND-regex（`Code: [A-Z0-9]{4,}` / `Wire: (red|blue|yellow)` / `Height: [0-9]+`）。値を読み echo で記録する Mission1 方式。remote のまま commit/push でクリア成立を確認
  - 補足: case_file.sh は「捜査タスクの証跡」を判定し、git add/commit/push は git コマンド側で構造的に強制（§ 10 判定フローとの整合。Mission参照の Mission1 5patterns のうち git 3件は regex ではなく構造で担保）
  - テスト: `tests/test_mission2_3.py`（9件）追加。全 46 tests green / ruff clean

### Frontend
- [ ] Nuxt ルーティング（/missions, /missions/{id}）
- [ ] UI 3領域レイアウト
- [ ] ターミナル UI 実装（自作 `TerminalView.vue`。xterm.js は不採用 — 2026-07-06 改訂）
- [ ] WebSocket 接続（初回 `auth` フレーム認証 + `exec`/`result` プロトコル。設計指示書 § 7）
- [ ] コマンド一覧パネル
- [ ] 場面画像のカレントディレクトリ紐付け（`scene_images` 最長一致解決は noir-client で実装済み。WS の state 連動と cd/ssh/exit フェードの結合は未）
- [ ] 場所別画像アセットの制作（`office_desk.png` / `amusement_park_gate.png` など。現状は `office.png` 1 枚のみ）
- [ ] セーブ選択 UI（再ログイン時の commit 一覧）

### テスト
- [ ] コマンドカテゴリごとの正常系/異常系
- [ ] Mission1〜3 のE2Eシナリオ
- [ ] 再ログイン時の state 復元テスト

---

## 未確定（設計上の残課題）

### Phase2 拡張の実装タスク（2026-07-06 採用確定に伴い追加）
- [ ] `docs/バックエンド_コマンド機能仕様.md` に Phase2 新コマンド（約50個）の定義を追加（実装着手時に段階的に）※egrep/fgrep は 2026-07-07 に定義済み（grep の alias）
- [ ] evaluator 構文対応: glob / 引用符 / `2>` `2>&1` `<` / `$?` / 変数 / `if`・`for`・`test` サブセット
- [ ] 仮想プロセステーブル（state JSON に `processes` 配列）
- [ ] 仮想ユーザーテーブル（`current_user` + 権限判定）
- [ ] 仮想 cron テーブル（`cron_jobs` 配列)
- [ ] アーカイブの入れ子表現（仮想FSノードに `archive_content`）
- [ ] FHS 版の仮想FSマップ（Mission19 用）
- [ ] フロントエンド: Tab 補完 / `↑↓` 履歴 / `Ctrl+R` / `Ctrl+C` / `Ctrl+L`（`TerminalView.vue` の keydown 処理）
- [ ] ゲーム機能 12 項目（設計指示書 § 11。Phase2 の 8 + 2026-07-07 追加の 4）の UI 設計
- [ ] やらかし体験室の隔離 state 実装（使い捨て state / 本編 evaluator は denylist 不変）
- [ ] エラー図鑑の翻訳文データ作成（§ 12 エラー一覧と 1:1 対応）
- [ ] 現場実習カードの文面作成（安全コマンド限定 + macOS/Windows のターミナルの開き方）
- [ ] `cowsay` / `figlet` の evaluator 定義（バックエンド_コマンド機能仕様への追加。隠し実績の解放条件設計も）

### Mission4〜22 の詳細化（実装時）
- 概要は確定済み（`docs/Mission参照ファイル.md` § 5）。各 Mission の `expected_script_patterns` 詳細正規表現・初期FS・ヒント3段階は実装時に確定する（Mission2/3 と同じ運用）
- Mission の実施順序は入れ替え可能（Mission22 のみ最終章固定）

### /proc・環境変数の未定項目（2026-07-08 採用に伴う）
- 仮想プロセステーブルの内容（正規プロセス名・PID 範囲・偽装プロセスの cmdline）は Mission6/7 実装時に確定
- `/proc/cpuinfo`・`meminfo` の表示内容（実 Linux 出力のどこまでを再現するか）は evaluator 実装時に確定
- Mission21 の汚染 PATH 初期値・正常値の正規表現は実装時に確定
- `export`/`unset`/`printenv`/`type` の evaluator 定義（バックエンド_コマンド機能仕様への追加）は Phase2 コマンド定義タスクに含む

### ゲーム機能 9〜12 の未定項目（2026-07-07 採用に伴う）
- やらかし体験室の解放トリガー（案: denylist コマンドを初めて打って拒否された直後に相棒が誘う。未確定）
- ご褒美コマンド（cowsay/figlet）の隠し実績の条件（案: 隠しファイル収集数と連動。未確定）
- Mission1〜3 の現場実習カード文面（実装時確定。Mission4〜22 も同様）

### SSH 接続先の未定項目
- ~~`ghost.example`（Mission12 用）~~（解消: 2026-07-20。初期ディレクトリ /den + 内部FS確定。IP "10.66.6.6" 別名あり。`noir-api/app/evaluator/commands.py` SSH_HOSTS 参照）
- `corp_server` と `archive_node` は Mission 未割当のまま予約（Phase3 以降の拡張用）

### ~~Mission4/5 の詳細~~（解消: 2026-07-06）
- Phase2 拡張採用により Mission4〜20（現 4〜22）として概要確定（`docs/Mission参照ファイル.md` § 5）

### ~~cp / mv コマンド~~（解消: 2026-07-06）
- allowlist の Level 8 に追加済み。`docs/バックエンド_コマンド機能仕様.md` への定義追加は Phase2 実装タスクに含む

### case_file.sh の具体的な中身
- Mission1 の正規表現パターンは推奨値あり（Mission参照ファイル参照）
- Mission2/3 の正規表現パターンは概要レベル。実装時に詳細化が必要

---

## 対話中に出た重要な注意点

- ファイルを無駄に増やさない（ユーザーの明確な方針）
- 統合できるものは統合する
- 変更時は old_files/ に採番バックアップしてから更新
- ユーザーへの返答は常に日本語
- ゲーム操作と実 PC 操作の意味を一致させる（最重要設計原則）
