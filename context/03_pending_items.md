# 未完了・未確定の項目

更新日: 2026-08-12（バックエンド Phase2 完了 + フロントエンド実バックエンド接続 完了。Mission1〜3 がブラウザで通しプレイ可能）

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

**Part5 永続統合ワールド化 P3-01〜P3-03（2026-08-16 完了）の残タスク**（追加のみ。evaluator/API/WS は引き続き Mission 別 `MissionState` を読み書きしている）:
- [ ] `missionstate` テーブルの drop（P3-01 の Alembic リビジョンでは行っていない。API/WS 層を `PlayerState` に切り替えるカットオーバー＝P3-10/P3-11 完了後に別リビジョンとして実施）
- [x] `env_vars` のユーザー別 dict 化に伴う evaluator 側の追随（**P3-04c として P3-10 から前倒しで実施、2026-08-16 完了**。新規 `app/evaluator/env.py` の `env_for(state)` がフラット/ユーザー別の両形状を吸収し、engine の `_expand_env_vars`/PATH解決/`$?`、commands の cd/export/unset/printenv、judge の Mission21 判定を経由させた。`git_ops.py` のスナップショットは丸ごと deepcopy なので両形状で動作し変更不要。前倒しの理由: これが無いと統合ワールド state で `engine.evaluate()` 経由のコマンドが 1 つも動かず、P3-05 以降を実際に動かして検証できないため）
- [ ] P3-03 の移設（`/root` 直下の裸置きファイル → Mission 専用サブディレクトリ）に伴う旧パス参照の追随。**統合ワールドでのみパスが変わり、Mission 別 FS は現役のため今は変更しない**（P3-08/P3-12/P3-13 で対応。一覧は `app/content/missions.py` の `_RELOCATIONS` 直下のコメントにも記載）:
  - `app/evaluator/judge.py` `_MISSION10_ORIGINAL_PATH`/`_MISSION10_SUBMITTED_PATH` → `/root/will_office/`
  - `app/evaluator/judge.py` `_MISSION19_SCRIPT_PATH`（プレイヤーが作る `patrol.sh` の置き場）→ `/root/precinct_desk/patrol.sh`
  - `app/content/missions.py` `_MISSION15_HISTORY`（情報屋の履歴）→ `/root/informant_trail/journal.log`
- [ ] Mission5 の `/root/vault/inner` が統合ワールドでは空部屋になる（`case_file.sh` を動的生成へ移す方針＝Part5 の確定事項により、そこにあった解錠ギミックが廃止されたため）。`locked_evidence.txt` の本文が `inner` を指しているので、部屋に何を置くか（あるいは本文を書き換えるか）のコンテンツ判断が要る。P3-04 の `case_file.sh` 動的生成とあわせて決める

**疑似ターミナルの使用感（UX-01a, 2026-09-12 実施。446 tests green）**: 普段 CUI を使う人が不自然に思う挙動を実 bash に合わせた。
`>file`/`>>file` の空白なし表記 / `&&` `||` `;` は黙って一部実行せず `Error: invalid input`（引用符内は対象外。本実装は設計指示書 § 8 構文レベル外のため見送り）/ `~`・`~/...` 展開（`~user` は非対応）/ `cd -`（`OLDPWD`）/ `history` が `command_log` を bash 書式で表示。詳細は `docs/バックエンド_コマンド機能仕様.md`「共通構文」「cd」「history」、テストは `tests/test_shell_idioms.py`。
- [ ] 残る意味不一致（BUG-HUNT-01）: `find` が常に絶対パスを出力する（Mission2 導線とセットで判断）/ `&&` `;` の本実装 / `git commit -m"msg"`（クォート隣接）/ Tab 補完（`complete` フレーム未実装）

**フロントエンド 実バックエンド接続 完了（2026-08-12）**: FE-01〜FE-08 を1 task = 1 commit + push で完遂。noir-client は実 noir-api に接続済みで、ログイン → Mission1〜3 の通しプレイがブラウザで動く（下記 Frontend / テスト節参照）。残る主な未着手は「Phase2 拡張の実装タスク」節に残る細目（awk 定義・仮想ユーザーテーブル・アーカイブ入れ子表現の一般化・cowsay/figlet 等のご褒美コマンド・ゲーム機能9〜12 の UI 等）と、下記の場所別画像アセット・Tab補完・ライン編集の残りキーマップ。

### Frontend（実バックエンド接続。2026-08-11 着手。詳細は `context/04_task_backlog.md` Part2 FE-01〜08）
- [x] 認証UI（ログイン画面 `app/pages/login.vue` + `useAuth.ts` composable。JWT を localStorage 保存 + 未ログインガード `middleware/auth.ts`。FE-01）
- [x] Nuxt ルーティング（/missions, /missions/{id}）。Mission 一覧 `app/pages/missions/index.vue` + 詳細/開始導線 `app/pages/missions/[id].vue`（ターミナル本体は FE-03/04 で追加配線）。FE-02
- [x] UI 3領域レイアウト（`app/pages/missions/[id].vue` で MissionHeader/SceneOverlay/CommandPanel/TerminalView を実配線。FE-04）
- [x] ターミナル UI 実装（自作 `TerminalView.vue`。xterm.js は不採用 — 2026-07-06 改訂。実 WS state（Pinia store）に接続し、`app/pages/index.vue` のモック evaluator は撤去。FE-04。Mission1 を cat→echo→sh case_file.sh→git add/commit/push までブラウザ（Playwright 実 Chromium）で通しプレイ確認済み・console error 0 件）
- [x] WebSocket 接続基盤（初回 `auth` フレーム認証 + `hello`/`exec`/`result`/`event`/`resume` プロトコル。設計指示書 § 7。`app/composables/useTerminalSocket.ts` + Pinia store `app/stores/terminal.ts`（DESIGN.md § 10-1 の単方向データフロー）+ 型定義 `app/types/ws.ts`。指数バックオフ再接続対応。FE-03。まだどのページからも呼ばれていない状態で Python の websockets クライアントでプロトコルの往復を検証済み — UI 配線は FE-04）
- [x] コマンド一覧パネル（`app/utils/commandCatalog.ts` で Mission 詳細 API の `allowed_commands` → `CommandPanel`/`CommandDetail` へ変換。`git` は git status/add/commit/push の4件に展開して highlight 表示。ヘッダーの探偵ランクも allowed_commands から算出。FE-05）
- [x] 場面画像のカレントディレクトリ紐付け（`app/pages/missions/[id].vue` で WS state（Pinia store の `currentPath`/`remoteMode`/`sshHost`）から `host:パス接頭辞` の最長一致解決 → `SceneOverlay` へ。`cd`/`ssh`/`exit` の画像切替は `SceneOverlay` 側の 0.8s クロスフェードが自動追従。FE-06。ssh amusement_park:/gate 用画像は未制作のためプレースホルダ表示 — 下記「場所別画像アセットの制作」で追跡）
- [ ] 場所別画像アセットの制作（現状は `office.png` 1 枚のみ。※素材制作待ち）。**必要な画像の一覧は `moc/images/NEEDED_IMAGES.md`**（2026-08-17 作成。Part5 統合ワールドの区画 + ssh 接続先から算出。サイズ 1536×1024・画風基準・`SCENE_IMAGES` への登録方法・優先度 A〜D 付き）。解決は前方一致の最長一致なので、`office:/root` があれば全部揃わなくても破綻しない
- [x] セーブ選択 UI（再ログイン時の commit 一覧。`SaveSelectModal.vue` を実データに接続し、hello フレームの `commits` に1件以上あれば全画面オーバーレイで表示。「このセーブで再開」で `resume` フレーム送信、「最初から」は現在の state のまま続行。FE-07。commit してから再接続 → セーブ選択 → 復元をブラウザで確認済み）
- [ ] Tab 補完（設計指示書 § 7 の `complete`/`completions` フレームが `noir-api/app/ws/terminal.py` に未実装のためフロント側も未着手。バックエンド側の実装が前提）
- [x] `TerminalView.vue` のキーマップ（UX-01b, 2026-09-12）: `↑↓` 履歴（ignoredups・上限 500・draft 退避）/ `Ctrl+C`（入力破棄 + `^C` 行）/ `Ctrl+L` と `clear` コマンド（scrollback 消去。store の `clearScrollback()`）/ `Ctrl+A`・`E`・`U`・`W`。DESIGN.md § 10-2。**ブラウザでの目視確認は未実施**（typecheck/build のみ）。残り: `Ctrl+R` 逆検索・Tab 補完（下記）
- [ ] `RankUpEffect.vue` の実配線（`event: rank_up` 受信は `useTerminalSocket` でシステム行表示のみ。演出コンポーネントとしては未接続）

### テスト
- [x] Mission1〜3 のE2Eシナリオ（FE-08。Playwright 経由の実 Chromium ブラウザで、ログイン → Mission1（cat/echo/sh case_file.sh/git add・commit・push）→ Mission2（find/grep/sh/git）→ Mission3（ssh amusement_park/exit を含む）まで通しプレイし、3件とも "Mission Complete!" とコンソールエラー 0 件を確認。加えてセーブ選択（再訪 → resume/start-over 両方）も確認。自動テストコード自体はリポジトリに未追加— 手動 E2E 確認の記録として残す。恒久的な自動化が必要なら Vitest/Playwright を `noir-client` に導入する別タスクとして検討）
- [ ] コマンドカテゴリごとの正常系/異常系（Vitest 等の自動テストが `noir-client` に未導入。上記 E2E は手動確認）
- [ ] 再ログイン時の state 復元テスト（FE-07 で手動確認済みだが自動テスト化は未）

---

## 未確定（設計上の残課題）

### Phase2 拡張の実装タスク（2026-07-06 採用確定・2026-07-20 時点の残り）
- [ ] `docs/バックエンド_コマンド機能仕様.md` に Phase2 新コマンド（約50個）の定義を追加（実装着手時に段階的に）※egrep/fgrep は 2026-07-07 に定義済み（grep の alias）
- [x] evaluator 構文対応（glob/引用符/`2>`/`$?`/変数/if・for）・仮想プロセス/ユーザー/cronテーブル・アーカイブ入れ子表現・FHS版仮想FSマップは Phase2 P2-01〜P2-19 で実装済み（Backend 節参照）
- [ ] フロントエンド: Tab 補完 / `Ctrl+R`（`↑↓` 履歴・`Ctrl+C`・`Ctrl+L` は UX-01b で実装済み。Frontend 節参照）
- [ ] ゲーム機能 12 項目（設計指示書 § 11。Phase2 の 8 + 2026-07-07 追加の 4）の UI 設計
- [ ] やらかし体験室の隔離 state 実装（使い捨て state / 本編 evaluator は denylist 不変）
- [ ] エラー図鑑の翻訳文データ作成（§ 12 エラー一覧と 1:1 対応）
- [ ] 現場実習カードの文面作成（安全コマンド限定 + macOS/Windows のターミナルの開き方）
- [ ] `cowsay` / `figlet` の evaluator 定義（バックエンド_コマンド機能仕様への追加。隠し実績の解放条件設計も）

### 解消済みの旧課題
- Mission4〜22 の詳細化・/proc・環境変数(PATH)・SSH接続先(ghost.example)・Mission4/5の詳細・cp/mvコマンド・case_file.shの中身は
  いずれも 2026-07-20 までに実装・確定済み（`noir-api/app/content/missions.py` 等が正）。経緯は `01_decisions_log.md` 参照
- ヒント3段階: Mission1〜3 は 2026-08-12 HINT-01 で仮実装済み（`MissionDef.hints` → API `MissionDetail.hints` →
  `noir-client/app/pages/missions/[id].vue` の簡易ボタンUI）。Mission4〜22 は文言未確定のまま（`hints` 空配列）。
  相棒キャラの見た目・表示トリガー等の UI/UX は次回設計セッションで詰める（`context/04_task_backlog.md` Part 3 参照）

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
