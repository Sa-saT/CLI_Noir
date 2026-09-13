"""PR レビュールール（バックエンド_コマンド機能仕様 § 5b）。

`gh pr view` / `gh pr merge` が、対象 PR の元になった Mission の `active_mission_id`
をキーに `PR_REVIEWS` を引き、現在の state に対する「残っている指摘」を計算する。
指摘が空リスト = APPROVED。レビュー担当（Chief Morgan 等）の寸評はここに固定文言で
持たせる（judge.py の Mission 別判定ロジックと同じ方針。実 Git のレビュー機能には
存在しない仕組みだが、疑似 Git の意図的な拡張として許容する）。

Mission23〜25 のコンテンツ本体（MissionDef）は今回未実装のため、ここでは Mission25
のプレースホルダのみ登録する。
"""

from collections.abc import Callable

from app.evaluator import fs

# git-team 編（Mission23〜25 想定）の共有作業ディレクトリ。
_TEAM_DESK_ROOT = "/root/team_desk"
_REPORT_PATH = f"{_TEAM_DESK_ROOT}/report.txt"
_SUSPECTS_PATH = f"{_TEAM_DESK_ROOT}/suspects.txt"
_CCTV_ABS_PATH = f"{_TEAM_DESK_ROOT}/cctv.log"


def _read_text(state: dict, abs_path: str) -> str | None:
    node = fs.get_node(state, abs_path)
    if not fs.is_file(node):
        return None
    return node.get("content", "")


def _mission25_review(state: dict) -> list[str]:
    """Mission25: report.txt に証拠の絶対パス引用 + 容疑者名の一致が要る。

    初期テンプレの report.txt は絶対パス引用を欠いた状態で配置する想定（Mission
    コンテンツ側の責務）のため、一発承認にはならない構造になる（§ 5b の判定メモ）。
    """
    report = _read_text(state, _REPORT_PATH) or ""
    requests: list[str] = []

    if _CCTV_ABS_PATH not in report:
        requests.append("証拠は絶対パスで引用しろ（/root/team_desk/cctv.log）")

    suspects_text = _read_text(state, _SUSPECTS_PATH)
    # ファイルが無い場合は「載っている名前が無い」＝一致しようがないので指摘が残る。
    names = [ln.strip() for ln in (suspects_text or "").split("\n") if ln.strip()]
    if not any(name in report for name in names):
        requests.append("容疑者名を suspects.txt と一致させろ")

    return requests


# mission_id -> (state) -> 残っている指摘のリスト（空 = APPROVED）。
PR_REVIEWS: dict[int, Callable[[dict], list[str]]] = {
    25: _mission25_review,
}
