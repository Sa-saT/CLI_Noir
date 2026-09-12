"""進行案内「独り言レイヤー」（STORY-01）。

`MissionDef.story_beats`（探偵の独り言）を、プレイヤーの行動・エラー・クリアに
応じて発火させる純粋関数群。DB・WebSocket には一切依存しない（`app/ws/terminal.py`
が呼び出し、発火した beat を `story` フレームとして送る）。

対応する state 形状は**統合ワールド state**（`mission_progress` を持つ
`default_world_state()`）のみ。`mission_progress` を持たない Mission 別 state
（`default_state()` / `build_initial_state()`）では、Mission 区画という概念自体が
無く発火記録の置き場も無いため、全関数が空リストを返し state を変更しない。

発火済み記録は `state["mission_progress"]["story_fired"]`
（`{str(mission_id): [beat_id, ...]}`）に書く。1 beat は同じ Mission で二度と
発火しない。
"""

import re

from app.content.missions import MissionDef, get_mission
from app.evaluator import progress

Beat = dict


def _fired_list(state: dict, mission_id: int) -> list[str]:
    """mission_id の発火済み beat id リストを返す（無ければ作って state に刺す）。"""
    story_fired = state["mission_progress"].setdefault("story_fired", {})
    return story_fired.setdefault(str(mission_id), [])


def _emit(mission_id: int, beat: Beat) -> dict:
    return {"id": beat["id"], "mission_id": mission_id, "text": beat["text"]}


def start_beats(state: dict) -> list[dict]:
    """アクティブ Mission の `when=="start"` beat を（未発火なら）返す。"""
    if "mission_progress" not in state:
        return []
    mission_id = progress.active_mission_id(state["mission_progress"])
    mission = get_mission(mission_id) if mission_id is not None else None
    if mission is None:
        return []

    fired = _fired_list(state, mission_id)
    results: list[dict] = []
    for beat in mission.story_beats:
        if beat["when"] != "start" or beat["id"] in fired:
            continue
        results.append(_emit(mission_id, beat))
        fired.append(beat["id"])
    return results


def _candidates(command_line: str, entry: dict | None) -> list[str]:
    candidates = [command_line]
    if entry is not None:
        candidates.append(entry["resolved_line"])
        argv0 = command_line.split()[0] if command_line.split() else ""
        candidates.extend(f"{argv0} {p}" for p in entry["paths"])
    return candidates


def _matches(beat: Beat, state: dict, candidates: list[str], out_lines: list[str]) -> bool:
    line_pat = beat.get("line")
    if line_pat is not None and not any(re.search(line_pat, c) for c in candidates):
        return False
    output_pat = beat.get("output")
    if output_pat is not None and not re.search(output_pat, "\n".join(out_lines)):
        return False
    if "remote" in beat and state.get("remote_mode", False) != beat["remote"]:
        return False
    return True


def after_beats(
    state: dict,
    mission_id: int | None,
    command_line: str,
    out_lines: list[str],
    entry: dict | None,
) -> list[dict]:
    """実行後の `when=="after"` beat を判定して返す（未発火の全一致 beat・定義順）。

    `mission_id` はコマンド実行時点のアクティブ Mission（呼び出し側が evaluate 前に
    取っておく）。`entry` はそのコマンドが成功して `resolved_command_log` に積まれた
    場合の末尾要素、エラーで積まれなかった場合は None。
    """
    if "mission_progress" not in state or mission_id is None:
        return []
    mission = get_mission(mission_id)
    if mission is None:
        return []

    fired = _fired_list(state, mission_id)
    candidates = _candidates(command_line, entry)
    results: list[dict] = []
    for beat in mission.story_beats:
        if beat["when"] != "after" or beat["id"] in fired:
            continue
        if not _matches(beat, state, candidates, out_lines):
            continue
        results.append(_emit(mission_id, beat))
        fired.append(beat["id"])
    return results


def clear_beats(state: dict, cleared_mission_id: int) -> list[dict]:
    """クリアした Mission の `when=="clear"` beat + 次 Mission の `start` beat を返す。"""
    if "mission_progress" not in state:
        return []

    results: list[dict] = []
    mission: MissionDef | None = get_mission(cleared_mission_id)
    if mission is not None:
        fired = _fired_list(state, cleared_mission_id)
        for beat in mission.story_beats:
            if beat["when"] != "clear" or beat["id"] in fired:
                continue
            results.append(_emit(cleared_mission_id, beat))
            fired.append(beat["id"])

    results.extend(start_beats(state))
    return results
