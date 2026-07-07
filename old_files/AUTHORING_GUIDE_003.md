# AUTHORING_GUIDE.md — Mission・コマンド作り込みガイド（AI Agent 向け）

CLI_Noir の Mission とコマンドを、**ゲームとして面白く、かつ LPIC 学習として正しく**作り込むためのガイド。
本ファイルを読めば、他の AI Agent（Opus 等）や人間コントリビュータが、既存クオリティと矛盾しない
コンテンツを単独で追加できる状態を目指す。

---

## 0. 作業前に読むファイル（この順で）

いずれも本ファイルと同じ `docs/` 内にある。

1. `設計指示書.md` — 全体仕様の正（allowlist / 疑似Git / エラー文言 § 12 / レベル表 § 8）
2. `Mission参照ファイル.md` — Mission1〜20 の確定仕様と出力フォーマット（§ 6）
3. `LPIC学習マップ.md` — コマンドごとの「実PCでの意味 ⇔ ゲーム内の対応」対照表
4. `バックエンド_コマンド機能仕様.md` — コマンド実装の定義フォーマット
5. `DESIGN.md` — ビジュアル・演出の仕様

**迷ったら `設計指示書.md` が正。** 本ガイドと矛盾したら設計指示書に従い、本ガイドを直す。

---

## 1. 絶対原則（違反したら作り直し）

1. **意味一致の原則**: ゲーム内の操作結果 = 実PCでの操作結果。「ゲームでしか通用しない操作」を作った時点で失敗。コマンドの出力は実 Linux の構造に寄せる（完全一致は不要、構造は一致）
2. **挫折させない**: 不正コマンドはエラー表示のみ（即失敗にしない）。時間切れ失敗を作らない。ヒント参照にペナルティを付けない
3. **必要性から学ばせる**: 「このコマンドを使え」ではなく「このコマンドを使わないと現実的に解けない状況」を設計する（例: 数万行のログ → パイプが必要になる）
4. **エラー文言は § 12 から選ぶ**: 新しいエラー文言を勝手に作らない。不足する場合は設計指示書 § 12 への追加をセットで提案する
5. **allowlist の外を要求しない**: Mission の想定解が allowlist（設計指示書 § 8）にないコマンドを要求してはならない。必要なら allowlist 更新を提案として明示する
6. **UI テキストは日本語 / ファイル名・コマンドは英語**
7. **クリアは必ず疑似 Git で締める**: `case_file.sh`（または相当の判定）→ `add` → `commit` → `push` の儀式で終わる。これは全 Mission 共通の「報告書提出」の型

---

## 2. Mission の解剖学 — 5幕構造

面白い Mission は必ずこの5幕を持つ。各幕の設計を飛ばさないこと。

### 第1幕: フック（30秒）
- ノワールの導入。「何が起きたか」「なぜお前がやるのか」を3行以内で
- 最初の1コマンド（大抵 `ls` か `pwd`）で必ず何かが見つかる状態にする。**最初の成功体験まで30秒**

### 第2幕: 探索（プレイの主部）
- 手がかりファイルを FS に散らす。1本道にしない（読む順序が違っても成立する = 判定は順不同許容）
- **手がかりは3層**にする:
  - 表層: `ls` で見えるファイル（誰でも見つかる）
  - 中層: 検索しないと見つからない（`find` / `grep` が必要）
  - 深層: 隠しファイル・ミスリードの奥（見つけなくてもクリア可能な収集要素）

### 第3幕: 壁（意図された詰まり）
- Mission の学習ターゲットそのものを「壁」にする。**壁は1 Mission に1枚**（2枚以上詰むと挫折する）
- 例: 画面がエラーで埋まる（→ `2>/dev/null`）、ファイルが開けない（→ 引用符）、量が多すぎる（→ パイプ）
- 壁の直前までは快適に進ませる。壁で詰まる→ヒント→突破、が学習の山場

### 第4幕: 発見（カタルシス)
- 壁を越えた直後に**必ず報酬**を置く: 決定的な手がかり、犯人の名前、意味が繋がる瞬間
- 「1記号で世界が変わる」演出を狙う（雑音が消えて声だけ残る、数万行が3行になる）

### 第5幕: 提出（儀式）
- `case_file.sh` 実行 → 疑似 Git で提出。ここは**安心して成功する場所**。新しい罠を置かない
- クリア演出 + 「実PCでも今と同じことができる」ことを一言添える

---

## 3. ゲーム性の道具箱

Mission に「ゲームらしさ」を足すときは、この道具から選ぶ（新しい道具の発明は設計指示書との整合確認をセットで）。

| 道具 | 使い方 | 実装済みの例 |
|---|---|---|
| **量の絶望** | cat では読めない物量 → 道具の必要性を体感させる | Mission4（数万行のログ） |
| **開かずの扉** | 権限・引用符・形式が理由で「開けない」→ 知識が鍵になる | Mission5, 15, 17 |
| **間違い探し** | 正解1つ+よく似た偽物N個。裏取りした者だけが確信できる | Mission6（プロセス）, 13（symlink）, 16（ハッシュ） |
| **ミスリード** | それらしい偽の手がかり。ただし**偽と分かる証拠を必ず併置**する（理不尽禁止） | Mission13 の偽リンク |
| **視点逆転** | プレイヤーの役割が変わる（実行する側→書く側、追う側→変装する側） | Mission18（スクリプト）, 7（su） |
| **反復の対** | 既習の構造を別文脈で再登場させ「同じだ」と気づかせる | ssh/exit と su/exit |
| **収集要素** | クリア条件外の隠しファイル。世界の裏側を語る | `.secret_memo`（背景ストーリー） |
| **加点（スマート捜査）** | 別解のうち上手い解に加点。初心者の正攻法を否定しない | パイプ1行解決、chmod 数値モード |
| **メタ構造** | ゲームの仕組み自体を物語に使う | Mission14（history が攻略チャート） |

### 難易度の目安

| 難易度 | ヒントなし想定クリア率 | 壁の性質 |
|---|---|---|
| 1〜2 | 80%+ | 壁なし〜既習の組み合わせ |
| 3 | 60% | 新概念1つ。ヒント1段階目で大半が突破 |
| 4 | 40% | 新概念+既習の複合。ヒント2段階目まで想定 |
| 5 | 20%（Mission20 のみ） | 複合。ヒントは1段階目のみ提供 |

---

## 4. ライティングガイド（ノワール文体）

### トーン
- ハードボイルド・短文・体言止め。感嘆符は多用しない
- プレイヤーは「お前」または「探偵」。相棒は軽口を叩くが答えは最後まで言わない
- 湿度のある比喩を1 Mission に1つだけ（多用すると安っぽくなる）

```
✅ 「雨の月曜だった。机の上の名刺入れは、空になっていた。」
✅ 「数字は嘘をつかない。嘘をつくのは、数字を書いた人間だ。」
❌ 「大変だ！名刺がなくなっちゃった！探してみよう！」（トーン違反）
❌ 「lsコマンドを入力してください」（説明書口調。ストーリーで言わせる）
```

### ヒント3段階の書き分け（重要）

| 段階 | 役割 | 例（Mission17） |
|---|---|---|
| 1: 方向性 | 世界観の言葉で方向を指す。コマンド名を出さない | 「雑音と声は、別々の管を通っている。管ごと塞げないか？」 |
| 2: 具体 | コマンド名・記号を出す。使い方は言わない | 「エラーは 2 番の管（標準エラー出力）だ。`2>` で流せる。捨て場所は `/dev/null`。」 |
| 3: ほぼ答え | コピペで動く一歩手前まで | 「`grep -r "witness" /archive 2>/dev/null` — 雑音は排水溝へ。」 |

### ゲーム内ファイルの書き方
- ファイル名: 英語スネークケース（`torn_note_03.txt`, `guest_list.txt`）
- 手がかりファイルの中身は「世界の住人が書いた文書」として書く（メタ表現・攻略指示を書かない）
- 判定に使うキー情報は正規表現で拾える固定書式にする（例: `Code: X9F2` / `Wire: red` / `Height: 173`）
- 1ファイルは 5〜30 行。判定キーの周囲に「読ませる肉付け」を足して、grep する理由を作る

---

## 5. Mission 定義スキーマ（完全版）

新 Mission はこの YAML を埋めれば実装可能になる。`Mission参照ファイル.md` § 6 の出力フォーマットの実装版。

```yaml
mission:
  id: 21                                # 既存と重複しない
  title_en: "Example Mission"
  title_ja: "見本事件"
  level: 5                              # 要求ランク（設計指示書 § 8 の表）
  learning_theme: "パイプ"               # LPIC 対応は LPIC学習マップ.md に追記
  difficulty: 3                         # § 3 の難易度表に従う
  est_minutes: 15                       # 10〜25 の範囲

story:
  hook: |                               # 3行以内。ノワール文体
    ...
  partner_lines:                        # 相棒の台詞（開始時/壁の前/クリア時）
    intro: "..."
    at_wall: "..."
    clear: "..."

initial_state:
  current_path: "/root/desk"
  remote_mode: false
  filesystem:                           # 設計指示書 § 4 の JSON スキーマに従う
    /root/desk/case_note.txt: |
      ...（世界の住人の文書として）
    /root/desk/.secret_memo: |          # 収集要素（任意）
      ...
  processes: []                         # Level 6 系のみ
  cron_jobs: []                         # Level 10 系のみ
  users: []                             # Level 7 系のみ

commands:
  required: ["grep", "sort", "uniq"]    # 全て allowlist 内であること
  bonus: ["wc", "head"]                 # 加点対象
  newly_unlocked: ["uniq"]              # この Mission で初解放（右パネルで点灯）

judgement:
  expected_script_patterns:             # 正規表現。順不同 AND が基本
    - 'grep\s+.+\|\s*sort\s*\|\s*uniq\s+-c'
    - 'TEL: [0-9]{3}-[0-9]{4}'
  match_policy: { order: any, case_sensitive: true }
  wrong_patterns:                       # 誤答への専用フィードバック（任意）
    - pattern: 'cat\s+tape\.log$'
      message: "Warning: too much output — try filtering"
  flags:                                # mission_flags の遷移定義
    - name: wall_passed
      set_when: "パイプ行の初回成功時"

hints:
  - "（1: 方向性。コマンド名なし）"
  - "（2: 具体。コマンド名・記号あり）"
  - "（3: ほぼ答え）"

presentation:
  scene_images:                         # 場所キー → 画像。current_path の前方一致・最長一致で解決（docs/DESIGN.md § 1）
    "office:/root": "mission21.png"     # Mission 既定（ルートに紐付け = フォールバック）
    "office:/root/desk": "office_desk.png"  # 任意: 意味のある場所にだけ追加。配下は親の絵を継承
  practice_card: |                      # 現場実習カード（設計指示書 § 11 機能11）。クリア演出後に表示
    君の本物の PC でも grep は同じだ。ターミナルを開いて
    `grep "検索したい語" ファイル名` を試してみろ。
    （安全な読み取り系コマンドのみ。破壊的操作は書かない）
  wall_effect: "..."                    # 壁の演出（例: 出力で画面が流れる）
  catharsis_effect: "..."              # 突破の演出（例: 3行だけ静かに残る）

tests:
  happy_path:                           # 正常系 3 件以上
    - ["cd desk", "grep TEL tape.log | sort | uniq -c", "sh case_file.sh",
       "git add case_file.sh", 'git commit -m "solved"', "git push"]
  error_cases:                          # 異常系 3 件以上（期待エラー文言は § 12 から）
    - cmd: "rm tape.log"
      expect: "Error: command not allowed"
    - cmd: "git push"                   # commit 前
      expect: "Error: push not allowed before commit"
```

---

## 6. 完全作例 — Mission4「盗聴テープを解析せよ」実装レベル詳細

`Mission参照ファイル.md` § 5 の Mission4 を、上記スキーマで実装可能レベルまで下ろした参考実装。
（正は Mission参照ファイル.md。ここでの具体値は実装時のたたき台）

```yaml
mission:
  id: 4
  title_en: "Wiretap Tape"
  title_ja: "盗聴テープを解析せよ"
  level: 5
  learning_theme: "パイプ・リダイレクト"
  difficulty: 3
  est_minutes: 15

story:
  hook: |
    深夜、匿名の小包が事務所に届いた。中身はテープ起こしのログが1本。
    差出人は書いていない。だが、これだけ長い記録を残す人間の目的は決まっている。
    ——誰かに見つけてほしいのだ。
  partner_lines:
    intro: "wc で数えてみろよ。読む気が失せるぞ。"
    at_wall: "全部読む探偵がいるか。絞って、並べて、数えるんだ。パイプって道具がある。"
    clear: "たった1行で片付けたな。……悪くない。"

initial_state:
  current_path: "/root/desk"
  remote_mode: false
  filesystem:
    /root/desk/tape.log: "<GENERATED: 約30,000行。下記生成ルール>"
    /root/desk/readme_from_sender.txt: |
      これは3ヶ月分の通話記録だ。
      あの男は同じ番号に何度も掛けている。一番多い番号がアジトだ。
      形式: [DATE] CALL from <name> TEL: XXX-XXXX
    /root/desk/.sender_note: |
      （収集要素）差出人の正体を匂わせる私信。クリアには不要。

  # tape.log 生成ルール（seed 固定で再現可能にする）:
  # - "TEL: NNN-NNNN" 形式の番号を 40 種、計 ~8,000 行に散らす
  # - 正解番号 "TEL: 484-0913" のみ 312 回（2位は 118 回。明確な差をつける）
  # - 残りはノイズ行（日付、無関係な会話メモ）。grep TEL で 1/4 に減る快感を作る

commands:
  required: ["grep", "sort", "uniq"]
  bonus: ["wc", "head", "tail"]
  newly_unlocked: ["head", "tail", "wc", "cut", "paste", "tr",
                   "sed", "diff", "nl", "tee", "xargs"]   # Level5 一括解放

judgement:
  expected_script_patterns:
    - 'grep\s+.*TEL.*tape\.log\s*\|\s*sort\s*\|\s*uniq\s+-c'
    - 'TEL: 484-0913'
    - '^git\s+push$'
  match_policy: { order: any, case_sensitive: true }
  wrong_patterns:
    - pattern: '^cat\s+tape\.log$'
      message: "Warning: 30000 lines... use filters"   # § 12 に追加提案が必要な新文言
  flags:
    - name: pipe_used
      set_when: "パイプを含むコマンドの初回成功"
    - name: number_found
      set_when: "case_file.sh に正解番号が記述された時"

hints:
  - "3ヶ月分を全部読む探偵はいない。欲しい行だけ「絞る」道具は、もう持っているはずだ。"
  - "絞った結果は | (パイプ) で次の道具に流せる。sort で並べ、uniq -c で数えろ。"
  - "grep TEL tape.log | sort | uniq -c | sort — 一番多い TEL がアジトだ。"

presentation:
  scene_images:
    "office:/root": "mission4.png"   # 案: 深夜の事務所。デスクに小包とテープ、床に印字用紙の山
  practice_card: |
    数万行のログも、君の PC では日常だ。ターミナルで
    `history | sort | uniq -c | sort -rn | head` — 自分が一番使うコマンドを数えてみろ。
  wall_effect: "cat tape.log 実行時、出力を高速スクロールで約3秒流し続ける（実出力は先頭1000行で打ち切り + Warning）"
  catharsis_effect: "uniq -c 成功時、出力を一拍おいて静かに表示。最多行だけ text-yellow-300"

tests:
  happy_path:
    - ["ls", "cat readme_from_sender.txt", "wc -l tape.log",
       "grep TEL tape.log | sort | uniq -c | sort",
       'echo "TEL: 484-0913" > case_file.sh', "sh case_file.sh",
       "git add case_file.sh", 'git commit -m "found the hideout"', "git push"]
    - ["cat tape.log", "grep TEL tape.log | sort | uniq -c",
       'echo "TEL: 484-0913" > case_file.sh', "sh case_file.sh",
       "git add case_file.sh", 'git commit -m "x"', "git push"]   # 壁に当たってから解く
    - ["grep 484 tape.log", 'echo "TEL: 484-0913" > case_file.sh',
       "sh case_file.sh", "git add case_file.sh",
       'git commit -m "x"', "git push"]   # 別解（パイプなし。クリア可・加点なし）
  error_cases:
    - cmd: "rm tape.log"
      expect: "Error: command not allowed"
    - cmd: "git commit -m \"x\""            # add 前
      expect: "Error: nothing to commit"
    - cmd: "git push"                        # 条件未達 commit のみ
      expect: "Error: mission requirements not met"
```

**この作例から読み取ってほしい設計判断:**
- 正解番号の出現回数に「2位と3倍差」を付ける（集計結果を見た瞬間に確信できる = カタルシス）
- パイプなしの別解を**塞がない**（正攻法でも解ける。パイプは「速い」だけ。加点で誘導する）
- 壁の演出（3秒スクロール）は演出であって懲罰ではない。直後に相棒がヒント方向を指す

---

## 7. コマンド作り込みガイド

新コマンドは `バックエンド_コマンド機能仕様.md` の形式で定義する。必須項目:

```markdown
### head
- 構文: `head [-n N] <file>`
- 前提条件: file が current_path から解決できる / remote_mode に応じた FS を参照
- 正常出力: 先頭 N 行（デフォルト 10）。実 Linux と同一の並び
- 異常出力:
  - file なし → `Error: file not found`
  - 引数不正（-n の値が数値でない）→ `Error: invalid input`
- state 更新: なし（読み取り専用）
- ゲーム内の意味: 分厚い調書の冒頭だけ確認する（LPIC学習マップ § 9）
```

### コマンド追加時のルール
1. **出力は実 Linux に寄せる**: 実機で同じコマンドを打ち、構造を写す（`uniq -c` の右寄せカウント、`ls -l` の列順など）。ゲーム独自の装飾はターミナル出力には入れない（装飾は GUI 側の演出で行う）
2. **オプションは学習に必要な最小集合**: LPIC 出題頻度の高いものだけ実装（例: `head` は `-n` のみ。`-c` は不要）。未実装オプションは `Error: invalid input` ではなく「無視して基本動作」より**明示的にエラー**の方が誤学習を防げる
3. **読み取り専用/破壊的を区別**: state を変更するコマンドは、変更内容（FS/フラグ/プロセステーブル…）を必ず定義に書く
4. **エラー文言は § 12 から**。足りなければ § 12 への追加をセットで提案
5. 完了したら `バックエンド_コマンド機能仕様.md` の実装チェックリストを更新

---

## 8. 品質チェックリスト（Mission DoD）

提出前に全項目を確認する。1つでも ✗ なら完成ではない。

- [ ] 5幕構造が揃っている（フック/探索/壁1枚/カタルシス/儀式）
- [ ] 最初の成功体験まで30秒（`ls` 一発で何かが見つかる）
- [ ] 必須コマンドが全て allowlist 内（不足分は allowlist 更新提案を添付）
- [ ] 全ての操作が「実PCで同じ意味を持つ」（意味一致の原則）
- [ ] 別解を塞いでいない（正規表現が特定の書き方を過剰に強制していない）
- [ ] ヒント3段階が書き分けられている（1段階目にコマンド名がない）
- [ ] エラー文言が全て設計指示書 § 12 に存在する（新文言は追加提案済み）
- [ ] 正常系テスト3件・異常系テスト3件以上
- [ ] 疑似 Git の順序制約（add→commit→push）と矛盾しない
- [ ] 手がかりファイルが「世界の住人の文書」として書けている（メタ表現なし）
- [ ] 収集要素（隠しファイル）が1つ以上ある（なくてもクリア可能）
- [ ] `LPIC学習マップ.md` に対応行がある（なければ追記）
- [ ] 場面画像の発注仕様（`scene_images` の場所キー・構図・場所とFSの整合）を書いた
- [ ] 現場実習カード（`practice_card`）の文面がある（安全な読み取り系コマンドのみ・破壊的操作なし）
- [ ] `Mission参照ファイル.md` § 6 のフォーマットで登録した

---

## 9. アンチパターン集（実例で覚える）

| ❌ アンチパターン | なぜダメか | ✅ 代わりに |
|---|---|---|
| `ls` の出力にヒントを直接埋め込む（`businesscard.txt ←これを見ろ!`） | 実PCの ls はそんなことをしない（意味一致違反） | ヒントは相棒の台詞か readme 系ファイルで |
| 「正確に `grep -E "^A"` と打て」という一字一句判定 | 別解殺し。実務では書き方が複数ある | 判定正規表現を緩くし、結果（正解の記述）で判定 |
| 壁を2枚以上重ねる（権限×パイプ×正規表現を同時に） | 詰まりの原因が特定できず挫折する | 壁は1枚。他の要素は既習のみ |
| 時間切れ・回数制限で失敗させる | 挫折させない原則違反 + state 復元と矛盾 | タイマーは演出のみ |
| ノイズファイルを無限に置く | 探索が作業になる。面白い無駄と退屈な無駄は違う | ミスリードには「偽と分かる証拠」を併置 |
| クリア後に新事実で「実は失敗」にする | 提出の儀式は安心の場所 | どんでん返しは次 Mission のフックでやる |
| 実在しないコマンド・独自コマンドを追加する | ゲーム限定知識の禁止 | 実 Linux コマンドのサブセットのみ |
| ヒント1段階目で答えを言う | 学習の山場（壁→突破）を潰す | § 4 の3段階書き分けに従う |

---

## 10. 提出物一覧（新 Mission 1本につき）

1. Mission 定義 YAML（§ 5 スキーマ・§ 6 相当の粒度）
2. `Mission参照ファイル.md` § 5 への追記（確定フォーマット）
3. 新コマンドがあれば `バックエンド_コマンド機能仕様.md` への定義追記
4. `LPIC学習マップ.md` への対応行追記
5. allowlist / エラー文言 / evaluator への変更が必要なら、`設計指示書.md` への変更提案（old_files/ バックアップ手順に従う）
6. `context/` 3ファイルの更新
