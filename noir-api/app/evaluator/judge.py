"""Mission 判定（case_file.sh）。

state.command_log の各行に対して Mission の expected_script_patterns を評価する。
match_policy: AND（全パターン一致必須）/ 順不同 / 大小文字区別あり（設計指示書 § 9）。
一致で mission_flags.case_checked=true。判定パターンは正規表現なので `re` のみ使う。
"""

import re

from app.content.missions import get_mission
from app.evaluator import fs

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


_MISSION10_ORIGINAL_PATH = "/root/original.txt"
_MISSION10_SUBMITTED_PATH = "/root/submitted.txt"


def _judge_mission10(state: dict) -> tuple[list[str], dict]:
    """Mission10: diff 実行 + submitted.txt が original.txt と完全一致するまで
    sed で復元されているかを検査する（1文字差の改ざんを sed で正確に直す）。
    """
    log = state.get("command_log", [])
    did_diff = any(re.match(r"\s*diff\b", line) for line in log)
    if not did_diff:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: run diff before you restore the will"], state

    original = fs.get_node(state, _MISSION10_ORIGINAL_PATH)
    submitted = fs.get_node(state, _MISSION10_SUBMITTED_PATH)
    if not (fs.is_file(original) and fs.is_file(submitted)):
        state["mission_flags"]["case_checked"] = False
        return ["Warning: pattern mismatch"], state
    if original.get("content") != submitted.get("content"):
        state["mission_flags"]["case_checked"] = False
        return ["Warning: submitted.txt still does not match the original"], state

    state["mission_flags"]["case_checked"] = True
    return ["case_file.sh: all checks passed"], state


_MISSION12_BOSS = "Selene Vance"
_MISSION12_EVIDENCE_PATH = "/den/evidence/orders.txt"


def _first_index(log: list[str], pattern: str) -> int | None:
    for i, line in enumerate(log):
        if re.match(pattern, line):
            return i
    return None


def _judge_mission12(state: dict) -> tuple[list[str], dict]:
    """Mission12: dig → ping → ssh の出現順序 + remote 証拠閲覧 + 黒幕名報告を検査する。

    「調べてから踏み込む」実務手順そのものを判定条件にする（Mission参照 § 12）。
    """
    log = state.get("command_log", [])
    dig_idx = _first_index(log, r"\s*dig\b")
    ping_idx = _first_index(log, r"\s*ping\b")
    ssh_idx = _first_index(log, r"\s*ssh\b")

    order_ok = (
        dig_idx is not None
        and ping_idx is not None
        and ssh_idx is not None
        and dig_idx < ping_idx < ssh_idx
    )
    if not order_ok:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: investigate before you breach"], state

    read_evidence = any(_MISSION12_EVIDENCE_PATH in line for line in log)
    reported_boss = any(_MISSION12_BOSS in line for line in log)
    if not read_evidence or not reported_boss:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: pattern mismatch"], state

    state["mission_flags"]["case_checked"] = True
    return ["case_file.sh: all checks passed"], state


_MISSION14_REAL_PATH = "/root/mirror_hall/vault/real_deed.txt"
_MISSION14_LINK_PATHS = [
    "/root/mirror_hall/deed_a.txt",
    "/root/mirror_hall/deed_b.txt",
    "/root/mirror_hall/deed_c.txt",
]


def _judge_mission14(state: dict) -> tuple[list[str], dict]:
    """Mission14: report（echo 行）に実体の絶対パスが書かれているかを検査する。

    探索中の cat/ls/file 呼び出しにはリンクパスが自然に出現するため、
    誤答判定は「report で使われた echo 行」に絞って行う（Mission参照 § 14）。
    """
    echo_lines = [line for line in state.get("command_log", []) if re.match(r"\s*echo\b", line)]
    reported_real = any(_MISSION14_REAL_PATH in line for line in echo_lines)
    reported_link_only = any(
        any(p in line for p in _MISSION14_LINK_PATHS) for line in echo_lines
    )

    if reported_real:
        state["mission_flags"]["case_checked"] = True
        return ["case_file.sh: all checks passed"], state
    if reported_link_only:
        state["mission_flags"]["case_checked"] = False
        return ["Error: that is only a mirror"], state

    state["mission_flags"]["case_checked"] = False
    return ["Warning: pattern mismatch"], state


_MISSION15_DESTINATION = "PIER 13"


def _judge_mission15(state: dict) -> tuple[list[str], dict]:
    """Mission15: informant_history の各行を command_log 上でそのまま再現し、
    かつ行き先を report（echo）したかを検査する。
    """
    mission = get_mission(state.get("mission_id")) if state.get("mission_id") else None
    required = mission.informant_history if mission else []
    required = required or []
    log = state.get("command_log", [])
    reproduced = all(cmd in log for cmd in required)
    reported = any(
        _MISSION15_DESTINATION in line for line in log if re.match(r"\s*echo\b", line)
    )

    if not reproduced:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: retrace the informant's exact steps"], state
    if not reported:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: pattern mismatch"], state

    state["mission_flags"]["case_checked"] = True
    return ["case_file.sh: all checks passed"], state


_MISSION16_CODE = "CODE: 4821-VESPER"


def _judge_mission16(state: dict) -> tuple[list[str], dict]:
    """Mission16: 数字 glob の使用 + 引用符付きファイルの cat 成功 + コード報告
    の3点を検査する。command_log には成功したコマンドの原文がそのまま残るため、
    未引用の "top secret.txt" 参照は失敗して記録されない＝quote 使用の証明になる。
    """
    log = state.get("command_log", [])
    used_digit_glob = any(re.search(r"\[0-9\]", line) for line in log)
    read_secret = any(re.search(r"\bcat\b.*top secret\.txt", line) for line in log)
    reported_code = any(_MISSION16_CODE in line for line in log)

    if not used_digit_glob:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: narrow the search with a glob pattern"], state
    if not read_secret:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: the warrant does not cover an unopened file"], state
    if not reported_code:
        state["mission_flags"]["case_checked"] = False
        return ["Warning: pattern mismatch"], state

    state["mission_flags"]["case_checked"] = True
    return ["case_file.sh: all checks passed"], state


_MISSION19_SCRIPT_PATH = "/root/patrol.sh"


def _judge_mission19(state: dict) -> tuple[list[str], dict]:
    """Mission19: 自作 patrol.sh の実行 + FOUND 出力 + スクリプト自体が変数定義と
    if 文を含むこと（ハードコードした echo FOUND だけでの通過を防ぐ）を検査する。
    """
    log = state.get("command_log", [])
    ran_script = any(re.search(r"\bsh\b.*patrol\.sh\b", line) for line in log)
    script_found = state.get("mission_flags", {}).get("script_found", False)

    script_node = fs.get_node(state, _MISSION19_SCRIPT_PATH)
    content = script_node.get("content", "") if fs.is_file(script_node) else ""
    has_var = re.search(r"^\s*[A-Za-z_][A-Za-z0-9_]*=", content, re.MULTILINE) is not None
    has_if = re.search(r"\bif\b", content) is not None

    if not (ran_script and script_found and has_var and has_if):
        state["mission_flags"]["case_checked"] = False
        return ["Warning: pattern mismatch"], state

    state["mission_flags"]["case_checked"] = True
    return ["case_file.sh: all checks passed"], state


_CUSTOM_JUDGES = {
    2: _judge_mission2,
    6: _judge_mission6,
    7: _judge_mission7,
    8: _judge_mission8,
    10: _judge_mission10,
    12: _judge_mission12,
    14: _judge_mission14,
    15: _judge_mission15,
    16: _judge_mission16,
    19: _judge_mission19,
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
