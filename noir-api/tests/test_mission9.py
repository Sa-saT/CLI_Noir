"""Mission9「封印された証拠品」: file/tar/unzip/gunzip で多重アーカイブを開封するフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_file_reveals_disguised_archive_type() -> None:
    s = build_initial_state(9)
    out, _ = _run(s, "file evidence.dat")
    assert out == ["evidence.dat: gzip compressed data"]


def test_file_plain_text() -> None:
    s = build_initial_state(9)
    out, _ = _run(s, "file case_file.sh")
    assert out == ["case_file.sh: ASCII text"]


def test_tar_extracts_sealed_zip_into_cwd() -> None:
    s = build_initial_state(9)
    _, s = _run(s, "tar -xzf evidence.dat")
    out, _ = _run(s, "ls")
    assert "sealed.zip" in out


def test_tar_rejects_non_archive() -> None:
    s = build_initial_state(9)
    out, _ = _run(s, "tar -xzf case_file.sh")
    assert out == ["Error: invalid input"]


def test_second_layer_unzip_reveals_final_clue() -> None:
    s = build_initial_state(9)
    _, s = _run(s, "tar -xzf evidence.dat")
    out, s = _run(s, "file sealed.zip")
    assert out == ["sealed.zip: Zip archive data"]

    _, s = _run(s, "unzip sealed.zip")
    out, _ = _run(s, "cat final_clue.txt")
    assert out == ["CODE: NOIR-1948"]


def test_mission9_golden_transcript() -> None:
    s = build_initial_state(9)

    _, s = _run(s, "file evidence.dat")
    _, s = _run(s, "tar -xzf evidence.dat")
    _, s = _run(s, "file sealed.zip")
    _, s = _run(s, "unzip sealed.zip")
    _, s = _run(s, "cat final_clue.txt")
    _, s = _run(s, 'echo "CODE: NOIR-1948" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "evidence unsealed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_gunzip_replaces_gz_with_decompressed_file() -> None:
    s = build_initial_state(9)
    root = s["filesystem"]["root"]["children"]
    root["notes.txt.gz"] = {
        "type": "file",
        "content": "",
        "mode": "rw-r--r--",
        "owner": "detective",
        "mtime": "2026-01-01T00:00:00Z",
        "immutable": True,
        "archive_type": "gzip",
        "archive_content": {
            "type": "file",
            "content": "hidden note",
            "mode": "rw-r--r--",
            "owner": "detective",
            "mtime": "2026-01-01T00:00:00Z",
            "immutable": False,
        },
    }
    _, s = _run(s, "gunzip notes.txt.gz")
    out, _ = _run(s, "cat notes.txt")
    assert out == ["hidden note"]
    assert "notes.txt.gz" not in s["filesystem"]["root"]["children"]
