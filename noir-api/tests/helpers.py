"""Phase F（tests/test_mission*.py の統合ワールド state への移行）用の共通ヘルパー。

旧: `app.ws.terminal.build_initial_state(n)` が Mission 別 state（`default_state()` +
Mission 固有の `initial_filesystem`/`initial_current_path` 等）を組み立てていたが、
本番の WS/API 層は既に永続統合ワールド state（`default_world_state()` +
`mission_progress`）へ移行済みで `build_initial_state` は使われていない。テスト側も
実プレイと同じ state 形状で検証するため、統合ワールドを Mission n まで進めた state を
組み立てる本ヘルパーへ揃えていく（context/04_task_backlog.md § Part5 Phase F）。
"""

from app.evaluator import progress
from app.models import default_world_state


def state_at_mission(n: int) -> dict:
    """Mission n が捜査中（1..n-1 クリア済み・n の区画が解放済み）の統合ワールド state。

    cwd は /root。Mission 1..n-1 は本物の `progress.advance_mission` で順番に
    クリア済みにする（区画解放・プロセス/cron 投入・/etc/hosts 追記などの副作用を
    ここで再実装せず、本番と同じロジックに委ねる）。
    """
    state = default_world_state()
    for i in range(1, n):
        progress.advance_mission(state, i)
    state["current_path"] = "/root"
    return state
