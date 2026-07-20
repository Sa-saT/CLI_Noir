"""Mission17「指紋は嘘をつかない」: md5sum で改ざんされた1通を特定するフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_md5sum_output_format() -> None:
    s = build_initial_state(17)
    out, _ = _run(s, "md5sum /root/contracts/copy_1.txt")
    digest, path = out[0].split("  ")
    assert len(digest) == 32
    assert path == "/root/contracts/copy_1.txt"


def test_identical_content_same_hash() -> None:
    s = build_initial_state(17)
    out1, _ = _run(s, "md5sum /root/contracts/copy_1.txt")
    out2, _ = _run(s, "md5sum /root/contracts/copy_2.txt")
    assert out1[0].split("  ")[0] == out2[0].split("  ")[0]


def test_tampered_copy_has_different_hash() -> None:
    s = build_initial_state(17)
    out1, _ = _run(s, "md5sum /root/contracts/copy_1.txt")
    out4, _ = _run(s, "md5sum /root/contracts/copy_4.txt")
    assert out1[0].split("  ")[0] != out4[0].split("  ")[0]


def test_ledger_matches_original_hash() -> None:
    s = build_initial_state(17)
    out, _ = _run(s, "md5sum /root/contracts/copy_1.txt")
    digest = out[0].split("  ")[0]
    ledger_out, _ = _run(s, "cat /root/contracts/ledger.txt")
    assert digest in ledger_out[0]


def test_md5sum_multiple_files() -> None:
    s = build_initial_state(17)
    out, _ = _run(s, "md5sum /root/contracts/copy_1.txt /root/contracts/copy_4.txt")
    assert len(out) == 2


def test_sha256sum_output_length() -> None:
    s = build_initial_state(17)
    out, _ = _run(s, "sha256sum /root/contracts/copy_1.txt")
    digest = out[0].split("  ")[0]
    assert len(digest) == 64


def test_mission17_golden_transcript() -> None:
    s = build_initial_state(17)

    for i in range(1, 6):
        _, s = _run(s, f"md5sum /root/contracts/copy_{i}.txt")
    _, s = _run(s, "diff /root/contracts/copy_1.txt /root/contracts/copy_4.txt")
    _, s = _run(s, 'echo "copy_4 was tampered" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "forgery identified"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission17_requires_md5sum_and_report() -> None:
    s = build_initial_state(17)
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
