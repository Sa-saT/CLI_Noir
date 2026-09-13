"""Phase F（tests/ の統合ワールド state への移行）用の共通ヘルパー。

旧: `app.ws.terminal.build_initial_state(n)`（Mission 別 state。`default_state()` +
Mission 固有の `initial_filesystem`/`initial_current_path` 等を組み立てる関数）は
Phase F で `MissionState` ごと廃止済み。本番の WS/API 層は永続統合ワールド state
（`default_world_state()` + `mission_progress`）のみを読み書きする。テスト側も
実プレイと同じ state 形状で検証するため、統合ワールドを Mission n まで進めた state を
組み立てる本ヘルパーに揃えている（context/04_task_backlog.md § Part5 Phase F）。
"""

from app.evaluator import progress
from app.evaluator.env import _DEFAULT_USER_ENV
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
        if i == 21:
            # Mission21 は解放時に探偵の PATH が汚染され、クリア条件が「PATH を復旧して
            # いること」なので、21 をクリア済みにした state では復旧済みでなければ
            # 辻褄が合わない（advance_mission は判定を肩代わりしないため手で戻す）。
            state["env_vars"]["detective"]["PATH"] = _DEFAULT_USER_ENV["PATH"]
    state["current_path"] = "/root"
    return state
