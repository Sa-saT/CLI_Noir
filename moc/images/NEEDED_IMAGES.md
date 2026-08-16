# 場面画像 制作リスト

作成日: 2026-08-17（Part5 永続統合ワールド化 P3-05 完了時点の世界構造から算出）

CLI_Noir の「場面画像」は**カレントディレクトリに紐付く**（`docs/DESIGN.md` § 1）。
本ファイルは、統合ワールド（`noir-api/app/content/missions.py::_build_world_fs()`）と
ssh 接続先（`app/evaluator/commands.py::SSH_HOSTS`）から洗い出した**必要な画像の一覧**。

---

## 仕様（制作前に読む）

- **サイズ**: 1536 × 1024（既存の `mission1.png` / `office.png` と同じ）。`object-fit: cover` で
  トリミングされるため、重要な要素は中央寄りに置く
- **形式**: PNG
- **画風の基準**: `moc/images/mission1.png`（セピア調・銅版画風ノワール）。上下にグラデーションの
  暗幕が重なり、右上にバッジ、下部にターミナルが乗るので、**上下 15% 程度は情報を置かない**
- **配置先**: `noir-client/public/images/`（`moc/images/` は画風の参考用。本番参照はしない）
- **登録先**: `noir-client/app/pages/missions/[id].vue` の `SCENE_IMAGES` に
  `'<host>:<パス接頭辞>': '/images/<ファイル名>'` を追加する。解決は**前方一致の最長一致**なので、
  親（`office:/root`）を用意しておけば子は自動でフォールバックする＝**全部揃わなくても破綻しない**
- `host` は local が `office`、ssh 中は接続先ホスト名

---

## 優先度 A: 今すぐ効く（Mission1〜3 が実プレイ可能な範囲）

| ファイル名 | 登録キー | Mission | 描くもの |
|---|---|---|---|
| `office.png` | `office:/root` | 全体 | **制作済み**。探偵事務所。全 local 場面のフォールバック |
| `desk.png` | `office:/root/desk` | 1 | 事務所の机まわり。名刺ファイル・ペン・灰皿 |
| `park.png` | `office:/root/park` | 2 | 夜の公園。ブランコ・噴水・ベンチが見渡せる引きの画 |
| `amusement_park_gate.png` | `amusement_park:/gate` | 3 | 閉園後の遊園地の門。奥に観覧車のシルエット |

## 優先度 B: local の各 Mission 区画（Mission4〜22）

| ファイル名 | 登録キー | Mission | 描くもの |
|---|---|---|---|
| `wiretap_room.png` | `office:/root/wiretap_room` | 4 | 盗聴テープの部屋。リールレコーダーとテープの山 |
| `vault.png` | `office:/root/vault` | 5・22 | 開かずの資料室。鋼鉄扉と封印された棚（Mission22 で再訪する場所） |
| `bar.png` | `office:/root/bar` | 8 | 場末のバー。カウンターとバーテンダー。奥に台帳のある裏部屋 |
| `evidence_locker.png` | `office:/root/evidence_locker` | 9 | 証拠品保管庫。封蝋・梱包された箱が積まれた棚 |
| `will_office.png` | `office:/root/will_office` | 10 | 遺言状を扱う事務所。書き物机に正本と写しが並ぶ |
| `scraps.png` | `office:/root/scraps` | 11 | 切り裂かれた脅迫状の断片が散らばる机 |
| `crontab_room.png` | `office:/root/crontab_room` | 13 | 時限装置の部屋。大時計と壁の予定表 |
| `mirror_hall.png` | `office:/root/mirror_hall` | 14 | 鏡の館。同じ扉が何枚も映り込み、実体が1つだけ分からない |
| `informant_trail.png` | `office:/root/informant_trail` | 15 | 情報屋の足取り。雨に濡れた路地と足跡、桟橋の気配 |
| `warehouse.png` | `office:/root/warehouse` | 16 | 倉庫。同じ形の事件ファイル箱が大量に並ぶ棚 |
| `contracts.png` | `office:/root/contracts` | 17 | 契約書の部屋。同一に見える書類 5 通と拡大鏡 |
| `archive.png` | `office:/root/archive` | 18 | 書庫。封印された閲覧不可の資料に埋もれた1枚の証言 |
| `precinct_desk.png` | `office:/root/precinct_desk` | 19 | 分署のデスク。手順書の見本とタイプライター |
| `toolbox_room.png` | `office:/root/toolbox_room` | 21 | 道具箱が消えた作業場。空の工具棚と貼り紙 |
| `clues.png` | `office:/root/clues` | 22 | 最終事件の手がかり部屋。壁一面の相関図と赤い糸 |
| `logs.png` | `office:/root/logs` | 22 | 通話記録の保管室。ロール紙の記録が壁を埋める |

## 優先度 C: 街のインフラ（FHS。Mission20 が主舞台、常時到達可能）

| ファイル名 | 登録キー | Mission | 描くもの |
|---|---|---|---|
| `city_etc.png` | `office:/etc` | 20 | 街の台帳室。住民登録簿と回線帳が並ぶ役所然とした部屋 |
| `city_varlog.png` | `office:/var/log` | 20 | 出入記録の保管所。日付印の押された入退室記録 |
| `city_tmp.png` | `office:/tmp` | 20 | 忘れ物置き場。誰かが捨てていったメモが残る |
| `mr_black_house.png` | `office:/home/mr_black` | 20 | 黒幕の住居。生活感の抜けた部屋と燃やしかけの帳簿 |

## 優先度 D: ssh 接続先（remote）

| ファイル名 | 登録キー | Mission | 描くもの |
|---|---|---|---|
| `ghost_den.png` | `ghost.example:/den` | 12・22 | 幽霊回線の先の隠れ家。裸電球と黒幕の指示書 |

- `10.66.6.6` は `ghost.example` の別名（dig で判明する IP）。**同じ画像を両方のキーに登録すること**
  （`10.66.6.6:/den` も追加する）

---

## 任意（余力があれば。無くても親画像にフォールバックする）

同じ Mission の中で場面が変わると気持ちがいい箇所。優先度は A〜D の全体が揃ったあと。

| 登録キー | Mission | 描くもの |
|---|---|---|
| `office:/root/park/swing` | 2 | ブランコの足元。猫の痕跡 |
| `office:/root/vault/inner` | 5 | 資料室のさらに奥の小部屋 |
| `office:/root/bar/back` | 8 | バーの裏部屋。バーテンダーだけが開ける台帳 |
| `office:/root/mirror_hall/vault` | 14 | 鏡の館の最奥。本物の権利書 |
| `amusement_park:/gate/ferris` | 3 | 観覧車の配線盤 |
| `ghost.example:/den/evidence` | 12 | 隠れ家の証拠棚 |

---

## 参考: 画像が不要な Mission

以下は舞台がファイルシステムではないため、専用の場面画像を持たない
（`office:/root` の事務所のまま進行する）。

- Mission6「盗聴器を止めろ」・Mission7「機械の胸の内」 … プロセステーブル / 疑似 `/proc` が舞台
- Mission12「幽霊回線を追え」 … local 側の探索は無く、`ghost.example:/den` へ ssh する

## 進捗

- [x] `office.png`（`moc/images/mission1.png` 由来）
- [ ] 上記のそれ以外すべて（優先度 A の 3 枚から）
