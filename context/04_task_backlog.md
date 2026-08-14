# 実装タスクバックログ（Sonnet 実装用）

作成日: 2026-07-20（Opus で設計）

> このファイルはセッション内タスクリストのバックアップ。
> 新セッションでタスクリストが空の場合、本ファイルから TaskCreate で復元してから着手する。
> 完了したらここのチェックボックスも [x] にする（タスクリストと二重管理だが、リスト消失対策として必須）。

## 進捗サマリ（2026-08-12 時点）

- **Part 1: バックエンド Phase2（P2-01〜P2-19）— 完了 ✅**（タスク #21〜#39。Mission1〜22 全実装・241 tests green / ruff clean）
- **Part 2: フロントエンド（FE-01〜FE-08）— 完了 ✅**。Goal 達成: **noir-client を実バックエンドに接続し、Mission1〜3 がブラウザで通しプレイ可能な状態にする**
- **Part 3: ヒント機能（HINT-01）— 完了 ✅（仮実装）**。Mission1〜3 のみ配線済み。UI/UX の作り込みは未設計のまま
- **Part 4: 疑似ターミナルのバグ修正 — Part5 に吸収・再設計**。ユーザーが実プレイで発見した BUG-01/BUG-02 は、Part5 の永続統合ワールド化（P3-07/P3-08）に統合して直す方針に確定（単独修正ではなく設計の一部として解決）
- **Part 5: 永続統合ワールド化（P3-01〜P3-14 + FE3-01/02）— 次回着手（設計確定・未実装）**。Goal: **Mission単位で分離されていた仮想FSを、ユーザーごとに1つの永続的な統合ワールドに再設計する**（2026-08-12 Opus で設計・ユーザーと数往復の議論で確定）

**次回セッションの入り方**: 「context/04_task_backlog.md の Part5 から着手して」と指示するか、このファイルの Part5 を読んで
TaskCreate で復元してから着手する（依存関係は Part5 冒頭の実行順序図を参照）。P3-01 から着手すること。

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

実装内容の要約（コード・テストが正。詳細な設計判断の経緯は `01_decisions_log.md`「Phase2 バックエンド完了」節を参照）:

| # | 内容 | Mission | テスト |
|---|---|---|---|
| P2-01 | 権限基盤: ls -l / chmod / mode 検査 | - | test_permissions.py |
| P2-02 | Mission5「開かずの資料室」 | 5 | test_mission5.py |
| P2-03 | プロセス基盤 + Mission6「盗聴器を止めろ」 | 6 | test_mission6.py |
| P2-04 | 疑似 /proc + free/uptime + Mission7「機械の胸の内」 | 7 | test_mission7.py |
| P2-05 | su/whoami/id + Mission8「変装潜入」 | 8 | test_mission8.py |
| P2-06 | file/tar/gunzip/unzip + Mission9「封印された証拠品」 | 9 | test_mission9.py |
| P2-07 | diff/sed + Mission10「改ざんされた遺言状」 | 10 | test_mission10.py |
| P2-08 | paste/tr + Mission11「切り裂かれた脅迫状」 | 11 | test_mission11.py |
| P2-09 | dig/host/ping/ss + Mission12「幽霊回線を追え」（ghost.example 確定） | 12 | test_mission12.py |
| P2-10 | crontab/date + Mission13「深夜0時の犯行予告」 | 13 | test_mission13.py |
| P2-11 | link ノード + ln + Mission14「鏡の館」 | 14 | test_mission14.py |
| P2-12 | Mission15「情報屋の足取り」（informant_history） | 15 | test_mission15.py |
| P2-13 | engine: glob 展開 + Mission16「一斉捜索令状」【engine変更】 | 16 | test_glob.py |
| P2-14 | md5sum/sha256sum + Mission17「指紋は嘘をつかない」 | 17 | test_mission17.py |
| P2-15 | engine: `2>` / `$?` + Mission18「雑音の中の声」【engine変更】 | 18 | test_mission18.py |
| P2-16 | sh スクリプト実行（変数/if/for） + Mission19「捜査手順書を書け」【engine変更】 | 19 | test_mission19.py |
| P2-17 | FHS 仮想FS + Mission20「この街の地図」 | 20 | test_mission20.py |
| P2-18 | 環境変数/PATH 解決 + Mission21「消えた道具箱」【engine変更】 | 21 | test_mission21.py |
| P2-19 | Mission22「最終事件」（8関所直列判定）+ 総仕上げ | 22 | test_mission22.py |

全タスク [x] 完了（2026-07-20）。実装の詳細は `noir-api/app/content/missions.py` / `app/evaluator/judge.py` / 各テストファイルが正。

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
- [x] 完了（2026-08-12）

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

---

# Part 4: 疑似ターミナルのバグ修正（2026-08-12 発見。Part5 に吸収・再設計済み）

> **本Partは実装しない**。BUG-01/BUG-02 の背景調査はそのまま有効なので残すが、修正方針は
> Part5「永続統合ワールド化」の P3-07（BUG-02）/ P3-08（BUG-01）に統合された。着手する場合は Part5 を見ること。

Goal: ユーザーが実プレイ（Mission1）で発見した2件の既知バグを直し、同じ手法で他コマンドの
「ゲーム操作 ≠ 実PC操作」のズレが無いか一通り洗い出して直す。**最重要設計原則**（CLAUDE.md「ゲーム操作 = 実PC操作の
意味一致」）の遵守チェックが今回のテーマ。

## 経緯（次回セッション向けの要約）
Mission1 を `cd desk` → 相対パスで `echo`/`git add` → `git push` と実プレイしたところ `Error: mission requirements not met`
になった。調査の結果:
1. `sh case_file.sh` を実行し忘れていたことが直接原因（`git_ops.py` の `_push` は直前 commit の
   `mission_flags.case_checked` を見るだけで、これは `sh case_file.sh` の判定成功でしか立たない）
2. **たとえ `sh case_file.sh` を実行していても、相対パスのままでは判定にパスしない**設計ギャップが判明（下記 BUG-01）
3. `case_file.sh` の配置場所（`/root/` 直下。`/root/desk/` ではない）を知らずに `desk/` から相対 `sh case_file.sh` を
   叩いて `Error: file not found` になった（これは仕様通りだが、ヒント文言等で誘導が弱い可能性はある）
4. 引数無し `cd` が実 bash の `$HOME` 遷移を持たず即エラーになる設計ギャップが判明（下記 BUG-02）
5. `cd /root` → `sh case_file.sh` で再現したところ `Warning: pattern mismatch`（BUG-01 の再現。echo が相対パスのまま
   command_log に残っていたため）

## BUG-01: AND-regex 判定が相対パスを解決しない【影響大・要設計判断】
- 症状: `judge.py` の汎用 AND-regex 評価（`re.match(pattern, line)`）は `command_log` の生テキストにそのままマッチさせる。
  `command_log` は入力どおりの生テキストを保存する仕様（P2-18 の env 展開時の決定を踏襲）ため、`cd desk` してから
  相対パス `businesscard.txt` で操作しても、絶対パスを要求する `expected_script_patterns`（例:
  `r"^echo\s+.+\s*>\s+/root/desk/businesscard\.txt$"`）には一致しない
- 実PCでは `cd desk && echo x > businesscard.txt` と `echo x > /root/desk/businesscard.txt` は完全に同じ結果になるため、
  現状は最重要設計原則に反する
- 影響範囲: 汎用 AND-regex 判定を使う全 Mission（Mission1, 3, 4, 9, 10, 11, 13, 17, 18 ほか。専用 judge（Mission2/6/7/8/12/14/15/16/19/20/21/22）は
  command_log の別要素（存在確認・順序等）を見ているものもあり影響有無は個別確認が必要）
- **要設計判断**（次回最初に決めること。実装より先に方針決定）:
  - 案A: `command_log` に記録する際、コマンド中のパス的トークンを実行時の `current_path` で絶対パス解決してから保存する
    （real bashの `history` は生テキストのままなので、ここは意図的にゲーム内部処理用のログとして解決する形になる。
    案B/Cとの互換のため command_log 自体は生テキストのまま保持し、判定専用に「解決済みコピー」を別途持たせる手も検討）
  - 案B: 判定側（`judge.py`）でパターンマッチ前に command_log の各行をトークナイズしてパス部分だけ正規化してからマッチする
    （判定ロジックが複雑化するリスク）
  - 案C: 各 Mission の `expected_script_patterns` 側でパスを絶対/相対どちらでも許容する正規表現に緩める
    （Mission定義側の変更量が多い・将来 Mission追加のたびに同じ配慮が要る）
  - 案Aが一番「意味一致」に忠実（実行時に実際に読み書きしたファイルの絶対パスを記録するため、そもそも相対/絶対の違いを
    吸収できる）だが、engine.py の command_log 記録ロジックとの整合が要る。方針は次回ユーザーと相談してから着手すること

## BUG-02: 引数無し `cd` が `$HOME` に遷移しない
- 症状: `noir-api/app/evaluator/commands.py` の `cmd_cd`（214行目付近）は `len(argv) < 2` で即 `Error: invalid input`。
  実 bash の `cd`（引数無し）は `$HOME`（root ユーザーなら `/root`）に移動するが、その挙動が無い
- `docs/バックエンド_コマンド機能仕様.md`「`cd <path>`」の記法が元々「引数必須」前提で書かれており、この抜けは
  設計時の見落としと思われる（意図的な制限ではない）
- 修正方針（次回そのまま着手可。設計判断不要な軽微な修正）:
  1. `cmd_cd`: `len(argv) < 2` の場合は `state.get("env_vars", {}).get("HOME", "/root")` へ移動する（`env_vars.HOME` は
     P2-18 で導入済み。無ければ `/root` にフォールバック）
  2. `docs/バックエンド_コマンド機能仕様.md`「`cd <path>`」の項を「`cd [path]`」に直し、`path` 省略時は `$HOME` に
     移動する旨を追記（変更前に `old_files/` へバックアップ）
  3. 既存 `tests/test_evaluator.py` 等に `cd`（引数無し）のテストケースを追加。ssh 中（remote FS）で引数無し `cd` を
     打った場合の挙動もあわせて確認（remote 側にも `env_vars.HOME` があるか要確認。無ければ remote 中は `/` 等への
     フォールバックを決める）
  4. pytest 全緑 / ruff clean

## BUG-HUNT-01: 他コマンドの意味不一致の洗い出し
- Goal: BUG-01/02 と同種の「実 bash なら通る操作がゲームでは弾かれる」パターンを allowlist 内の主要コマンドで
  一通り確認する。**ゲームの正解ルートが通ることの確認ではなく、正解ルート以外の妥当な操作が誤って拒否されないか**
  の観点で見ること
- 確認候補（実プレイ or ユニットテストで）:
  - `ls`/`cat`/`grep` 等の相対パス vs 絶対パス（BUG-01 と根が同じなら一括で直る可能性が高い）
  - `cd ~`（チルダ展開。bash なら $HOME 相当）
  - `cd -`（直前のディレクトリに戻る。bash の一般的な挙動。未実装なら未実装と明記するだけでも良い＝全部直す必要はない）
  - パイプ/リダイレクトの空白有無のバリエーション（`>file` / `> file` / `>  file` 等）
  - `git commit -m"msg"`（クォート隣接、スペース無し）等、bash的には通る細かい書式差異
  - grep/findの `-r`/`-l` 等オプションの短縮形・組み合わせ順序
- 優先度: BUG-01/02 ほど致命的ではないため、時間が無ければ「見つけたが直さない」も可。ただし見つけたものは
  `context/03_pending_items.md` に記録すること（無かったことにしない）

## 進め方（次回セッション）
1. BUG-01 の方針（案A/B/C）をユーザーに確認してから着手（設計判断が要るため、いきなり実装しない）
2. BUG-02 は方針確認不要なので先に直してよい（軽微・影響小）
3. BUG-HUNT-01 は BUG-01/02 の修正後、余裕があれば着手
4. 各修正は 1 task = 1 commit + push。DoD: pytest全緑/ruff clean、フロントも影響あれば typecheck/build
5. 完了ごとに本ファイルと `context/03_pending_items.md` を更新

---

# Part 5: 永続統合ワールド化（P3-01〜P3-14 + FE3-01/02。2026-08-12 設計確定・次回着手）

Goal: **Mission単位で分離されていた仮想FSを、ユーザーごとに1つの永続的な統合ワールドに再設計する**。
実務のssh/踏み台作業や都度違う障害対応を「Mission/探検」として楽しめるゲームにしたいというユーザーの狙いに沿い、
`docs/設計指示書.md` § 5 が元々示していた「1つに繋がったlocal構造」（一度も実装されたことがない）を実現する。
副次的に Part4 の BUG-01/BUG-02 もこの再設計に統合して直す（P3-07/P3-08）。

## 背景・確定した設計（2026-08-12、ユーザーと複数往復の議論で確定）

1. ユーザーごとに1つの永続的な仮想FS（Mission単位の`MissionState(user_id, mission_id)`分離を廃止）
2. 22Mission分の区画は最初から実体として存在。未解放は権限（mode）で不可視・操作不可。解放時にバックエンドが権限を書き換える
3. `case_file.sh`は常に`/root/case_file.sh`の1本。現在アクティブなMission（未クリアの最小mission_id）の内容を、
   `/proc`と同じ「stateから動的生成・`filesystem`には保存しない」方式で反映する
4. `/root`直下に裸置きされている約10Mission分のファイル（tape.log, evidence.dat, hint.txt等）は専用サブディレクトリへ移設する
5. `vault`（Mission5とMission22）は同一場所への意図的なコールバック。上書きではなく加算マージ
6. ssh接続先も到達性を該当Missionの解放状況でゲート（未解放は`Host not found`）
7. Git commit履歴はプレイ全体で1本（Mission単位のリセット・死蔵をやめる。ゲーム機能8「リプレイ台帳」の土台にもなる）
8. BUG-01は`command_log`を生テキストのまま維持しつつ、並行して解決済みパスを記録し判定側がそれも参照する方式で直す

実装調査で判明した3つの矛盾はユーザーと解消済み:
- **Mission5の謎解き矛盾**: `case_file.sh`が常時実行可能な動的生成物になるとchmod+x解錠パズルが成立しない
  → `locked_evidence.txt`のchmod+rパズルに集約。case_file.sh側の解錠ギミックは廃止
- **Mission20(FHS)の矛盾**: `/etc/hosts`に最初からghost.exampleのIPがあるとMission12のdig発見体験を潰す
  → `/etc`等は最初から存在させ、`/home/mr_black`だけMission20専用にゲート。hosts のghost.example行だけMission12解放まで非表示
- **PATH汚染の影響範囲**: そのまま統合すると世界全体でls/cat/grep等が使えなくなる
  → 別ユーザーアカウントにPATH汚染を閉じ込める（`su`で該当アカウントに入った時だけ有効。`detective`自身は常に正常）。
    env_varsをユーザー別dictにし、Mission21に`su`ステップを追加する内容変更を伴う

DBスキーマは**クリーンスレート移行**（本番未リリースのためデータ保持不要）。

## 実行順序と依存関係

```
P3-01 → P3-02 → P3-03 → P3-04 → P3-05 → P3-06
                    │                │
                    └──→ P3-08 ←─────┘（要: active-mission概念 + P3-03の新パス）
P3-07（独立・いつでも可）
P3-05,06,08,09 → P3-10 → P3-11 → FE3-01 → FE3-02
P3-12 → P3-13 → P3-14（各バックエンドMilestone後に追随、P3-11完了時に確定）
```

各Milestone = 1〜3コミット。DoD = pytest全緑 + ruff clean（FE3は`pnpm typecheck`/build + 手動ブラウザ確認）。

## Phase A: データモデル基盤

### P3-01 DB移行: `MissionState`→`PlayerState`
- [x] 完了（2026-08-14）。`PlayerState(user_id UNIQUE, data JSON, updated_at)`を追加（`MissionState`は
  P3-09/10カットオーバーまで残置）。Alembicリビジョン`a1b2c3d4e5f6`（`c300ce029dad`に連結、`playerstate`
  作成のみ・`missionstate`は未drop）。`data`の新フィールド（`env_vars`ユーザー別dict化・
  `resolved_command_log`・`mission_progress`）はP3-02/P3-03/P3-08で段階的に追加する（本タスクはテーブル
  追加のみのスコープ）。`tests/test_player_state_table.py`（新規）で健全性を確認。

`app/models/tables.py`に`PlayerState(user_id UNIQUE, data JSON, updated_at)`を新設。`data`は仮想世界全体
（`current_path`/`filesystem`/`remote_mode`/`ssh_host`/`current_user`/`processes`/`cron_jobs`/
`env_vars`（ユーザー別dictに変更）/`command_log`/`resolved_command_log`（新規）/`git_state`/
`mission_progress`（新規、旧`mission_flags`をMission横断の進捗dictに置き換え））。
Alembicで新規リビジョン（`missionstate`drop・`playerstate`create、クリーンスレートでよい）。
**移行中も既存テストを常時緑に保つため、`MissionState`は残したまま`PlayerState`を追加し、P3-09/10で一気に
API/WS層を切り替える**（削除→再構築ではなく追加→カットオーバー方式）。
ファイル: `app/models/tables.py`, `alembic/versions/`

### P3-02 `mission_progress`ヘルパーと"アクティブMission"概念
- [x] 完了（2026-08-14）。`app/evaluator/progress.py`新設: `completed_ids`/`status_for`（既存
  `api/missions.py::_status_for`と同ロジック。P3-11で差し替え予定）/`active_mission_id`（未クリアの
  最小mission_idを都度算出する純粋関数）。`default_state()`に`mission_progress`
  `{completed: [], active_mission_id: 1, case_checked: False}`を追加フィールドとして新設（既存
  `mission_flags`はそのまま残置・無影響）。キャッシュへの書き込みはP3-05の`advance_mission`が担う。
  `tests/test_progress.py`（新規。P3-14でゲート系テストを追加予定）。

新規`app/evaluator/progress.py`: `completed_ids(mission_progress)`・`status_for(mission_id, mission_progress)`
（既存`_status_for`と同じ順次解放ロジック）・`active_mission_id(mission_progress)`（未クリアの最小mission_id）。
`active_mission_id`はキャッシュフィールドとして`mission_progress`内に保存し、Mission解放/クリアの唯一の書き込み箇所
（P3-05の`advance_mission`）でのみ更新する。
ファイル: `app/evaluator/progress.py`（新規）, `app/models/tables.py::default_state()`

## Phase B: ワールドFSと仮想機構

### P3-03 `_WORLD_FS`構築: 22Mission統合 + 裸置きファイルの移設 + vault加算マージ
- [x] 完了（2026-08-14）。`app/content/missions.py::_build_world_fs()`新設（既存`_MISSIONn_FS`/
  `MissionDef.initial_filesystem`/`build_initial_state()`は無変更。呼び出しごとに独立dictを返す）。
  `case_file.sh`は深さ問わず全Missionから再帰除外（Mission2は`park/case_file.sh`、Mission5は
  `vault/inner/case_file.sh`など配置深さがMissionごとに違うため、トップレベルキー名だけの除外では
  漏れることをテストで発見・修正済み）。7Mission分の裸置きファイルを確定案どおり移設（M4 tape.log →
  wiretap_room/、M9 evidence.dat → evidence_locker/、M10 original.txt+submitted.txt → will_office/、
  M13 hint.txt → crontab_room/、M15 journal.log → informant_trail/、M19 sample.sh+evidence.txt →
  precinct_desk/、M21 hint.txt → toolbox_room/）。vaultはMission5/22の加算マージ（`_ADDITIVE_MERGE_DIRS`
  明示テーブル、キー衝突時は例外）。Mission20のetc/var/tmp/binは常時公開・home/mr_blackのみゲート。
  `/etc/hosts`のghost.example行は初期状態から除去（`GHOST_HOSTS_LINE`定数。P3-05のMission12解放時に
  追記予定）。`MissionDef.owned_paths`フィールドをここで追加（P3-05が新設する予定だったが、P3-03の
  初期ロック状態計算にも同じマッピングが要るため二重管理を避けてここで前倒し導入。18 Mission分に設定、
  M3/6/7/12はFSを持たないため空リスト）。各区画の初期mode/owner設定（Mission1=desk と常時公開FHSは
  open、他は"---------"/"system"でlocked）。検証: `tests/test_world_fs.py`（新規、11テスト）+
  `grep -n '"/root/'`によるパスリテラル洗い出し（judge.py側の追随はP3-08のスコープ、今回は未着手）。

`app/content/missions.py`に`_build_world_fs()`を新設:
1. 各`_MISSIONn_FS["root"]["children"]`を1つの`world["root"]["children"]`へ統合。**`case_file.sh`は全除外**
   （P3-04で動的生成に置換するため静的マージ対象から外す）
2. 裸置きだった約10Mission分を専用サブディレクトリへ移設（命名は確定案）:
   - Mission4 `tape.log` → `wiretap_room/tape.log`
   - Mission9 `evidence.dat` → `evidence_locker/evidence.dat`
   - Mission10 `original.txt`/`submitted.txt` → `will_office/`
   - Mission13 `hint.txt` → `crontab_room/hint.txt`
   - Mission15 `journal.log` → `informant_trail/journal.log`
   - Mission19 `sample.sh`/`evidence.txt`（+ プレイヤー作成`patrol.sh`の設置先） → `precinct_desk/`
   - Mission21 `hint.txt` → `toolbox_room/hint.txt`
   - 既にサブディレクトリを持つMission（desk/park/vault/bar/mirror_hall/warehouse/contracts/archive、
     Mission22のclues/vault/logs）は変更なし
3. `vault`は例外的に加算マージ（`_ADDITIVE_MERGE_DIRS = {"vault": [5, 22]}`のような明示テーブルで扱う。
   汎用衝突解決アルゴリズムにはしない — 意図しない衝突を握りつぶさないため）
4. Mission20: `etc`/`var`/`tmp`/`bin`はワールド直下の常時公開システムディレクトリとしてマージ。
   `/home/mr_black`だけMission20専用の被ゲート区画にする。`/etc/hosts`は初期状態でghost.example行を含めず、
   Mission12解放時（P3-05）に追記する
5. 各Mission区画のトップレベルdirノードに初期`mode`/`owner`を設定: 未解放は`mode="---------", owner="system"`、
   Mission1の区画（と常時公開のFHSシステムディレクトリ）は`mode="rwxr-xr-x", owner="detective"`
6. **検証**: `grep -n '"/root/' app/content/missions.py app/evaluator/judge.py`で全絶対パスリテラルを洗い出し、
   移設漏れ・意図しない衝突が無いか確認するテスト/スクリプトを書く

ファイル: `app/content/missions.py`（最大の差分）

### P3-04 ディレクトリ権限ゲート機構（新規サブシステム）
- [x] 完了（2026-08-14）。`fs.py::can_traverse(node, current_user)`新設（modeが未設定なら常にTrue。
  設定時は実行ビットをowner/otherの二値で判定）。`_walk`/`get_node`/`get_parent`が経路上の未解放
  ディレクトリで`None`を返すよう修正（末端ノード自身はここではチェックしない — cd/ls/find等の
  呼び出し側が個別に検査。get_parentは書き込み系コマンドがここ1箇所しか経由しないため親ディレクトリ
  自身もチェック）。5箇所（`cmd_cd`/`cmd_ls`/`cmd_find`/`engine._glob_matches`/`commands._walk_files`
  ＝grep -r用）を個別修正。全て「Error: path not found」「Error: directory not found」等の既存の
  「存在しない」文言を再利用（Permission deniedは使わない）。**追加実装（Part5背景節item3が要求して
  いたがP3-03/P3-04どちらの明示ファイルリストにも無かったギャップ）**: `/root/case_file.sh`の動的生成
  （`fs.py`、`/proc`と同じ「filesystemに無ければ動的生成」方式。全Missionで判定文言は同一定数なので
  active_mission_id分岐は不要と判断）。`tests/test_permissions.py`に14テスト追加（デフォルト開放の
  明示確認・ロック済みディレクトリのls/cd/find/grep-r/glob全経路での不可視化・mode書き換えでの再可視化・
  動的case_file.shの存在確認と正規パス限定の確認）。既存263テストは無影響（274 passed）。

現状、ディレクトリ単位の権限チェックは一切存在しない（ファイル単位の`can_read`/`can_exec`のみ）。
`cmd_ls`/`cmd_cd`/`cmd_find`/glob展開/`grep -r`はすべて権限チェック無しで`children`を直接走査している。
1. `fs.py`: `can_traverse(node, current_user) -> bool`（**modeが未設定なら常にTrue**というデフォルト開放ポリシー。
   ファイル用`can_exec`の「デフォルト閉鎖」とは別物として実装。既存22Mission分のディレクトリノードはmode未設定
   なので無影響であることをテストで保証）
2. `_walk`/`get_node`/`get_parent`（`fs.py`）: 子ディレクトリへ降りる前に`can_traverse`チェック。拒否時は
   存在しないのと同じ`None`を返す（`/proc`の不存在pidと同じ扱い）
3. `cmd_cd`（`commands.py`）: 解決先ノード自体の`can_traverse`もチェックし、拒否時は`Error: directory not found`
   （見えない/触れない演出を優先し`Permission denied`は使わない）
4. `cmd_ls`: 列挙時に`can_traverse`を通らない子を除外（一覧に出さない）
5. `cmd_find`: 再帰時に`can_traverse`を通らないディレクトリへ降りない・出力しない
6. `engine.py::_glob_matches`: 同様にフィルタ
7. `commands.py`の`_walk_files`（`grep -r`用）: 同様にディレクトリレベルでスキップ追加
8. **完了確認**: `.get("children"`/`["children"]`の全呼び出し箇所をgrepし、上記5箇所以外に直接走査している場所が
   無いか確認してから次のMilestoneへ

ファイル: `app/evaluator/fs.py`, `app/evaluator/commands.py`（5箇所）, `app/evaluator/engine.py`

### P3-05 Mission解放遷移: 権限反映・ssh到達性・`/etc/hosts`追記・processes/cron解放
- [x] 完了（ssh到達性ゲート=P3-06は別Milestone。2026-08-14）。`app/evaluator/progress.py::advance_mission
  (state, cleared_mission_id)`新設: 1) `mission_progress.completed`に記録し`active_mission_id`を
  再計算・保存（新アクティブMissionの`case_checked`はFalseへリセット）、2) 新アクティブMissionの
  `owned_paths`（P3-03で前倒し導入済みのため本タスクでは新規追加せず利用のみ）のディレクトリmodeを
  open化、3) 新アクティブMissionがMission12なら`/etc/hosts`に`GHOST_HOSTS_LINE`を追記、4) 新アクティブ
  Missionの`initial_processes`/`initial_cron_jobs`を`owning_mission_id`タグ付きで`state["processes"]`/
  `state["cron_jobs"]`へ追加（`ps`/`crontab -l`側の追加フィルタは不要と判断——未解放Missionのエントリは
  そもそもこの時点まで追加されないため、既存の「stateをそのまま返す」実装で自動的に「解放済みMissionの
  分だけ表示」が成立する）。`git_ops.py::_push`から呼び出し。**注記（設計判断）**: 仕様文面は無条件で
  呼ぶ想定だったが、`_push`は旧Mission単位フロー（`build_initial_state`が`state["mission_id"]`を固定
  Missionに設定）と共有されており、無条件に呼ぶと旧フローの1Mission分の孤立stateに対して誤った
  「次Mission」解放処理が走ってしまう（旧フローのmission_progressは他Missionの完了履歴を持たないため）。
  `state.get("mission_id") is None`（永続統合ワールドは元々mission_idを使わない）をガードとして追加し、
  P3-01の「追加→カットオーバー方式」を守った。全263件の既存テストは無変更で緑。新規: `advance_mission`
  単体テスト12件（`tests/test_progress.py`）+ 旧フロー無変更確認・新フロー配線確認2件
  （`tests/test_git_and_judge.py`）。**判明した副次課題（本タスクのファイル一覧外につき未着手）**:
  `judge.py::run_case_file`は`state["mission_id"]`（旧フロー専用）を見て判定Missionを選ぶ実装のままで、
  永続統合ワールド（mission_id=None）では`mission_progress.active_mission_id`を見るよう改修しないと
  `sh case_file.sh`が機能しない。judge.pyはP3-05のファイル一覧に無く、P3-08（BUG-01の判定側改修）か
  P3-11（API層）でのjudge.py改修時に併せて対応する必要がある。

`app/evaluator/progress.py::advance_mission(state, cleared_mission_id)`を新設。`git_ops._push`が
`mission_flags.completed=True`を立てていた箇所から呼ぶ:
1. `mission_progress`に該当Missionのクリアを記録、`active_mission_id`を再計算・保存
2. 次Missionが所有する区画（`MissionDef.owned_paths: list[str]`を新規フィールドとして追加し、文字列推測に
   頼らない）のディレクトリ`mode`を解放
3. Mission12解放時は`/etc/hosts`にghost.example行を追記
4. 該当Missionの`processes`/`cron_jobs`エントリを`state["processes"]`/`state["cron_jobs"]`へ追加
   （各エントリに`owning_mission_id`タグを付け、`ps`/`crontab -l`は解放済みMissionの分だけ表示する）

ファイル: `app/evaluator/git_ops.py`（`_push`から呼び出し）, `app/evaluator/progress.py`,
`app/content/missions.py`（`MissionDef.owned_paths`追加）

### P3-06 SSH到達性ゲート
- [x] 完了（2026-08-14）。`SSH_HOSTS["amusement_park"]["required_mission_id"]=3`・
  `SSH_HOSTS["ghost.example"]["required_mission_id"]=12`を追加（`10.66.6.6`は同一dict参照のため自動追随）。
  `cmd_ssh`: 未登録ホストチェックの直後に`progress.status_for(required, mission_progress) == "locked"`なら
  同じ`Host not found`を返す。`dig`/`ping`/`host`は無変更（意図的に非ゲート）。**注記（P3-05と同種の設計
  判断）**: 無条件適用だと`default_state()`由来の汎用stateやMission3/12自身の旧フローstateまで
  `mission_progress`が空のため「常にlocked」になり既存テストが壊れるため、P3-05と同じ
  `state.get("mission_id") is None`ガードを追加。`tests/test_evaluator.py`の
  `test_ssh_and_exit_swaps_filesystem`は本来ssh/exitのFS入れ替え機構の検証が目的なので、
  Mission3解放済み相当の`mission_progress`を明示的に与えるよう更新（フィクスチャが元々
  `default_state()`直接使用でmission_id=Noneだったため、新ゲートの影響を受けていた）。新規テスト6件
  （amusement_park/ghost.example各々の未解放拒否・解放後成功、旧フロー無影響、dig/ping/hostの非ゲート
  確認）を`tests/test_evaluator.py`に追加。全286テスト緑。

`SSH_HOSTS[host]`に`required_mission_id`を追加（`amusement_park`=3, `ghost.example`/`10.66.6.6`=12）。
`cmd_ssh`: 既存の未登録ホストチェックに加え、該当Missionが`locked`なら同じ`Host not found`を返す。
`dig`/`ping`/`host`（`NET_HOSTS`）は意図的にゲートしない（ssh到達性のみ。DNS解決自体は現実でも認可と無関係という理屈）。
ファイル: `app/evaluator/commands.py`

## Phase C: 判定バグ修正

### P3-07 BUG-02: 引数無し`cd`
- [x] 完了（2026-08-14）。`cmd_cd`: `len(argv) < 2`時に`state["env_vars"]["HOME"]`へ遷移するよう修正（`Error:
  directory not found`は$HOME自体が存在しない異常時のみ）。**注記**: 原文は
  `state["env_vars"][current_user]["HOME"]`（env_varsのユーザー別dict化前提）だったが、そのdict化を担う
  タスクIDがPart5に見当たらなかった（P3-01は「data スキーマの目標」を書いているだけでファイル一覧に
  `commands.py`/`missions.py`/`judge.py`が無く、他タスクにも記載なし。Mission21へのsuステップ追加という
  内容変更を伴うため独断で実装せず。最終報告で要確認）。そのため現行の平坦な`state["env_vars"]["HOME"]`
  を参照する形で実装（per-user dict化された際は参照箇所を1行差し替えるだけで追随可能）。
  `tests/test_evaluator.py::test_cd_without_argument_goes_home`追加。

`cmd_cd`: `len(argv) < 2`時に`Error: invalid input`ではなく`state["current_path"] = state["env_vars"][current_user]["HOME"]`
（env_varsがユーザー別dictになる前提、P3-01/R4対応後）へ移動。既存テストに旧挙動を前提にしたものが無いか確認してから修正
（`grep -rn "cd.*invalid input" tests/`）。他Milestoneと独立なので単独コミットで先に片付けてよい。
ファイル: `app/evaluator/commands.py`

### P3-08 BUG-01: 解決済みパスの並行記録と判定側の対応
- [x] 完了（2026-08-15）。**記録側**: `fs.py::normalize`を`(current_path, path)`から`(state, path)`へ
  変更（内部の純粋文字列処理は`_normalize_path`として分離・維持。ユーザー入力を伴わない内部パス連結
  ——grep -rの再帰列挙——はこちらを直接呼び記録対象から除外）。呼ぶたびに
  `state["_resolved_this_command"]`へ`(raw_token, resolved_abs_path)`を積む。`engine.evaluate()`の
  成功パスで`command_log`追記と同じ箇所でスナップショットし`resolved_command_log`
  （`{"line", "paths", "mission_id"}`）へ変換、スクラッチ領域は`_set_status`が全リターン経路で確実に
  破棄（`_stderr`と違い明示初期化箇所が無くても取りこぼさない設計）。`mission_id`タグは旧フロー
  （`state["mission_id"]`固定）と永続統合ワールド（`mission_progress.active_mission_id`キャッシュ）の
  両対応。**判定側**: `judge.py`に`_combined_lines(state)`（生テキスト+解決済みパスの結合文字列を
  返す）を新設し、汎用AND-regexマッチャーと13カスタムjudge全てに適用。Mission1の2パターンのみ
  `^...$`完全一致だったため書き換え必須（他8Mission=3,4,5,9,11,13,17,18は元々アンカー無しで無改修）。
  Mission15の`informant_history`再現チェックも`cmd in log`（list membership）から`any(cmd in line for
  line in log)`（部分一致）に修正（同じBUG-01の派生問題）。`judge.py`に`_resolve_active_mission`
  （旧mission_id/新active_mission_id両対応）と`_set_case_checked`（`mission_flags`+永続統合ワールドでは
  `mission_progress.case_checked`も更新）を追加——**P3-05で判明していた「judge.pyがmission_id=Noneの
  永続統合ワールドに対応していない」ギャップをここで解消**。`default_state()`に
  `resolved_command_log: []`追加。**回帰確認**: 全294テスト緑（既存292本 + 新規: Mission1相対パス1件・
  Mission2挙動修正1件+新規1件・Mission8相対パス1件・Mission15部分一致修正・Mission20相対パス1件・
  resolved_command_log単体4件）。ruff clean。**未着手（次タスクへの申し送り）**: Mission19の
  `_MISSION19_SCRIPT_PATH = "/root/patrol.sh"`はP3-03のprecinct_desk/移設に未追随（旧フローの
  `test_mission19.py`が`/root/patrol.sh`を前提にしているため、他タスクと同様の理由で今回は変更せず）。
  永続統合ワールドでの正しい設置先（`/root/precinct_desk/patrol.sh`）への追随は、パスリテラル更新を
  担うP3-13でjudge.py側も合わせて更新すること。

`command_log`は生テキストのまま維持（リプレイ台帳・実bash風履歴のため）。並行して`state["resolved_command_log"]`を追加。
実装: `fs.normalize(current_path, path)`が呼ばれるたびに`state["_resolved_this_command"]`（`_stderr`と同じ、
evaluate内でのみ生成され戻り値には残さないスクラッチ領域の慣習を踏襲）へ`(raw_token, resolved_abs_path)`を積む。
`engine.evaluate()`の`command_log`追記と同じ箇所で、このスクラッチ領域を
`resolved_command_log.append({"line": command_line, "paths": [...], "mission_id": active_mission_id})`として
スナップショットしクリアする（`mission_id`タグはP3-09のリプレイ台帳フィルタ用）。
`judge.py::run_case_file`の汎用AND-regex: 各行について「生テキスト + 解決済みパス」を1つの検索対象文字列に結合
してから`re.search`する。**既存9Mission分（1,3,4,5,9,11,13,17,18）の`expected_script_patterns`を1件ずつ見直し**、
「コマンド名+パス」を要求するパターンと「パスのみ」で足りるパターンを区別する（`^`アンカー付きパターンは結合文字列
だと意味が変わるため個別確認必須）。13個のカスタムjudge（`_MISSIONn_*_PATH in line`形式: Mission8/12/14/20/22等）
も解決済みパスを参照するよう更新。**このMilestoneは既存Missionテストの大半に影響する**。他Milestoneより広く回帰確認すること。
ファイル: `app/evaluator/fs.py`, `app/evaluator/engine.py`, `app/evaluator/judge.py`（汎用matcher + 13カスタムjudge）,
`app/models/tables.py::default_state()`

## Phase D: Git履歴・API/WS層

### P3-09 Git履歴の一本化 + リプレイ台帳の土台
- [ ] 一部完了・**要ユーザー判断のため中断**（2026-08-15）。「advance_mission呼び出しの配線」自体は
  P3-05でgit_ops.py::_pushから既に配線済み（本タスクが要求するファイル変更はP3-05で先行実施済み）。
  リプレイ台帳のMission別フィルタ設計は`resolved_command_log`の`mission_id`タグ（P3-08）で担保済み。
  本タスク固有の残作業だった「30コミット上限×統合済みワールド全体のdeepcopyのサイズを一度実測」を実施し、
  **設計指示書 § 4 の256KB size guardと矛盾する結果が出た**ため、ここで実装を止めてユーザー判断を仰ぐ:
  - 実測: 統合ワールド全体（22Mission分の`_build_world_fs()`）の1コミットあたりsnapshot
    （current_path/filesystem/mission_flags/env_vars）が約19KB。30コミット上限まで積むと
    約570KB、`git_state`以外のstate本体（約19KB）を足すと**stateレコード全体で約590KB**——
    設計指示書 § 4「1 stateレコードの上限: 256KB」を2.3倍超過する
  - 旧Mission単位フローでは1Missionの小さいFSしか持たないため元々問題にならなかったが、
    永続統合ワールド化で「1コミット=ワールド全体のスナップショット」になった結果、初めて顕在化した
    トレードオフ（Part5の設計自体が当初から抱えていた未検証事項。P3-09のタスク文面にも
    「テキストのみなので通常は問題ないはずだが未検証」と明記されていた）
  - 現状、この256KBガード自体はコード上どこにも実装されていない（`grep`で確認済み、ドキュメントのみの
    目標値）ため、今すぐ何かが壊れるわけではない。ただし今後実装するなら約590KBという実測値を踏まえて
    上限値を見直すか、コミット方式そのもの（フルスナップショット→差分保存等）を再検討する必要がある
  - 選択肢（例、独断で選ばず提示のみ）: (a) 256KB上限を実測値に見合う値へ設計指示書側で引き上げる、
    (b) 永続統合ワールドの30コミット上限を減らす、(c) commitをフルスナップショットではなく差分
    （diff）で保持する方式に変更する（git_ops.py/P3-10のresume処理双方に影響する設計変更）、
    (d) 256KBガードは元々未実装のドキュメント目標値に過ぎないため、実装自体を見送る
  - **P3-10（WS単一セッション化）・P3-11（API層）はこの実測結果を踏まえた設計判断が必要になり得る
    （P3-10のresume処理・P3-11のcommit一覧APIは、コミット方式そのものが変わるかどうかに直接影響される）
    ため、ユーザーの方針確認が済むまで着手しないこと**。

`git_ops.py`自体はP3-01/03で状態が1本化されれば機能的な変更はほぼ不要（Mission単位のリセットが構造的に無くなるため）。
30コミット上限×統合済みワールド全体のdeepcopyのサイズを一度実測（テキストのみなので通常は問題ないはずだが未検証）。
リプレイ台帳機能は、P3-08で`resolved_command_log`に付けた`mission_id`タグでフィルタする設計とする。
ファイル: `app/evaluator/git_ops.py`（`advance_mission`呼び出しの配線のみ）

### P3-10 `ws/terminal.py`: 単一永続セッション化
- [ ] 未着手

`build_initial_state(mission_id)` → `build_initial_world_state()`（mission_id引数を廃止）。
`/ws/terminal?mission_id=<id>`のクエリパラメータを廃止（未リリースのため同時デプロイ前提でよい）。
`_load_or_create(session, user_id, mission_id)` → `_load_or_create(session, user_id)`（`PlayerState`単一行）。
`mission_clear`イベントの`next_mission_id`計算は`active_mission_id`を読むだけに簡略化。
`_handle_resume`のcommitスナップショット復元はワールド全体を復元する形になる（過去commitへの復帰でロック状態も
当時に戻る挙動は許容）。
ファイル: `app/ws/terminal.py`

### P3-11 API層: `missions.py`/`state.py`
- [ ] 未着手

`missions.py::_completed_ids`: 全`MissionState`行を跨ぐクエリ→単一`PlayerState`の`mission_progress`読み取りに変更。
**`GET /api/missions/`と`GET /api/missions/{id}/`のレスポンス形は変えない**（フロント無改修で済む）。
`state.py`: `GET /api/missions/{mission_id}/state/` → `GET /api/state/`へ変更（Mission単位のセーブ一覧という概念が
無くなるため）。レスポンスの`mission_flags`は廃止し`mission_progress`全体を返す形に変更（**フロントのSaveSelectModal.vue
がこのAPI契約変更に追随する必要あり**、FE3-01と合わせて対応）。
ファイル: `app/api/missions.py`, `app/api/state.py`, `app/main.py`（ルータマウント変更があれば）

## Phase E: フロントエンド

### FE3-01 `useTerminalSocket.ts` / `stores/terminal.ts`: 単一永続接続化
- [ ] 未着手

`connect(id: number)` → `connect()`（mission_idクエリ廃止、P3-10と対）。
`stores/terminal.ts::resetForMission(missionId)`をMission遷移毎の呼び出しから撤去。WS接続確立は
「ログイン後/アプリ起動時に1回」のみに変更。`activeMissionId`をサーバーの`hello`/`result`フレームの`state`要約
から取得するようstoreを変更（`noir-api/app/ws/frames.py`の`state_summary`に`active_mission_id`が無ければ
P3-10とあわせて追加）。
ファイル: `noir-client/app/composables/useTerminalSocket.ts`, `noir-client/app/stores/terminal.ts`

### FE3-02 `pages/missions/[id].vue`: ナビゲーションでの再接続/リセット廃止
- [ ] 未着手

`watch(missionId, ...)`によるdisconnect→再接続を撤去。WS接続はアプリ/レイアウトレベルで1回確立し、`[id].vue`は
Missionのブリーフィング・ヒント・コマンド一覧パネルの表示切替のみを担当する形に再設計。「捜査を開始する」ボタンの
意味を再検討（永続世界なのでログイン後は常にターミナルが使える設計にするか、従来どおり明示的な開始導線を残すかは
UX判断。実装時にユーザー確認を挟む）。`SaveSelectModal.vue`をP3-11の新API（`GET /api/state/`、mission_id無し）に
追随させる。テストは本プロジェクトの既存方針どおり手動（`pnpm dev` + ブラウザ確認）。
ファイル: `noir-client/app/pages/missions/[id].vue`, `noir-client/app/pages/missions/index.vue`,
`noir-client/app/components/SaveSelectModal.vue`

## Phase F: テスト移行

### P3-12 共通テストフィクスチャ: 「Mission Nまで進行済みの統合state」
- [ ] 未着手

`tests/helpers.py::state_at_mission(n)`を新設。`build_initial_world_state()`→ Mission `1..n-1`を実際の
`advance_mission`関数（テスト専用の別実装を作らない）で順にクリア済みにし、Mission `n`が解放された状態を返す。
2〜3ファイルで先に試してパターンを固めてから、残り約19本の`test_mission*.py`を一括変換。
ファイル: `tests/helpers.py`（新規）, `tests/test_mission*.py`（全面差し替え）

### P3-13 テスト内の絶対パスリテラル更新
- [ ] 未着手

P3-03で移設した約7Mission分の絶対パス（`/root/tape.log`等）をテスト側でも更新。`default_state()`の形状に依存する
テスト（`test_state.py`/`test_ws.py`等）は新フィールド（`resolved_command_log`/`mission_progress`/ユーザー別
`env_vars`）に合わせて書き換え。
ファイル: `tests/test_mission4.py`, `test_mission9.py`, `test_mission10.py`, `test_mission13.py`, `test_mission15.py`,
`test_mission19.py`, `test_mission21.py`, `test_state.py`, `test_ws.py`ほか

### P3-14 新規サブシステムのテスト
- [ ] 未着手

ディレクトリ権限ゲート（未解放区画の不可視/操作不可、解放済み区画は無影響であることの回帰確認）、ssh到達性ゲート
（未解放ホスト→`Host not found`）、BUG-01（`cd desk && echo x > businesscard.txt`が絶対パス要求パターンを満たす）/
BUG-02（引数無し`cd`）、解放遷移が意図した区画だけを開けること、`vault`加算マージの正しさ、Mission21のPATH汚染が
別ユーザーアカウントに閉じ込められ`detective`のPATHに影響しないこと。
ファイル: `tests/test_permissions.py`（拡張）, `tests/test_progress.py`（新規）, `tests/test_evaluator.py`（拡張）

## 検証方法

- 各Milestone: `cd noir-api && source .venv/bin/activate && pytest && ruff check .`
- P3-04完了時: 権限ゲートが「デフォルト開放」であることを明示的に確認するテストを含めてから次へ進む
- P3-08完了時: 通常のMilestoneより広く全Missionのgolden transcriptテストを流す
- FE3系: `pnpm dev`起動 + 実ブラウザでログイン→複数Mission分を通しプレイし、権限ゲートで未解放区画が見えない/
  入れないこと、ssh到達性ゲート、PATH汚染の局所化（Mission21のsuアカウントに入った時だけ影響）を目視確認
- 最終確認: `context/03_pending_items.md`・`docs/設計指示書.md` § 4/5（統合ワールド仕様に更新）を実装完了後に反映
