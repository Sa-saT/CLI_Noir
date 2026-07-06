# docs/design-system — CLI_Noir デザインシステム（local ミラー）

claude.ai/design の **「CLI_Noir Design System」** プロジェクトの **local ミラー**。
プロジェクトのルート構造をそのまま複製している。

> **デザインの正は ClaudeDesign プロジェクト側**（このディレクトリはそれを落とし込んだ複製）。
> 開発仕様（2026-07-07 確定）: **デザイン変更は ClaudeDesign で行い、変更を local へ落とし込む**。
> 詳細は末尾「更新フロー」を参照。

## 構成

```
docs/design-system/
├ styles.css              … トークンを束ねるエントリ（各コンポーネントが @import する）
├ tokens/
│  ├ fonts.css            … Webfont（JetBrains Mono / Zilla Slab / Inter、現状 Google Fonts）
│  ├ colors.css           … 配色トークン（gray / indigo / terminal phosphor / sepia + semantic alias）
│  ├ typography.css       … フォント・タイプスケール・ウェイト
│  └ spacing.css          … 余白・角丸・影・レイアウト幅
└ components/<name>/index.html … コンポーネントのプレビュー（1行目に @dsCard マーカー）
```

各 `components/<name>/index.html` は `@import "../../styles.css"` でトークンを継承する。
`docs/design-system/` = design プロジェクトルート、という対応なので相対パスがそのまま解決する。

## コンポーネント一覧（`docs/DESIGN.md § 5` 準拠）

| グループ | コンポーネント | 対応する DESIGN.md |
|---|---|---|
| Terminal | `terminal-view` / `prompt` | § 10 TerminalView / § 4 プロンプト |
| Panels | `command-panel` / `command-detail` | § 5 CommandPanel / CommandDetail |
| Scene | `mission-header` / `scene-overlay` | § 3 レイアウト / § 5 |
| Feedback | `clear-effect` / `rank-up-effect` / `save-select-modal` | § 6 モーション / § 5 |
| Primitives | `button` | § 2 アクセント |

## 元仕様との整合

- 表示テキストは `docs/DESIGN.md § 8`（moc と確定仕様の差分）に合わせている
  （日本語ラベル、`Error: command not allowed`、git は add→commit→push の順序を warn で表現）。
- フォントは `tokens/fonts.css` で Google Fonts をロード中。実 woff2 セルフホストへ切替時は
  このファイルの `@font-face` を差し替えれば全コンポーネントへ波及する（`DESIGN.md § 10-6`）。
- `_ds_manifest.json` / `_ds_bundle.js` などアプリ生成物はコミットしない（プロジェクト側で自動生成）。

## 更新フロー（開発仕様・2026-07-07 確定）

**同期方向: ClaudeDesign プロジェクト（＝正）→ local。逆流させない。**

1. **デザイン変更は ClaudeDesign で行う** — claude.ai/design の「CLI_Noir Design System」で
   トークン・コンポーネントの見た目を変更する。
2. **変更を local に落とし込む**（Claude Code が `DesignSync` で pull する）:
   1. `DesignSync list_files` / `get_file` でプロジェクトの最新を取得
   2. `docs/design-system/`（このミラー）へ反映
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
| `tokens/*.css`, `styles.css` | `docs/design-system/` | `noir-client/app/assets/css/tokens/`, `main.css` |
| `components/<name>/index.html` | `docs/design-system/components/` | `noir-client/app/components/*.vue` |
