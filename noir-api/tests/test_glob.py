"""engine の glob 展開（* ? []）のテスト。"""

from app.evaluator import evaluate
from app.models import default_state


def _with_files(names: list[str]) -> dict:
    s = default_state()
    root = s["filesystem"]["root"]["children"]
    for i, name in enumerate(names):
        root[name] = {
            "type": "file",
            "content": f"content {i}",
            "mode": "rw-r--r--",
            "owner": "detective",
            "mtime": "2026-01-01T00:00:00Z",
            "immutable": False,
        }
    return s


def test_star_glob_expands_to_matching_files() -> None:
    s = _with_files(["case_1.txt", "case_2.txt", "other.txt"])
    out, _ = evaluate("ls case_*", s)
    assert out == ["case_1.txt", "case_2.txt"]


def test_bracket_glob_expands_digits_only() -> None:
    s = _with_files(["case_1.txt", "case_2.txt", "case_10.txt"])
    out, _ = evaluate("ls case_[0-9].txt", s)
    assert out == ["case_1.txt", "case_2.txt"]


def test_question_mark_glob() -> None:
    s = _with_files(["a1.txt", "a2.txt", "ab.txt"])
    out, _ = evaluate("ls a?.txt", s)
    assert out == ["a1.txt", "a2.txt", "ab.txt"]


def test_no_match_stays_literal() -> None:
    s = _with_files(["real.txt"])
    out, _ = evaluate("ls nope_*.txt", s)
    assert out == ["Error: path not found"]


def test_glob_not_applied_to_command_name() -> None:
    # コマンド名自体は展開対象外（glob 文字を含む実在コマンドは存在しないので
    # command not allowed になることを確認する）。
    s = default_state()
    out, _ = evaluate("c*t x", s)
    assert out == ["Error: command not allowed"]


def test_quoted_pattern_stays_literal() -> None:
    s = _with_files(["case_1.txt"])
    out, _ = evaluate('ls "case_*"', s)
    # 引用符付きなので展開されず、"case_*" という名前のファイルは無いのでエラー。
    assert out == ["Error: path not found"]


def test_glob_with_pipe() -> None:
    s = _with_files(["case_1.txt", "case_2.txt", "other.txt"])
    out, _ = evaluate("ls case_* | grep 1", s)
    assert out == ["case_1.txt"]


def test_quoted_filename_with_space_preserved() -> None:
    s = default_state()
    s["filesystem"]["root"]["children"]["top secret.txt"] = {
        "type": "file",
        "content": "CODE: 4821",
        "mode": "rw-r--r--",
        "owner": "detective",
        "mtime": "2026-01-01T00:00:00Z",
        "immutable": False,
    }
    out, _ = evaluate('cat "top secret.txt"', s)
    assert out == ["CODE: 4821"]


def test_find_name_quoted_pattern_still_works() -> None:
    # find -name "*.txt" は find 自身のパターンマッチであり、glob 展開の影響を
    # 受けないことを確認する回帰テスト（cwd 直下に一致ファイルがある場合）。
    s = _with_files(["a.txt"])
    out, _ = evaluate('find /root -name "*.txt"', s)
    assert out == ["/root/a.txt"]
