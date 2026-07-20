"""Mission12「幽霊回線を追え」: dig/ping/ss と ghost.example への突入フロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_dig_resolves_known_host() -> None:
    s = build_initial_state(12)
    out, _ = _run(s, "dig ghost.example")
    assert any("10.66.6.6" in ln for ln in out)


def test_dig_unknown_host() -> None:
    s = build_initial_state(12)
    out, _ = _run(s, "dig nowhere.example")
    assert out == ["Host not found"]


def test_host_command() -> None:
    s = build_initial_state(12)
    out, _ = _run(s, "host ghost.example")
    assert out == ["ghost.example has address 10.66.6.6"]


def test_ping_known_host() -> None:
    s = build_initial_state(12)
    out, _ = _run(s, "ping ghost.example")
    assert "PING ghost.example (10.66.6.6): 56 data bytes" in out[0]
    assert any("0% packet loss" in ln for ln in out)


def test_ping_unknown_host() -> None:
    s = build_initial_state(12)
    out, _ = _run(s, "ping nowhere.example")
    assert out == ["Host not found"]


def test_ss_shows_listening_port() -> None:
    s = build_initial_state(12)
    out, _ = _run(s, "ss -tln")
    assert any("22" in ln for ln in out)


def test_ssh_by_hostname_and_by_ip() -> None:
    s = build_initial_state(12)
    out, s2 = _run(s, "ssh ghost.example")
    assert out == ["Connected to ghost.example"]
    assert s2["current_path"] == "/den"

    s3 = build_initial_state(12)
    out2, s4 = _run(s3, "ssh 10.66.6.6")
    assert out2 == ["Connected to 10.66.6.6"]
    assert s4["current_path"] == "/den"


def test_mission12_golden_transcript() -> None:
    s = build_initial_state(12)

    _, s = _run(s, "dig ghost.example")
    _, s = _run(s, "ping ghost.example")
    _, s = _run(s, "ss -tln")
    _, s = _run(s, "ssh ghost.example")
    _, s = _run(s, "cat /den/evidence/orders.txt")
    _, s = _run(s, 'echo "BOSS: Selene Vance" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "ghost traced"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission12_ssh_before_investigation_blocks_clear() -> None:
    s = build_initial_state(12)
    # dig/ping せずいきなり ssh してしまうと順序不成立。
    _, s = _run(s, "ssh ghost.example")
    _, s = _run(s, "cat /den/evidence/orders.txt")
    _, s = _run(s, 'echo "BOSS: Selene Vance" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: investigate before you breach"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission12_wrong_order_blocks_clear() -> None:
    s = build_initial_state(12)
    # ping より先に ssh してしまうと順序不成立（dig はしている）。
    _, s = _run(s, "dig ghost.example")
    _, s = _run(s, "ssh ghost.example")
    _, s = _run(s, "ping ghost.example")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: investigate before you breach"]
