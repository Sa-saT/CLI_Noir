# CLI_Noir

Linux コマンドを「探偵ゲーム」として遊びながら学ぶ、CUI 学習ゲーム。
Mission を解き進めるうちに LPIC Level 1 相当のコマンド操作が自然と身につくことを目指す。

> 「理解してから触る」ではなく「触りながら理解する」。黒い画面アレルギーを、遊びで克服する。

## コンセプト

- ノワール探偵の世界観で、実際の Linux 操作と**意味が一致する**コマンド体験を提供する
- ゲーム内の操作結果は実 PC と同じ意味を持ち、ゲーム限定の知識にはしない
- MVP は Mission1〜3、Phase2 で Mission4〜20 / Level 5〜11 まで拡張予定

## 技術スタック（予定）

| 領域 | 技術 |
|---|---|
| フロントエンド | Vue 3 / Nuxt（SPA）、TypeScript、Pinia、Tailwind CSS、自作ターミナル UI |
| バックエンド | FastAPI、SQLModel、Alembic、擬似シェル evaluator（純粋 Python） |
| 通信 | WebSocket（コマンド実行）、JWT 認証 |

## ステータス

設計ドキュメント主導で開発中。フロントエンド（[`noir-client/`](noir-client/)・Nuxt 4 SPA）は実装着手済み、バックエンド（FastAPI）は未着手。仕様ドキュメントは [`docs/`](docs/) に集約している。

| ディレクトリ | 内容 | 状態 |
|---|---|---|
| [`docs/`](docs/) | 全設計ドキュメント（正）+ `design-system/`（デザイン local ミラー） | 継続更新 |
| [`noir-client/`](noir-client/) | Nuxt 4 フロント実装（10 コンポーネント + Mission1 合成画面 + ギャラリー） | 実装済み（evaluator はモック） |
| `noir-api/` | FastAPI バックエンド | 未着手 |
| `context/` | AI セッション復元用（00→03 の順で読む） | 継続更新 |

## ドキュメント

| ファイル | 内容 |
|---|---|
| [`docs/設計指示書.md`](docs/設計指示書.md) | 全体仕様の正（スタック / API / WebSocket / 疑似Git / エラー定義） |
| [`docs/Mission参照ファイル.md`](docs/Mission参照ファイル.md) | Mission1〜20 の詳細仕様 |
| [`docs/LPIC学習マップ.md`](docs/LPIC学習マップ.md) | LPIC 出題範囲とゲーム内コマンドの対応表 |
| [`docs/バックエンド_コマンド機能仕様.md`](docs/バックエンド_コマンド機能仕様.md) | evaluator / コマンド実装定義 |
| [`docs/DESIGN.md`](docs/DESIGN.md) | UI・ビジュアル・ターミナル実装仕様 |
| [`docs/AUTHORING_GUIDE.md`](docs/AUTHORING_GUIDE.md) | Mission・コマンドの作り込みガイド |
| [`docs/環境構築手順.md`](docs/環境構築手順.md) | 開発環境セットアップ |

## セットアップ

実装着手時の手順は [`docs/環境構築手順.md`](docs/環境構築手順.md) を参照。
