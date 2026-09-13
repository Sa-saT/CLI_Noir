"""図鑑の登録（ゲーム機能 2・10）。純粋関数。WS ハンドラが評価後に呼ぶ。

`state["codex"] = {"commands": {name: {"first_mission": id, "count": n}},
                   "errors": {key: {"first_mission": id, "count": n, "sample": line}}}`
戻り値は今回**新しく登録された**エントリ（フロントが scene の図鑑レイヤーに出す）。
"""

import re

from app.content.codex import error_entry_for
from app.evaluator import progress
from app.evaluator.registry import get_command

_STAGE_SPLIT = re.compile(r"\s*\|\s*")


def _command_names(command_line: str) -> list[str]:
    names: list[str] = []
    for stage in _STAGE_SPLIT.split(command_line.strip()):
        tok = stage.split()
        if not tok:
            continue
        name = tok[0].rsplit("/", 1)[-1]
        if get_command(name) is not None and name not in names:
            names.append(name)
    return names


def register(state: dict, command_line: str, out_lines: list[str], ok: bool) -> list[dict]:
    codex = state.setdefault("codex", {"commands": {}, "errors": {}})
    mission_id = progress.active_mission_id(state["mission_progress"])
    new: list[dict] = []

    if ok:
        for name in _command_names(command_line):
            entry = codex["commands"].get(name)
            if entry is None:
                codex["commands"][name] = {"first_mission": mission_id, "count": 1}
                new.append({"kind": "command", "key": name})
            else:
                entry["count"] += 1

    for line in out_lines:
        found = error_entry_for(line)
        if found is None:
            continue
        entry = codex["errors"].get(found["key"])
        if entry is None:
            codex["errors"][found["key"]] = {
                "first_mission": mission_id,
                "count": 1,
                "sample": line,
            }
            new.append({"kind": "error", "key": found["key"], "title": found["title"], "text": found["text"]})
        else:
            entry["count"] += 1
    return new


def listing(state: dict) -> dict:
    """GET /api/codex/ 用: 登録済みの道具とエラー（翻訳文付き）。"""
    codex = state.get("codex", {"commands": {}, "errors": {}})
    errors = []
    for key, meta in codex["errors"].items():
        found = error_entry_for(key) or {"key": key, "title": key, "text": ""}
        errors.append({"key": key, "title": found["title"], "text": found["text"], **meta})
    commands = [{"name": name, **meta} for name, meta in codex["commands"].items()]
    return {"commands": commands, "errors": errors}
