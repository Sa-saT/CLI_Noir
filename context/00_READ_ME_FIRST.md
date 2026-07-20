# CLI_Noir AI コンテキスト復元ガイド

このフォルダは、AI Agent がプロジェクトの設計対話を引き継ぐためのバックアップ。  
チャットが途切れた場合、新しいセッションでこのフォルダを読み込めば続行できる。

## 読み込み順序（必須）

1. `00_READ_ME_FIRST.md`（本ファイル。全体把握）
2. `01_decisions_log.md`（対話で確定した全決定事項）
3. `02_current_state.md`（ファイル構成と各ファイルの役割・現在の状態）
4. `03_pending_items.md`（未完了・未確定の項目）
5. `04_task_backlog.md`（実装タスクバックログ。**実装を続ける場合は必読** — セッション内タスクリストが空ならここから復元）

## 実装の現状（2026-07-20 時点）

- **バックエンド `noir-api/`（FastAPI）は Phase2 まで完了**: Mission1〜22 すべて実プレイ可能（241 tests green / ruff clean）。詳細は `02_current_state.md`「noir-api/」節・`01_decisions_log.md`「Phase2 バックエンド完了」節を参照
- **フロント `noir-client/`（Nuxt 4 SPA）は実装着手済みだが未接続**: DESIGN.md § 5 の 10 コンポーネント + Mission1 合成画面（`pages/index.vue`・**evaluator はモックのまま、実バックエンド未接続**）+ ギャラリー（`pages/design.vue`）。デザインは ClaudeDesign から pull（[[design-workflow-claudedesign-to-local]]）
- **次の実装対象はフロントエンド**: `04_task_backlog.md` の「Part 2: フロントエンド」（FE-01〜FE-08。認証UI→Mission一覧→WS接続→TerminalView連携→コマンドパネル→場面画像→セーブ選択→E2E確認の順）
- タスク別に読むファイルを絞る指針は `CLAUDE.md`「エージェント向け・読むファイルの絞り込み」を参照

## 読み込み後にやること

- 上記を読んだ後、`docs/設計指示書.md` を正として扱う（設計ドキュメントは全て `docs/` に集約。2026-07-06 整理）
- バックエンド実装に入る場合は `docs/バックエンド_コマンド機能仕様.md` と `docs/Mission参照ファイル.md` を併読する
- フロントエンド実装・演出は `docs/DESIGN.md` + `noir-client/app/` を併読する（moc との差分表あり）
- Mission・コマンドを新規作成する場合は `docs/AUTHORING_GUIDE.md` に従う
- 環境セットアップは `docs/環境構築手順.md` に従う
- LPIC 対応の確認は `docs/LPIC学習マップ.md` を参照する
- デザインを変える場合は `docs/design-system/README.md` の更新フロー（ClaudeDesign→local）に従う

## 注意

- `old_files/` は過去バージョンのバックアップ。参照不要（履歴確認用）
- `noir-api/.venv/` は未追跡・巨大。読み込まない
- `moc/index.html` は UI モック。本番実装とは分離
- ユーザーへの返答は常に日本語で行う
