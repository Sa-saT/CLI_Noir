# 対話で確定した全決定事項

日付: 2026-02-17（初版）/ 2026-07-06（Phase2 拡張採用）  
対話回数: 約20往復 + Phase2 拡張対話

---

## 実装方式の改訂（2026-07-06 確定・熟考レビューによる訂正）

技術スタック・API・WS の設計を精査し、以下を改訂（旧版は old_files/ の _004 / _001 系に退避済み）。

### 訂正（欠陥の修正）
- **`PUT /api/missions/{id}/state/` を廃止**: クライアントが mission_flags 等を直接書けるチート穴だった。state 書き込みは WS evaluator のみ
- **`POST /api/missions/{id}/complete/` を廃止**: `{"passed": true}` の自己申告設計は改ざん可能。クリア判定・記録・次 Mission 解放は `git push` 成功時にサーバー内部で実施
- **WS 認証を query parameter → 初回 `auth` フレームに変更**: URL 上のトークンはログ/プロキシに漏洩するため

### 技術選定の変更
- **Django + DRF + Channels → FastAPI + SQLModel + Alembic + uvicorn**（同日のユーザー確認で確定）: 本アプリの主役は WebSocket であり、FastAPI はネイティブ対応で Channels/daphne/ASGI 設定が丸ごと不要。Pydantic が WS フレーム定義と 1:1 で検証も自動化。async 一本の単一パラダイム。DB は SQLite（開発）→ PostgreSQL（本番・JSONB）
- **認証は PyJWT + passlib[bcrypt]**（simplejwt は DRF 専用のため使用不可。access 30分 / refresh 7日）
- **xterm.js → 自作 `TerminalView.vue`**: 行単位入出力のみのゲームでは xterm は過剰（ライン編集は結局自作）。構造化 JSON 出力の DOM 直描画の方が演出自由度が高く、日本語 IME（commit メッセージ等）も native input が安全。Phase3 の vi 導入時に xterm.js を再評価。**詳細な実装仕様（品質基準）は docs/DESIGN.md § 10 を正とする**
- **フロント追加技術**: TypeScript（WS フレーム型共有）/ Pinia / Vitest / Playwright / ESLint + Prettier。バックエンドは pytest + httpx + ruff
- **Nuxt は SPA モード（ssr: false）**: 認証必須 + WS 主体で SSR の利点なし
- **採用しない技術を明文化**（設計指示書 § 2）: Redis / Celery / Socket.IO / GraphQL / SSR / 開発時 Docker

### 設計の具体化
- WS メッセージプロトコル確定: `auth` / `hello` / `resume` / `exec` / `result`（style 付き行）/ `stream` / `event`。channel layer（Redis）は MVP 不要
- 仮想FSノードスキーマ確定: `type` / `content` / `mode` / `owner` / `mtime` / `immutable`（Phase2 の chmod/ls -l に備え最初から持たせる）
- サイズガード: state 256KB 上限 / commits 30 件上限 / 生成系巨大ファイルは seed のみ保存
- evaluator 実装方式: shlex トークナイズ + 小型パーサ / 純粋関数 + registry パターン / 実 subprocess・実FS 禁止 / ゴールデントランスクリプトテスト（バックエンド_コマンド機能仕様 § 0.5）

## ディレクトリ整理（2026-07-06 確定）

- 設計ドキュメント 5 点（設計指示書 / Mission参照ファイル / バックエンド_コマンド機能仕様 / LPIC学習マップ / 環境構築手順）をルートから `docs/` へ移動し、DESIGN.md / AUTHORING_GUIDE.md と集約
- ルートは `CLAUDE.md` + 4 フォルダ（docs / context / moc / old_files）のみ
- 各ファイル間の参照は同一フォルダ内のためファイル名のみで維持。`context/` と `CLAUDE.md` からは `docs/` 付きパスで参照
- あわせて不整合を修正: mission_id 範囲を 1..20 に / SSH 接続先に `ghost.example`（Mission11）を追加 / LPIC学習マップ § 7・§ 8 の古い「Mission4/5 で導入予定」表記を実際の Mission 番号に更新

## Phase2 拡張の採用（2026-07-06 確定）

`LPIC拡張_Mission案.md`（提案）を**全面採用**し、各正ドキュメントへ統合済み（提案ファイルは old_files/ へ移動）。

- **レベル体系**: Level 5〜11 を追加（探偵ランク制度: 情報屋/監視者/潜入捜査官/証拠管理官/追跡者/主任探偵/参謀）→ 設計指示書 § 8
- **allowlist 拡張**: 約50コマンド追加（head/tail/sed/ps/kill/su/tar/md5sum/ping/dig/crontab/sh 等）→ 設計指示書 § 8
- **構文レベルの許可**: glob / 引用符 / `2>` / `$?` / 変数 / if・for（evaluator パーサー対応が必要）→ 設計指示書 § 8
- **kill は仮想プロセステーブル限定**。sudo は denylist 維持（イベント演出限定で検討）
- **Mission4〜20 を確定**（概要レベル。詳細正規表現は実装時）→ Mission参照ファイル § 5
- **Phase2 ゲーム機能 8 項目**（ランク制度/コマンド図鑑/スマート捜査ボーナス/相棒キャラ/隠しファイル収集/man=捜査ハンドブック/タイムアタック演出のみ/リプレイ台帳）→ 設計指示書 § 11
- **非コマンド学習要素**（glob/引用符/リダイレクト/FHS/キー操作）→ LPIC学習マップ § 16
- **Phase3 候補（未確定のまま）**: vi / mount / パッケージ管理 → LPIC学習マップ § 17

---

## 実装着手・デザインシステム（2026-07-07 確定）

- **Nuxt フロント実装に着手**: `noir-client/`（Nuxt 4 SPA / ssr:false）。DESIGN.md § 5 の 10 コンポーネントを SFC 化（NoirButton / MissionHeader / CommandPanel / CommandDetail / PromptLabel / TerminalView / SceneView / SceneOverlay / ClearEffect / RankUpEffect / SaveSelectModal）+ ページ 2 枚（`index`=Mission1 合成画面・モック evaluator / `design`=ギャラリー）。Tailwind は未導入で、トークン CSS 変数方式（ClaudeDesign 出力と 1:1）
- **デザインシステムを ClaudeDesign（claude.ai/design）で管理**: プロジェクト「CLI_Noir Design System」。local ミラーを `docs/design-system/` に置く
- **開発仕様（デザイン更新フロー）確定**: **デザイン変更は ClaudeDesign で行い、変更を local へ落とし込む**（同期方向 = ClaudeDesign（正）→ local、逆流禁止）。落とし込みは Claude Code が `DesignSync` で pull → `docs/design-system/`（ミラー）→ `noir-client/`（実装）の二層に反映。手順の正は `docs/design-system/README.md`「更新フロー」
- **背景画像**: 探偵事務所の部屋 = `moc/images/mission1.png` を `noir-client/public/images/office.png`（場所ベース命名）としてコピー・配線

---

---

## 技術スタック
- Frontend: Vue 3 + Nuxt（file-based routing）+ Tailwind CSS + xterm.js（※2026-07-06 改訂: xterm.js → 自作 TerminalView。上記「実装方式の改訂」参照）
- Backend: Django + DRF + Django Channels + PyJWT（※2026-07-06 改訂: → FastAPI + SQLModel。上記「実装方式の改訂」参照）
- volta / pnpm / brew / pyenv はインストール済み

## 認証
- HTTP API: Authorization Bearer ヘッダー
- WebSocket: query parameter で JWT を渡す

## 仮想FS
- ユーザー × ミッション単位で1レコード（DB の JSON カラム）
- 再ログイン時に復元する（カレントパス / FS / remote_mode / git_state / mission_flags）
- 復元しない（入力途中文字列 / UIスクロール / 一時エラー / 通信中フラグ）

## コマンド制御
- allowlist 方式（設計指示書 § 8 に定義）
- 判定順序: denylist → allowlist → 実行
- `git` は第1トークンで判定後、サブコマンドを別途分岐
- `rm` は全般禁止。`curl` は mock API 限定

## 疑似 Git（重要：通常のGitワークフローとは異なる）
- `git commit` = ゲームセーブ（1 Mission 中に何度でも可能）
- `git push` = クリア判定（最新 commit の状態で合否判定）
- 順序制約: add（必須）→ commit → push
- add なしで commit → `Error: nothing to commit`
- commit なしで push → `Error: push not allowed before commit`
- push 時にクリア条件未達 → `Error: mission requirements not met`
- 再ログイン時に commit 一覧から任意のセーブを選んで再開可能
- 次 Mission 遷移時、前 Mission のクリア前 commit は全消去

## Mission 判定
- 正規表現ベース / 順不同許容 / 大小文字区別あり
- 不正コマンド時: エラーメッセージ表示のみ（即失敗にしない）
- `case_file.sh` の実行 → add → commit → push の流れでクリア

## SSH
- 疑似接続。接続先確定:
  - `amusement_park`（MVP Mission3 必須、初期ディレクトリ `/gate`）
  - `corp_server`, `archive_node`（将来拡張用）
- エラー: `Host not found` / `Permission denied`
- local に戻るには `exit` のみ（`cd` では不可）

## Mission 設計
- MVP: Mission1〜3（段階的に増やす前提）
- Mission1: Edit Business Card（名刺編集。ls/cd/cat/echo/git）
- Mission2: Park Cat Search（猫探し。find/grep/cat）
- Mission3: Amusement Park Bomb（爆弾解除。ssh/find/grep/awk/正規表現）
- Mission4/5: 将来拡張（パイプ・リダイレクト / 権限管理）

## ゲームの趣旨
- 「触りながら理解する」原体験の再現
- 黒い画面アレルギーの克服
- LPIC 学習の入り口（教科書挫折問題の解決）
- PC の理論性・概念フローを遊びで体に染み込ませる
- ゲーム操作と実 PC 操作の意味を一致させる（ゲーム限定の知識にしない）

## ペルソナ
- ターゲット: PC の根本に興味がある人（年齢・性別不問）
- 副次: LPIC 受験予定者
- 「まず触って確かめたい」タイプを中心に設計

## ファイル構成の方針
- 無駄にファイルを増やさない
- 統合できるものは統合する（allowlist_denylist.md とタスクフロー.md は設計指示書に吸収済み）
- 変更時は old_files/ に採番バックアップを取ってから更新
- 設計指示書.md を最上位の正とし、他ファイルはそこを参照する

## UI
- 3 領域（上部: 背景+情報 / 右: コマンド一覧 / 下: ターミナル）
- 日本語統一
- ssh/exit 時に背景フェード遷移
- コマンド説明はフェード表示
- touch で作成したファイルは UI 削除ボタンで削除可能
- デフォルト配置ファイルは削除不可
