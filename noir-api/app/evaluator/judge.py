"""Mission 判定（case_file.sh）。

state.command_log の各行に対して Mission の expected_script_patterns を評価する。
match_policy: AND（全パターン一致必須）/ 順不同 / 大小文字区別あり（設計指示書 § 9）。
一致で mission_flags.case_checked=true。判定パターンは正規表現なので `re` のみ使う。
"""

import re

from app.content.missions import get_mission


def run_case_file(state: dict) -> tuple[list[str], dict]:
    """`sh case_file.sh` の判定本体。case_checked を更新して結果行を返す。"""
    mission = get_mission(state.get("mission_id")) if state.get("mission_id") else None
    patterns = mission.expected_script_patterns if mission else []

    if not patterns:
        # 判定パターン未設定の Mission（詳細未確定）。合格にしない。
        state["mission_flags"]["case_checked"] = False
        return ["case_file.sh: no checks configured for this mission"], state

    log = state.get("command_log", [])
    try:
        unmatched = [
            p for p in patterns if not any(re.search(p, line) for line in log)
        ]
    except re.error:
        return ["Error: invalid pattern"], state

    if unmatched:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: pattern mismatch"], state

    state["mission_flags"]["case_checked"] = True
    return ["case_file.sh: all checks passed"], state
