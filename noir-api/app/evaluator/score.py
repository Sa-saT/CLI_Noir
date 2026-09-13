"""スマート捜査ボーナス（機能 3）とタイムアタック演出（機能 7）。2026-09-13 実装。

クリア（advance_mission）時に、その Mission で打ったコマンド数・パイプの使用・所要時間を
`mission_progress["scores"][str(mission_id)]` に記録する。時間切れの失敗は作らない
（§ 11 機能 7。残り時間は演出だけ）。

- 手数: resolved_command_log のうち mission_id が一致する成功コマンド（case_file.sh の
  判定・git add/commit/push は手数に数えない＝「捜査」の手数だけ）
- 目安（par）: ヒント 3 段目（コマンド列）の矢印の数から算出（判定・git の 4 手を引く）
- ボーナス: 手数 ≤ 目安 → SMART（+50）/ パイプを 1 行でも使った Mission で使った → PIPE（+20）/
  目安 × 1.5 以内 → +20（部分点）。基本点 100
- 時間: Mission が解放（開始）された時刻 `timers[id]["started_at"]` からクリアまで。目安は
  `TARGET_MINUTES`（Mission定義に無いので既定 15 分）。超過しても失敗にならない
"""

import re
from datetime import datetime, timezone

from app.content.missions import get_mission

BASE_SCORE = 100
SMART_BONUS = 50
NEAR_BONUS = 20
PIPE_BONUS = 20
DEFAULT_TARGET_MINUTES = 15
# 手数に数えないコマンド（判定と疑似 git、画面操作）
_NOT_COUNTED = re.compile(r"\s*(sh\s+.*case_file\.sh|git\b|clear\b|history\b|pwd\b|man\b)")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def mark_started(state: dict, mission_id: int) -> None:
    timers = state["mission_progress"].setdefault("timers", {})
    timers.setdefault(str(mission_id), {})["started_at"] = _now().isoformat()


# ヒント 3 段目の矢印数から自動算出できない Mission（1 手にまとめて書いた箇所がある /
# 最終事件はヒントが 1 段）だけ明示する。値は「最短でこの手数」の目安。
_PAR_OVERRIDES: dict[int, int] = {
    3: 8,   # ssh・find・cat×3・echo×3
    22: 18,  # 8 関所（find・ssh+cat+exit・chmod+cat・パイプ・tar+cat・md5sum・自作 sh 5 行・報告）
}


def par_for(mission_id: int) -> int:
    if mission_id in _PAR_OVERRIDES:
        return _PAR_OVERRIDES[mission_id]
    mission = get_mission(mission_id)
    if mission is None or len(mission.hints) < 3:
        return 8
    steps = mission.hints[2].count("→") + 1
    return max(3, steps - 4)  # sh case_file.sh / git add / commit / push を除く


def mission_commands(state: dict, mission_id: int) -> list[str]:
    return [
        e["line"]
        for e in state.get("resolved_command_log", [])
        if e.get("mission_id") == mission_id and not _NOT_COUNTED.match(e["line"])
    ]


def record_clear(state: dict, mission_id: int) -> dict:
    """クリア時の評価を計算して mission_progress["scores"] に記録し、その dict を返す。"""
    lines = mission_commands(state, mission_id)
    par = par_for(mission_id)
    bonuses: list[str] = []
    score = BASE_SCORE
    if len(lines) <= par:
        bonuses.append("SMART")
        score += SMART_BONUS
    elif len(lines) <= par * 1.5:
        bonuses.append("NEAR")
        score += NEAR_BONUS
    if any("|" in ln for ln in lines):
        bonuses.append("PIPE")
        score += PIPE_BONUS

    timers = state["mission_progress"].setdefault("timers", {}).setdefault(str(mission_id), {})
    finished = _now()
    timers["finished_at"] = finished.isoformat()
    elapsed: int | None = None
    if timers.get("started_at"):
        try:
            started = datetime.fromisoformat(timers["started_at"])
            elapsed = max(0, int((finished - started).total_seconds()))
        except ValueError:
            elapsed = None

    record = {
        "commands": len(lines),
        "par": par,
        "bonuses": bonuses,
        "score": score,
        "elapsed_seconds": elapsed,
        "target_minutes": DEFAULT_TARGET_MINUTES,
    }
    state["mission_progress"].setdefault("scores", {})[str(mission_id)] = record
    return record


def score_of(state: dict, mission_id: int) -> dict | None:
    return state.get("mission_progress", {}).get("scores", {}).get(str(mission_id))


def started_at(state: dict, mission_id: int | None) -> str | None:
    if mission_id is None:
        return None
    return state.get("mission_progress", {}).get("timers", {}).get(str(mission_id), {}).get("started_at")
