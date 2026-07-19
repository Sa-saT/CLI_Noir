# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

CLI_Noir は Linux(LPIC) を「ノワール探偵ゲーム」として遊びながら学ぶ CUI 学習ゲーム。**設計ドキュメント主導**で進めており、フロントエンド実装（`noir-client/`）は着手済み、バックエンド（FastAPI）は未着手（`context/03_pending_items.md` 参照）。

- コンセプト: **Linux(LPIC)・PC への理解 + 黒い画面（ターミナル）は「理解すれば怖くない」**を遊びで身につけさせる（設計指示書 § 11）
- MVP: Mission1〜3 / Phase2: Mission4〜22・Level 5〜11 採用済み（2026-07-06 確定、2026-07-08 に /proc・PATH の 2 Mission 追加で全 22 に）
- ユーザーへの返答は**常に日本語**で行う
- ファイル名は英語、UI ラベル・ドキュメントは日本語

## ディレクトリ構成

```
CLI_Noir/
├ CLAUDE.md      … 本ファイル
├ docs/          … 全設計ドキュメント（正）+ design-system/（デザイン local ミラー）
├ context/       … AI コンテキスト復元用（セッション開始時に 00 から読む）
├ noir-client/   … Nuxt 4 フロント実装（実装済み。app/components/*.vue + pages）
├ noir-api/      … FastAPI バックエンド（未追跡のローカルスキャフォールドのみ。実装未着手）
├ moc/           … UI モック（参考用。確定仕様との差分あり）
└ old_files/     … 過去バージョンのバックアップ（参照不要）
```

### エージェント向け・読むファイルの絞り込み（トークン節約）

タスク種別ごとに読むべきファイルだけを開く。関係ないディレクトリは開かない。

| やること | 読む | 開かない |
|---|---|---|
| 仕様の確認・変更 | `docs/設計指示書.md`（正）+ 関連する `docs/*.md` | `old_files/` `noir-client/` `docs/design-system/` |
| バックエンド実装 | `docs/バックエンド_コマンド機能仕様.md` + `docs/Mission参照ファイル.md` | `old_files/` `moc/` |
| フロント実装 | `docs/DESIGN.md` + `noir-client/app/` | `old_files/` |
| デザイン更新 | `docs/design-system/README.md`（フロー）+ `DesignSync` | ミラーの生成物 |
| Mission/コマンド追加 | `docs/AUTHORING_GUIDE.md` + `docs/Mission参照ファイル.md` | `old_files/` |

- `old_files/` は**採番バックアップ専用**。検索・参照しない（履歴が要る時だけ）。
- `noir-api/.venv/` は gitignore 済み・未追跡。**絶対に読み込まない**（巨大）。

## ドキュメント構成と参照優先順位

`docs/設計指示書.md` が最上位の正。矛盾があれば設計指示書に従う。

1. `docs/設計指示書.md` — 全体仕様（技術スタック / API / WebSocket / allowlist・レベル表 / 疑似Git / Mission判定 / エラー一覧 / 受け入れ基準）
2. `docs/Mission参照ファイル.md` — Mission1〜22 の詳細仕様（正規表現・ヒント・配置ファイル）
3. `docs/バックエンド_コマンド機能仕様.md` — evaluator 実装時の各コマンド定義書（引数 / 出力 / state 更新）
4. `docs/LPIC学習マップ.md` — LPIC Level 1 とゲーム内コマンドの対応表（非コマンド学習要素含む）
5. `docs/環境構築手順.md` — Nuxt / FastAPI のセットアップ手順

セッション開始時にコンテキストを復元する場合は `context/00_READ_ME_FIRST.md` から順に `context/` 内 5 ファイルを読む。

**バックエンド実装タスクの復元**: セッション内タスクリストが空の場合、`context/04_task_backlog.md`（Phase2 タスク P2-01〜P2-19 の正）から未完了タスクを TaskCreate で復元してから着手する。タスク完了時は backlog 側のチェックボックスも [x] にする。

- `docs/DESIGN.md` — UI/ビジュアル仕様（カラートークン・レイアウト・コンポーネント分解・moc との差分表）。フロントエンド実装時に併読
- `docs/AUTHORING_GUIDE.md` — Mission・コマンドの作り込みガイド（5幕構造・定義スキーマ・DoD）。コンテンツ追加時は必読
- `old_files/` は過去バージョンのバックアップ。参照不要
- `moc/index.html` は UI モック（Vue CDN 直書き）。本番実装とは分離。**moc と確定仕様の差分は `docs/DESIGN.md` § 8 を参照**（moc をそのまま写さない）

## ファイル管理ルール（ユーザーの明確な方針）

- **無駄にファイルを増やさない**。統合できるものは統合する
- 仕様変更時は、先に `old_files/` へ採番バックアップ（例: `設計指示書_004.md`。既存の連番に続ける）を取ってから更新する
- 仕様変更後は `context/` 内のファイル（決定事項ログ・現在状態・未確定項目）も最新化する

## セットアップコマンド（実装着手時）

前提: macOS / zsh、volta / pnpm / brew / pyenv インストール済み。詳細は `docs/環境構築手順.md`。

```bash
# Frontend (Vue 3 + Nuxt SPA + Tailwind + 自作ターミナルUI)
pnpm create nuxt@latest frontend && cd frontend && pnpm install
pnpm dev

# Backend (FastAPI + SQLModel + Alembic, Python 3.12.8) ※2026-07-06 Django から変更
pyenv local 3.12.8
python -m venv .venv && source .venv/bin/activate
pip install "fastapi[standard]" sqlmodel alembic pyjwt bcrypt pydantic-settings  # passlib は廃止（bcrypt 5.x 非互換のため直接使用。2026-07-08）
pip install pytest httpx ruff
# プロジェクトは手で掘る（スケルトンは docs/環境構築手順.md § 3-4）
cd backend && alembic upgrade head && uvicorn app.main:app --reload
```

## アーキテクチャの要点

- **仮想FS**: `user_id + mission_id` 単位で 1 レコード、DB の JSON カラムに永続化。再ログイン時に current_path / filesystem / remote_mode / git_state / mission_flags を復元する
- **WebSocket**: `/ws/terminal?mission_id=<id>`。初回 `auth` フレームで JWT 認証 → `hello` で state 返却 → `exec`/`result` フレームでコマンド実行（denylist → allowlist → evaluator → state 更新）。**state とクリア判定の書き込みは evaluator のみ**(クライアントが state を書ける HTTP API は廃止済み)
- **認証**: HTTP は `Authorization: Bearer`(SimpleJWT)、WebSocket は接続後の初回メッセージで JWT を渡す(query parameter は漏洩リスクのため不採用)
- **コマンド制御**: allowlist 方式。判定順序は denylist → allowlist → 実行。`git` は第1トークン判定後にサブコマンドを別途分岐。`rm` は全般禁止、`curl` は mock API 限定
- **SSH**: 疑似接続。`amusement_park`（初期ディレクトリ `/gate`、Mission3 用）が確定済み。local へ戻るのは `exit` のみ（`cd` 不可）

## 疑似 Git（通常の Git ワークフローとは意味が異なる）

- `git commit` = **ゲームセーブ**（何度でも可）、`git push` = **クリア判定**（最新 commit の snapshot で合否判定）
- 順序制約: `sh case_file.sh`（判定実行）→ `git add`（必須）→ `git commit` → `git push`
- 再ログイン時は commits 一覧から任意のセーブを選んで再開。次 Mission 遷移時に前 Mission のクリア前 commit は全消去
- 実 Git 連携は行わない（`git_state` JSON で管理）

## 最重要設計原則

**ゲーム操作 = 実 PC 操作の意味一致**。ゲーム限定の知識にしない。仕様追加・変更時は、実際の Linux コマンドの挙動と意味が一致しているかを必ず確認する（疑似 Git のみ意図的な例外）。
