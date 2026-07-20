"""Mission11「切り裂かれた脅迫状」: sort/cut/paste/tr で断片を復元するフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state
from app.models import default_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


# --- paste ---
def test_paste_joins_two_files_with_tab() -> None:
    s = default_state()
    root = s["filesystem"]["root"]["children"]
    root["a.txt"] = {
        "type": "file", "content": "1\n2", "mode": "rw-r--r--",
        "owner": "detective", "mtime": "2026-01-01T00:00:00Z", "immutable": False,
    }
    root["b.txt"] = {
        "type": "file", "content": "x\ny", "mode": "rw-r--r--",
        "owner": "detective", "mtime": "2026-01-01T00:00:00Z", "immutable": False,
    }
    out, _ = _run(s, "paste /root/a.txt /root/b.txt")
    assert out == ["1\tx", "2\ty"]


def test_paste_custom_delimiter() -> None:
    s = default_state()
    root = s["filesystem"]["root"]["children"]
    root["a.txt"] = {
        "type": "file", "content": "1", "mode": "rw-r--r--",
        "owner": "detective", "mtime": "2026-01-01T00:00:00Z", "immutable": False,
    }
    root["b.txt"] = {
        "type": "file", "content": "x", "mode": "rw-r--r--",
        "owner": "detective", "mtime": "2026-01-01T00:00:00Z", "immutable": False,
    }
    out, _ = _run(s, "paste -d: /root/a.txt /root/b.txt")
    assert out == ["1:x"]


# --- tr ---
def test_tr_transliterates() -> None:
    s = default_state()
    out, _ = _run(s, "echo abc | tr abc xyz")
    assert out == ["xyz"]


def test_tr_delete() -> None:
    s = default_state()
    out, _ = _run(s, "echo 'h e l l o' | tr -d ' '")
    assert out == ["hello"]


def test_tr_mismatched_length_invalid() -> None:
    s = default_state()
    out, _ = _run(s, "echo abc | tr ab xyz")
    assert out == ["Error: invalid input"]


# --- Mission11 ---
def test_mission11_sort_then_cut_reconstructs_text() -> None:
    s = build_initial_state(11)
    out, _ = _run(s, "sort /root/scraps/pieces.txt | cut -d: -f2")
    assert out == ["MIDNIGHT AT THE OLD PIER", "BRING THE LEDGER", "ALONE"]


def test_mission11_golden_transcript() -> None:
    s = build_initial_state(11)

    _, s = _run(s, "sort /root/scraps/pieces.txt | cut -d: -f2")
    _, s = _run(
        s, 'echo "MIDNIGHT AT THE OLD PIER BRING THE LEDGER ALONE" > report.txt'
    )

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "note restored"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission11_incomplete_text_blocks_clear() -> None:
    s = build_initial_state(11)
    _, s = _run(s, "sort /root/scraps/pieces.txt | cut -d: -f2")
    _, s = _run(s, 'echo "MIDNIGHT AT THE OLD PIER" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
