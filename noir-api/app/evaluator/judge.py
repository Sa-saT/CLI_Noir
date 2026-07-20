"""Mission 判定（case_file.sh）。

state.command_log の各行に対して Mission の expected_script_patterns を評価する。
match_policy: AND（全パターン一致必須）/ 順不同 / 大小文字区別あり（設計指示書 § 9）。
一致で mission_flags.case_checked=true。判定パターンは正規表現なので `re` のみ使う。
"""

import re

from app.content.missions import get_mission

# Mission ごとの専用判定（誤答メッセージを個別化する Mission だけ登録）。
# 汎用 AND-regex では表現しづらい「絶対パス必須」「特定キー抽出」等をここで扱う。
_CATINFO_ABS = "/root/park/swing/catinfo.txt"


def _judge_mission2(state: dict) -> tuple[list[str], dict]:
    """Mission2: find 使用・catinfo 絶対パス参照・STATUS 抽出の 3 点を検査する。

    誤答メッセージは Mission参照ファイル § 3 の確定文言に一致させる。
    """
    log = state.get("command_log", [])
    used_find = any(re.match(r"\s*find\b", line) for line in log)
    used_abs_path = any(_CATINFO_ABS in line for line in log)
    # STATUS 抽出: grep/echo 等で STATUS キーまたはその値 stray を含む行があるか。
    read_status = any(
        re.search(r"STATUS", line, re.IGNORECASE) or "stray" in line for line in log
    )

    if not used_find:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: use find to locate clues"], state
    if not used_abs_path:
        state["mission_flags"]["case_checked"] = False
        return ["Error: absolute path required"], state
    if not read_status:
        state["mission_flags"]["case_checked"] = False
        return ["Error: required cat status not found"], state

    state["mission_flags"]["case_checked"] = True
    return ["case_file.sh: all checks passed"], state


def _judge_mission6(state: dict) -> tuple[list[str], dict]:
    """Mission6: 盗聴プログラム listener_x が processes から除去されているか検査する。

    正規プロセス（protected）を kill しても kill 側で削除されないため、ここでは
    listener_x の残存のみを見ればよい（誤って正規プロセスを止めても即失敗にしない）。
    """
    processes = state.get("processes", [])
    still_running = any(p.get("name") == "listener_x" for p in processes)

    if still_running:
        state["mission_flags"]["case_checked"] = False
        state["mission_flags"]["bug_removed"] = False
        return ["Warning: the bug is still running"], state

    state["mission_flags"]["case_checked"] = True
    state["mission_flags"]["bug_removed"] = True
    return ["case_file.sh: all checks passed"], state


_MISSION7_IMPOSTOR_PID = 923
_MISSION7_FAKE_CMDLINE = "/tmp/.fake/exfil --send"


def _judge_mission7(state: dict) -> tuple[list[str], dict]:
    """Mission7: /proc での裏取り（status/cmdline 閲覧）→ 偽装 cmdline の報告
    → 停止、の 3 段階を検査する。「名簿（ps）と持ち物検査（/proc）」の二段推理。
    """
    log = state.get("command_log", [])
    pid = _MISSION7_IMPOSTOR_PID
    inspected = any(re.search(rf"/proc/{pid}/(status|cmdline)", line) for line in log)
    reported = any(_MISSION7_FAKE_CMDLINE in line for line in log)
    still_running = any(p.get("pid") == pid for p in state.get("processes", []))

    if not inspected:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: check /proc before you accuse anyone"], state
    if not reported:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: report the impostor's real command"], state
    if still_running:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: the impostor is still running"], state

    state["mission_flags"]["case_checked"] = True
    return ["case_file.sh: all checks passed"], state


_MISSION8_SECRET_PATH = "/root/bar/back/ledger.txt"


def _judge_mission8(state: dict) -> tuple[list[str], dict]:
    """Mission8: su barman → whoami → 秘密ファイル閲覧 → 元ユーザーへの復帰、
    の 4 段階を検査する。exit で local に戻る Mission3 の ssh/exit と対になる構造。
    """
    log = state.get("command_log", [])
    did_su = any(re.match(r"\s*su\s+barman\b", line) for line in log)
    did_whoami = any(re.match(r"\s*whoami\b", line) for line in log)
    read_secret = any(_MISSION8_SECRET_PATH in line for line in log)
    returned_home = state.get("current_user", "detective") == "detective"

    if not did_su:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: find a way to become barman"], state
    if not did_whoami:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: confirm who you are with whoami"], state
    if not read_secret:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: the ledger is still unread"], state
    if not returned_home:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: return to your own identity before reporting"], state

    state["mission_flags"]["case_checked"] = True
    return ["case_file.sh: all checks passed"], state


_CUSTOM_JUDGES = {
    2: _judge_mission2,
    6: _judge_mission6,
    7: _judge_mission7,
    8: _judge_mission8,
}


def run_case_file(state: dict) -> tuple[list[str], dict]:
    """`sh case_file.sh` の判定本体。case_checked を更新して結果行を返す。"""
    mission = get_mission(state.get("mission_id")) if state.get("mission_id") else None

    custom = _CUSTOM_JUDGES.get(mission.id) if mission else None
    if custom is not None:
        return custom(state)

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
