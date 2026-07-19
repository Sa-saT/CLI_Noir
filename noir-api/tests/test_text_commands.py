"""テキスト処理コマンド（sort / uniq / wc / head / tail / cut）のテスト。"""

import pytest

from app.evaluator import evaluate
from app.models import default_state


def _with_file(content: str, name: str = "data.txt") -> dict:
    s = default_state()
    s["filesystem"]["root"]["children"][name] = {
        "type": "file",
        "content": content,
        "mode": "rw-r--r--",
        "owner": "detective",
        "mtime": "2026-01-01T00:00:00Z",
        "immutable": False,
    }
    return s


@pytest.fixture
def fruit_state() -> dict:
    return _with_file("banana\napple\ncherry\napple")


# --- sort ---
def test_sort_lexical(fruit_state: dict) -> None:
    out, _ = evaluate("sort /root/data.txt", fruit_state)
    assert out == ["apple", "apple", "banana", "cherry"]


def test_sort_reverse(fruit_state: dict) -> None:
    out, _ = evaluate("sort -r /root/data.txt", fruit_state)
    assert out == ["cherry", "banana", "apple", "apple"]


def test_sort_unique(fruit_state: dict) -> None:
    out, _ = evaluate("sort -u /root/data.txt", fruit_state)
    assert out == ["apple", "banana", "cherry"]


def test_sort_numeric() -> None:
    s = _with_file("10\n2\n1\n30")
    assert evaluate("sort /root/data.txt", s)[0] == ["1", "10", "2", "30"]
    assert evaluate("sort -n /root/data.txt", s)[0] == ["1", "2", "10", "30"]


# --- uniq ---
def test_uniq_adjacent() -> None:
    s = _with_file("a\na\nb\nb\nb\nc")
    assert evaluate("uniq /root/data.txt", s)[0] == ["a", "b", "c"]


def test_uniq_count() -> None:
    s = _with_file("a\na\nb\nb\nb\nc")
    out, _ = evaluate("uniq -c /root/data.txt", s)
    assert out == ["      2 a", "      3 b", "      1 c"]


def test_uniq_duplicates_only() -> None:
    s = _with_file("a\na\nb\nc\nc")
    assert evaluate("uniq -d /root/data.txt", s)[0] == ["a", "c"]


def test_uniq_only_collapses_adjacent() -> None:
    # 非隣接の重複は残る（sort していないため）。
    s = _with_file("a\nb\na")
    assert evaluate("uniq /root/data.txt", s)[0] == ["a", "b", "a"]


def test_sort_uniq_pipeline() -> None:
    s = _with_file("b\na\nb\na\nb")
    out, _ = evaluate("sort /root/data.txt | uniq -c", s)
    assert out == ["      2 a", "      3 b"]
