# docs/design-system — CLI_Noir デザインシステム（ソース）

claude.ai/design の **「CLI_Noir Design System」** プロジェクト（GitHub 連携: `Sa-saT/CLI_Noir`）の
ソース・オブ・トゥルース。プロジェクトのルート構造をそのままミラーしている。

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

## 更新フロー

1. ここ（`docs/design-system/`）のファイルを編集
2. commit & push（GitHub 経由で design プロジェクトへ同期）
