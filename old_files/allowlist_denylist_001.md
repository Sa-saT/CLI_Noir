allowlist（許可コマンド一覧）と denylist（禁止コマンド一覧）
⸻

🔐 コマンド許可・禁止（正しい allowlist / denylist）

✅ 最終的な許可（Allowlist）

下記コマンドは ゲーム内で使用可能 とします：

🧰 基本コマンド

ls
cd
pwd
touch
mkdir
cat
less
echo
history
clear

※ 自身でtouchで作成したファイルは削除ボタンで削除できる。
   デフォルトで作成されるファイルは削除ボタンが無いため削除できない。
   
🔎 検索系・テキスト系

grep        # 正規表現対応
find        # ファイル検索
awk         # 正規表現 + 条件処理
sort
uniq

🛠 シェル制御

ssh
exit

※ exit は remote_mode 解除用

📦 Git 風疑似コマンド

git status
git add
git commit
git push

※ 実 Git ではなく疑似判定（ゲーム内のルール）

⚙️ システム系（許可）

chmod
chown
curl

―― これらは 実際の Linux でもよく使うが、ゲーム内でも OK とします。

⸻

❌ 禁止（Denylist）

下記のコマンドは ゲーム内で使用できません：

rm -rf /
sudo
shutdown
poweroff
reboot
telnet
ftp
wget
nc (netcat)
dd
mkfs

これらは セキュリティ上危険／ゲーム進行に不要 のため拒否。

禁止コマンドは以下の基準で選定されています。
❌ 実際の OS で危険性の高いもの
❌ ネットワーク攻撃や不正アクセス系
❌ ゲーム進行に不要なもの

補足
一部、実ファイルシステムに影響を与えるようなコマンド（例: rm -rf /, dd, mkfs）はゲーム内でも禁止が確定です。

という設計意図です。

⸻

📊 許可コマンド階層（レベル分け）

レベル	コマンド
Level 1	ls, cd, pwd, touch, mkdir, cat, echo, clear
Level 2	less, history
Level 3	grep, find, sort, uniq
Level 4	awk
全レベル	ssh, exit
Git 系	git status/add/commit/push

→ ミッション進行に合わせて段階的に学習可能。

⸻

📌 実行時の制御仕様（バックエンド eval）

バックエンドでは バックエンド側 evaluator（擬似シェル） が以下をチェックします：

1) コマンド名の解析

cmd = inputCommand.split(" ")[0]

2) Allowlist 判定

if cmd in ALLOWLIST:
    eval_command(cmd, args)
else:
    return "Error: command not allowed."


⸻

📌 例：許可/拒否メッセージ

例：許可コマンド

$ grep "clue" notes.txt
Matched 2 lines.

例：禁止コマンド

$ wget http://malicious
Error: command not allowed in game environment.


⸻

🧾 allowlist（決定版）

ALLOWLIST = [
  "ls", "cd", "pwd",
  "touch", "mkdir", "cat", "less",
  "echo", "history", "clear",
  "grep", "find", "sort", "uniq", "awk",
  "ssh", "exit",
  "git", "git status", "git add",
  "git commit", "git push",
  "chmod", "chown", "curl"
]

※ ただし curl は「ローカル環境内で mock API 呼び出し的に使う」程度の限定仕様とする方針（実ネットアクセスはさせない）

⸻

🔁 denylist（決定版）

DENYLIST = [
  "rm", "sudo", "shutdown",
  "poweroff", "reboot",
  "telnet", "ftp", "wget",
  "nc", "dd", "mkfs"
]

※ rm 全般は禁止

⸻