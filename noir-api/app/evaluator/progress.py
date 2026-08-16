"""`mission_progress` 読み書きヘルパー（Part5, P3-02 / P3-05）。

PlayerState.data["mission_progress"] のスキーマ（app/models/tables.py::default_world_state()
参照）を対象にした純粋関数群。DB・I/O には一切依存しない。

Mission 解放/クリアの書き込みは P3-05 の `advance_mission` に集約し、`active_mission_id`
キャッシュの更新は本モジュールの `refresh_active_mission_id` 経由のみで行う。それ以外の
関数はすべて引数の `mission_progress` を変更しない（副作用なし）。

state には 2 形状がある（`app/evaluator/env.py::env_for` と同じ考え方。当面両方を壊さず
共存させる）:
  - Mission 別 state（`default_state()`。現行 API/WS が使う。当面現役）:
    `mission_flags = {"case_checked": ..., "completed": ...}`
  - 統合ワールド state（`default_world_state()`）:
    `mission_progress = {"completed": [...], "active_mission_id": N, "flags": {...}}`
`flags(state)` はこの違いを吸収する（P3-05）。
"""

import copy

from app.content import missions
from app.content.missions import all_missions


def flags(state: dict) -> dict:
    """アクティブ Mission の一時フラグ dict を返す（両形状に対応）。

    統合ワールド state（`mission_progress` を持つ）なら
    `mission_progress["flags"]` を、Mission 別 state なら `mission_flags` を返す。
    いずれも無ければその場で作って返す。返り値は参照なので、呼び出し側が書き換える
    と state（またはコミットのスナップショット dict）に反映される。`_push` が
    commit スナップショットからも読むため、通常の state 以外の任意の dict に
    対しても同じロジックで動くようにしてある。
    """
    if "mission_progress" in state:
        return state["mission_progress"].setdefault("flags", {})
    return state.setdefault("mission_flags", {})


def completed_ids(mission_progress: dict) -> set[int]:
    """クリア済み mission_id の集合。

    `mission_progress` に "completed" キーが無い場合も空集合として扱う。
    """
    return set(mission_progress.get("completed", []))


def status_from_completed(mission_id: int, completed: set[int]) -> str:
    """cleared / open / locked を返す。

    Mission1 は常に open。以降は直前 Mission の完了で順次解放される
    （既存 app/api/missions.py::_status_for と同一ロジック）。
    """
    if mission_id in completed:
        return "cleared"
    if mission_id == 1 or (mission_id - 1) in completed:
        return "open"
    return "locked"


def status_for(mission_id: int, mission_progress: dict) -> str:
    """status_from_completed(mission_id, completed_ids(mission_progress)) と同義。"""
    return status_from_completed(mission_id, completed_ids(mission_progress))


def compute_active_mission_id(mission_progress: dict) -> int | None:
    """未クリアの最小 mission_id を再計算する（キャッシュを読まない純粋計算）。

    全 Mission クリア済みなら None を返す。
    """
    completed = completed_ids(mission_progress)
    for mission in all_missions():
        if mission.id not in completed:
            return mission.id
    return None


def refresh_active_mission_id(mission_progress: dict) -> int | None:
    """compute_active_mission_id() で再計算し active_mission_id に書き戻す。

    `mission_progress["active_mission_id"]` キャッシュの唯一の書き込み口
    （P3-05 の advance_mission から呼ぶ）。戻り値は書き戻した値と同じ。
    """
    active = compute_active_mission_id(mission_progress)
    mission_progress["active_mission_id"] = active
    return active


def active_mission_id(mission_progress: dict) -> int | None:
    """キャッシュ済み active_mission_id を読む。

    キーが無い場合のみ再計算にフォールバックする（この場合も mission_progress
    への書き戻しは行わない＝読み取りは副作用なし）。
    """
    if "active_mission_id" in mission_progress:
        return mission_progress["active_mission_id"]
    return compute_active_mission_id(mission_progress)


def _node_at(world: dict, abs_path: str) -> dict | None:
    """ワールド（"root"/"etc" 等をトップレベルキーに持つ filesystem dict）から
    絶対パスのノードを直接辿る。app/content/missions.py::_node_at と同じ実装（P3-05）。

    重要: app/evaluator/fs.py の get_node() は権限ゲートを通すため、未解放
    （ロック中）のディレクトリを None として扱ってしまい、解放処理には使えない
    （ロック中のノードにこそ mode/owner を書き込む必要があるため）。ここでは
    ゲートを一切見ない素朴な木構造の辿りだけを行う。
    """
    node: dict | None = {"type": "dir", "children": world}
    for seg in [s for s in abs_path.split("/") if s]:
        if node is None or node.get("type") != "dir":
            return None
        node = node.get("children", {}).get(seg)
    return node


def release_missions(state: dict) -> None:
    """未解放（locked でない）Mission の区画を解放する（統合ワールド state 専用・冪等）。

    `mission_progress` を持たない state（Mission 別 state）に対しては何もせず
    即 return する（Mission 別 state は Mission 区画という概念自体を持たず、
    initial_filesystem/initial_processes/initial_cron_jobs が Mission 開始時に
    丸ごと投入されるため、この関数の出番がない）。

    `mission_progress["released"]`（解放処理を実施済みの mission_id のリスト）
    を見て、`status_for` が "locked" でない かつ まだ released に無い Mission
    にだけ、以下を1回限り行う:
      - `missions.mission_area_paths(mission_id)` の各ディレクトリノードの
        mode/owner を OPEN_DIR_MODE/OPEN_DIR_OWNER に書き換える（未解放時は
        存在しないパスをテストで気づけるよう、黙って飛ばさず例外にする）
      - `initial_processes`/`initial_cron_jobs` があれば owning_mission_id を
        付けて state["processes"]/state["cron_jobs"] に追加する
      - Mission12 なら /etc/hosts に GHOST_HOSTS_LINE を追記する（既にあれば何もしない）
      - 最後に released へ mission_id を追加する

    `git push` が複数回打たれても、Mission6 で kill 済みのプロセスが復活したり
    /etc/hosts に同じ行が二重に入ったりしないことを、この released リストが保証する
    （毎回全 Mission を走査するが、released 済みのものは即 continue するだけ）。
    """
    mission_progress = state.get("mission_progress")
    if mission_progress is None:
        return

    completed = completed_ids(mission_progress)
    released = mission_progress.setdefault("released", [])
    released_set = set(released)
    world = state.get("filesystem", {})

    for mission in all_missions():
        mission_id = mission.id
        if mission_id in released_set:
            continue
        if status_from_completed(mission_id, completed) == "locked":
            continue

        # ディレクトリ権限ゲートを解放する（未解放は mode="---------"/owner="system"）。
        for path in missions.mission_area_paths(mission_id):
            node = _node_at(world, path)
            if node is None or node.get("type") != "dir":
                # 区画が世界に存在しないのは設計ミス（build_world_filesystem 側の
                # バグ）。黙って飛ばすとテストでも気づけないため例外にする。
                raise ValueError(
                    f"mission area {path} not found while releasing mission {mission_id}"
                )
            node["mode"] = missions.OPEN_DIR_MODE
            node["owner"] = missions.OPEN_DIR_OWNER

        # 初期プロセス / cron ジョブを解放時に積む（owning_mission_id は P3-09 の
        # リプレイ台帳用のタグ付けのみで、表示フィルタとしては使わない）。
        if mission.initial_processes:
            processes = state.setdefault("processes", [])
            for proc in mission.initial_processes:
                processes.append({**copy.deepcopy(proc), "owning_mission_id": mission_id})
        if mission.initial_cron_jobs:
            cron_jobs = state.setdefault("cron_jobs", [])
            for job in mission.initial_cron_jobs:
                cron_jobs.append({**copy.deepcopy(job), "owning_mission_id": mission_id})

        # Mission12（幽霊回線）解放時に /etc/hosts へ ghost.example 行を追記する
        # （初期ワールドには含めない。dig で見つける体験を守るため解放時のみ追加）。
        if mission_id == 12:
            hosts_node = _node_at(world, missions.HOSTS_PATH)
            if hosts_node is not None and hosts_node.get("type") == "file":
                lines = hosts_node["content"].split("\n")
                if missions.GHOST_HOSTS_LINE not in lines:
                    hosts_node["content"] = "\n".join([*lines, missions.GHOST_HOSTS_LINE])

        released.append(mission_id)
        released_set.add(mission_id)


def advance_mission(state: dict, cleared_mission_id: int) -> None:
    """cleared_mission_id をクリア済みとして記録し、次 Mission へ遷移する（統合ワールド state 専用）。

    1. mission_progress["completed"] に記録する（重複させない・昇順を保つ）
    2. refresh_active_mission_id() で active_mission_id を再計算する
    3. flags を {"case_checked": False} にリセットする（アクティブ Mission に対する
       一時フラグなので、次の Mission に持ち越してはいけない）
    4. release_missions(state) を呼び、新しく open/cleared になった Mission の
       区画・プロセス・cron・/etc/hosts を解放する
    """
    mission_progress = state["mission_progress"]
    completed = mission_progress.setdefault("completed", [])
    if cleared_mission_id not in completed:
        completed.append(cleared_mission_id)
        completed.sort()
    refresh_active_mission_id(mission_progress)
    mission_progress["flags"] = {"case_checked": False}
    release_missions(state)
