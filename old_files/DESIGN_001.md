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
├ GameTerminal.vue          … xterm.js ラッパ。WS 送受信。emit: command
├ SaveSelectModal.vue       … 再ログイン時の commit（セーブ）一覧選択
├ ClearEffect.vue           … "Mission Complete!" 演出 + 次 Mission 導線
└ RankUpEffect.vue          … ランクアップ演出（Phase2: 辞令 + 新コマンド解放）
```

- 状態管理: mission state（current_path / remote_mode / git_state / mission_flags）は WS 返却の `state` を単一ソースとして store に反映。フロントで独自に FS を推測しない
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
| Notebook（メモ帳）パネル | 未採用。導入する場合は Phase2 で別途確定（state 復元対象外の懸念があるため） |
| 素の `<div>` ターミナル | xterm.js を使用（確定スタック） |
| ヘッダー「ミッション1：Edit businesscard.txt」 | 表記は「Mission1: Edit Business Card」+ 日本語副題の 2 段構成を推奨 |

---

## 9. アクセシビリティ・操作

- ターミナルへのフォーカスを最優先。画面クリックでターミナル入力へ復帰
- キー操作（Phase2 確定分）: Tab 補完 / `↑↓` 履歴 / `Ctrl+R` 逆検索 / `Ctrl+C` 中断 / `Ctrl+L` クリア
- 緑文字 on 黒はコントラスト良好だが、`text-gray-400`（未解放）は装飾でなく `🔒` 等の記号併用で状態を伝える
- フェード中もターミナル入力は受け付ける（演出でプレイヤーを待たせない）
