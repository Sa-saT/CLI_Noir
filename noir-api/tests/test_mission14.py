"""Mission14「鏡の館」: シンボリックリンク（ls -l/file/cat/ln）のフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_ls_long_shows_arrow_for_links() -> None:
    s = build_initial_state(14)
    out, _ = _run(s, "ls -l /root/mirror_hall")
    deed_a = [ln for ln in out if ln.endswith("deed_a.txt -> /root/mirror_hall/deed_b.txt")]
    assert len(deed_a) == 1
    assert deed_a[0].startswith("l")

    vault = [ln for ln in out if ln.endswith(" vault")]
    assert vault[0].startswith("d")


def test_file_reports_symbolic_link() -> None:
    s = build_initial_state(14)
    out, _ = _run(s, "file /root/mirror_hall/deed_a.txt")
    assert out == ["/root/mirror_hall/deed_a.txt: symbolic link to /root/mirror_hall/deed_b.txt"]


def test_file_reports_real_file_as_text() -> None:
    s = build_initial_state(14)
    out, _ = _run(s, "file /root/mirror_hall/vault/real_deed.txt")
    assert out == ["/root/mirror_hall/vault/real_deed.txt: ASCII text"]


def test_cat_follows_single_hop_link() -> None:
    s = build_initial_state(14)
    out, _ = _run(s, "cat /root/mirror_hall/deed_b.txt")
    assert out == ["DEED: THE OLD LIGHTHOUSE PROPERTY"]


def test_cat_follows_multi_hop_link() -> None:
    s = build_initial_state(14)
    # deed_c -> deed_a -> deed_b -> real_deed.txt (3 hops)
    out, _ = _run(s, "cat /root/mirror_hall/deed_c.txt")
    assert out == ["DEED: THE OLD LIGHTHOUSE PROPERTY"]


def test_ln_creates_new_link_that_resolves() -> None:
    s = build_initial_state(14)
    _, s = _run(s, "ln -s /root/mirror_hall/vault/real_deed.txt /root/mirror_hall/deed_d.txt")
    out, _ = _run(s, "cat /root/mirror_hall/deed_d.txt")
    assert out == ["DEED: THE OLD LIGHTHOUSE PROPERTY"]


def test_ln_without_s_flag_invalid() -> None:
    s = build_initial_state(14)
    out, _ = _run(s, "ln /root/mirror_hall/vault/real_deed.txt /root/mirror_hall/deed_d.txt")
    assert out == ["Error: invalid input"]


def test_mission14_golden_transcript() -> None:
    s = build_initial_state(14)

    _, s = _run(s, "ls -l /root/mirror_hall")
    _, s = _run(s, "file /root/mirror_hall/deed_a.txt")
    _, s = _run(s, "cat /root/mirror_hall/deed_a.txt")
    _, s = _run(s, 'echo "/root/mirror_hall/vault/real_deed.txt" > report.txt')

    out, s = _run(s, "sh /root/mirror_hall/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "found the real deed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission14_link_path_report_is_a_mirror() -> None:
    s = build_initial_state(14)
    _, s = _run(s, 'echo "/root/mirror_hall/deed_a.txt" > report.txt')
    out, s = _run(s, "sh /root/mirror_hall/case_file.sh")
    assert out == ["Error: that is only a mirror"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission14_no_report_blocks_clear() -> None:
    s = build_initial_state(14)
    _, s = _run(s, "cat /root/mirror_hall/deed_a.txt")
    out, s = _run(s, "sh /root/mirror_hall/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
