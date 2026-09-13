"""`gh`（GitHub CLI 相当。バックエンド_コマンド機能仕様 § 5b。git-team 編
Mission23〜25 想定。2026-09-13 確定、実装中）。

`git` と同じく PATH 解決の対象外の組み込み扱い（allowlist.py / engine.py の
`_BUILTINS` を参照）。PR は `git_state.repo.prs` に保持し、レビューは
`app/evaluator/pr_review.py` の `PR_REVIEWS[active_mission_id]` で毎回評価する
（Mission に紐付くレビュアーが無ければ常に APPROVED）。
"""

import copy

from app.evaluator import fs, progress
from app.evaluator.errors import CommandError
from app.evaluator.git_branches import _next_commit_id
from app.evaluator.pr_review import PR_REVIEWS
from app.evaluator.registry import command

PR_URL_BASE = "https://hq.example/casework/pull"
_REVIEWER = "Chief Morgan"


def _repo(state: dict) -> dict:
    repo = state.get("git_state", {}).get("repo")
    if repo is None:
        raise CommandError("Error: not a git repository")
    return repo


def _find_flag_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _find_pr(repo: dict, number: int | None) -> dict | None:
    """number 指定ならその PR、無指定なら現在の枝の PR（最後に作られたもの）。"""
    if number is not None:
        return next((pr for pr in repo["prs"] if pr["number"] == number), None)
    branch = repo["current_branch"]
    matches = [pr for pr in repo["prs"] if pr["branch"] == branch]
    return matches[-1] if matches else None


def _resolve_pr(repo: dict, number: int | None) -> dict:
    pr = _find_pr(repo, number)
    if pr is None:
        if number is not None:
            raise CommandError(f"Error: no pull request found for #{number}")
        raise CommandError(
            f"Error: no pull request found for current branch '{repo['current_branch']}'"
        )
    return pr


def _evaluate_review(state: dict, pr: dict) -> list[str]:
    """現在の state で PR に残っている指摘を計算し、状態が変わっていれば
    `pr["reviews"]` に履歴を1件積む（CHANGES_REQUESTED→APPROVED の遷移を残すため）。
    """
    mission_id = progress.focused_mission_id(state)
    reviewer = PR_REVIEWS.get(mission_id) if mission_id is not None else None
    requests = reviewer(state) if reviewer is not None else []

    new_state = "CHANGES_REQUESTED" if requests else "APPROVED"
    reviews = pr.setdefault("reviews", [])
    if not reviews or reviews[-1]["state"] != new_state:
        reviews.append(
            {"by": _REVIEWER, "state": new_state, "comments": list(requests)}
        )
    return requests


@command("gh")
def cmd_gh(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    if len(argv) < 3 or argv[1] != "pr":
        raise CommandError("Error: command not allowed")

    sub = argv[2]
    if sub == "create":
        return _pr_create(state, argv)
    if sub == "view":
        return _pr_view(state, argv)
    if sub == "list":
        return _pr_list(state), state
    if sub == "merge":
        return _pr_merge(state, argv)
    raise CommandError("Error: command not allowed")


def _pr_create(state: dict, argv: list[str]) -> tuple[list[str], dict]:
    repo = _repo(state)
    title = _find_flag_value(argv, "--title")
    if not title:
        raise CommandError("Error: invalid input")
    body = _find_flag_value(argv, "--body") or ""

    branch = repo["current_branch"]
    if branch == "main":
        raise CommandError("Error: no commits between main and main")
    if any(pr["branch"] == branch and pr["state"] == "open" for pr in repo["prs"]):
        raise CommandError(f"Error: a pull request for branch '{branch}' already exists")

    number = len(repo["prs"]) + 1
    repo["prs"].append(
        {
            "number": number,
            "title": title,
            "body": body,
            "branch": branch,
            "state": "open",
            "reviews": [],
        }
    )
    return [f"#{number}", f"{PR_URL_BASE}/{number}"], state


def _parse_number(argv: list[str]) -> int | None:
    operands = [a for a in argv[3:] if not a.startswith("-")]
    if not operands:
        return None
    try:
        return int(operands[0])
    except ValueError as exc:
        raise CommandError("Error: invalid input") from exc


def _pr_view(state: dict, argv: list[str]) -> tuple[list[str], dict]:
    repo = _repo(state)
    number = _parse_number(argv)
    pr = _resolve_pr(repo, number)

    requests = _evaluate_review(state, pr)
    lines = [
        f"#{pr['number']}  {pr['title']}",
        f"branch: {pr['branch']}",
        f"state: {pr['state']}",
    ]
    if requests:
        lines.append("review: CHANGES_REQUESTED")
        lines.extend(f"- {req}" for req in requests)
    else:
        lines.append("review: APPROVED")
    return lines, state


def _pr_list(state: dict) -> list[str]:
    repo = _repo(state)
    return [
        f"#{pr['number']}  {pr['title']}  {pr['branch']}"
        for pr in repo["prs"]
        if pr["state"] == "open"
    ]


def _pr_merge(state: dict, argv: list[str]) -> tuple[list[str], dict]:
    repo = _repo(state)
    number = _parse_number(argv)
    pr = _resolve_pr(repo, number)

    requests = _evaluate_review(state, pr)
    if requests:
        raise CommandError(f"Error: pull request #{pr['number']} is not approved")
    if repo.get("merging"):
        raise CommandError("Error: cannot merge, resolve conflicts on the branch first")

    branch_tree = repo["branches"][pr["branch"]]["tree"]
    main = repo["branches"]["main"]

    main["tree"] = copy.deepcopy(branch_tree)
    main["log"].append(
        {
            "id": _next_commit_id(repo),
            "message": f"Merge pull request #{pr['number']} from {pr['branch']}",
        }
    )

    pr["state"] = "merged"
    repo["current_branch"] = "main"
    node = fs.get_node(state, repo["root"])
    node["children"] = copy.deepcopy(main["tree"])

    return [f"Merged pull request #{pr['number']}"], state
