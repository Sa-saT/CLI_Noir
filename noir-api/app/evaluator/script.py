"""Mission19: `sh` で実行する汎用スクリプトの最小インタープリタ。

対応構文（設計指示書 § 8 の if/for/test サブセット）:
- `#` コメント・空行
- `NAME=value`（ローカル変数。value は `$OTHER` 展開後にクォート剥がし）
- `$NAME` / `"$NAME"`（コマンド行内の変数展開。engine の `$?` とは独立）
- `if <cmd>; then ... fi`（単一行形式・複数行形式のどちらも同じ文リストに正規化して処理）
- `for x in a b c; do ... done`（同上。加点要素）

if/for のネストは非対応（本ゲームの学習範囲を超えるため）。スクリプト内の各コマンドは
`evaluate()` を再帰呼び出しするため、denylist/allowlist を通る（設計指示書 § 8）。
"""

import re

_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_VAR_REF = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _expand_vars(text: str, variables: dict[str, str]) -> str:
    return _VAR_REF.sub(lambda m: variables.get(m.group(1), ""), text)


def _dequote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def _split_on_semicolons(line: str) -> list[str]:
    """`;` で分割する（引用符内の `;` は保護する）。"""
    parts: list[str] = []
    buf: list[str] = []
    in_quote: str | None = None
    for ch in line:
        if in_quote:
            buf.append(ch)
            if ch == in_quote:
                in_quote = None
        elif ch in "'\"":
            in_quote = ch
            buf.append(ch)
        elif ch == ";":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def _split_statements(content: str) -> list[str]:
    """スクリプト全文を「文」のフラットな列へ正規化する。

    改行と `;` はどちらも文区切りとして扱うため、単一行形式
    (`if X; then Y; fi`) と複数行形式 (`if X` / `then` / `Y` / `fi`) が
    同じ文リストに正規化され、後続の解釈ロジックを共通化できる。
    """
    statements: list[str] = []
    for raw_line in content.split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        for part in _split_on_semicolons(line):
            part = part.strip()
            if part:
                statements.append(part)
    return statements


def run_script(state: dict, content: str) -> tuple[list[str], dict]:
    """スクリプト全文を実行し (出力行, 新 state) を返す。"""
    from app.evaluator.engine import evaluate  # 遅延 import（循環回避: engine→commands→script→engine）

    statements = _split_statements(content)
    variables: dict[str, str] = {}
    output: list[str] = []
    cur_state = state

    def run_command(line: str) -> None:
        nonlocal cur_state
        out_lines, cur_state = evaluate(_expand_vars(line, variables), cur_state)
        output.extend(out_lines)

    def condition_succeeds(line: str) -> bool:
        nonlocal cur_state
        out_lines, new_state = evaluate(_expand_vars(line, variables), cur_state)
        if any(ln.startswith("Error:") for ln in out_lines):
            return False
        cur_state = new_state
        return True

    def run_statement(stmt: str) -> None:
        m = _ASSIGN.match(stmt)
        if m:
            name, raw_value = m.group(1), m.group(2)
            variables[name] = _dequote(_expand_vars(raw_value, variables))
            return
        run_command(stmt)

    i, n = 0, len(statements)
    while i < n:
        stmt = statements[i]

        if stmt.startswith("if "):
            cond = stmt.removeprefix("if ").strip()
            i += 1
            then_stmt = statements[i] if i < n else ""
            body_start = ""
            if then_stmt == "then" or then_stmt.startswith("then "):
                body_start = then_stmt.removeprefix("then").strip()
            i += 1
            body: list[str] = [body_start] if body_start else []
            while i < n and statements[i] != "fi":
                body.append(statements[i])
                i += 1
            i += 1  # skip 'fi'
            if condition_succeeds(cond):
                for body_stmt in body:
                    run_statement(body_stmt)

        elif stmt.startswith("for "):
            header = stmt.removeprefix("for ")
            var_name, _, rest = header.partition(" in ")
            var_name = var_name.strip()
            items = rest.strip().split()
            i += 1
            do_stmt = statements[i] if i < n else ""
            body_start = ""
            if do_stmt == "do" or do_stmt.startswith("do "):
                body_start = do_stmt.removeprefix("do").strip()
            i += 1
            body = [body_start] if body_start else []
            while i < n and statements[i] != "done":
                body.append(statements[i])
                i += 1
            i += 1  # skip 'done'
            for item in items:
                variables[var_name] = item
                for body_stmt in body:
                    run_statement(body_stmt)

        else:
            run_statement(stmt)
            i += 1

    return output, cur_state
