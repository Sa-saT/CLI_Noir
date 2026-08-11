# 実装タスクバックログ（Sonnet 実装用）

作成日: 2026-07-20（Opus で設計）

> このファイルはセッション内タスクリストのバックアップ。
> 新セッションでタスクリストが空の場合、本ファイルから TaskCreate で復元してから着手する。
> 完了したらここのチェックボックスも [x] にする（タスクリストと二重管理だが、リスト消失対策として必須）。

## 進捗サマリ（2026-08-12 時点）

- **Part 1: バックエンド Phase2（P2-01〜P2-19）— 完了 ✅**（タスク #21〜#39。Mission1〜22 全実装・241 tests green / ruff clean）
- **Part 2: フロントエンド（FE-01〜FE-08）— 完了 ✅**。Goal 達成: **noir-client を実バックエンドに接続し、Mission1〜3 がブラウザで通しプレイ可能な状態にする**

**次回セッションの入り方**: Part1/2 とも完了。残作業は `context/03_pending_items.md` の Frontend 節下部（Tab補完・残りキーマップ・RankUpEffect 配線・場所別画像アセット）と、`noir-client` への自動テスト（Vitest/Playwright）導入。新規タスクとして着手時はまずそちらを本ファイルに Part3 として追記してから始める。

---

# Part 1: バックエンド Phase2（完了 ✅）

Goal: **バックエンド完成 = Mission5〜22 全て実プレイ可能 + Phase2 コマンド/構文**

## 全タスク共通ルール

- **1 task = 1 commit + push**（push してから次へ）。コミットメッセージは英語 + 末尾に `Co-Authored-By:` トレーラ（実装モデル名）
- 実装リファレンス: Mission1〜4 の実装（`missions.py` / `judge.py` / `commands.py` / `tests/test_mission*.py`）のパターンを踏襲
- evaluator は**純粋関数・実 OS 非依存**（subprocess/os 禁止。glob=fnmatch / 正規表現=re / ハッシュ=hashlib は可）
- エラー文言は設計指示書 § 12 と一致させる。**ゲーム操作 = 実 Linux の意味一致**（最重要原則）
- DoD（全タスク共通）: pytest 全緑 / ruff clean / `context/03_pending_items.md` 更新を同 commit に含める
- 「engine 変更・要注意」印のタスクで難航したら Opus への切替をユーザーに提案する
- `noir-api/.venv/` は読まない

## 推奨実装順序と依存

順番どおり（P2-01 → P2-19）でよい。真の依存は:
P2-02←P2-01 / P2-04←P2-03 / P2-11←P2-01,P2-06 / P2-18←P2-15 / P2-19←ほぼ全部

---

## P2-01 権限基盤: ls -l / chmod / mode 検査（タスク #21）
- [x] 完了（2026-07-20）

参照: 設計指示書 § 4（mode="rw-r--r--" 9文字）/ バックエンド_コマンド機能仕様の ls・chmod

1. `cmd_ls` に `-l`: 「-rw-r--r-- 1 <owner> <owner> <size> <date> <name>」（dir は先頭 d）。size=len(content)
2. `cmd_chmod` 新規: シンボリック（+r/+x/-r 等）と数値（644 等）両対応。mode 9文字を更新。無いパスは `Error: path not found`
3. mode 検査: `fs.py` に `can_read(node)` / `can_exec(node)` ヘルパー。cat/less/grep/head/tail/wc/sort/uniq/cut の読み取りで owner 読みビット無なら `Error: permission denied`。**既存 78+ tests を壊さない**（Mission1〜4 の既定 mode は読める）
4. `tests/test_permissions.py` 新規

## P2-02 Mission5「開かずの資料室」（#22）【前提: P2-01】
- [x] 完了（2026-07-20）

参照: Mission参照ファイル § Mission5。フロー: ls -l で "----------" → chmod +r で解錠 → ヒント → x 無し case_file.sh → chmod +x → 実行。

1. `_MISSION5_FS`: /root/vault/locked_evidence.txt（mode "---------"、ヒント記載）→ /root/vault/inner/case_file.sh（x 無し）。expected_script_patterns=[r"chmod\s+\+?r", r"chmod\s+\+?x"]
2. Mission5 の case_file.sh は chmod +x 後のみ sh 可（can_exec と整合。immutable 特例を適用しない設計に）
3. `tests/test_mission5.py`: ゴールデン + chmod 前 cat 拒否 + x 無し sh 拒否

## P2-03 プロセス基盤 + Mission6「盗聴器を止めろ」（#23）
- [x] 完了（2026-07-20）

参照: 設計指示書 § 4 疑似 /proc・§ 8 kill / Mission参照 § Mission6

1. default_state に `"processes"` 配列 [{pid,name,user,cmdline,state,protected}]（.get 後方互換）。MissionDef に `initial_processes` 追加 + build_initial_state 反映
2. `cmd_ps`（`ps`/`ps aux`: USER PID STAT COMMAND）、`cmd_kill`（無い PID=`Error: no such process`。protected プロセスは削除せず `Warning: you stopped a legitimate process` で state 不変）
3. Mission6: clock/mailbox/heater=protected + listener_x（pid 666, cmdline "/tmp/.hidden/listener_x --tap"）。判定は Mission6 専用 judge（processes に listener_x 不在=クリア。残存時 "Warning: the bug is still running"）
4. `tests/test_mission6.py`

## P2-04 疑似 /proc + free/uptime + Mission7（#24）【前提: P2-03】
- [x] 完了（2026-07-20）

参照: 設計指示書 § 4「疑似 /proc」（**filesystem JSON に保存せず動的生成・読み取り専用**）/ Mission参照 § Mission7

1. `fs.get_node` に /proc フック: processes から /proc/<PID>/status（Name/State/Uid）・cmdline、/proc/cpuinfo・meminfo・uptime を動的生成。書き込み系は `Error: permission denied`
2. `cmd_free`（meminfo と整合）、`cmd_uptime`
3. Mission7: 名前 "clock" だが cmdline "/tmp/.fake/exfil --send" の偽装プロセス。専用 judge（status/cmdline 閲覧履歴 + 偽装 cmdline の echo 記述 + kill 済み）
4. `tests/test_mission7.py`

## P2-05 su/whoami/id + Mission8「変装潜入」（#25）
- [x] 完了（2026-07-20）

参照: Mission参照 § Mission8

1. default_state に `"current_user": "detective"`。can_read/can_exec を owner 対応（owner 不一致 + その他読みビット無 = 拒否）
2. `cmd_su`（_user_stack で退避。exit は user_stack 優先で復帰 → ssh の exit と共存）、`cmd_whoami`、`cmd_id`
3. Mission8: bar/ に合言葉ヒント + owner="barman"/mode "rw-------" の秘密ファイル。専用 judge（su barman・whoami・秘密 cat の履歴 + current_user=="detective" に復帰済み）
4. `tests/test_mission8.py`

## P2-06 file/tar/gunzip/unzip + Mission9「封印された証拠品」（#26）
- [x] 完了（2026-07-20）

参照: Mission参照 § Mission9

1. file ノード拡張: `archive_type`（"tar.gz"|"zip"|"gzip"）+ `archive_content`（展開で現れる children dict）
2. `cmd_file`（型表示）、`cmd_tar`（-xzf/-xf: カレントに展開）、`cmd_gunzip`、`cmd_unzip`
3. Mission9: evidence.dat（tar.gz）→ sealed.zip → final_clue.txt（"CODE: NOIR-1948"）の 3 層。判定: AND-regex（tar / unzip / CODE echo）
4. `tests/test_mission9.py`

## P2-07 diff/sed + Mission10「改ざんされた遺言状」（#27）
- [x] 完了（2026-07-20）

1. `cmd_diff`（古典形式 "3c3" "< 旧" "---" "> 新"。同一なら無出力）、`cmd_sed`（`s/old/new/` と /g のみ。-i 無し・リダイレクトで保存）
2. Mission10: original.txt と submitted.txt（1 文字差 "5000"→"5OOO"）。専用 judge（diff 履歴 + 復元ファイル content が original と一致）
3. `tests/test_mission10.py`

## P2-08 paste/tr + Mission11「切り裂かれた脅迫状」（#28）
- [x] 完了（2026-07-20）

1. `cmd_paste`（TAB 結合、-d 対応）、`cmd_tr`（`tr a b`/`tr -d x`、stdin のみ）
2. Mission11 は glob 非依存に設計: pieces.txt（行頭に順序タグ 3:/1:/2:）→ sort → cut -d: -f2 で全文復元。判定: AND-regex（sort / cut|paste / 全文 echo）
3. `tests/test_mission11.py`

## P2-09 dig/host/ping/ss + Mission12「幽霊回線を追え」（#29）
- [x] 完了（2026-07-20）

参照: Mission参照 § Mission12。ghost.example の FS はこのタスクで確定し decisions_log に記録。

1. NET_HOSTS = {"ghost.example": "10.66.6.6"}。`cmd_dig`/`cmd_host`/`cmd_ping`（未知は `Host not found`）/`cmd_ss`（22/tcp LISTEN 静的表示）
2. SSH_HOSTS に ghost.example（initial_path "/den"、orders.txt="BOSS: <黒幕名>" + デコイ）。IP でも接続可（alias）
3. 専用 judge: dig→ping→ssh の**出現順序**検査 + remote 証拠 cat + 黒幕名 echo。順序不成立は "Warning: investigate before you breach"
4. `tests/test_mission12.py`

## P2-10 crontab/date + Mission13「深夜0時の犯行予告」（#30）
- [x] 完了（2026-07-20）

1. default_state に `"cron_jobs"` 配列 + MissionDef.initial_cron_jobs
2. `cmd_crontab`（-l 閲覧のみ。解除は判定側: 正解ジョブの発動日時 echo で判定成功=解除フラグ）、`cmd_date`
3. Mission13: "0 0 * * 5 /tmp/.dark/broadcast.sh"（金曜 0:00）+ 無害 2 件 + man 5 crontab 風ヒントファイル。判定: AND-regex（crontab -l / "FRIDAY 00:00" 等の echo）
4. `tests/test_mission13.py`

## P2-11 link ノード + ln + Mission14「鏡の館」（#31）【前提: P2-01, P2-06】
- [x] 完了（2026-07-20）

参照: 設計指示書 § 4「type: link（target 保持）」

1. fs.py: `resolve_link` ヘルパー。cat は link を辿る。ls -l は "lrwxrwxrwx ... name -> target"。file は "symbolic link to <target>"
2. `cmd_ln`（-s のみ）
3. Mission14: mirror_hall/ に link 多数 + 実体 1 つ（/root/mirror_hall/vault/real_deed.txt）。専用 judge（実体絶対パスの echo。link パスは "Error: that is only a mirror"）
4. `tests/test_mission14.py`

## P2-12 Mission15「情報屋の足取り」（#32）
- [x] 完了（2026-07-20）

1. MissionDef に `informant_history: list[str] | None`。cmd_history はそれを番号付き表示（無ければ従来の空）
2. Mission15: informant_history 2〜3 行 + journal.log 末尾に行き先 "PIER 13"。専用 judge（履歴各行が command_log に出現 + 行き先 echo）
3. `tests/test_mission15.py`

## P2-13 engine: glob 展開 + Mission16「一斉捜索令状」（#33）【engine 変更・要注意】
- [x] 完了（2026-07-20）

1. evaluate: shlex 後・パイプ分割前に glob 展開（* ? [ ] を含むトークンを FS と fnmatch 照合。マッチ無ければそのまま=bash 既定。コマンド名には不適用）。引用符付き "top secret.txt" は shlex が 1 トークン化済み
2. Mission16: warehouse/ に case_1..case_42.txt + "top secret.txt"（コード）。専用 judge（[0-9] glob 使用 + 引用符 cat + コード echo）
3. `tests/test_glob.py`（回帰重要: 既存全テスト緑維持）

## P2-14 md5sum/sha256sum + Mission17「指紋は嘘をつかない」（#34）
- [x] 完了（2026-07-20）

1. `cmd_md5sum`/`cmd_sha256sum`（hashlib で実ハッシュ。"<hash>  <path>"。複数ファイル可）
2. Mission17: copy_1..5.txt（copy_4 のみ 1 文字差）+ ledger.txt に**実際に計算した**原本ハッシュを記載。専用 judge（md5sum 履歴 + "copy_4" echo）
3. `tests/test_mission17.py`

## P2-15 engine: 2>・$? + Mission18「雑音の中の声」（#35）【engine 変更・要注意】
- [x] 完了（2026-07-20）

1. stderr チャネル: state["_stderr"]（一時キー・永続化しない）にエラー行を積み、engine が `2>/dev/null` で破棄 / `2> file` で書き込み / 指定無しは出力へ結合
2. `$?`: 成功=0/エラー=1 を env_vars["?"] に保存。echo $? の最小展開
3. grep に -r（再帰。読めないノードは stderr へ "Error: permission denied: <path>"）
4. Mission18: archive/ に読めないファイル多数（mode "---------"）+ witness_note.txt。判定: AND-regex（`2>\s*/dev/null` / 手がかり echo）
5. `tests/test_mission18.py`（回帰重要）

## P2-16 sh スクリプト実行 + Mission19「捜査手順書を書け」（#36）【engine 変更・要注意】
- [x] 完了（2026-07-20）

1. `app/evaluator/script.py` 新設: 行単位ミニインタープリタ（NAME=value / $NAME 展開 / if <cmd>; then...fi / for...done / #コメント）。条件は evaluate 再帰（denylist/allowlist 通過）。grep に -q 追加
2. Mission19: sample.sh（見本）+ evidence.txt。プレイヤーは echo リダイレクトで patrol.sh 自作。専用 judge + sh 側で mission_flags.script_found を立てる
3. `tests/test_mission19.py`

## P2-17 FHS 仮想FS + Mission20「この街の地図」（#37）
- [x] 完了（2026-07-20）

1. `_MISSION20_FS`: /etc/hosts・/var/log/entry.log・/tmp/.forgotten・/home/mr_black/・/bin/（空）・/root。initial_current_path="/root"
2. 専用 judge: /etc・/var/log・/tmp・/home の 4 区画アクセス履歴 + "mr_black" echo。欠けは "Warning: the map is incomplete"
3. `tests/test_mission20.py`

## P2-18 環境変数/PATH + Mission21「消えた道具箱」（#38）【engine 変更・要注意。前提: P2-15】
- [x] 完了（2026-07-20）

参照: 設計指示書 § 4「環境変数」（PATH 解決の確定仕様）

1. 変数展開: $NAME/${NAME} を env_vars から置換（シングルクォート内保持。shlex 前の正規表現方式推奨）。$? 統合
2. PATH 解決: allowlist 通過後、env_vars["PATH"] に /bin 系が無ければ `Error: command not found`。絶対パス実行（/bin/ls: basename が allowlist 内）は PATH 無視
3. `cmd_export`/`cmd_unset`/`cmd_printenv`/`cmd_which`/`cmd_type`
4. Mission21: MissionDef.initial_env_vars で PATH="/tmp/.stolen" に汚染。専用 judge（PATH 正常値一致 + 復旧後コマンド成功履歴 + 偽 PATH echo）
5. `tests/test_mission21.py`（回帰重要: default PATH は正常値）

## P2-19 Mission22「最終事件」+ 総仕上げ（#39）【前提: ほぼ全部】
- [x] 完了（2026-07-20）— **Phase2 全19タスク完了。Mission1〜22 全実装。241 tests green / ruff clean**

1. Mission22: 関所直列（find → dig/ssh → chmod → grep|sort|uniq -c → tar → md5sum → 自作 sh → 黒幕名 echo → git push）。専用 judge（欠け関所を "Warning: checkpoint <n> incomplete"）
2. `tests/test_mission22.py`（フル・ゴールデン）
3. 総仕上げ: context 3 ファイル（01/02/03）を全面更新、全体回帰確認

---

# Part 2: フロントエンド（次回着手）

Goal: **noir-client（Nuxt 4 SPA）を実バックエンド（noir-api）に接続し、ログイン → Mission1〜3 の通しプレイがブラウザで動く状態にする**

## 前提・現状（2026-07-20 時点）

- `noir-client/app/pages/index.vue` は **モック evaluator** で動いている（WS 未接続。ファイル冒頭にモックである旨のコメントあり）
- 実装済み: `app/components/*.vue` 10個（TerminalView / SceneOverlay / CommandPanel / MissionHeader / SaveSelectModal 等）、`app/pages/design.vue`（コンポーネントギャラリー）
- 未実装: ルーティング（`/missions` `/missions/:id`）、ログイン画面、WS クライアント、認証トークン保存、実 API 連携全般
- バックエンドは Mission1〜22 全実装済み・起動可能（`cd noir-api && source .venv/bin/activate && uvicorn app.main:app --reload`）
- 参照ドキュメント: `docs/DESIGN.md`（UI/コンポーネント仕様。§ 10 が TerminalView の品質基準）、`docs/設計指示書.md` § 6（API）/ § 7（WebSocket）

## 全タスク共通ルール

- **1 task = 1 commit + push**
- フロントエンドに pytest は無い。DoD は「`pnpm dev` で実ブラウザ操作して機能することを確認」（`verify` skill を使ってよい）+ 型チェック（`nuxt typecheck` があれば）
- `docs/DESIGN.md` § 8「moc と確定仕様の差分」に従う（moc をそのまま写さない）
- 既存コンポーネントは極力再利用・拡張する（新規コンポーネント乱立を避ける。CLAUDE.md「無駄にファイルを増やさない」）
- DoD 共通: 変更後に `context/03_pending_items.md` の Frontend 節を更新して同 commit に含める

## 推奨実装順序

FE-01 → FE-02 → FE-03 → FE-04 → FE-05 → FE-06 → FE-07 → FE-08（ほぼ直列。FE-03 が土台になるので早めに）

---

## FE-01 認証UI（ログイン画面 + JWTトークン保存）
- [x] 完了（2026-08-11）。`app/pages/login.vue` / `app/composables/useAuth.ts` / `app/middleware/auth.ts`。トークンは localStorage 保存。あわせて Pinia（`@pinia/nuxt`）・typescript/vue-tsc（`nuxt typecheck` 用）を devDependency 追加（後続 FE-03 以降で使用する前提インフラ）。実バックエンド（`POST /api/auth/login/`）に対しログイン→ `/missions` 遷移をブラウザで確認済み

参照: 設計指示書 § 6「認証」（`POST /api/auth/login/` → access/refresh トークン）

1. `app/pages/login.vue` 新設: username/password フォーム → `POST /api/auth/login/` → 成功時 access_token を保存（Pinia store か `useState`/localStorage。設計上は SPA なので localStorage 可）
2. `app/composables/useAuth.ts`（新設）: login/logout・トークン取得・`Authorization: Bearer` ヘッダ付与のヘルパー
3. 未ログイン時に `/missions` 等へアクセスしたら `/login` へリダイレクトするガード（Nuxt middleware）
4. refresh トークンでの再取得は必須ではない（access 30分で十分。将来対応）

DoD: `pnpm dev` でログイン→トークン取得→保護ページに遷移できることをブラウザで確認。

## FE-02 Mission一覧・詳細ページ
- [x] 完了（2026-08-11）。`app/pages/missions/index.vue`（`GET /api/missions/` を status ごとにカード表示、locked はクリック不可）+ `app/pages/missions/[id].vue`（`GET /api/missions/{id}/` のブリーフィング + 「捜査を開始する」導線。ターミナル本体は FE-03/04 で追加）。認証付き fetch は新設 `app/composables/useApi.ts` に集約（401 で自動ログアウト+/login へ）。一覧→詳細→開始の導線をブラウザで確認済み

参照: 設計指示書 § 6 エンドポイント一覧（`GET /api/missions/`, `GET /api/missions/{id}/`）

1. `app/pages/missions/index.vue` 新設: `GET /api/missions/` を叩き status（cleared/open/locked）ごとにカード表示。`MissionHeader.vue` 等の既存コンポーネントを再利用できるか確認してから流用
2. `app/pages/missions/[id].vue` 新設: Mission 詳細 + 「開始」ボタン → ターミナル画面（後続の FE-03/04 で接続する index.vue 相当）へ遷移
3. Nuxt ルーティング確定（設計指示書 § 3「ルーティング」参照）

DoD: ブラウザで一覧→詳細→開始の導線が繋がることを確認。

## FE-03 WebSocket 接続基盤（composable）
- [x] 完了（2026-08-11）。`app/composables/useTerminalSocket.ts`（`auth`→`hello`→`exec`/`result`/`event`/`resume` を実装。切断時は 1s→2s→4s…最大30s の指数バックオフで再接続。DESIGN.md § 10-7）。state/scrollback の単一ソースとして Pinia store `app/stores/terminal.ts` を新設（DESIGN.md § 5・§ 10-1 の指示どおり）。WS フレーム型は `app/types/ws.ts` に集約し `noir-api/app/ws/frames.py` と 1:1（設計指示書 § 2）。DoD どおりまだ UI 未配線の状態で、Python websockets クライアントで `noir-api` 実サーバーに対し auth/hello/exec/result/resume の往復を確認済み（UI 配線は FE-04）

参照: 設計指示書 § 7「WebSocket 仕様」（接続 `/ws/terminal?mission_id=<id>` → 初回 `auth` フレーム → `hello` → `exec`/`result`）。バックエンド実装は `noir-api/app/ws/terminal.py`・`app/ws/frames.py` を参照（フレーム形式の正）

1. `app/composables/useTerminalSocket.ts` 新設: WebSocket 接続・`auth` フレーム送信（JWT）・`hello` 受信で state 保持・`exec` 送信/`result` 受信・`event`（mission_clear）受信・切断/再接続ハンドリング
2. state は reactive に保持（current_path, filesystem 有無, mission_flags 等。UI 側が参照する最小限のみ。仮想FS全体を保持する必要は無い想定 — 表示に必要な差分は result フレームの `lines`/`state` サマリから得る。`noir-api/app/ws/frames.py` の `state_summary` の返却形を確認すること）
3. 接続品質: `docs/DESIGN.md` § 10-7「接続品質」の基準に従う（再接続・エラー表示等）

DoD: ブラウザの開発者ツールで WS 接続 → auth → hello → 簡単な exec が通ることを確認（コンソールログ等で可、UI 未接続でも可）。

## FE-04 TerminalView を WS 連携に置換（モック evaluator 撤去）
- [x] 完了（2026-08-11）。`app/pages/missions/[id].vue` の「捜査を開始する」以降で `useTerminalSocket`/Pinia store に接続し `TerminalView` へ実データを流す。`app/pages/index.vue` のモック evaluator を撤去（`/` は認証状態に応じて `/missions` or `/login` へ redirect するだけのエントリポイントに変更）。`mission_clear` イベント受信で `ClearEffect` を発火し次 Mission へ導線。Tab 補完はバックエンドに `complete` フレームの実装が無いため本タスクではスキップ（別タスク化を検討。設計指示書 § 7 に定義はあるが `noir-api/app/ws/terminal.py` 未実装）。
  **最重要 DoD 達成**: Mission1 を実ブラウザ（Playwright 経由の実 Chromium。claude-in-chrome 等の対話ツールは本セッションで利用不可だったため代替手段として使用）で `cat`→`echo`→`sh case_file.sh`→`git add`→`git commit`→`git push` まで通しプレイし "Mission Complete!" 演出まで確認。console error 0 件。あわせて `noir-api` 実サーバーに対する Python websockets クライアントでのプロトコル検証、`nuxt typecheck`/`nuxt build` の通過も確認済み

参照: `docs/DESIGN.md` § 10「TerminalView 実装仕様」（アーキテクチャ・入力ライン編集・出力レンダリング・Tab補完プロトコル・プロンプト表示の品質基準）

1. `app/pages/missions/[id].vue`（または index.vue 相当）で FE-03 の composable を使い、`TerminalView.vue` へ実データを流す
2. `app/pages/index.vue` 内のモック evaluator 実装を削除（コメントに「WS 実装後に置き換え」とある箇所）
3. Tab 補完: 設計指示書 § 7「補完フレーム」参照。バックエンドに補完エンドポイント/フレームが実装済みか要確認（未実装なら本タスクではスキップしフロント側の暫定候補生成に留めるか、別タスク化を検討）
4. mission_clear イベント受信時に `ClearEffect.vue` を発火させる

DoD: ブラウザで Mission1 を実際に `cat`→`echo`→`sh case_file.sh`→`git add/commit/push` まで通しプレイできることを確認（最重要 DoD）。

## FE-05 コマンド一覧パネルの Mission 連動
- [x] 完了（2026-08-12）。新設 `app/utils/commandCatalog.ts`（`buildCommandEntries`/`commandDetailFor`/`rankLabelFor`）を `app/pages/missions/[id].vue` に配線。Mission 詳細の `allowed_commands` から `CommandPanel` の表示エントリを生成し（`git` は 4 サブコマンドに展開して highlight）、クリックで `CommandDetail` をフェード表示する既存 UX はそのまま維持。ヘッダーの探偵ランク表示も allowed_commands ベースで算出。Mission ごとに一覧が変わることをブラウザで確認済み

1. `CommandPanel.vue`/`CommandDetail.vue` を Mission 詳細 API の `allowed_commands`（バックエンド `MissionDef.allowed_commands` 相当。`GET /api/missions/{id}/` のレスポンスに含まれるか確認）に連動させる
2. コマンドクリックで入力欄に挿入する等、既存コンポーネントの UX を壊さない範囲で配線

DoD: Mission ごとに異なるコマンド一覧が表示されることを確認。

## FE-06 場面画像の state 連動（cd/ssh/exit フェード）
- [x] 完了（2026-08-12）。`app/pages/missions/[id].vue` に `host:パス接頭辞 → 画像` の辞書と最長一致解決（DESIGN.md § 1）を実装し、Pinia store の `currentPath`/`remoteMode`/`sshHost`（WS `state` 由来）から `SceneOverlay` の `:image` を算出。フェード自体は既存の `SceneOverlay.vue` の 0.8s クロスフェードにそのまま乗る。画像アセットは `office.png` 1枚のみのため他の場所はプレースホルダ表示（許容範囲。素材制作は別タスク）。`cd`/`ssh`/`exit` でシーンが切り替わることをブラウザで確認済み（Mission3 で ssh amusement_park 接続時にプロンプトが remote 色に変わることも確認）

参照: `docs/DESIGN.md` § 1「場面画像とカレントディレクトリの紐付け」（`scene_images` 最長一致解決は実装済み・呼び出し元が未配線）

1. FE-03 の WS state（current_path 等）を `SceneOverlay.vue` に渡し、`cd`/`ssh`/`exit` 実行結果に応じてフェード遷移させる
2. 画像アセットは `office.png` 1枚のみ現状（他は後回しで可。プレースホルダ許容）

DoD: `cd`/`ssh`/`exit` でシーン画像が切り替わる（フェード込み）ことを確認。

## FE-07 セーブ選択 UI（再ログイン時の commit 一覧）
- [x] 完了（2026-08-12）。`SaveSelectModal.vue` を `app/pages/missions/[id].vue` に接続。`useTerminalSocket` の `hello` フレームで `commits` が1件以上あれば Pinia store の `pendingResume` を立て、画面全体を覆う固定オーバーレイ（`.resume-overlay`）としてモーダルを表示（scene 領域内の absolute overlay だとターミナル入力が素通りしてしまうため fixed に変更）。「このセーブで再開」で `resume` フレーム送信 → 応答の `hello` を「セーブから再開しました」システム行として表示（再接続時の「reconnected」文言と区別）。「最初から」は現在の live state のまま続行（`pendingResume` を倒すだけ）。
  commit 済みの Mission を再訪 → セーブ選択モーダル表示 → 「このセーブで再開」/「最初から」の双方をブラウザ（Playwright 実 Chromium）で確認済み

参照: 設計指示書 § 10「セーブ仕様」・§ 7 の `resume` フレーム。バックエンド `noir-api/app/ws/terminal.py` の `_handle_resume`・`GET /api/missions/{id}/state/` を参照

1. `SaveSelectModal.vue` を実データ（commits 一覧）に接続。再ログイン時に state API または hello フレームの commits から一覧表示
2. 選択した commit で `resume` フレームを送信し state を復元

DoD: 一度 `git commit` してから再接続し、セーブ選択→復元が動くことを確認。

## FE-08 手動 E2E 確認（Mission1〜3 通しプレイ）
- [x] 完了（2026-08-12）。`run`/`verify`/`claude-in-chrome` は本セッションで利用不可だったため、代替として Playwright（実 Chromium、headless）で自動操作する E2E スクリプトを作成し確認した（スクリプト自体はリポジトリには追加していない一時検証コード。恒久的な自動テストが要るなら別タスクで `noir-client` に Vitest/Playwright を導入する）。
  1. ログイン → `/missions` → Mission1 開始 → `cat`/`echo` リダイレクト → `sh case_file.sh` → `git add`/`commit`/`push` → "Mission Complete!" → 次 Mission 導線、を確認。console error 0 件
  2. 同じ流れで Mission2（`find`/`grep`/`sh`/`git`）、Mission3（`ssh amusement_park` で `/gate` に接続 → プロンプトが remote 配色に切替 → ヒント3件を `cat`/`echo` → `sh`/`git`）を最後まで確認。ssh 接続中のプロンプト・シーンのリモート表示、`exit` での local 復帰も確認
  3. 追加でセーブ選択（一度 commit 済みの Mission に再訪 → モーダル表示 → 「このセーブで再開」/「最初から」の両方）も確認
  4. 発見した不具合: 実装中に `useTerminalSocket` の `resume` 応答を「reconnected」と誤表示する問題を自己発見・その場で修正（`awaitingResumeHello` フラグを追加して区別。FE-07 コミットに含む）。それ以外はブラウザ確認で不具合なし
  5. `nuxt typecheck` / `nuxt build` は全 FE タスクで都度グリーン

DoD: Mission1〜3 が実ブラウザでノーエラーにクリアできる ✅

---

# Part 3: ヒント機能（仮実装。2026-08-12 着手）

Goal: 設計指示書 § 11 ゲーム機能4「相棒キャラクター: 3段階ヒントの語り手」・Mission参照ファイル § 1-D「ヒント: 3段階」が
文言はMission1のみ確定・配線が一切無い状態だったため、**Mission1〜3の範囲で最小限つなぐ**（バックエンド hints フィールド
+ API 拡張 + フロント簡易UI）。UI/UX の作り込み（自動表示かボタンか・相棒キャラの見た目・失敗時トリガーの具体仕様）は
**今回はやらない**。次回の実装セッションで AskUserQuestion 等を使い先に仕様を詰めてから着手すること。

## HINT-01 Mission1〜3 ヒント3段階の配線（仮実装）
- [ ] 未着手

### 背景
- Mission1 のヒント3段階は `docs/Mission参照ファイル.md` § 2 に確定済み（そのまま使う）
- Mission2/3 はヒント文言自体が未確定だった。今回 Opus が AUTHORING_GUIDE.md § 4「ヒント3段階の書き分け」
  （1:方向性=コマンド名なし / 2:具体=コマンド名あり・使い方なし / 3:ほぼ答え=コピペ一歩手前）に沿って新規に起草した
  （下記「使用する文言」）。**この文言は仮**。ノワール文体としてMission1（説明書口調寄り）と若干トーンが異なる点も含め、
  次回ユーザー確認・調整の対象
- Mission4〜22 のヒントは未確定のまま（対象外。バックエンドは `hints` が空配列なら該当 Mission として扱う）

### 使用する文言（そのまま実装に使うこと。書き換えない）

**Mission1**（`docs/Mission参照ファイル.md` § 2 と同一。動かさない）:
1. `まず机(desk)を調べ、名刺ファイルの場所を確認しよう。`
2. `名刺にはあなたのユーザー名を書き込む必要があります。`
3. `編集後は git add -> git commit -m -> git push の順で進めよう。`

**Mission2**（新規・仮）:
1. `公園は広い。当てずっぽうで歩き回っても日が暮れるだけだ。的を絞る道具を使え。`
2. `find を使え。猫の情報ファイルは、遊具の近くのどこかに眠っている。`
3. `find /root/park -name catinfo.txt — 見つけたら絶対パスで読み、STATUS の欄まで報告書に書き写せ。`

**Mission3**（新規・仮）:
1. `遊園地の門の向こうに、答えはある。だがここからじゃ届かない。回線を繋げ。`
2. `ssh amusement_park で門(gate)まで踏み込め。中の設備を一つずつ find と cat で洗え。`
3. `ssh amusement_park のあと find . -type f で3つの手がかりを探し、cat で読んだ Code / Wire / Height を echo で報告書に書き出せ。`

### 実装手順
1. **バックエンド**: `noir-api/app/content/missions.py` の `MissionDef` に `hints: list[str] = field(default_factory=list)` を追加。
   Mission1/2/3 の `MissionDef(...)` 呼び出しに上記文言を設定（他 Mission は未指定のまま=空配列でよい）
2. `noir-api/app/api/missions.py` の `MissionDetail` に `hints: list[str]` を追加し、`mission_detail()` のレスポンスに含める
   （`MissionSummary`/一覧APIには不要。詳細APIのみ）
3. テスト: 既存の Mission1系テスト（`tests/test_evaluator.py` 等、詳細API を叩いている箇所）に hints 件数 or 内容の assertion を
   1件追加。無ければ `tests/test_missions_api.py` のような新規テストを追加してよい。pytest 全緑・ruff clean を維持
4. **ドキュメント**: 変更前に `old_files/Mission参照ファイル_004.md` へバックアップしてから、
   `docs/Mission参照ファイル.md` の Mission2/Mission3 節に上記文言を「ヒント:」として追記する
   （Mission1 と同じ書式。§ 5 見出し直下、確定情報の末尾に追加）
5. **フロントエンド（最小限。凝った演出は作らない）**: `noir-client/app/pages/missions/[id].vue` に
   `mission.hints`（配列。0件ならUI自体を非表示）を使った簡易UI: 「ヒントを見る (n/3)」ボタン1つ。クリックのたびに
   revealed カウントを+1し、それまでに開放した段階のヒントをテキストで上から順に表示する。サーバー側に状態は持たせない
   （ページ離脱でリセットで良い。ペナルティ無し=AUTHORING_GUIDE.md § 1 原則2）。既存コンポーネントに大きく手を入れず、
   ページ内の素朴な実装でよい（専用の「相棒キャラ」コンポーネント化は次回のUX設計後）
6. DoD: `nuxt typecheck` / `nuxt build` / バックエンド pytest 全緑。ブラウザで Mission1〜3 それぞれ「ヒントを見る」を
   3回クリックして3段階すべて表示されることを確認。Mission4〜22（hints 空）ではボタンが出ないことも確認
7. 完了後 `context/03_pending_items.md` を更新: 「ヒント3段階のフロント表示文言のみ未着手」の記述を
   「Mission1〜3は仮実装済み・Mission4〜22は文言未確定のまま・UI/UXは次回設計」に更新する
8. 1 commit + push（このタスク単体で1コミットでよい）。コミットメッセージ末尾に `Co-Authored-By:` トレーラを付ける

### 次回に持ち越す事項（今回は着手しない）
- ヒント表示の具体的トリガー（自動 or ボタン。失敗検知との連動）
- 相棒キャラクターの見た目・演出（設計指示書 § 11 機能4）
- Mission2/3 の仮ヒント文言のレビュー・確定（トーンをMission1と揃えるか、AUTHORING_GUIDE寄りに寄せるか）
- Mission4〜22 のヒント文言の起草
