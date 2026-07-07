# DESIGN.md — CLI_Noir UI/ビジュアルデザイン仕様

`moc/index.html` と `moc/images/mission1.png` を基準に、Nuxt 実装のためのビジュアル・UX 仕様を定義する。
機能仕様は `設計指示書.md`（§ 3 UI/UX ほか）が上位の正。本ファイルは「どう見せるか・どう作るか」を担当する。

---

## 1. アートディレクション

### コンセプト: 「ノワール探偵事務所 × 生きたターミナル」

- 世界観はモノクロ〜セピアの**銅版画/ペン画風イラスト**（`mission1.png` の画風を全 Mission の基準とする）
- 画面下 1/3 は本物のターミナル（黒地・緑文字）。**上の「物語の世界」と下の「操作の世界」が常に同居**し、コマンドを打つと物語側が反応する、が体験の核
- 光源は少なく（デスクランプ、ブラインド越しの窓光）、陰影で「事件の匂い」を出す

### 背景画像の制作ルール（`mission{n}.png`）

| 項目 | 仕様 |
|---|---|
| 画風 | モノクロ〜セピアの手描き線画調（mission1.png と統一） |
| アスペクト比 | 3:2 目安（`bg-cover bg-center` で全面表示するため周縁は切れてよい） |
| 構図 | 中央〜やや左に焦点（右 320px はコマンドパネルに隠れるため重要要素を置かない） |
| 明度 | 暗め。上に載る白文字（text-overlay）が読める濃度にする |
| 場所の対応 | ミッションの仮想FSと矛盾しない絵にする（机がある部屋なら FS に `desk/` がある） |
| remote 用 | ssh 接続先ごとに別画像（遊園地など）。local と明確に空気感を変える |

---

## 2. カラーパレット（Tailwind トークン）

moc で使用されている実トークンを基準に定義する。

### ベース

| 用途 | トークン | 備考 |
|---|---|---|
| アプリ背景 | `bg-gray-900` | 全体の地色 |
| 上部シーン領域の地 | `bg-gray-700` | 背景画像ロード前のフォールバック |
| パネル地 | `bg-gray-800` / `bg-gray-700` | 右パネル・カード類 |
| ターミナル地 | `bg-black` | 下部 1/3 |
| 本文テキスト | `text-white` / `text-gray-200` | |

### アクセント（インディゴ = 探偵の署名色）

| 用途 | トークン |
|---|---|
| ヘッダー帯 | `bg-indigo-800` |
| 主ボタン | `bg-indigo-600` / hover `bg-indigo-500` |
| 強調枠線 | `border-indigo-500` |
| 見出しテキスト | `text-indigo-200` |

### ターミナル・セマンティック

| 用途 | トークン |
|---|---|
| コマンド出力 | `text-green-400` |
| 入力中テキスト | `text-green-300` |
| 重要コマンド（git 系・ミッション鍵） | `text-yellow-300 font-bold` |
| 未解放コマンド（グレーアウト） | `text-gray-400` |
| エラー出力（`Error:`） | `text-red-400` |
| 警告出力（`Warning:`） | `text-yellow-300` |
| クリア演出テキスト | `text-emerald-300` |

### オーバーレイ

背景画像上のテキストは必ず下記の帯を敷く（moc の `.text-overlay` を踏襲）:

```css
background: rgba(0, 0, 0, 0.5);
padding: 0.5rem 1rem;
border-radius: 0.35rem;
```

---

## 3. レイアウト

### 画面構造（moc 準拠・設計指示書 § 3 の 3 領域）

```
┌────────────────────────────────────────────┐
│ ヘッダー帯: ミッション番号・タイトル (bg-indigo-800)      │
├───────────────────────────┬────────────────┤
│ シーン領域 (flex-1, relative)      │ 右パネル (w-80)  │
│  - 背景画像 (absolute inset-0)     │  - 使用可能コマンド │
│  - 説明テキスト (text-overlay)     │  - コマンド説明     │
│  - イベントカード (中央モーダル風)   │    (選択時フェード)  │
├───────────────────────────┴────────────────┤
│ ターミナル (h-1/3, bg-black, font-mono text-sm)         │
│  - 出力エリア (flex-1, overflow-y-auto, 自動スクロール)   │
│  - 入力行 (border-t, プロンプト付き input)               │
└────────────────────────────────────────────┘
```

- ルート: `flex flex-col h-screen overflow-hidden`（ページ自体はスクロールさせない）
- ターミナル出力は追記のたびに `scrollTop = scrollHeight` で最下部へ（moc の実装を踏襲）

### レスポンシブ

| 幅 | 挙動 |
|---|---|
| lg 以上 | 上記 3 領域。コマンド一覧はパネル内 1 列 |
| md | 右パネルを `w-64` に縮小、コマンド一覧 2〜3 列グリッド |
| sm 以下 | 右パネルをドロワー化（ヘッダーのボタンで開閉）。ターミナルは `h-2/5` に拡大（スマホでは入力が主役） |

---

## 4. タイポグラフィ

| 対象 | 指定 |
|---|---|
| UI 全般（日本語） | システム sans（`font-sans`）。UI ラベルは日本語統一（設計指示書 § 1） |
| ターミナル | `font-mono text-sm`。等幅必須（`ls` の桁揃え・`ls -l` の権限表示が崩れないこと） |
| ヘッダー | `text-2xl font-bold` |
| シーン内説明 | `text-xl font-semibold` + text-overlay |

プロンプト表記は状態を反映する（学習要素を兼ねる）:

```
local:  detective@office:/root/desk $
remote: detective@amusement_park:/gate $
su 中:  barman@office:/bar $
```

---

## 5. コンポーネント分解（Nuxt 実装ガイド）

```
pages/
├ missions/index.vue        … Mission 一覧 + セーブ選択
└ missions/[id].vue         … ゲーム画面（下記を組み立てる）

components/
├ MissionHeader.vue         … タイトル帯。props: mission
├ SceneView.vue             … 背景画像 + フェード制御。props: imageUrl, fading
├ SceneOverlay.vue          … 説明テキスト/イベントカードのスロット
├ CommandPanel.vue          … 使用可能コマンド一覧。props: commands(解放状態付き)
│                             クリックで CommandDetail をフェード表示
├ CommandDetail.vue         … コマンド説明（実PCでの意味 + ゲーム内の意味を並記）
├ TerminalView.vue          … 自作ターミナル（構造化行レンダリング + ライン入力。WS 送受信。emit: command）
├ SaveSelectModal.vue       … 再ログイン時の commit（セーブ）一覧選択
├ ClearEffect.vue           … "Mission Complete!" 演出 + 次 Mission 導線
└ RankUpEffect.vue          … ランクアップ演出（Phase2: 辞令 + 新コマンド解放）
```

- `TerminalView.vue` の詳細な実装仕様（品質基準・コードの方向性）は **§ 10** を正とする
- 状態管理: mission state（current_path / remote_mode / git_state / mission_flags）は WS 返却の `state` を単一ソースとして store（Pinia）に反映。フロントで独自に FS を推測しない
- コマンド一覧の解放状態はランク（Level 1〜11）に応じてグレーアウト表示（moc の `grep (later)` 表現を踏襲し、「次に何が来るか」を予告する）

---

## 6. モーション仕様

基準トランジション（moc 踏襲): `transition: opacity 0.8s ease-in-out`

| 場面 | 演出 |
|---|---|
| ssh 接続 / exit | 背景をフェードアウト → 画像差し替え → フェードイン（0.8s × 2）。ターミナルは操作可能のまま |
| コマンド説明の表示 | パネル内フェードイン（0.3s 程度。頻繁に起きるため短く） |
| Mission クリア | 背景フェード → "Mission Complete!"（emerald）→ 次 Mission 導線。git push 成功の返却を受けてから発火 |
| ランクアップ（Phase2） | クリア演出後に辞令カード表示 → 右パネルの新コマンドが点灯していく |
| エラー表示 | 点滅・シェイクはしない（ミスを責めない。赤テキスト表示のみ） |
| タイムアタック（Phase2） | 残り時間は演出のみ（実際の時間切れ失敗は作らない。設計指示書 § 11） |

---

## 7. 画面一覧

| ルート | 内容 |
|---|---|
| `/missions` | Mission カード一覧（open / locked / cleared）。クリア済みには「リプレイ台帳」導線（Phase2）。再ログイン時はセーブ選択モーダルを重ねる |
| `/missions/{id}` | ゲーム画面（§ 3 のレイアウト） |

---

## 8. moc と確定仕様の差分（実装時に moc をそのまま写さないこと）

moc は初期スケッチのため、以下は**確定仕様が優先**される。

| moc の記述 | 確定仕様 |
|---|---|
| `vi / open businesscard.txt` でカード編集 | 編集は `echo "..." > file`（Mission1 確定仕様）。vi は Phase3 候補。GUI 編集カードは廃止（CLI 操作が主役） |
| `git status` → `git push` のみで成功 | `add（必須）→ commit → push` の順序制約あり（設計指示書 § 10） |
| `git status` 出力 "On branch main / nothing to commit…" | § 10 の 4 状態表（`Nothing to commit` / `Changes staged` / `No commits yet` / `Ready to push`）に従う |
| `command not found` | `Error: command not allowed` ほか § 12 のエラー文言に従う |
| UI テキストが英語（"Available Commands" 等） | UI ラベルは日本語統一（「使用可能コマンド」等）。ファイル名・コマンドは英語のまま |
| Notebook（メモ帳）パネル | 未採用。導入する場合は Phase2 で別途確定（state 復元対象外の懸念があるため) |
| 素の `<div>` ターミナル | **方式としては moc が正しい**。自作 `TerminalView.vue` として正式採用（WS の style 付き行をそのまま DOM 描画 + ライン入力）。xterm.js は不採用 — 行単位入出力のみのゲームでは過剰で、IME・演出の面で不利（設計指示書 § 2。Phase3 の vi 導入時に再評価） |
| ヘッダー「ミッション1：Edit businesscard.txt」 | 表記は「Mission1: Edit Business Card」+ 日本語副題の 2 段構成を推奨 |

---

## 9. アクセシビリティ・操作

- ターミナルへのフォーカスを最優先。画面クリックでターミナル入力へ復帰
- キー操作（Phase2 確定分）: Tab 補完 / `↑↓` 履歴 / `Ctrl+R` 逆検索 / `Ctrl+C` 中断 / `Ctrl+L` クリア
- 緑文字 on 黒はコントラスト良好だが、`text-gray-400`（未解放）は装飾でなく `🔒` 等の記号併用で状態を伝える
- フェード中もターミナル入力は受け付ける（演出でプレイヤーを待たせない）

---

## 10. TerminalView 実装仕様（品質基準・コードの方向性）

疑似ターミナルはこのゲームの主役 UI。「本物のターミナルと同じ手触り」が品質基準。
実装 Agent はこの節をコードの正として従うこと。

### 10-1. アーキテクチャ（単方向データフロー）

```
useTerminalSocket (WS 接続・再接続・フレーム処理)
        ↓ result/stream/event フレーム
Pinia store (state / scrollback が唯一の真実)
        ↓ props/computed
TerminalView.vue（表示専用）
        ↑ emit("command", line)
useLineEditor / useHistory / useCompletion (入力系 composables)
```

- composable 分割: `useTerminalSocket` / `useLineEditor`（入力バッファ・カーソル）/ `useHistory`（履歴 + Ctrl+R）/ `useCompletion`（Tab 補完）/ `useScrollback`（行バッファ管理）
- 行モデル: `{ id: number, text: string, style: Style, source: "input" | "output" | "system" }`。`id` は連番（`TransitionGroup` のキーと自動スクロール判定に使う）
- **フロントは FS・コマンドの意味を一切知らない**。表示と入力だけを担当し、解釈はすべてサーバー（この分離を崩すコードはレビューで弾く）

### 10-2. 入力（ライン編集）の品質基準

- 入力は最下行に固定した native `<input>` 1個。透明背景・緑文字・等幅でターミナルの入力行に見せる
- **IME 対応（必須）**: `compositionstart`〜`compositionend` の間は keydown ハンドラを全て無効化する。特に**変換確定の Enter で送信してはならない**（`isComposing` / `keyCode 229` を確認）
- キーマップ（実 bash 準拠。それ自体が学習になる）:

| キー | 挙動 |
|---|---|
| `Enter` | 送信。入力行はエコーとして scrollback に `$ <cmd>` を積む |
| `↑` / `↓` | 履歴移動。編集中の未送信バッファは退避し、最下端で復元 |
| `Tab` | 補完（10-4）。候補1件=即補完、複数=2度目の Tab で候補一覧を出力領域に表示 |
| `Ctrl+C` | 入力破棄。`^C` を表示して新プロンプト（実行中 stream があれば中断フレーム送信） |
| `Ctrl+L` | 画面クリア（`clear` と同じ。scrollback を空に) |
| `Ctrl+R` | 履歴逆検索。プロンプトを `(reverse-i-search)'':` 表示に切替 |
| `Ctrl+A` / `Ctrl+E` | 行頭 / 行末へ（native input のデフォルトに任せず明示実装） |
| `Ctrl+U` / `Ctrl+W` | 行削除 / 直前ワード削除 |
| `Home` / `End` | 行頭 / 行末 |

- ペースト: 複数行ペーストは**先頭行のみ**入力欄に入れ、`-- multi-line paste truncated --` をシステム行で表示（誤爆実行の防止）
- フォーカス: 画面クリックで input へ復帰。ただし**テキスト選択中（コピー操作中）は奪わない**（`window.getSelection()` を確認）

### 10-3. 出力レンダリングの品質基準

- scrollback 上限 2,000 行（超過分は先頭から破棄）。加えて**サーバー側で 1 応答 1,000 行に切り詰め**、`-- output truncated (N lines) --` を末尾に付ける（設計指示書 § 7）。フロントに仮想スクロールは導入しない（上限管理で十分）
- 自動スクロール: **最下部にいる時のみ**追従。ユーザーが上へスクロール中は追従を止め、右下に「↓ 新しい出力」ピルを表示（クリックで最下部へ）
- タイプライター演出（1文字ずつ表示）は**使わない**（プレイヤーを待たせない）。行単位の軽いフェードイン（50ms stagger、`prefers-reduced-motion` で無効化）まで
- テキスト選択・コピーは常に可能（`user-select: text`。コンテキストメニューも禁止しない）
- 例外として `stream` フレーム（tail -f 監視）は届いた行を逐次追記（張り込みのライブ感）

### 10-4. Tab 補完のプロトコル

フロントは FS を知らないため、補完は**サーバー問い合わせ**で行う（設計指示書 § 7 の `complete` フレーム）:

```json
// クライアント → サーバー（Tab 押下時のみ。デバウンス不要）
{ "type": "complete", "id": 44, "line": "cat bus", "cursor": 7 }
// サーバー → クライアント
{ "type": "completions", "id": 44, "candidates": ["businesscard.txt"], "replace_from": 4 }
```

- サーバーは current_path・allowlist・解放レベルを踏まえて候補を返す（未解放コマンドは候補に出さない）
- 候補 0 件は無反応（ベル音は Phase2 のサウンド導入時に検討）

### 10-5. プロンプト表示

- `detective@office:/root/desk $` を state から算出。色分け: ユーザー名 = `text-green-300` / ホスト = local `text-gray-300`・remote `text-yellow-300` / パス = `text-indigo-200`
- remote 切替（ssh/exit）・su によるユーザー変化がプロンプトに即時反映されること（現在地の自己確認という学習要素を兼ねる）

### 10-6. フォント・見た目の仕上げ

- 等幅フォント: `JetBrains Mono`（セルフホスト woff2）→ fallback `ui-monospace, Menlo, monospace`。日本語混在行（commit メッセージ等）は `Noto Sans JP` fallback で幅ズレを許容（桁揃えが必要な出力は ASCII のみとサーバー側で保証）
- カーソル: input 標準 caret + `caret-color: theme(green.400)`。ブロックカーソル化は Phase2 の磨き込み項目
- CRT 風演出（グロー）はコンテナに 1 枚のオーバーレイで行う（行ごとの `text-shadow` は禁止 — 大量行で描画が重くなる）

### 10-7. 接続品質

- WS 切断時: `-- connection lost, reconnecting... --`（style=warning）を表示し、指数バックオフ（1s→2s→4s…最大 30s）で再接続。復帰時は `auth`→`hello` で state を再同期し `-- reconnected --` を表示
- 再接続中の入力は受け付けるが送信はキューせず、`Error: not connected` 相当のシステム行を返す（silent drop 禁止）

### 10-8. テスト基準

- `useLineEditor` / `useHistory` / `useCompletion` は Vitest でユニットテスト（純粋ロジックに保つ）
- E2E（Playwright）: Mission1 ハッピーパス + IME 合成入力 + 履歴/補完キー操作 + 切断→再接続
- 性能基準: 1,000 行の一括出力で入力レイテンシ体感劣化なし（キー入力→エコー表示 16ms 以内）
