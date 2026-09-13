"""再捜査（クリア済み Mission の遊び直し）と隠し Mission の土台。2026-09-14 実装。

ユーザー方針: 「遊び返せる方が楽しみが続く」「クリア後の Mission に隠し Mission を出したい」。

- `state["replay"] = {"mission_id", "log_start", "resolved_start", "started_at"}` が立っている間は
  **その Mission が「注目中（focused）」**になり、`case_file.sh` の合成・判定・独り言・commit の
  mission_id・図鑑/台帳のタグがすべて注目中の Mission を向く（`progress.focused_mission_id`）。
  本編の進捗（completed / active_mission_id）は動かさない。
- 開始時にその Mission の舞台を初期状態に戻す（区画のファイル・プロセス・cron・サービス・
  枝・PATH 汚染・sandbox）。判定と独り言は再捜査を始めてからのコマンドだけを見る
  （`view()` がログを切り詰めた state の写しを作る）。
- `git push` で判定が通れば再捜査完了: 評価を `mission_progress["scores_replay"]` に残し
  （ベスト更新）、再捜査を閉じて事務所へ戻る。
- 隠し Mission（`MissionDef.secret_of`）はプレイ順序に入らない。親 Mission がクリア済みなら
  再捜査と同じ仕組みで遊べる（初回クリアは `scores_replay` に "secret" として記録）。
"""

import copy
from datetime import datetime, timezone

from app.content import missions
from app.content.missions import get_mission
from app.evaluator import progress


def active(state: dict) -> dict | None:
    return state.get("replay")


def can_replay(state: dict, mission_id: int) -> bool:
    """クリア済み、または親がクリア済みの隠し Mission なら再捜査できる。"""
    mission = get_mission(mission_id)
    if mission is None:
        return False
    completed = progress.completed_ids(state["mission_progress"])
    if mission.secret_of is not None:
        return mission.secret_of in completed
    return mission_id in completed


def _reset_area(state: dict, mission_id: int) -> None:
    """区画のファイルを初期ワールドの雛形から戻す（プレイヤーが書き換えた分を消す）。"""
    template = missions.build_world_filesystem()
    world = state["filesystem"]
    for path in missions.mission_area_paths(mission_id):
        segs = [s for s in path.split("/") if s]
        parent = progress._node_at(world, "/" + "/".join(segs[:-1]))
        src = progress._node_at(template, path)
        if parent is None or parent.get("type") != "dir" or src is None:
            continue
        node = copy.deepcopy(src)
        node["mode"] = missions.OPEN_DIR_MODE
        node["owner"] = missions.OPEN_DIR_OWNER
        parent["children"][segs[-1]] = node


def _reapply_hooks(state: dict, mission_id: int) -> None:
    """解放時のフック（プロセス・cron・枝・PATH 汚染・sandbox）をもう一度当てる。"""
    mission = get_mission(mission_id)
    if mission is None:
        return
    if mission.initial_processes:
        state["processes"] = [
            p for p in state.get("processes", []) if p.get("owning_mission_id") != mission_id
        ]
        for proc in mission.initial_processes:
            state["processes"].append({**copy.deepcopy(proc), "owning_mission_id": mission_id})
    if mission.initial_cron_jobs:
        state["cron_jobs"] = [
            j for j in state.get("cron_jobs", []) if j.get("owning_mission_id") != mission_id
        ]
        for job in mission.initial_cron_jobs:
            state["cron_jobs"].append({**copy.deepcopy(job), "owning_mission_id": mission_id})
    if mission.initial_env_vars:
        state.setdefault("env_vars", {}).setdefault("detective", {}).update(
            copy.deepcopy(mission.initial_env_vars)
        )
    if mission.initial_branches:
        from app.evaluator import git_ops

        repo = state.get("git_state", {}).get("repo")
        if repo is not None:
            for name, spec in mission.initial_branches.items():
                repo["branches"].pop(name, None)
                git_ops.add_branch(
                    state, name, spec["base_from"], spec.get("tree"), spec["message"],
                    files=spec.get("files"), base_files=spec.get("base_files"),
                )
            repo["merging"] = None
    if mission.initial_repo:
        # 枝の状態も初期に戻す（main だけ・作業ツリーの中身）
        from app.evaluator import git_ops

        repo_spec = mission.initial_repo
        state["git_state"].pop("repo", None)
        git_ops.init_repo(state, repo_spec["root"], repo_spec["branch"], repo_spec["message"])
    # ssh 先のサービス状態（systemctl start/stop の記録）を戻す
    from app.evaluator.commands import SSH_HOSTS

    for host, info in SSH_HOSTS.items():
        if info.get("required_mission_id") == mission_id:
            state.get("remote_services", {}).pop(host, None)
    if mission.sandbox:
        from app.evaluator import sandbox

        sandbox.enter(state)


def start(state: dict, mission_id: int) -> None:
    """再捜査を始める。舞台を初期化し、独り言の発火記録を消し、ログの起点を記録する。"""
    if not can_replay(state, mission_id):
        raise ValueError("mission is not replayable")
    if active(state):
        stop(state)
    _reset_area(state, mission_id)
    _reapply_hooks(state, mission_id)
    state["mission_progress"].setdefault("story_fired", {}).pop(str(mission_id), None)
    progress.flags(state)["case_checked"] = False
    state["replay"] = {
        "mission_id": mission_id,
        "log_start": len(state.get("command_log", [])),
        "resolved_start": len(state.get("resolved_command_log", [])),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    progress.return_to_office(state)


def stop(state: dict) -> None:
    """再捜査をやめる（完了・離脱の両方）。sandbox なら本物の世界を戻す。"""
    box = state.pop("replay", None)
    if box is None:
        return
    from app.evaluator import sandbox

    sandbox.leave(state)
    progress.flags(state)["case_checked"] = False
    progress.return_to_office(state)


def view(state: dict) -> dict:
    """判定・独り言用: 再捜査開始以降のログだけを持つ state の浅い写し。

    ログ以外は同じオブジェクトを指すので、判定側の `progress.flags(view)[...] = ...` は
    本物の state に書かれる。呼び出し側は戻り値の state を捨てて元の state を使うこと。
    """
    box = active(state)
    if box is None:
        return state
    v = dict(state)
    v["command_log"] = state.get("command_log", [])[box["log_start"]:]
    v["resolved_command_log"] = state.get("resolved_command_log", [])[box["resolved_start"]:]
    return v


def finish(state: dict) -> dict:
    """`git push` が通った: 評価を記録して再捜査を閉じる。戻り値は評価。"""
    from app.evaluator import score

    box = active(state)
    assert box is not None
    mission_id = box["mission_id"]
    v = view(state)
    lines = score.mission_commands(v, mission_id)
    par = score.par_for(mission_id)
    bonuses: list[str] = []
    points = score.BASE_SCORE
    if len(lines) <= par:
        bonuses.append("SMART")
        points += score.SMART_BONUS
    elif len(lines) <= par * 1.5:
        bonuses.append("NEAR")
        points += score.NEAR_BONUS
    if any("|" in ln for ln in lines):
        bonuses.append("PIPE")
        points += score.PIPE_BONUS
    started = datetime.fromisoformat(box["started_at"])
    elapsed = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
    record = {
        "commands": len(lines), "par": par, "bonuses": bonuses, "score": points,
        "elapsed_seconds": elapsed, "target_minutes": score.DEFAULT_TARGET_MINUTES,
        "replay": True,
    }
    store = state["mission_progress"].setdefault("scores_replay", {})
    best = store.get(str(mission_id))
    if best is None or points > best.get("score", 0):
        store[str(mission_id)] = record
    stop(state)
    return record
