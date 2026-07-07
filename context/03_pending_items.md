# 未完了・未確定の項目

更新日: 2026-07-07

---

## 未着手（実装前に必要）

### 環境構築
- [ ] Nuxt プロジェクト作成（`pnpm create nuxt@latest frontend`）
- [ ] FastAPI プロジェクト作成（スケルトンは `docs/環境構築手順.md` § 3-4。2026-07-06 Django から変更）
- [ ] `.env.example` 作成
- [ ] API 疎通確認用の最小エンドポイント

### Backend
- [ ] 認証 API 実装（login / refresh / me。PyJWT + passlib）
- [ ] Mission API 実装（一覧 / 詳細。complete API は廃止 — クリアは git push 時にサーバー内部で記録）
- [ ] state API 実装（取得のみ。更新 API は廃止 — 書き込みは WS evaluator のみ。2026-07-06 改訂）
- [ ] WebSocket エンドポイント実装（auth/hello/resume/exec/result/complete フレーム。Pydantic モデル）
- [ ] evaluator 実装（allowlist判定 → コマンド実行 → state更新）
- [ ] 仮想FS モデル / JSON保存
- [ ] 疑似Git（commits 配列 / セーブ選択 / push判定）
- [ ] Mission 判定ロジック（正規表現評価）

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

### Mission4〜20 の詳細化（実装時）
- 概要は確定済み（`docs/Mission参照ファイル.md` § 5）。各 Mission の `expected_script_patterns` 詳細正規表現・初期FS・ヒント3段階は実装時に確定する（Mission2/3 と同じ運用）
- Mission の実施順序は入れ替え可能（Mission20 のみ最終章固定）

### ゲーム機能 9〜12 の未定項目（2026-07-07 採用に伴う）
- やらかし体験室の解放トリガー（案: denylist コマンドを初めて打って拒否された直後に相棒が誘う。未確定）
- ご褒美コマンド（cowsay/figlet）の隠し実績の条件（案: 隠しファイル収集数と連動。未確定）
- Mission1〜3 の現場実習カード文面（実装時確定。Mission4〜20 も同様）

### SSH 接続先の未定項目
- `ghost.example`（Mission11 用）の初期ディレクトリと内部FSは未定 → Mission11 実装時に確定
- `corp_server` と `archive_node` は Mission 未割当のまま予約（Phase3 以降の拡張用）

### ~~Mission4/5 の詳細~~（解消: 2026-07-06）
- Phase2 拡張採用により Mission4〜20 として概要確定（`docs/Mission参照ファイル.md` § 5）

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
