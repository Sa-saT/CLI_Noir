import type { CommandEntry } from '~/components/CommandPanel.vue'

/*
 * コマンド図鑑の静的データ（FE-05）。設計指示書 § 8 のレベル表 / allowlist に対応。
 * Mission 詳細 API の `allowed_commands` から CommandPanel/CommandDetail への変換をここに集約する。
 * git は 4 つの疑似 Git サブコマンドとして展開する（設計指示書 § 10 の判定フロー）。
 */

export interface CommandDetail {
  syntax: string
  real: string
  inGame: string
}

const GIT_SUBCOMMANDS: Array<{ name: string, detail: CommandDetail }> = [
  {
    name: 'git status',
    detail: { syntax: 'git status', real: '作業ツリーの変更状態を確認する。', inGame: '証拠の提出準備がどこまで整ったか確認する。' },
  },
  {
    name: 'git add',
    detail: { syntax: 'git add <ファイル>', real: '変更をステージに載せる。', inGame: '提出する証拠を封筒に入れる（提出前の必須手順）。' },
  },
  {
    name: 'git commit',
    detail: { syntax: 'git commit -m "..."', real: '変更を記録する。', inGame: 'ゲームのセーブ。何度でも可能。' },
  },
  {
    name: 'git push',
    detail: { syntax: 'git push', real: 'コミットをリモートへ送る。', inGame: 'クリア判定。最新セーブの内容で合否が出る。' },
  },
]

export const COMMAND_DETAILS: Record<string, CommandDetail> = {
  ls: { syntax: 'ls [パス]', real: 'そのディレクトリにあるファイル・フォルダを一覧する。', inGame: '今いる部屋にある手がかりを見回す。' },
  cd: { syntax: 'cd <パス>', real: '作業ディレクトリを移動する。', inGame: '別の部屋・現場へ移動する。' },
  pwd: { syntax: 'pwd', real: '今いる作業ディレクトリの絶対パスを表示する。', inGame: '今どこにいるか自分の位置を確認する。' },
  cat: { syntax: 'cat <ファイル>', real: 'ファイルの中身を表示する。', inGame: '書類や手紙を読む。' },
  echo: { syntax: 'echo "文字列" [> <ファイル>]', real: '文字列を出力する。> でファイルへ書き込む。', inGame: '記録を書き込む、あるいは手がかりを読み上げる。' },
  find: { syntax: 'find <パス> -name "パターン"', real: '条件に一致するファイルを再帰的に探す。', inGame: '現場を隅々まで捜索し、手がかりのファイルを探し出す。' },
  grep: { syntax: 'grep "パターン" <ファイル>', real: 'ファイルの中から指定した文字列を含む行を抜き出す。', inGame: '証言・記録の中からキーワードを拾い出す。' },
  awk: { syntax: "awk '{ print $1 }' <ファイル>", real: '列（フィールド）単位でテキストを加工・抽出する。', inGame: '記録の中から必要な項目だけを抜き出す。' },
  sort: { syntax: 'sort <ファイル>', real: '行を並べ替える。', inGame: '証拠を順序立てて整理する。' },
  uniq: { syntax: 'uniq <ファイル>', real: '連続する重複行をまとめる。', inGame: '重複した証言を1つにまとめる。' },
  ssh: { syntax: 'ssh <ホスト名>', real: 'リモートホストへ接続する。', inGame: '現場（遠隔地）へ潜入する。' },
  exit: { syntax: 'exit', real: '現在のシェル（remote 接続時は接続元）へ戻る。', inGame: '現場から事務所へ帰還する。' },
}

/** 未収録コマンドの汎用フォールバック説明（man 参照を促す）。 */
function genericDetail(name: string): CommandDetail {
  return {
    syntax: name,
    real: `実際の PC での詳しい意味は man ${name} を参照。`,
    inGame: 'この事件の捜査で使用が許可されているコマンドの一つ。',
  }
}

export function commandDetailFor(name: string): CommandDetail {
  const git = GIT_SUBCOMMANDS.find(g => g.name === name)
  if (git) return git.detail
  return COMMAND_DETAILS[name] ?? genericDetail(name)
}

/** allowed_commands（設計指示書 § 6 Mission詳細）から CommandPanel の表示エントリを組み立てる。 */
export function buildCommandEntries(allowed: string[]): CommandEntry[] {
  const out: CommandEntry[] = []
  for (const cmd of allowed) {
    if (cmd === 'git') {
      for (const g of GIT_SUBCOMMANDS) out.push({ name: g.name, state: 'highlight' })
    } else {
      out.push({ name: cmd, state: 'unlocked' })
    }
  }
  return out
}

// 設計指示書 § 8 レベル表（探偵ランク）。正はバックエンド app/evaluator/rank.py（state.rank）で、
// ここは未接続時のフォールバック表示用。
const LEVEL_MAP: Record<string, number> = {
  ls: 1, cd: 1, pwd: 1, touch: 1, mkdir: 1, cat: 1, echo: 1, clear: 1,
  less: 2, history: 2,
  grep: 3, find: 3, sort: 3, uniq: 3, egrep: 3, fgrep: 3,
  awk: 4,
  head: 5, tail: 5, wc: 5, cut: 5, paste: 5, tr: 5, sed: 5, diff: 5, nl: 5, tee: 5, xargs: 5,
  ps: 6, top: 6, kill: 6, pgrep: 6, jobs: 6, free: 6, uptime: 6,
  chmod: 7, chown: 7, umask: 7, su: 7, whoami: 7, id: 7, who: 7,
  cp: 8, mv: 8, tar: 8, gzip: 8, gunzip: 8, zip: 8, unzip: 8, ln: 8, file: 8,
  which: 8, locate: 8, du: 8, df: 8, md5sum: 8, sha256sum: 8, stat: 8,
  ping: 9, ip: 9, ss: 9, dig: 9, host: 9, hostname: 9, traceroute: 9,
  crontab: 10, at: 10, date: 10, cal: 10, systemctl: 10, journalctl: 10, uname: 10, env: 10, alias: 10,
  export: 10, unset: 10, printenv: 10, type: 10,
  sh: 11, test: 11, read: 11, basename: 11, dirname: 11, seq: 11,
}
const RANK_NAMES: Record<number, string> = {
  1: '見習い探偵', 2: '新米探偵', 3: '捜査員', 4: '分析官', 5: '情報屋', 6: '監視者',
  7: '潜入捜査官', 8: '証拠管理官', 9: '追跡者', 10: '主任探偵', 11: '参謀',
}

/** allowed_commands から現在の探偵ランク表示を算出する（最も高いレベルのコマンドを基準）。 */
export function rankLabelFor(allowed: string[]): string {
  const level = allowed.reduce((max, cmd) => Math.max(max, LEVEL_MAP[cmd] ?? 1), 1)
  return `Lv.${level} ${RANK_NAMES[level] ?? ''}`.trim()
}
