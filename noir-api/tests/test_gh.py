"""`gh pr create/view/list/merge`（バックエンド_コマンド機能仕様 § 5b）のテスト。

git-team 編（Mission23〜25）のコンテンツ自体は未実装のため、`git_ops.init_repo`
で `/root/team_desk` にスクラッチリポジトリを作り、レビュールール
（`app.evaluator.pr_review.PR_REVIEWS`）はアクティブ Mission（Mission1）向けに
monkeypatch して検証する。
"""

import pytest

from app.evaluator import evaluate, git_ops, progress
from app.evaluator.pr_review import PR_REVIEWS
from app.models import default_world_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


@pytest.fixture
def repo_state() -> dict:
    state = default_world_state()
    _, state = _run(state, "mkdir /root/team_desk")
    _, state = _run(state, "echo hello > /root/team_desk/report.txt")
    git_ops.init_repo(state, "/root/team_desk", "main", "initial case notes")
    _, state = _run(state, "cd /root/team_desk")
    return state


def _make_branch_with_pr(state: dict) -> dict:
    """report/harbor ブランチで1コミットし、PR を作った state を返す。"""
    _, state = _run(state, "git checkout -b report/harbor")
    _, state = _run(state, "echo v2 > /root/team_desk/report.txt")
    _, state = _run(state, "git add .")
    _, state = _run(state, 'git commit -m "harbor report"')
    _, state = _run(state, 'gh pr create --title "Harbor report" --body "see notes"')
    return state


@pytest.fixture(autouse=True)
def _clean_pr_reviews():
    """テスト間で PR_REVIEWS への monkeypatch が漏れないようにする。"""
    original = dict(PR_REVIEWS)
    yield
    PR_REVIEWS.clear()
    PR_REVIEWS.update(original)


def test_pr_create_rejects_from_main(repo_state: dict) -> None:
    out, _ = _run(repo_state, 'gh pr create --title "x"')
    assert out == ["Error: no commits between main and main"]


def test_pr_create_and_list(repo_state: dict) -> None:
    s = _make_branch_with_pr(repo_state)
    out, s = _run(s, "gh pr list")
    assert out == ["#1  Harbor report  report/harbor"]


def test_pr_create_rejects_duplicate_open_pr(repo_state: dict) -> None:
    s = _make_branch_with_pr(repo_state)
    out, _ = _run(s, 'gh pr create --title "again"')
    assert out == ["Error: a pull request for branch 'report/harbor' already exists"]


def test_pr_view_and_merge_changes_requested_then_approved(repo_state: dict) -> None:
    s = _make_branch_with_pr(repo_state)
    active = progress.active_mission_id(s["mission_progress"])
    PR_REVIEWS[active] = lambda st: ["fix the header"]

    out, s = _run(s, "gh pr view")
    assert out == [
        "#1  Harbor report",
        "branch: report/harbor",
        "state: open",
        "review: CHANGES_REQUESTED",
        "- fix the header",
    ]

    out, s = _run(s, "gh pr merge")
    assert out == ["Error: pull request #1 is not approved"]

    # レビュー履歴に CHANGES_REQUESTED が1件だけ積まれている（同じ状態を繰り返し
    # 積まない）。
    pr = s["git_state"]["repo"]["prs"][0]
    assert [r["state"] for r in pr["reviews"]] == ["CHANGES_REQUESTED"]

    # 修正 → 承認
    del PR_REVIEWS[active]
    out, s = _run(s, "gh pr view")
    assert out == [
        "#1  Harbor report",
        "branch: report/harbor",
        "state: open",
        "review: APPROVED",
    ]
    pr = s["git_state"]["repo"]["prs"][0]
    assert [r["state"] for r in pr["reviews"]] == ["CHANGES_REQUESTED", "APPROVED"]

    out, s = _run(s, "gh pr merge")
    assert out == ["Merged pull request #1"]
    assert s["git_state"]["repo"]["prs"][0]["state"] == "merged"
    assert s["git_state"]["repo"]["current_branch"] == "main"

    out, _ = _run(s, "cat /root/team_desk/report.txt")
    assert out == ["v2"]


def test_pr_merge_succeeds_when_no_reviewer_registered(repo_state: dict) -> None:
    """アクティブ Mission に PR_REVIEWS が登録されていなければ常に APPROVED。"""
    s = _make_branch_with_pr(repo_state)
    out, s = _run(s, "gh pr view")
    assert "review: APPROVED" in out
    out, s = _run(s, "gh pr merge")
    assert out == ["Merged pull request #1"]


def test_pr_view_missing_number(repo_state: dict) -> None:
    s = _make_branch_with_pr(repo_state)
    out, _ = _run(s, "gh pr view 99")
    assert out == ["Error: no pull request found for #99"]


def test_mission25_review_rule_requires_absolute_path_and_suspect_name(repo_state: dict) -> None:
    """PR_REVIEWS[25] のプレースホルダ実装を直接検証する。"""
    s = repo_state
    _, s = _run(s, 'echo "witness statement" > /root/team_desk/report.txt')

    from app.evaluator.pr_review import PR_REVIEWS as reviews

    review = reviews[25]
    requests = review(s)
    assert "証拠は絶対パスで引用しろ（/root/team_desk/cctv.log）" in requests
    assert "容疑者名を suspects.txt と一致させろ" in requests

    _, s = _run(
        s,
        'echo "see /root/team_desk/cctv.log for the timeline" >> /root/team_desk/report.txt',
    )
    _, s = _run(s, "echo Nico Faro > /root/team_desk/suspects.txt")
    _, s = _run(s, "echo Nico Faro >> /root/team_desk/report.txt")

    requests = review(s)
    assert requests == []
