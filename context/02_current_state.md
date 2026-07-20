# 現在のファイル構成と各ファイルの役割

更新日: 2026-07-20（バックエンド Mission1〜22 全実装完了・Phase2 コマンド大半実装を反映）

---

## ディレクトリ構成

```
CLI_Noir/
├ CLAUDE.md          … Claude Code 用ガイド（参照優先順位・運用ルールの要約）
├ docs/              … 全設計ドキュメント（+ design-system/ = デザイン local ミラー）
├ context/           … 本フォルダ（AI コンテキスト復元用。04_task_backlog.md も参照）
├ noir-client/       … Nuxt 4 フロント実装（2026-07-07 着手・evaluator はモックのまま）
├ noir-api/          … FastAPI バックエンド（2026-07-13 骨格〜MVP、2026-07-20 Mission1〜22 全実装。241 tests green）
├ moc/               … UI モック（参考用）
└ old_files/         … 過去バージョンのバックアップ（参照不要）
```

2026-07-06 の整理で、設計ドキュメント 5 点をルートから `docs/` へ移動した。
2026-07-07 に Nuxt 実装（`noir-client/`）とデザインシステム local ミラー（`docs/design-system/`）を追加。

---

## `noir-api/`（FastAPI バックエンド。2026-07-13 骨格〜MVP、2026-07-20 Phase2 完了）

**Mission1〜22 すべて実プレイ可能**（241 tests green / ruff clean）。詳細は `context/01_decisions_log.md`「Phase2 バックエンド実装」節・`context/03_pending_items.md` Backend 節を参照。

- `app/api/`（auth / missions / state）・`app/ws/terminal.py`（WS ハンドシェイク）・`app/models/`（User / MissionState / default_state）は MVP 時点から変更なし
- `app/content/missions.py`: 全22 Mission の定義 + FS/プロセス/cron/env_vars 初期値。`MissionDef` は `initial_filesystem`・`initial_current_path`・`initial_processes`・`initial_cron_jobs`・`informant_history`・`initial_env_vars` を持つ
- `app/evaluator/`:
  - `fs.py` — パス解決一元化・疑似 `/proc` 動的生成・symlink 解決（`resolve_link`）・権限検査（`can_read`/`can_exec`、owner ベース）
  - `commands.py` — 実装コマンド一覧は下記
  - `engine.py` — トークナイズ（引用符追跡）→ 環境変数展開（`$VAR`/`$?`、シングルクォート保護）→ glob 展開 → パイプ分割 → PATH 解決付き dispatch → リダイレクト（`>`/`>>`/`2>`）→ `$?` 記録
  - `script.py`（新規）— `sh` 汎用スクリプトのミニインタープリタ（変数・if・for、ネスト非対応）
  - `judge.py` — Mission 別カスタム判定（`_CUSTOM_JUDGES`）+ 汎用 AND-regex フォールバック
  - `git_ops.py` — 疑似Git（変更なし）
- 実装済コマンド（allowlist 内、Phase2 含む）: ls(+`-l`)/cd/pwd/cat/less/touch/mkdir/chmod/echo/grep(+`-r`/`-q`/egrep/fgrep)/find/sort/uniq/wc/head/tail/cut/paste/tr/diff/sed/file/tar/gunzip/unzip/ln/md5sum/sha256sum/ps/kill/free/uptime/su/whoami/id/dig/host/ping/ss/crontab/date/export/unset/printenv/which/type/ssh/exit/sh/git/clear/history
- 未実装（allowlist にあるが未登録）: awk のみ
- `docs/設計指示書.md` の ghost.example「初期ディレクトリ未定」は**解消済み**（`/den`、Mission12/22 で使用）。`corp_server`・`archive_node` は Phase3 予約のまま未使用

---

## 実装・デザインシステム（2026-07-07 追加）

### `noir-client/`（Nuxt 4 SPA / ssr:false）
- `app/components/*.vue` … DESIGN.md § 5 の 10 コンポーネント実装（TerminalView がハブ）。SceneOverlay が `image`/`fading` でシーン画像を第一級に扱う（旧 SceneView は統合し廃止）
- `app/pages/index.vue` … Mission1 合成画面（**モック evaluator**。本番は WS evaluator へ置換予定）。場面画像は `sceneImages`（`ホスト:パス接頭辞` の最長一致）で **current_path に紐付け**（2026-07-07 確定・DESIGN.md § 1）
- `app/pages/design.vue` … コンポーネントギャラリー
- `app/assets/css/tokens/*.css` + `main.css` … デザイントークン（`docs/design-system` のコピー）
- `public/images/office.png` … 探偵事務所の部屋（`moc/images/mission1.png` 由来）

### `docs/design-system/`（デザインの local ミラー）
- claude.ai/design プロジェクト「CLI_Noir Design System」の**最小ミラー**（`styles.css` + `tokens/` + `ui_kits/detective-terminal/index.html`）。2026-07-07 に `components/*.jsx` の複製を廃止（Vue SFC と重複・ビルド未使用のため。React 実ソースは ClaudeDesign 側にあり `DesignSync get_file` で都度参照）
- **デザインの正は ClaudeDesign 側**。更新フロー（ClaudeDesign → local）は `docs/design-system/README.md` を正とする
- アートディレクション更新済み（2026-07-07）: スチームパンク金属 + ネオングロー + フレンチポスター調。トークンに brass/copper/poster/glow/bezel と font-hero(Jost)/font-accent(Josefin) を追加。コンポーネントの実ソースは `.jsx`（Vue SFC はこれを移植）、`ui_kits/detective-terminal/index.html` は自己完結の全画面リファレンス

---

## docs/（アクティブファイル 7 つ）

### `docs/設計指示書.md`（最上位の正）
- プロジェクト概要・趣旨・ペルソナ / 技術スタック / UI・ルーティング
- 仮想FS（JSONスキーマ・復元範囲・セーブ選択・疑似 /proc・env_vars（2026-07-08 追加））
- local/remote（SSH接続先: amusement_park 確定、ghost.example は Mission12 用・初期ディレクトリ未定）
- API 詳細仕様 / WebSocket 仕様
- コマンド実行制御（allowlist 約70コマンド + egrep/fgrep + export/unset/printenv/type・denylist・Level 1〜11 探偵ランク表・構文レベルの許可）
- Mission 判定仕様 / 疑似 Git・セーブ仕様
- Mission 設計（MVP 1〜3 + Phase2 4〜22 一覧 + ゲーム機能 12 項目 = Phase2 の 8 + 2026-07-07 コンセプト強化の 4（やらかし体験室 / エラー図鑑 / 現場実習カード / ご褒美コマンド））
- エラーメッセージ一覧 / 受け入れ基準 / 開発フロー

### `docs/Mission参照ファイル.md`
- Mission 共通テンプレート（mission_id: 1..22）
- Mission1〜3: 確定詳細（正規表現・ヒント3段階・配置ファイル）
- Mission4〜22: Phase2 概要確定（あらすじ/フロー/必須コマンド/クリア条件/ゲーム性。詳細正規表現は実装時）。2026-07-08 に Mission7（/proc）・Mission21（PATH）を追加し番号振り直し（旧 7〜19 → 8〜20、旧 20 → 22）
- Agent 出力フォーマット / 参照優先順位

### `docs/バックエンド_コマンド機能仕様.md`
- evaluator 実装時のコマンド定義書（引数・前提・正常/異常出力・state更新）
- ※Phase2 新コマンド（約50個）の定義追加は未着手（03_pending_items 参照）

### `docs/LPIC学習マップ.md`
- § 1〜8: Phase1 コマンドの「実PCでの意味 ⇔ ゲーム内の対応」対照表
- § 9〜16: Phase2 拡張（テキスト処理/プロセス/権限・ユーザー/アーカイブ・鑑識/ネットワーク/システム管理/シェルスクリプト/非コマンド学習要素）
- § 17: Phase3 候補（vi / mount / パッケージ管理。未確定）
- § 18: LPIC 出題範囲サマリ / § 19: 設計時のルール

### `docs/環境構築手順.md`
- Nuxt（SPA + TypeScript + Pinia）/ FastAPI + SQLModel + Alembic のセットアップ手順（2026-07-06 Django から変更）

### `docs/DESIGN.md`（2026-07-06 作成）
- moc 準拠の UI/ビジュアル仕様: アートディレクション・カラートークン・レイアウト・Nuxt コンポーネント分解・モーション仕様
- **§ 8: moc と確定仕様の差分表**（vi/Notebook/英語UI は不採用等。実装時に moc をそのまま写さないこと）

### `docs/AUTHORING_GUIDE.md`（2026-07-06 作成）
- AI Agent 向け Mission・コマンド作り込みガイド
- 絶対原則 / 5幕構造 / ゲーム性の道具箱 / ノワール文体 / Mission定義YAMLスキーマ / Mission4 完全作例 / コマンド定義ルール / DoD チェックリスト / アンチパターン集

---

## その他

| パス | 内容 |
|---|---|
| `CLAUDE.md` | Claude Code 用ガイド。ドキュメント参照優先順位と運用ルールの要約 |
| `moc/index.html` | UI モック（Vue CDN 直書き）。確定仕様との差分は `docs/DESIGN.md` § 8 |
| `moc/images/mission1.png` | 背景画像の画風基準（セピア調・銅版画風ノワール） |
| `context/` | 本フォルダ（読み込み順は 00 → 01 → 02 → 03 → 04） |

## old_files/（バックアップ・参照不要）

| ファイル | 内容 |
|---|---|
| `設計指示書_001〜008.md` | 設計指示書の過去版（003 = Phase2 統合前 / 006 = 場面画像・egrep/fgrep 前 / 007 = ゲーム機能 9〜12 追加前 / 008 = /proc・PATH 追加前） |
| `DESIGN_001〜003.md` / `AUTHORING_GUIDE_001〜003.md` / `バックエンド_コマンド機能仕様_001〜002.md` / `環境構築手順_001〜002.md` | 各仕様の変更前バックアップ |
| `LPIC学習マップ_001〜004.md` / `Mission参照ファイル_001〜003.md` | Phase2 統合前ほか |
| `LPIC拡張_Mission案_001.md` | Phase2 提案原本（2026-07-06 全面採用・統合済み） |
| `追加確認事項.md` / `allowlist_denylist_001.md` / `タスクフロー_001.md` | 初期の統合済みファイル |

---

## Agent 参照優先順位

1. `docs/設計指示書.md`
2. `docs/Mission参照ファイル.md`
3. `docs/バックエンド_コマンド機能仕様.md`
4. `docs/LPIC学習マップ.md`
5. `docs/DESIGN.md` / `docs/AUTHORING_GUIDE.md`（実装・コンテンツ作成時）
6. `docs/環境構築手順.md`
