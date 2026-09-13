"""追加エピソード（git 編 Mission23〜25 / サーバー編 Mission26〜28）のゴールデントランスクリプトと誤答。

設計は docs/Mission参照ファイル.md § 5b。プレイ順序は 11 → 23 → 24 → 25 → 12 … 21 → 26 → 27 → 28 → 22。
"""

from app.content.missions import all_missions
from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def _clear(s: dict, mission_id: int, message: str) -> dict:
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"], out
    _, s = _run(s, "git add .")
    _, s = _run(s, f'git commit -m "{message}"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert mission_id in s["mission_progress"]["completed"]
    return s


def test_play_order_places_the_episodes() -> None:
    order = [m.id for m in all_missions()]
    assert order[:11] == list(range(1, 12))
    assert order[11:15] == [23, 24, 25, 29]
    assert order[15] == 12
    assert order[-4:] == [26, 27, 28, 22]


# --- Mission23 ---
def test_mission23_golden_transcript() -> None:
    s = state_at_mission(23)
    assert s["git_state"]["repo"]["current_branch"] == "main"
    _, s = _run(s, "cd /root/team_desk")
    _, s = _run(s, "git checkout -b lead/harbor")
    _, s = _run(s, 'echo "LEAD 3: HARBOR van seen at pier 13 (cctv)" >> case_notes.txt')
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "harbor lead"')
    _, s = _run(s, "git checkout main")
    out, _ = _run(s, "cat case_notes.txt")
    assert not any("HARBOR" in ln for ln in out)  # 枝に置いてきたので main には無い
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: main does not carry the harbor lead yet (merge the branch)"]
    out, s = _run(s, "git merge lead/harbor")
    assert out == ["Fast-forward"]
    out, _ = _run(s, "cat case_notes.txt")
    assert any("HARBOR" in ln for ln in out)
    s = _clear(s, 23, "merged")
    assert progress.active_mission_id(s["mission_progress"]) == 24


def test_mission23_requires_a_branch() -> None:
    s = state_at_mission(23)
    _, s = _run(s, 'echo "LEAD 3: HARBOR" >> /root/team_desk/case_notes.txt')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: cut a branch before you follow the lead"]


# --- Mission24 ---
def test_mission24_conflict_then_resolve() -> None:
    s = state_at_mission(24)
    assert "reed/statement" in s["git_state"]["repo"]["branches"]
    _, s = _run(s, "cd /root/team_desk")
    out, s = _run(s, "git merge reed/statement")
    assert any("CONFLICT" in ln for ln in out)
    out, _ = _run(s, "cat statement.txt")
    assert any(ln.startswith("<<<<<<<") for ln in out)
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Error: unresolved conflict markers in statement.txt"]

    _, s = _run(s, 'echo "WITNESS STATEMENT - harbor night watchman" > statement.txt')
    _, s = _run(s, 'echo "I saw a man leave warehouse B at 23:50." >> statement.txt')
    _, s = _run(s, 'echo "He carried a ledger under his arm." >> statement.txt')
    _, s = _run(s, "git add statement.txt")
    out, s = _run(s, 'git commit -m "resolve"')
    assert any("Merge branch 'reed/statement'" in ln for ln in out)
    s = _clear(s, 24, "merged reed")


def test_mission24_wrong_side_contradicts_cctv() -> None:
    s = state_at_mission(24)
    _, s = _run(s, "cd /root/team_desk")
    _, s = _run(s, "git merge reed/statement")
    _, s = _run(s, 'echo "WITNESS STATEMENT - harbor night watchman" > statement.txt')
    _, s = _run(s, 'echo "I saw a man leave warehouse B at 23:10." >> statement.txt')
    _, s = _run(s, "git add statement.txt")
    _, s = _run(s, 'git commit -m "keep mine"')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: the statement contradicts cctv.log"]


# --- Mission25 ---
def test_mission25_review_loop() -> None:
    s = state_at_mission(25)
    _, s = _run(s, "cd /root/team_desk")
    _, s = _run(s, "git checkout -b report/harbor")
    _, s = _run(s, 'echo "Suspect: Nico Faro" >> report.txt')
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "draft"')
    out, s = _run(s, 'gh pr create --title "Harbor case" --body "draft"')
    assert out[0] == "#1"
    out, s = _run(s, "gh pr view")
    assert "review: CHANGES_REQUESTED" in out
    out, s = _run(s, "gh pr merge")
    assert out == ["Error: pull request #1 is not approved"]
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: the pull request is not merged yet"]

    _, s = _run(s, 'echo "Evidence: /root/team_desk/cctv.log 23:50" >> report.txt')
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "cite"')
    out, s = _run(s, "gh pr view")
    assert "review: APPROVED" in out
    out, s = _run(s, "gh pr merge")
    assert out == ["Merged pull request #1"]
    s = _clear(s, 25, "report merged")
    assert progress.active_mission_id(s["mission_progress"]) == 29


def test_mission25_requires_a_pull_request() -> None:
    s = state_at_mission(25)
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: open a pull request with gh pr create"]


# --- Mission26 ---
def test_mission26_golden_transcript() -> None:
    s = state_at_mission(26)
    _, s = _run(s, "ssh archive_node")
    out, s = _run(s, "df -h")
    assert any("98%" in ln and "/var" in ln for ln in out)
    out, s = _run(s, "du -sh /var/log/*")
    assert any(ln.startswith("17G") and "spool.log" in ln for ln in out)
    _, s = _run(s, "systemctl status archive-indexer")
    out, s = _run(s, "journalctl -u archive-indexer")
    assert any("No space left on device" in ln for ln in out)
    _, s = _run(s, "exit")
    out, s = _run(s, 'echo "spool.log is huge"')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    _, s = _run(s, 'echo "/var/log/spool.log filled /var: No space left on device"')
    s = _clear(s, 26, "archive")


def test_mission26_requires_all_four_diagnostics() -> None:
    s = state_at_mission(26)
    _, s = _run(s, "ssh archive_node")
    _, s = _run(s, "df -h")
    _, s = _run(s, "exit")
    _, s = _run(s, 'echo "/var/log/spool.log No space left"')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: diagnose before you report (df / du / systemctl / journalctl)"]


# --- Mission27 ---
def test_mission27_golden_transcript_and_wrong_stop() -> None:
    s = state_at_mission(27)
    _, s = _run(s, "ssh corp_server")
    out, s = _run(s, "curl http://169.254.169.254/latest/meta-data/instance-id")
    assert out == ["i-0f3e9a7c2b1d4e5f6"]
    out, s = _run(s, "ss -tln")
    assert any(":4444" in ln for ln in out)
    _, s = _run(s, "systemctl stop app-web")
    _, s = _run(s, "exit")
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: you stopped the legitimate service (app-web)"]
    _, s = _run(s, "ssh corp_server")
    _, s = _run(s, "systemctl start app-web")
    _, s = _run(s, "exit")
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: the back door is still open (backdoor-relay)"]
    _, s = _run(s, "ssh corp_server")
    _, s = _run(s, "systemctl stop backdoor-relay")
    out, s = _run(s, "ss -tln")
    assert not any(":4444" in ln for ln in out)
    _, s = _run(s, "exit")
    _, s = _run(s, 'echo "i-0f3e9a7c2b1d4e5f6 port 4444 backdoor-relay stopped"')
    s = _clear(s, 27, "cloud")


# --- Mission28 ---
def test_mission28_golden_transcript() -> None:
    s = state_at_mission(28)
    _, s = _run(s, "ssh archive_node")
    out, s = _run(s, "journalctl -u backup")
    assert any("Connection refused" in ln for ln in out)
    _, s = _run(s, "cat /etc/os-release")
    _, s = _run(s, "exit")
    _, s = _run(s, 'echo "Debian and Ubuntu"')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: visit both sites before you report"]
    _, s = _run(s, "ssh corp_server")
    out, s = _run(s, "sh /opt/app/case_file.sh")
    assert out == ["Warning: the backup route is still closed"]
    _, s = _run(s, "systemctl start sshd")
    _, s = _run(s, "cat /etc/os-release")
    _, s = _run(s, "exit")
    s = _clear(s, 28, "two sites")
    assert progress.active_mission_id(s["mission_progress"]) == 22


# --- Mission29（やらかし体験室） ---
def test_mission29_sandbox_rm_dd_and_restore() -> None:
    s = state_at_mission(29)
    assert s["sandbox"]["backup"]["root"]["children"]["team_desk"]
    _, s = _run(s, "ls /root/team_desk")
    out, s = _run(s, "rm /root/team_desk")
    assert out == ["rm: cannot remove '/root/team_desk': Is a directory"]
    out, s = _run(s, "rm -rf /root/team_desk")
    assert out[-1] == "removed directory '/root/team_desk'"
    out, _ = _run(s, "ls /root")
    assert "team_desk" not in out
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: the evidence disk is not wiped (dd)"]
    out, s = _run(s, "dd if=/dev/zero of=/dev/sdb")
    assert out[0] == "2048+0 records in"
    out, _ = _run(s, "ls /root/vault")
    assert out == []
    s = _clear(s, 29, "duress")
    # 予備の機械を外す＝本物の世界が戻る。sandbox は消え、rm は再び禁止
    assert "sandbox" not in s
    out, _ = _run(s, "ls /root/team_desk")
    assert "case_notes.txt" in out
    out, _ = _run(s, "ls /root/vault")
    assert out != []
    assert _run(s, "rm -rf /root/desk")[0] == ["Error: command not allowed"]
    assert progress.active_mission_id(s["mission_progress"]) == 12


def test_rm_and_dd_stay_denied_outside_the_sandbox() -> None:
    for mission_id in (1, 12, 22):
        s = state_at_mission(mission_id)
        assert _run(s, "rm -rf /")[0] == ["Error: command not allowed"]
        assert _run(s, "dd if=/dev/zero of=/dev/sda")[0] == ["Error: command not allowed"]


def test_mission29_case_file_survives_rm_rf_root() -> None:
    """やけになって /root ごと消しても判定スクリプトは動く（詰まない）。"""
    s = state_at_mission(29)
    _, s = _run(s, "rm -rf /root")
    _, s = _run(s, "dd if=/dev/zero of=/dev/sdb")
    assert _run(s, "ls")[0] == ["Error: path not found"]  # cwd /root ごと消えている
    _, s = _run(s, "ls /")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
