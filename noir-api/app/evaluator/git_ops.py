"""疑似 Git（commit=セーブ / push=クリア判定）。

設計指示書 § 10 / バックエンド_コマンド機能仕様 § 5:
  git status / add / commit -m "<msg>" / push。
実 Git 連携なし。git は engine が第1トークンで判定後、ここでサブコマンド分岐する。
"""

import copy

from app.evaluator.errors import CommandError
from app.evaluator.fs import now_iso
from app.evaluator.registry import command

COMMIT_CAP = 30  # git_state.commits の上限 / Mission（設計指示書 § 4）


@command("git")
def cmd_git(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    sub = argv[1] if len(argv) > 1 else ""
    if sub == "status":
        return _status(state), state
    if sub == "add":
        return _add(state, argv)
    if sub == "commit":
        return _commit(state, argv)
    if sub == "push":
        return _push(state)
    raise CommandError("Error: command not allowed")


def _status(state: dict) -> list[str]:
    git = state["git_state"]
    checked = state["mission_flags"].get("case_checked", False)
    if git["commits"] and checked:
        return ["Ready to push"]
    if git["staged"]:
        return ["Changes staged"]
    if git["commits"]:
        return ["No commits yet"]
    return ["Nothing to commit"]


def _add(state: dict, argv: list[str]) -> tuple[list[str], dict]:
    # 変更ファイル + mission_flags の現在値を staged に上げる（MVP は対象名を記録）。
    targets = argv[2:] or ["."]
    state["git_state"]["staged"] = list(targets)
    return [], state


def _commit(state: dict, argv: list[str]) -> tuple[list[str], dict]:
    git = state["git_state"]
    if not git["staged"]:
        raise CommandError("Error: nothing to commit")

    message = None
    if "-m" in argv:
        idx = argv.index("-m")
        if idx + 1 < len(argv) and argv[idx + 1].strip():
            message = argv[idx + 1]
    if message is None:
        raise CommandError("Error: commit message required")

    next_id = (git["commits"][-1]["id"] + 1) if git["commits"] else 1
    git["commits"].append(
        {
            "id": next_id,
            "message": message,
            "snapshot": {
                "current_path": state["current_path"],
                "filesystem": copy.deepcopy(state["filesystem"]),
                "mission_flags": copy.deepcopy(state["mission_flags"]),
                "env_vars": copy.deepcopy(state.get("env_vars", {})),
            },
            "created_at": now_iso(),
        }
    )
    # 上限超過時は最古のセーブから削除（設計指示書 § 4）。
    if len(git["commits"]) > COMMIT_CAP:
        del git["commits"][0 : len(git["commits"]) - COMMIT_CAP]
    git["staged"] = []
    return [f"[saved #{next_id}] {message}"], state


def _push(state: dict) -> tuple[list[str], dict]:
    git = state["git_state"]
    if not git["commits"]:
        raise CommandError("Error: push not allowed before commit")

    latest = git["commits"][-1]
    checked = latest["snapshot"]["mission_flags"].get("case_checked", False)
    if not checked:
        raise CommandError("Error: mission requirements not met")

    git["pushed"] = True
    state["mission_flags"]["completed"] = True
    return ["Mission Complete! Next mission unlocked."], state
