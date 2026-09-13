"""疑似 Git のブランチ・マージ（バックエンド_コマンド機能仕様 § 5b）のテスト。

git-team 編（Mission23〜25）のコンテンツ自体は未実装のため、
`git_ops.init_repo` / `git_ops.add_branch`（解放フック本体）を直接呼び、
`default_world_state()` 上に作った `/root/team_desk` スクラッチリポジトリで検証する。
"""

import pytest

from app.evaluator import evaluate, git_ops, progress
from app.models import default_world_state
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


@pytest.fixture
def repo_state() -> dict:
    """/root/team_desk に notes.txt 1 本だけの main リポジトリを持つ state。"""
    state = default_world_state()
    _, state = _run(state, "mkdir /root/team_desk")
    _, state = _run(state, "echo hello > /root/team_desk/notes.txt")
    git_ops.init_repo(state, "/root/team_desk", "main", "initial case notes")
    _, state = _run(state, "cd /root/team_desk")
    return state


def test_init_repo_snapshots_current_tree(repo_state: dict) -> None:
    repo = repo_state["git_state"]["repo"]
    assert repo["root"] == "/root/team_desk"
    assert repo["current_branch"] == "main"
    assert repo["branches"]["main"]["tree"]["notes.txt"]["content"] == "hello"
    assert repo["branches"]["main"]["base"] is None
    assert repo["branches"]["main"]["log"] == [
        {"id": "0000001", "message": "initial case notes"}
    ]


def test_branch_lists_current_marker(repo_state: dict) -> None:
    out, s = _run(repo_state, "git checkout -b feature")
    assert out == ["Switched to a new branch 'feature'"]

    out, _ = _run(s, "git branch")
    assert out == ["* feature", "  main"]


def test_checkout_b_rejects_existing_name(repo_state: dict) -> None:
    _, s = _run(repo_state, "git checkout -b feature")
    out, _ = _run(s, "git checkout -b feature")
    assert out == ["Error: a branch named 'feature' already exists"]


def test_checkout_switch_restores_files(repo_state: dict) -> None:
    s = repo_state
    _, s = _run(s, "git checkout -b feature")
    _, s = _run(s, "echo changed > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "feature edit"')

    out, s = _run(s, "git checkout main")
    assert out == ["Switched to branch 'main'"]
    out, s = _run(s, "cat /root/team_desk/notes.txt")
    assert out == ["hello"]

    out, s = _run(s, "git checkout feature")
    assert out == ["Switched to branch 'feature'"]
    out, _ = _run(s, "cat /root/team_desk/notes.txt")
    assert out == ["changed"]


def test_checkout_missing_branch(repo_state: dict) -> None:
    out, _ = _run(repo_state, "git checkout nope")
    assert out == ["Error: pathspec 'nope' did not match any branch"]


def test_checkout_refuses_with_uncommitted_changes(repo_state: dict) -> None:
    s = repo_state
    _, s = _run(s, "git checkout -b feature")
    _, s = _run(s, "git checkout main")
    _, s = _run(s, "echo dirty > /root/team_desk/notes.txt")

    out, _ = _run(s, "git checkout feature")
    assert out == ["Error: commit your changes before switching branches"]


def test_log_per_branch(repo_state: dict) -> None:
    s = repo_state
    _, s = _run(s, "git checkout -b feature")
    _, s = _run(s, "echo v2 > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "second"')

    out, s = _run(s, "git log")
    assert out == ["0000002 second", "0000001 initial case notes"]

    _, s = _run(s, "git checkout main")
    out, _ = _run(s, "git log")
    assert out == ["0000001 initial case notes"]


def test_fast_forward_merge(repo_state: dict) -> None:
    s = repo_state
    _, s = _run(s, "git checkout -b feature")
    _, s = _run(s, "echo changed > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "feature edit"')
    _, s = _run(s, "git checkout main")

    out, s = _run(s, "git merge feature")
    assert out == ["Fast-forward"]

    out, s = _run(s, "cat /root/team_desk/notes.txt")
    assert out == ["changed"]
    out, _ = _run(s, "git log")
    assert out == ["0000002 feature edit", "0000001 initial case notes"]


def test_three_way_merge_without_conflict(repo_state: dict) -> None:
    """main と feature が別ファイルを触っていれば、両方の変更を自動採用できる。"""
    s = repo_state
    _, s = _run(s, "touch /root/team_desk/other.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "add other file"')

    _, s = _run(s, "git checkout -b feature")
    _, s = _run(s, "echo feature_change > /root/team_desk/other.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "feature edit"')

    _, s = _run(s, "git checkout main")
    _, s = _run(s, "echo main_change > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "main edit"')

    out, s = _run(s, "git merge feature")
    assert out == ["Merge made by the 'ort' strategy."]
    assert s["git_state"]["repo"]["merging"] is None

    out, s = _run(s, "cat /root/team_desk/notes.txt")
    assert out == ["main_change"]
    out, s = _run(s, "cat /root/team_desk/other.txt")
    assert out == ["feature_change"]

    out, _ = _run(s, "git log")
    assert out[0] == "0000005 Merge branch 'feature'"


def test_merge_line_level_conflict_and_resolve_via_commit(repo_state: dict) -> None:
    s = repo_state
    _, s = _run(s, "git checkout -b reed/statement")
    _, s = _run(s, "echo reed_version > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "reed edit"')

    _, s = _run(s, "git checkout main")
    _, s = _run(s, "echo main_version > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "main edit"')

    out, s = _run(s, "git merge reed/statement")
    assert out == [
        "CONFLICT (content): Merge conflict in notes.txt",
        "Automatic merge failed; fix conflicts and then commit the result.",
    ]
    assert s["git_state"]["repo"]["merging"] == {
        "from": "reed/statement",
        "conflicts": ["notes.txt"],
    }

    out, s = _run(s, "cat /root/team_desk/notes.txt")
    assert out == [
        "<<<<<<< HEAD",
        "main_version",
        "=======",
        "reed_version",
        ">>>>>>> reed/statement",
    ]

    # 競合を解消してからセーブすると merging が消え、log に Merge branch が積まれる。
    _, s = _run(s, "echo resolved > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    out, s = _run(s, 'git commit -m "resolve"')
    assert out == ['[saved #3] resolve', "[main 0000004] Merge branch 'reed/statement'"]
    assert s["git_state"]["repo"]["merging"] is None

    out, s = _run(s, "git log")
    assert out[0] == "0000004 Merge branch 'reed/statement'"
    out, _ = _run(s, "cat /root/team_desk/notes.txt")
    assert out == ["resolved"]


def test_merge_whole_file_conflict_when_line_counts_differ(repo_state: dict) -> None:
    s = repo_state
    _, s = _run(s, "git checkout -b feature")
    _, s = _run(s, 'echo "line one" > /root/team_desk/notes.txt')
    _, s = _run(s, 'echo "line two" >> /root/team_desk/notes.txt')
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "feature multi-line"')

    _, s = _run(s, "git checkout main")
    _, s = _run(s, "echo single_line_change > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "main edit"')

    out, s = _run(s, "git merge feature")
    assert out == [
        "CONFLICT (content): Merge conflict in notes.txt",
        "Automatic merge failed; fix conflicts and then commit the result.",
    ]

    out, _ = _run(s, "cat /root/team_desk/notes.txt")
    assert out == [
        "<<<<<<< HEAD",
        "single_line_change",
        "=======",
        "line one",
        "line two",
        ">>>>>>> feature",
    ]


def test_merge_refuses_while_merging(repo_state: dict) -> None:
    s = repo_state
    _, s = _run(s, "git checkout -b a")
    _, s = _run(s, "echo a_version > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "a edit"')

    _, s = _run(s, "git checkout -b b")
    _, s = _run(s, "git checkout main")
    _, s = _run(s, "echo main_version > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "main edit"')

    _, s = _run(s, "git merge a")  # conflict, leaves merging pending
    out, _ = _run(s, "git merge b")
    assert out == ["Error: you have unmerged files; resolve them and commit first"]


def test_checkout_refuses_while_merging(repo_state: dict) -> None:
    s = repo_state
    _, s = _run(s, "git checkout -b feature")
    _, s = _run(s, "echo feature_version > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "feature edit"')

    _, s = _run(s, "git checkout main")
    _, s = _run(s, "echo main_version > /root/team_desk/notes.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "main edit"')

    _, s = _run(s, "git merge feature")  # conflict
    out, _ = _run(s, "git checkout feature")
    assert out == ["Error: you have unmerged files; resolve them and commit first"]


def test_diff_between_branches(repo_state: dict) -> None:
    s = repo_state
    _, s = _run(s, "git checkout -b feature")
    _, s = _run(s, "echo changed > /root/team_desk/notes.txt")
    _, s = _run(s, "touch /root/team_desk/only_in_feature.txt")
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "feature edit"')

    out, _ = _run(s, "git diff main feature")
    assert "diff main feature -- notes.txt" in out
    assert "< hello" in out
    assert "> changed" in out
    assert "Only in feature: only_in_feature.txt" in out


def test_add_branch_hook_sets_base_from_named_branch(repo_state: dict) -> None:
    s = repo_state
    git_ops.add_branch(
        s,
        "reed/statement",
        "main",
        {"statement.txt": {"type": "file", "content": "23:50", "mode": "rw-r--r--",
                            "owner": "detective", "mtime": "2026-01-01T00:00:00Z",
                            "immutable": False}},
        "reed's statement",
    )
    repo = s["git_state"]["repo"]
    assert repo["branches"]["reed/statement"]["tree"]["statement.txt"]["content"] == "23:50"
    assert repo["branches"]["reed/statement"]["base"] == repo["branches"]["main"]["tree"]
    assert repo["branches"]["reed/statement"]["log"] == [
        {"id": "0000002", "message": "reed's statement"}
    ]


# --- 回帰: 従来の疑似 Git（世界セーブ / クリア判定）が repo 併存下でも壊れないこと ---
def test_world_save_commit_and_mission1_push_still_work_with_repo_present() -> None:
    """git commit（世界セーブ）・git push（Mission1 クリア判定）は、
    git_state.repo が存在していても従来どおり機能する（§ 5b 追加の回帰確認）。
    """
    s = state_at_mission(1)
    _, s = _run(s, "mkdir /root/team_desk")
    _, s = _run(s, "echo hello > /root/team_desk/notes.txt")
    git_ops.init_repo(s, "/root/team_desk", "main", "initial case notes")

    _, s = _run(s, "cat /root/desk/businesscard.txt")
    _, s = _run(s, 'echo "NAME: Sam Spade" > /root/desk/businesscard.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]

    _, s = _run(s, "git add .")
    out, s = _run(s, 'git commit -m "solved"')
    assert out[0] == "[saved #1] solved"  # repo があれば枝の commit 行が続く
    assert len(s["git_state"]["commits"]) == 1
    # repo は今回の commit（世界セーブ）にリンクされていないが、通常のコミットが
    # repo の main ブランチにも波及していないことを確認する（team_desk を触って
    # いないため notes.txt は初期のまま）。
    assert s["git_state"]["repo"]["branches"]["main"]["tree"]["notes.txt"]["content"] == "hello"

    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["git_state"]["pushed"] is True
    assert 1 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 2


def test_merge_unknown_branch_and_self(repo_state: dict) -> None:
    s = repo_state
    out, _ = _run(s, "git merge nosuch")
    assert out == ["merge: nosuch - not something we can merge"]
    out, _ = _run(s, "git merge main")
    assert out == ["Already up to date."]
