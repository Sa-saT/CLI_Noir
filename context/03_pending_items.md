# 未完了・未確定の項目

更新日: 2026-07-20（バックエンド Phase2 完了。Mission1〜22 全実装・241 tests green / ruff clean）

---

## 未着手（実装前に必要）

### 環境構築
- [x] Nuxt（`noir-client/`）/ FastAPI（`noir-api/`）とも構築済み

### Backend（`noir-api/`。2026-07-20 Phase2 完了 — Mission1〜22 全実装・241 tests green / ruff clean）
- [x] 認証 API / Mission API / state API / WebSocket / evaluator（denylist→allowlist→registry dispatch→state更新）すべて実装済み
- [x] 仮想FS モデル・疑似Git・Mission 判定ロジック実装済み
- [x] **Mission1〜22 すべて実プレイ可能**（タスク #21〜#39 / P2-01〜P2-19 全19件を 1 task = 1 commit + push で完遂）

実装済みコマンド一覧・ファイル構成の要約は `context/02_current_state.md`「noir-api/」節、各 Mission の FS/判定の実装詳細は
`noir-api/app/content/missions.py` + `app/evaluator/judge.py` + `tests/test_mission*.py`（コードが正）、タスク単位の記録は
`context/04_task_backlog.md` Part 1、設計判断の経緯は `01_decisions_log.md`「Phase2 バックエンド完了」節を参照。
残る未着手は Frontend（下記）と「Phase2 拡張の実装タスク」節に残る細目（awk 定義・cowsay/figlet 等のご褒美コマンド・ゲーム機能9〜12 の UI 等）のみ。

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

### Phase2 拡張の実装タスク（2026-07-06 採用確定・2026-07-20 時点の残り）
- [ ] `docs/バックエンド_コマンド機能仕様.md` に Phase2 新コマンド（約50個）の定義を追加（実装着手時に段階的に）※egrep/fgrep は 2026-07-07 に定義済み（grep の alias）
- [x] evaluator 構文対応（glob/引用符/`2>`/`$?`/変数/if・for）・仮想プロセス/ユーザー/cronテーブル・アーカイブ入れ子表現・FHS版仮想FSマップは Phase2 P2-01〜P2-19 で実装済み（Backend 節参照）
- [ ] フロントエンド: Tab 補完 / `↑↓` 履歴 / `Ctrl+R` / `Ctrl+C` / `Ctrl+L`（`TerminalView.vue` の keydown 処理）
- [ ] ゲーム機能 12 項目（設計指示書 § 11。Phase2 の 8 + 2026-07-07 追加の 4）の UI 設計
- [ ] やらかし体験室の隔離 state 実装（使い捨て state / 本編 evaluator は denylist 不変）
- [ ] エラー図鑑の翻訳文データ作成（§ 12 エラー一覧と 1:1 対応）
- [ ] 現場実習カードの文面作成（安全コマンド限定 + macOS/Windows のターミナルの開き方）
- [ ] `cowsay` / `figlet` の evaluator 定義（バックエンド_コマンド機能仕様への追加。隠し実績の解放条件設計も）

### 解消済みの旧課題
- Mission4〜22 の詳細化・/proc・環境変数(PATH)・SSH接続先(ghost.example)・Mission4/5の詳細・cp/mvコマンド・case_file.shの中身は
  いずれも 2026-07-20 までに実装・確定済み（`noir-api/app/content/missions.py` 等が正）。経緯は `01_decisions_log.md` 参照

### ゲーム機能 9〜12 の未定項目（2026-07-07 採用に伴う）
- やらかし体験室の解放トリガー（案: denylist コマンドを初めて打って拒否された直後に相棒が誘う。未確定）
- ご褒美コマンド（cowsay/figlet）の隠し実績の条件（案: 隠しファイル収集数と連動。未確定）
- Mission1〜3 の現場実習カード文面（実装時確定。Mission4〜22 も同様）

### SSH 接続先の未定項目
- `corp_server` と `archive_node` は Mission 未割当のまま予約（Phase3 以降の拡張用）

---

## 対話中に出た重要な注意点

- ファイルを無駄に増やさない（ユーザーの明確な方針）
- 統合できるものは統合する
- 変更時は old_files/ に採番バックアップしてから更新
- ユーザーへの返答は常に日本語
- ゲーム操作と実 PC 操作の意味を一致させる（最重要設計原則）
