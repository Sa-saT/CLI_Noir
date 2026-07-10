"""コマンド評価エンジン（allowlist 判定 → 実行 → state 更新）。

判定順序（設計指示書 § コマンド制御）:
  denylist → allowlist → evaluator 実行
  `git` は第1トークン判定後にサブコマンドを別途分岐。
  `rm` は全般禁止、`curl` は mock API 限定。

純粋 Python として実装し、入出力は dict（state）で受け渡す（未実装）。
"""

# TODO: def evaluate(command: str, state: dict) -> tuple[str, dict]:
#   コマンド文字列と現在 state を受け取り、(出力テキスト, 更新後 state) を返す。
