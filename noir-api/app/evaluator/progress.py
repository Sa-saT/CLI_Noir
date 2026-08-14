"""`mission_progress`（Mission横断の進捗dict）を操作するヘルパー（Part5 P3-02）。

永続統合ワールド化（`context/04_task_backlog.md` Part5）に伴い、旧`mission_flags`
（Mission単位のstateが個別に持っていた`completed`）を、ワールド全体で共有する
進捗dictへ置き換える。

`mission_progress`のスキーマ:
    {
        "completed": [1, 2, 3],       # クリア済み mission_id の一覧
        "active_mission_id": 4,       # 未クリアの最小 mission_id（キャッシュ）
        "case_checked": False,        # active_mission_id に対する case_file.sh 判定結果
    }

`active_mission_id`はキャッシュフィールドであり、本モジュールの`active_mission_id()`
関数（純粋関数。completed から都度算出する）の戻り値を書き込むのは
`app/evaluator/progress.py::advance_mission`（Mission解放/クリアの唯一の書き込み箇所。
Part5 P3-05）のみとする。
"""

from app.content.missions import GHOST_HOSTS_LINE, all_missions, get_mission
from app.evaluator import fs

_MISSION12_ID = 12
_OPEN_MODE = "rwxr-xr-x"
_OPEN_OWNER = "detective"


def completed_ids(mission_progress: dict) -> set[int]:
    """クリア済み mission_id の集合を返す。"""
    return set(mission_progress.get("completed", []))


def status_for(mission_id: int, mission_progress: dict) -> str:
    """cleared: 完了 / open: 遊べる / locked: 前の Mission 未完了。

    Mission1 は常に open。以降は直前 Mission の完了で解放される（順次解放）。
    `app/api/missions.py::_status_for` と同じロジック（P3-11 でこちらへ差し替える）。
    """
    completed = completed_ids(mission_progress)
    if mission_id in completed:
        return "cleared"
    if mission_id == 1 or (mission_id - 1) in completed:
        return "open"
    return "locked"


def active_mission_id(mission_progress: dict) -> int | None:
    """未クリアの最小 mission_id を算出する（全 Mission 完了済みなら None）。

    `mission_progress["active_mission_id"]`（キャッシュ）の値ではなく、
    `completed`から都度算出する純粋関数。キャッシュへの反映は`advance_mission`
    （Part5 P3-05）が行う。
    """
    completed = completed_ids(mission_progress)
    for mission in all_missions():
        if mission.id not in completed:
            return mission.id
    return None


def _unlock_directories(state: dict, mission_id: int) -> None:
    """mission_id が所有する区画（`MissionDef.owned_paths`）の mode を解放する。

    `fs.get_node` は経路上の未解放ディレクトリだけを None 扱いする（末端ノード
    自身の lock 状態はチェックしない。Part5 P3-04）ため、まだ閉じている区画自身の
    ノードもここで取得できる。owned_paths の親（/root・/home）は常時公開なので、
    経路上でブロックされることもない。
    """
    mission = get_mission(mission_id)
    if mission is None:
        return
    for path in mission.owned_paths:
        node = fs.get_node(state, path)
        if node is None:
            continue
        node["mode"] = _OPEN_MODE
        node["owner"] = _OPEN_OWNER


def _append_ghost_hosts_line(state: dict) -> None:
    """Mission12 解放時に /etc/hosts へ ghost.example 行を追記する（Part5 P3-03/P3-05）。"""
    hosts = fs.get_node(state, "/etc/hosts")
    if hosts is None or hosts.get("type") != "file":
        return
    lines = hosts.get("content", "").split("\n") if hosts.get("content") else []
    if GHOST_HOSTS_LINE not in lines:
        lines.append(GHOST_HOSTS_LINE)
        hosts["content"] = "\n".join(lines)


def _release_processes_and_cron(state: dict, mission_id: int) -> None:
    """mission_id の initial_processes/initial_cron_jobs を state へ追加する。

    各エントリに owning_mission_id タグを付ける。`ps`/`crontab -l` は
    state["processes"]/state["cron_jobs"] をそのまま返すだけで良い —
    未解放 Mission のエントリはそもそもここで追加されるまで存在しないため、
    実質的に「解放済み Mission の分だけ表示される」が自動的に成り立つ
    （コマンド側に追加のフィルタは不要）。
    """
    mission = get_mission(mission_id)
    if mission is None:
        return
    if mission.initial_processes:
        processes = state.setdefault("processes", [])
        for p in mission.initial_processes:
            entry = dict(p)
            entry["owning_mission_id"] = mission_id
            processes.append(entry)
    if mission.initial_cron_jobs:
        cron_jobs = state.setdefault("cron_jobs", [])
        for c in mission.initial_cron_jobs:
            entry = dict(c)
            entry["owning_mission_id"] = mission_id
            cron_jobs.append(entry)


def advance_mission(state: dict, cleared_mission_id: int) -> dict:
    """cleared_mission_id のクリアを記録し、次に解放される Mission を開放する。

    Mission 解放/クリアに伴う world state 書き換えの唯一の書き込み箇所
    （Part5 P3-05）。`app/evaluator/git_ops.py::_push` から呼ぶ。state を
    その場で書き換えて返す（engine の deepcopy 済み state を前提とする、
    他の evaluator 関数と同じ規約）。
    """
    mission_progress = state.setdefault(
        "mission_progress", {"completed": [], "active_mission_id": 1, "case_checked": False}
    )
    completed = completed_ids(mission_progress)
    completed.add(cleared_mission_id)
    mission_progress["completed"] = sorted(completed)
    # 新しくアクティブになる Mission はまだ判定していない。
    mission_progress["case_checked"] = False

    new_active = active_mission_id(mission_progress)
    mission_progress["active_mission_id"] = new_active

    if new_active is not None:
        _unlock_directories(state, new_active)
        if new_active == _MISSION12_ID:
            _append_ghost_hosts_line(state)
        _release_processes_and_cron(state, new_active)

    return state
