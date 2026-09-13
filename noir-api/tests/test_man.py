"""`man` = 捜査ハンドブック（機能 6）。"""

from app.content.manpages import MANPAGES
from app.evaluator import evaluate
from app.evaluator.registry import _REGISTRY
from app.models import default_world_state


def test_every_registered_command_has_a_manpage() -> None:
    missing = sorted(n for n in _REGISTRY if n not in MANPAGES)
    assert missing == [], missing


def test_man_renders_sections() -> None:
    out, _ = evaluate("man ls", default_world_state())
    assert out[0].startswith("LS(1)")
    assert "NAME" in out and "SYNOPSIS" in out and "IN THIS OFFICE" in out
    assert any("ls - ディレクトリの中身を一覧する" in ln for ln in out)


def test_man_section_and_missing() -> None:
    out, _ = evaluate("man 5 crontab", default_world_state())
    assert out[0].startswith("CRONTAB(5)")
    assert evaluate("man xyzzy", default_world_state())[0] == ["No manual entry for xyzzy"]
    assert evaluate("man", default_world_state())[0] == ["What manual page do you want?"]


def test_whatis_and_apropos() -> None:
    s = default_world_state()
    assert evaluate("whatis grep", s)[0][0].startswith("grep (1)")
    out, _ = evaluate("apropos 指紋", s)
    assert any(ln.startswith("md5sum") for ln in out)
    assert evaluate("apropos zzz", s)[0] == ["zzz: nothing appropriate."]


def test_man_works_while_path_is_broken() -> None:
    """Mission21 で PATH が壊れていても手引きは読める（組み込み扱い）。"""
    from tests.helpers import state_at_mission

    s = state_at_mission(21)
    out, _ = evaluate("man export", s)
    assert out[0].startswith("EXPORT(1)")
