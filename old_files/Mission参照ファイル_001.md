# Mission参照ファイル（Agent用）

各 Mission の仕様を Agent が参照する基準書。  
確定情報は固定値で記載し、未確定は最小限だけ残す。

---

## 0. 共通ルール（確定）

- MVP: Mission1〜3（Mission4/5 は将来拡張）
- 判定: 正規表現ベース / 順不同許容 / 大小文字区別あり
- 不正コマンド時: エラーメッセージ表示のみ（即失敗にしない）
- 疑似 Git: `git add -> git commit -m "<msg>" -> git push` 順序必須
- `git commit` = ゲームセーブ（1 Mission 中に何度でも可。再開時にセーブ選択可）
- `git push` = クリア判定（最新 commit の状態で合否判定）
- 次 Mission 遷移時、前 Mission のクリア前 commit は全消去
- commit message: 1 文字以上（MVP はパターン制約なし）
- 実 Git 連携なし（内部 `git_state` で判定）
- エラーメッセージは `設計指示書.md` § 12 を正とする
- コマンド仕様は `バックエンド_コマンド機能仕様.md` を正とする

---

## 1. Mission共通テンプレート（推奨初期値）

### A. 基本情報
- mission_id: `1..5`
- title: `Mission名（英語） + 画面表示名（日本語）`
- 学習テーマ: `基本操作 / 検索 / remote操作 / 正規表現 / 疑似Git`
- 想定プレイ時間: `10〜25分`
- 難易度: `1〜5`

### B. 初期状態
- current_path: `Mission1=/root, Mission2=/root/park, Mission3=remote接続後に/gate`
- local / remote: `Mission1,2=local / Mission3=local開始→sshでremote`
- 初期FS: `設計指示書.md § 5 の local構造 + Mission専用ヒントファイル`
- 初期 `git_state`: `staged=[] / committed=false / pushed=false`

### C. 判定仕様
- `expected_script_patterns`: 正規表現配列
- AND/OR: 基本 AND（全パターン一致必須）。必要時のみ OR グループ追加
- `case_file.sh` 採点対象: コマンド実行ログ + 生成/編集ファイル内容 + git_state
- 不一致時: `Warning: pattern mismatch`（致命時は `Error: pattern mismatch`）

### D. 失敗/例外
- 想定エラー: `file not found / path not found / invalid pattern / command not allowed`
- ヒント: 3 段階（方向性 → 具体コマンド → ほぼ答え）
- リトライ: 失敗理由表示 → ヒント表示 → 再実行

### E. UI/演出
- 背景画像: `mission{n}.png`
- 説明文: ミッション目的 + 主要コマンド + 完了条件を 3 行で表示
- クリア演出: フェード + "Mission Complete!" + 次 Mission 導線

---

## 2. Mission1（Edit Business Card）

### 確定
- 目的: 名刺ファイルにユーザー名を書き込み、`case_file.sh` 判定後に疑似 `git push` まで完了する
- 想定コマンド: `ls`, `cd`, `cat`, `echo`, `git status/add/commit/push`
- 進行条件: 疑似 Git ワークフロー成功まで
- 名刺ファイル: `/root/desk/businesscard.txt`
- `case_file.sh` の正規表現:
  - `^cat\\s+/root/desk/businesscard\\.txt$`
  - `^echo\\s+.+\\s*>\\s+/root/desk/businesscard\\.txt$`
  - `^git\\s+add\\s+.+$`
  - `^git\\s+commit\\s+-m\\s+.+$`
  - `^git\\s+push$`
- ヒント:
  - 1: `まず机(desk)を調べ、名刺ファイルの場所を確認しよう。`
  - 2: `名刺にはあなたのユーザー名を書き込む必要があります。`
  - 3: `編集後は git add -> git commit -m -> git push の順で進めよう。`

---

## 3. Mission2（Park Cat Search）

### 確定
- 目的: 公園で猫ファイルを探索し、絶対パス・状態を満たした `case_file.sh` で完了する
- 完了には疑似 `git push` 成功を含む
- 猫ファイル: `catinfo.txt`（配置: `/root/park/swing/catinfo.txt`）
- 必須コマンド: `find`, `cat`, `grep`
- 任意（加点）: `awk`, `sort`, `uniq`
- 誤答パターン:
  - 絶対パス未記述: `Error: absolute path required`
  - 猫情報キー不足: `Error: required cat status not found`
  - `find` 未使用: `Warning: use find to locate clues`

---

## 4. Mission3（Amusement Park Bomb）

### 確定
- 目的: remote（遊園地）でヒント収集し、正規表現条件を満たす `case_file.sh` で完了する
- `ssh amusement_park` で接続 → 初期ディレクトリ `/gate`
- local へ戻る: `exit` のみ（`cd` 不可）
- 接続エラー: `Host not found` / `Permission denied`
- 必須: `ssh amusement_park` → `find` → `cat/grep` → `case_file.sh` → 疑似 `git push`
- 任意: `awk`, `sort`, `uniq`
- 必須正規表現キー:
  - `Code: [A-Z0-9]{4,}`
  - `Wire: (red|blue|yellow)`
  - `Height: [0-9]+`

---

## 5. Mission4/5（将来拡張）

- MVP 対象外
- 学習テーマ案:
  - Mission4: パイプとリダイレクト
  - Mission5: 権限管理と複合検索
- evaluator 拡張: パイプ簡易対応 / OR グループ評価 / スコアリング

---

## 6. Agent 出力フォーマット（固定）

```md
# Mission{n}: <title>

## 目的
## 初期状態
## 必須コマンド
## expected_script_patterns
## クリア条件
## 失敗条件/エラー文言
## テストケース（正常系 / 異常系）
```

---

## 7. Agent 参照優先順位

1. `設計指示書.md`（全体方針・API・エラー定義・開発フロー）
2. `Mission参照ファイル.md`（本ファイル。Mission詳細）
3. `バックエンド_コマンド機能仕様.md`（コマンド実装詳細）
4. `環境構築手順.md`（セットアップ手順）
