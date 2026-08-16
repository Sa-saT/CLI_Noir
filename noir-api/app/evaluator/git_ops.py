"""疑似 Git（commit=セーブ / push=クリア判定）。

設計指示書 § 10 / バックエンド_コマンド機能仕様 § 5:
  git status / add / commit -m "<msg>" / push。
実 Git 連携なし。git は engine が第1トークンで判定後、ここでサブコマンド分岐する。
"""

import copy

from app.evaluator import progress
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
    checked = progress.flags(state).get("case_checked", False)
    if git["commits"] and checked:
        return ["Ready to push"]
    if git["staged"]:
        return ["Changes staged"]
    if git["commits"]:
        return ["No commits yet"]
    return ["Nothing to commit"]


def _add(state: dict, argv: list[str]) -> tuple[list[str], dict]:
    # 変更ファイル + flags(state) の現在値を staged に上げる（MVP は対象名を記録）。
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

    # 統合ワールド state かどうかで commit に記録する mission_id の出所を変える
    # （_push が「この commit はどの Mission のものか」を照合するために使う。P3-05）。
    is_world = "mission_progress" in state
    mission_id = (
        progress.active_mission_id(state["mission_progress"])
        if is_world
        else state.get("mission_id")
    )

    next_id = (git["commits"][-1]["id"] + 1) if git["commits"] else 1
    snapshot = {
        "current_path": state["current_path"],
        "filesystem": copy.deepcopy(state["filesystem"]),
        # キー名は互換のため "mission_flags" のまま保つ。中身は progress.flags(state)
        # （両 state 形状に対応）の deepcopy にする。
        "mission_flags": copy.deepcopy(progress.flags(state)),
        "env_vars": copy.deepcopy(state.get("env_vars", {})),
    }
    if is_world:
        # P3-10 の resume がワールド全体（completed/active_mission_id/released 等）を
        # 復元できるよう mission_progress も丸ごと含める。
        snapshot["mission_progress"] = copy.deepcopy(state["mission_progress"])

    git["commits"].append(
        {
            "id": next_id,
            "message": message,
            "mission_id": mission_id,
            "snapshot": snapshot,
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

    is_world = "mission_progress" in state
    current_active = progress.active_mission_id(state["mission_progress"]) if is_world else None
    if is_world and current_active is None:
        # 全 Mission クリア済み。押せる関所がもう無いので commit 照合まで進めない
        # （進めると advance_mission(state, None) に落ちてクラッシュする）。
        raise CommandError("Error: mission requirements not met")
    if is_world and latest.get("mission_id") != current_active:
        # 穴塞ぎ（P3-05）: Git 履歴がプレイ全体で1本になったため、直近 commit が
        # 現在のアクティブ Mission のものでない場合（= 前 Mission クリア直後に
        # もう一度 push した等）は、その commit の case_checked を現在の Mission の
        # 合格判定に流用させない。Mission 別 state では commit ごとに Mission が
        # 分離されているためこのチェックを行わない（挙動不変）。
        raise CommandError("Error: mission requirements not met")

    git["pushed"] = True
    if is_world:
        progress.advance_mission(state, current_active)
    else:
        state["mission_flags"]["completed"] = True
    return ["Mission Complete! Next mission unlocked."], state
