"""隠しファイル収集（機能 5）とご褒美コマンド（機能 12）。"""

from app.content.collection import FRAGMENTS, TOTAL
from app.evaluator import evaluate, rewards
from app.models import default_world_state
from tests.helpers import state_at_mission


def _run(s, line):
    return evaluate(line, s)


def _read(s, cmd):
    n = len(s.get("resolved_command_log", []))
    out, s = _run(s, cmd)
    entry = s["resolved_command_log"][-1] if len(s.get("resolved_command_log", [])) > n else None
    return out, s, rewards.register(s, cmd, entry)


def test_fragments_are_hidden_until_ls_a() -> None:
    s = default_world_state()
    assert ".old_photo_note" not in _run(s, "ls /root/desk")[0]
    assert ".old_photo_note" in _run(s, "ls -a /root/desk")[0]
    assert _run(s, "ls -a /root/desk")[0][:2] == [".", ".."]


def test_every_fragment_exists_in_its_released_area() -> None:
    s = state_at_mission(22)
    for path in FRAGMENTS:
        out, _ = _run(s, f"cat {path}")
        assert out and not out[0].startswith("Error"), path


def test_reading_a_fragment_registers_once() -> None:
    s = default_world_state()
    out, s, events = _read(s, "cat /root/desk/.old_photo_note")
    assert events == [{"kind": "fragment", "no": 1, "title": "写真の裏", "found": 1, "total": TOTAL}]
    _, s, events = _read(s, "cat /root/desk/.old_photo_note")
    assert events == []
    # 読み系以外（ls -a）では登録しない
    _, s, events = _read(s, "ls -a /root/desk")
    assert events == []


def test_rewards_unlock_cowsay_then_figlet() -> None:
    s = state_at_mission(22)
    assert _run(s, "cowsay hi")[0] == ["Error: command not found"]
    paths = list(FRAGMENTS)
    for path in paths[:4]:
        _, s, _ = _read(s, f"cat {path}")
    _, s, events = _read(s, f"cat {paths[4]}")
    assert any(e == {"kind": "unlock", "command": "cowsay", "label": "回想を 5 つ集めた"} for e in events)
    out, _ = _run(s, "cowsay moo")
    assert out[1] == "< moo >"
    assert _run(s, "figlet HI")[0] == ["Error: command not found"]
    for path in paths[5:]:
        _, s, events = _read(s, f"cat {path}")
    assert "figlet" in s["unlocked_commands"]
    out, _ = _run(s, "figlet HI")
    assert len(out) == 5 and "#" in out[0]
    listing = rewards.listing(s)
    assert listing["total"] == TOTAL and [f["no"] for f in listing["fragments"]] == list(range(1, TOTAL + 1))
