# docs/design-system — CLI_Noir デザインシステム（local ミラー）

claude.ai/design の **「CLI_Noir Design System」** プロジェクトの **local ミラー**。
プロジェクトのルート構造を複製している。

> **デザインの正は ClaudeDesign プロジェクト側**（このディレクトリはそれを落とし込んだ複製）。
> 開発仕様（2026-07-07 確定）: **デザイン変更は ClaudeDesign で行い、変更を local へ落とし込む**。
> 詳細は末尾「更新フロー」を参照。

## アートディレクション（2026-07-07 更新）

ノワール基調に 3 つの意匠レイヤーを重ねた作り込みへ更新済み:

- **スチームパンク金属**（brass / copper）… パネルのベゼル・トリム・ランクチップ・封蝋
- **サイバーパンク・ネオングロー**（cyan / indigo / red / brass glow + scanlines）… ターミナル/パネルのフォーカス・ホバー
- **60 年代フレンチ映画ポスター**（poster palette + Jost/Josefin）… ミッションヘッダー帯・シーン・クリア演出

トークンにこれらの色・影・書体（`--brass-*` / `--poster-*` / `--glow-*` / `--bezel-brass` / `--hairline-scan` / `--font-hero` / `--font-accent`）を追加済み。

## 構成

```
docs/design-system/
├ styles.css                        … トークンを束ねるエントリ
├ tokens/
│  ├ fonts.css                      … Webfont（JetBrains Mono / Zilla Slab / Inter / Jost / Josefin Sans、現状 Google Fonts）
│  ├ colors.css                     … 配色（gray / indigo / phosphor / sepia / brass / copper / poster + semantic alias）
│  ├ typography.css                 … 書体（hero=Jost / display=Zilla Slab / ui=Inter / mono=JetBrains / accent=Josefin）
│  └ spacing.css                    … 余白・角丸・影・glow・bezel・レイアウト幅
├ components/<name>/<Name>.jsx      … 各コンポーネントの実ソース（React。移植元＝正）
└ ui_kits/detective-terminal/index.html … 全画面の組み上げ（自己完結・最良の視覚リファレンス）
```

- コンポーネントの実体は **`<Name>.jsx`**（ClaudeDesign が生成する React 実装）。noir-client の Vue SFC はこれを移植したもの。
- `ui_kits/detective-terminal/index.html` は `@import "../../styles.css"` のみで動く**自己完結の全画面デモ**（ヘッダー帯・シーン・3 段ヒント・コマンドレール・疑似ターミナル）。ブラウザで直接開ける。
- ClaudeDesign 側の `index.html`（各コンポーネント）は `_ds_bundle.js`（アプリ生成物）に依存する demo ハーネスのため、**ミラーには含めない**（`.jsx` を正とする）。

## コンポーネント ⇔ 実装対応（`docs/DESIGN.md § 5` 準拠）

| グループ | .jsx（正） | noir-client の Vue SFC | 対応する DESIGN.md |
|---|---|---|---|
| Terminal | `terminal-view` / `prompt` | `TerminalView.vue` / `PromptLabel.vue` | § 10 / § 4 |
| Panels | `command-panel` / `command-detail` | `CommandPanel.vue` / `CommandDetail.vue` | § 5 |
| Scene | `mission-header` / `scene-overlay` | `MissionHeader.vue` / `SceneOverlay.vue` | § 3 / § 5 |
| Feedback | `clear-effect` / `rank-up-effect` / `save-select-modal` | `ClearEffect.vue` / `RankUpEffect.vue` / `SaveSelectModal.vue` | § 6 / § 5 |
| Primitives | `button` | `NoirButton.vue` | § 2 |

### prop 名の対応メモ（React → Vue で踏襲）

- MissionHeader: `tag` / `title` / `subtitle` / `rank`（旧 `index` は廃止）
- CommandPanel: `commands[{ name, state, badge }]`（旧 `level` → `badge`）、状態アイコン `›`(unlocked) / `★`(highlight) / `☢`(locked)
- CommandDetail: `name` / `syntax` / `real` / `inGame`（旧 `game` → `inGame`）
- Prompt: `user` / `host` / `path` / `hostType`（`local`/`remote`/`su`、旧 `remote:boolean` から変更）/ `caret`
- ClearEffect: `stamp` / `sub` / `ctaLabel`（旧 `title` → `stamp`）
- RankUpEffect: `eyebrow` / `title` / `body` / `from` / `to` / `unlocks`
- SaveSelectModal: `saves[{ hash, message, when, latest }]`（旧 `title` → `message`）
- SceneOverlay: `image`（シーン地。場面ごと差し替え）/ `fading` / `caption` / `badge` / `cardTitle` / `cardBody`。`image` を第一級要素として `object-fit: cover` で敷き、ポスター調のキャプション帯・バッジ・イベントカードはその上にオーバーレイ。写真シーンには可読性スクリムを自動付与。`image` 変化で 0.8s クロスフェード（ssh/exit の local⇄remote 遷移）。`image` 空はポスターグラデにフォールバック。

> **シーンのメイン画像は第一級の仕様**（2026-07-07 追加）。ClaudeDesign の SceneOverlay が `image`/`fading` を持つよう更新済み。
> かつて Nuxt 固有だった `SceneView.vue` はこの更新で役割を SceneOverlay に統合し**廃止**した。
> 場面→画像のマッピング（Mission1-3=自室 `office.png` / ssh 先=現地絵）はゲーム状態＝ページ側（`pages/index.vue` の `sceneImages`）が持つ。

## 元仕様との整合

- 表示テキストは `docs/DESIGN.md § 8`（moc と確定仕様の差分）に合わせている
  （日本語ラベル、`Error: command not allowed`、git は add→commit→push の順序を warn で表現）。
- フォントは `tokens/fonts.css` で Google Fonts をロード中。実 woff2 セルフホストへ切替時は
  このファイルの `@import` を差し替えれば全コンポーネントへ波及する（`DESIGN.md § 10-6`）。
- `_ds_manifest.json` / `_ds_bundle.js` などアプリ生成物はコミットしない（プロジェクト側で自動生成）。

## 更新フロー（開発仕様・2026-07-07 確定）

**同期方向: ClaudeDesign プロジェクト（＝正）→ local。逆流させない。**

1. **デザイン変更は ClaudeDesign で行う** — claude.ai/design の「CLI_Noir Design System」で
   トークン・コンポーネントの見た目を変更する。
2. **変更を local に落とし込む**（Claude Code が `DesignSync` で pull する）:
   1. `DesignSync list_files` / `get_file` でプロジェクトの最新を取得
   2. `docs/design-system/`（このミラー）へ反映（tokens/*.css + components/*.jsx + ui_kits/）
   3. 差分に合わせて **`noir-client/` の実装を更新**
      （トークンは `noir-client/app/assets/css/tokens/` にもコピーがある。両方を揃える／
      該当コンポーネント SFC `noir-client/app/components/*.vue` を追随させる）
3. commit & push（local を最新化して GitHub へ）

### やってはいけないこと

- **local 側を直接いじって design プロジェクトへ push しない**（source は ClaudeDesign）。
  急ぎで local を触った場合も、正は ClaudeDesign 側に反映してから改めて落とす。
- `_ds_manifest.json` / `_ds_bundle.js` などアプリ生成物は pull 対象外（プロジェクト側で自動生成）。

### local の対応先（落とし込み先の二層）

| ClaudeDesign 側 | local ミラー | Nuxt 実装 |
|---|---|---|
| `tokens/*.css`, `styles.css` | `docs/design-system/tokens/`, `styles.css` | `noir-client/app/assets/css/tokens/`, `main.css` |
| `components/<name>/<Name>.jsx` | `docs/design-system/components/<name>/<Name>.jsx` | `noir-client/app/components/*.vue` |
| `ui_kits/detective-terminal/` | `docs/design-system/ui_kits/detective-terminal/` | `noir-client/app/pages/index.vue`（レイアウト参照） |
