# 現在のファイル構成と各ファイルの役割

更新日: 2026-09-14（2026-09-13 の追加エピソード 23〜29・ゲーム機能 12 項目・Phase F 完了を反映）

---

## ディレクトリ構成

```
CLI_Noir/
├ CLAUDE.md          … Claude Code 用ガイド（参照優先順位・運用ルールの要約）
├ docs/              … 全設計ドキュメント（+ design-system/ = デザイン local ミラー）
├ context/           … 本フォルダ（AI コンテキスト復元用。04_task_backlog.md も参照）
├ noir-client/       … Nuxt 4 フロント実装（実バックエンド接続済み・常時ターミナル）
├ noir-api/          … FastAPI バックエンド（全 29 Mission 実装・統合ワールド。559 tests green / ruff clean）
├ moc/               … UI モック（参考用）+ images/NEEDED_IMAGES.md（場面画像の制作リスト）
└ old_files/         … 過去バージョンのバックアップ（参照不要）
```

---

## `noir-api/`（FastAPI バックエンド）

**全 29 Mission が実プレイ可能**（1〜22 + git 編 23〜25 + サーバー編 26〜28 + やらかし体験室 29）。
**id は事件番号で固定、プレイ順序は `app/content/missions.py::_DEFS` の並び**（11 → 23〜25 → 29 → 12 … 21 → 26〜28 → 22）。
ユーザーごとに 1 つの永続統合ワールド `PlayerState.data`（JSON）。書き込みは WS evaluator のみ。

### state の形（`app/models/tables.py::default_world_state()`）
- `current_path` / `filesystem`（全区画を最初から持ち、未解放はディレクトリ権限で不可視）/ `remote_mode` / `ssh_host` / `current_user`
- `processes` / `cron_jobs`（解放時に投入）/ `env_vars`（ユーザー別 dict。Mission21 解放時に detective の PATH を汚す）
- `command_log`（成功コマンドの生テキスト）/ `resolved_command_log`（`{line, resolved_line, paths, mission_id}`。mission_id は打った時点の捜査中 Mission）
- `git_state`（`staged` / `commits`（セーブ。`pushed` 印）/ `pushed` / `repo`（ブランチ・PR。git 編））
- `mission_progress`（`completed` / `active_mission_id` / `flags` / `released` / `story_fired` / `scores` / `timers`）
- `codex`（道具・エラー図鑑）/ `collection`（回想）/ `unlocked_commands`（cowsay/figlet）/ `sandbox`（Mission29 の退避）/ `remote_services`（systemctl の状態）

### モジュール
- `app/api/`: `auth`（JWT）/ `missions`（一覧・詳細（hints / field_card）・`/{id}/replay/`）/ `state` / `codex`
- `app/ws/terminal.py`: `auth` → `hello`（state + commits + story）→ `exec`/`result`（+ `event: mission_clear` → `rank_up` → `story`、result に `codex`/`collection`）/ `complete`/`completions` / `resume`（push 済み commit はクリア直後へ）。`frames.py` に Pydantic モデルと `state_summary`（rank / sandbox / mission_started_at 込み）
- `app/content/`: `missions.py`（MissionDef 29 件 + 世界 FS の合成 `_build_world_fs`・`_RELOCATIONS`・`_MISSION_AREAS`・隠しファイル配置）/ `codex.py`（エラー翻訳）/ `collection.py`（回想 13 枚）/ `field_cards.py`（現場実習カード）/ `manpages.py`（man）
- `app/evaluator/`:
  - `engine.py` … トークナイズ → 環境変数展開 → glob → パイプ → denylist/allowlist（sandbox 中の rm/dd・未解放のご褒美コマンドはここで判定）→ PATH 解決 → dispatch → リダイレクト → `$?` → ログ
  - `commands.py` … 一般コマンド + `SSH_HOSTS`（amusement_park / ghost.example / archive_node / corp_server）+ サーバー系（hostname/uname/df/du/ip/systemctl/journalctl/curl mock）+ man/whatis/apropos
  - `git_ops.py`（status/add/commit/push）+ `git_branches.py`（branch/checkout/log/diff/merge・三方マージ・競合）+ `gh.py`（pr create/view/list/merge）+ `pr_review.py`（レビュー規則）
  - `judge.py`（`case_file.sh` 判定。`_CUSTOM_JUDGES` 2/6/7/8/10/12/14/15/16/19/20/21/22/23〜29 + 汎用 AND-regex）
  - `progress.py`（`advance_mission`＝クリア記録→評価→sandbox 解除→解放→事務所へ戻す、`release_missions`、古いセーブへの区画/隠しファイル継ぎ足し）
  - `story.py`（独り言）/ `rank.py`（探偵ランク）/ `score.py`（ボーナス・タイマー）/ `codex.py`（図鑑登録）/ `rewards.py`（回想・cowsay/figlet）/ `sandbox.py`（Mission29）/ `complete.py`（Tab 補完）/ `env.py` / `fs.py` / `script.py`
- `alembic/`: 最新 `63217880f0a0`（`missionstate` drop）
- `tests/`: 552 件。`tests/helpers.py::state_at_mission(n)` でプレイ順序に沿って進めた統合ワールドを組む

---

## `noir-client/`（Nuxt 4 SPA / ssr:false。常時ターミナル）

- `app/app.vue` … ログイン状態にひもづけて WS を 1 本張る
- `app/pages/login.vue` / `missions/index.vue`（ポスター調の事件一覧。pt 表示）/ `missions/[id].vue`（ゲーム画面。表示切替専用）/ `design.vue`
- `app/components/`: `TerminalView`（↑↓・Ctrl 系・Tab 補完・Ctrl+R）/ `PromptLabel` / `MissionHeader` / `SceneOverlay` / `MonologueLayer`（独り言。最前面 z40）/ `CodexLayer`（図鑑: エラー/道具/回想。z30）/ `ClearEffect`（評価行付き）/ `RankUpEffect`（辞令）/ `FieldCard`（現場実習カード）/ `ReplayLedger` / `SaveSelectModal`（クリア印・日時）/ `CommandPanel` / `CommandDetail` / `NoirButton`
- クリア時の順番: Mission Complete → 辞令 → 現場実習カード → 独り言（ブリーフィングを閉じてから）
- `app/composables/useTerminalSocket.ts`（シングルトン WS。`exec` / `complete` / `resume`）/ `useAuth.ts` / `useApi.ts`
- `app/stores/terminal.ts`（state・scrollback・独り言キュー・図鑑・演出の保留フラグ）/ `app/types/ws.ts`（`frames.py` と 1:1）/ `app/utils/commandCatalog.ts`
- 未実装: 自動テスト（Vitest/Playwright 未導入。検証は scratchpad の Playwright スクリプトで都度）、右パネルの新コマンド点灯アニメ、場所別画像（`office.png` 以外）

### `docs/design-system/`（デザインの local ミラー）
- claude.ai/design「CLI_Noir Design System」の最小ミラー（`styles.css` + `tokens/` + `ui_kits/detective-terminal/index.html`）。**正は ClaudeDesign 側**。更新フローは `docs/design-system/README.md`

---

## docs/（アクティブファイル 7 つ）

| ファイル | 内容 |
|---|---|
| `設計指示書.md`（最上位の正） | 概要 / 技術スタック / 仮想FS・セーブ選択 / local・remote（SSH 4 ホスト）/ API・WS 仕様（complete・rank_up・codex・collection）/ allowlist・denylist・ランク表 / 判定 / 疑似 Git（+ 5b ブランチ・PR は バックエンド仕様に）/ Mission 設計（1〜22 + § 5b 追加 23〜28 + 29）/ ゲーム機能 12 項目（すべて実装済みの注記付き）/ エラー一覧 / 受け入れ基準 |
| `Mission参照ファイル.md` | Mission1〜3 の確定詳細、4〜22 の仕様 + 起草済み注記、§ 5b 追加エピソード 23〜29 |
| `バックエンド_コマンド機能仕様.md` | evaluator のコマンド定義 + § 5b ブランチ/マージ/PR、§ 5c サーバー編の基盤 |
| `LPIC学習マップ.md` | LPIC ⇔ ゲーム内コマンド対照 |
| `環境構築手順.md` | Nuxt / FastAPI セットアップ |
| `DESIGN.md` | UI/ビジュアル仕様・コンポーネント分解（CodexLayer/FieldCard/ReplayLedger 込み）・TerminalView 品質基準 |
| `AUTHORING_GUIDE.md` | Mission・コマンド作り込みガイド |

---

## その他

| パス | 内容 |
|---|---|
| `CLAUDE.md` | Claude Code 用ガイド。ドキュメント参照優先順位と運用ルールの要約 |
| `moc/images/NEEDED_IMAGES.md` | 場面画像の制作リスト（優先度 A〜E。E は追加エピソード） |
| `noir-api/noir.db` | dev DB（`detective01` = ユーザー本人、`e2e01`/`e2e02` = 検証用。パスワード `secret`） |
