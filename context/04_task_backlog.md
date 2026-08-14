# 実装タスクバックログ（Sonnet 実装用）

作成日: 2026-07-20（Opus で設計）

> このファイルはセッション内タスクリストのバックアップ。
> 新セッションでタスクリストが空の場合、本ファイルから TaskCreate で復元してから着手する。
> 完了したらここのチェックボックスも [x] にする（タスクリストと二重管理だが、リスト消失対策として必須）。

## 進捗サマリ（2026-07-20 時点）

- **Part 1: バックエンド Phase2（P2-01〜P2-19）— 完了 ✅**（タスク #21〜#39。Mission1〜22 全実装・241 tests green / ruff clean）
- **Part 2: フロントエンド（FE-01〜FE-08）— 次回着手（未着手）**。Goal: **noir-client を実バックエンドに接続し、Mission1〜3 がブラウザで通しプレイ可能な状態にする**

**次回セッションの入り方**: 「context/04_task_backlog.md の FE-01 から実装して」と指示するか、このファイルを読んで FE-01 から TaskCreate で復元して着手する。

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
- [ ] 未着手

参照: 設計指示書 § 6「認証」（`POST /api/auth/login/` → access/refresh トークン）

1. `app/pages/login.vue` 新設: username/password フォーム → `POST /api/auth/login/` → 成功時 access_token を保存（Pinia store か `useState`/localStorage。設計上は SPA なので localStorage 可）
2. `app/composables/useAuth.ts`（新設）: login/logout・トークン取得・`Authorization: Bearer` ヘッダ付与のヘルパー
3. 未ログイン時に `/missions` 等へアクセスしたら `/login` へリダイレクトするガード（Nuxt middleware）
4. refresh トークンでの再取得は必須ではない（access 30分で十分。将来対応）

DoD: `pnpm dev` でログイン→トークン取得→保護ページに遷移できることをブラウザで確認。

## FE-02 Mission一覧・詳細ページ
- [ ] 未着手

参照: 設計指示書 § 6 エンドポイント一覧（`GET /api/missions/`, `GET /api/missions/{id}/`）

1. `app/pages/missions/index.vue` 新設: `GET /api/missions/` を叩き status（cleared/open/locked）ごとにカード表示。`MissionHeader.vue` 等の既存コンポーネントを再利用できるか確認してから流用
2. `app/pages/missions/[id].vue` 新設: Mission 詳細 + 「開始」ボタン → ターミナル画面（後続の FE-03/04 で接続する index.vue 相当）へ遷移
3. Nuxt ルーティング確定（設計指示書 § 3「ルーティング」参照）

DoD: ブラウザで一覧→詳細→開始の導線が繋がることを確認。

## FE-03 WebSocket 接続基盤（composable）
- [ ] 未着手

参照: 設計指示書 § 7「WebSocket 仕様」（接続 `/ws/terminal?mission_id=<id>` → 初回 `auth` フレーム → `hello` → `exec`/`result`）。バックエンド実装は `noir-api/app/ws/terminal.py`・`app/ws/frames.py` を参照（フレーム形式の正）

1. `app/composables/useTerminalSocket.ts` 新設: WebSocket 接続・`auth` フレーム送信（JWT）・`hello` 受信で state 保持・`exec` 送信/`result` 受信・`event`（mission_clear）受信・切断/再接続ハンドリング
2. state は reactive に保持（current_path, filesystem 有無, mission_flags 等。UI 側が参照する最小限のみ。仮想FS全体を保持する必要は無い想定 — 表示に必要な差分は result フレームの `lines`/`state` サマリから得る。`noir-api/app/ws/frames.py` の `state_summary` の返却形を確認すること）
3. 接続品質: `docs/DESIGN.md` § 10-7「接続品質」の基準に従う（再接続・エラー表示等）

DoD: ブラウザの開発者ツールで WS 接続 → auth → hello → 簡単な exec が通ることを確認（コンソールログ等で可、UI 未接続でも可）。

## FE-04 TerminalView を WS 連携に置換（モック evaluator 撤去）
- [ ] 未着手

参照: `docs/DESIGN.md` § 10「TerminalView 実装仕様」（アーキテクチャ・入力ライン編集・出力レンダリング・Tab補完プロトコル・プロンプト表示の品質基準）

1. `app/pages/missions/[id].vue`（または index.vue 相当）で FE-03 の composable を使い、`TerminalView.vue` へ実データを流す
2. `app/pages/index.vue` 内のモック evaluator 実装を削除（コメントに「WS 実装後に置き換え」とある箇所）
3. Tab 補完: 設計指示書 § 7「補完フレーム」参照。バックエンドに補完エンドポイント/フレームが実装済みか要確認（未実装なら本タスクではスキップしフロント側の暫定候補生成に留めるか、別タスク化を検討）
4. mission_clear イベント受信時に `ClearEffect.vue` を発火させる

DoD: ブラウザで Mission1 を実際に `cat`→`echo`→`sh case_file.sh`→`git add/commit/push` まで通しプレイできることを確認（最重要 DoD）。

## FE-05 コマンド一覧パネルの Mission 連動
- [ ] 未着手

1. `CommandPanel.vue`/`CommandDetail.vue` を Mission 詳細 API の `allowed_commands`（バックエンド `MissionDef.allowed_commands` 相当。`GET /api/missions/{id}/` のレスポンスに含まれるか確認）に連動させる
2. コマンドクリックで入力欄に挿入する等、既存コンポーネントの UX を壊さない範囲で配線

DoD: Mission ごとに異なるコマンド一覧が表示されることを確認。

## FE-06 場面画像の state 連動（cd/ssh/exit フェード）
- [ ] 未着手

参照: `docs/DESIGN.md` § 1「場面画像とカレントディレクトリの紐付け」（`scene_images` 最長一致解決は実装済み・呼び出し元が未配線）

1. FE-03 の WS state（current_path 等）を `SceneOverlay.vue` に渡し、`cd`/`ssh`/`exit` 実行結果に応じてフェード遷移させる
2. 画像アセットは `office.png` 1枚のみ現状（他は後回しで可。プレースホルダ許容）

DoD: `cd`/`ssh`/`exit` でシーン画像が切り替わる（フェード込み）ことを確認。

## FE-07 セーブ選択 UI（再ログイン時の commit 一覧）
- [ ] 未着手

参照: 設計指示書 § 10「セーブ仕様」・§ 7 の `resume` フレーム。バックエンド `noir-api/app/ws/terminal.py` の `_handle_resume`・`GET /api/missions/{id}/state/` を参照

1. `SaveSelectModal.vue` を実データ（commits 一覧）に接続。再ログイン時に state API または hello フレームの commits から一覧表示
2. 選択した commit で `resume` フレームを送信し state を復元

DoD: 一度 `git commit` してから再接続し、セーブ選択→復元が動くことを確認。

## FE-08 手動 E2E 確認（Mission1〜3 通しプレイ）
- [ ] 未着手

1. `run`/`verify` skill を使い、ログイン→Mission1→Mission2→Mission3 まで実ブラウザで通しプレイし、詰まる箇所・エラーを洗い出して修正
2. Mission3 の ssh/exit・remote 表示が正しくフェードすることも確認
3. 発見した不具合はその場で直すか、新規タスクとして本ファイルに追記する

DoD: Mission1〜3 が実ブラウザでノーエラーにクリアできる。
