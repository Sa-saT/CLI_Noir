"""隠しファイル収集（機能 5）とご褒美コマンド（機能 12）。2026-09-13 実装。

- 回想の収集: 隠しファイル（app/content/collection.py の FRAGMENTS）を読むコマンド
  （cat/head/tail/less）で開くと `state["collection"]["found"]` に発見順で積む。
- ご褒美: 収集数が閾値に達すると `state["unlocked_commands"]` にコマンドを足す。engine は
  ご褒美コマンドを「解放されるまで存在しない（command not found）」扱いにする——実機に
  cowsay を入れる前と同じ手触り。
- cowsay / figlet は実在する遊びコマンドの簡易実装（意味一致原則 § 11 機能 12）。
"""

import re

from app.content.collection import FRAGMENTS, TOTAL
from app.evaluator.errors import CommandError
from app.evaluator.registry import command

REWARDS: list[dict] = [
    {"command": "cowsay", "needed": 5, "label": "回想を 5 つ集めた"},
    {"command": "figlet", "needed": TOTAL, "label": "回想を全部集めた"},
]
REWARD_COMMANDS = {r["command"] for r in REWARDS}
_READERS = re.compile(r"\s*(cat|head|tail|less|grep)\b")


def is_unlocked(state: dict, name: str) -> bool:
    return name in state.get("unlocked_commands", [])


def register(state: dict, command_line: str, entry: dict | None) -> list[dict]:
    """読んだ隠しファイルを回想として登録し、解放されたご褒美があれば併せて返す。"""
    if entry is None or not _READERS.match(command_line):
        return []
    found = state.setdefault("collection", {"found": []})["found"]
    events: list[dict] = []
    for path in entry.get("paths", []):
        frag = FRAGMENTS.get(path)
        if frag is None or path in found:
            continue
        found.append(path)
        events.append({
            "kind": "fragment",
            "no": frag["no"],
            "title": frag["title"],
            "found": len(found),
            "total": TOTAL,
        })
    if not events:
        return []
    unlocked = state.setdefault("unlocked_commands", [])
    for reward in REWARDS:
        if len(found) >= reward["needed"] and reward["command"] not in unlocked:
            unlocked.append(reward["command"])
            events.append({"kind": "unlock", "command": reward["command"], "label": reward["label"]})
    return events


def listing(state: dict) -> dict:
    """図鑑 API 用: 見つけた回想（本文付き。時系列順）と総数、解放済みご褒美。"""
    found = state.get("collection", {}).get("found", [])
    fragments = sorted(
        ({"path": p, **FRAGMENTS[p]} for p in found if p in FRAGMENTS), key=lambda f: f["no"]
    )
    return {
        "fragments": fragments,
        "total": TOTAL,
        "unlocked_commands": list(state.get("unlocked_commands", [])),
    }


# --- ご褒美コマンド -----------------------------------------------------------
_COW = r"""        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||"""


@command("cowsay")
def cmd_cowsay(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    text = " ".join(argv[1:]) if len(argv) > 1 else " ".join(stdin)
    if not text:
        raise CommandError("cowsay: no message (usage: cowsay <text>)")
    width = len(text)
    bubble = [
        " " + "_" * (width + 2),
        f"< {text} >",
        " " + "-" * (width + 2),
    ]
    return [*bubble, *_COW.split("\n")], state


# figlet の簡易フォント（5 行・A〜Z 0〜9 と記号少々）。実 figlet の "banner" 風。
_FONT: dict[str, list[str]] = {
    "A": [" ## ", "#  #", "####", "#  #", "#  #"],
    "B": ["### ", "#  #", "### ", "#  #", "### "],
    "C": [" ###", "#   ", "#   ", "#   ", " ###"],
    "D": ["### ", "#  #", "#  #", "#  #", "### "],
    "E": ["####", "#   ", "### ", "#   ", "####"],
    "F": ["####", "#   ", "### ", "#   ", "#   "],
    "G": [" ###", "#   ", "# ##", "#  #", " ###"],
    "H": ["#  #", "#  #", "####", "#  #", "#  #"],
    "I": ["###", " # ", " # ", " # ", "###"],
    "J": ["  ##", "   #", "   #", "#  #", " ## "],
    "K": ["#  #", "# # ", "##  ", "# # ", "#  #"],
    "L": ["#   ", "#   ", "#   ", "#   ", "####"],
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    "O": [" ## ", "#  #", "#  #", "#  #", " ## "],
    "P": ["### ", "#  #", "### ", "#   ", "#   "],
    "Q": [" ## ", "#  #", "#  #", "# ##", " ###"],
    "R": ["### ", "#  #", "### ", "# # ", "#  #"],
    "S": [" ###", "#   ", " ## ", "   #", "### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#  #", "#  #", "#  #", "#  #", " ## "],
    "V": ["#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "# # #", "## ##", "#   #"],
    "X": ["#   #", " # # ", "  #  ", " # # ", "#   #"],
    "Y": ["#   #", " # # ", "  #  ", "  #  ", "  #  "],
    "Z": ["####", "   #", "  # ", " #  ", "####"],
    "0": [" ## ", "#  #", "#  #", "#  #", " ## "],
    "1": [" # ", "## ", " # ", " # ", "###"],
    "2": [" ## ", "#  #", "  # ", " #  ", "####"],
    "3": ["### ", "   #", " ## ", "   #", "### "],
    "4": ["#  #", "#  #", "####", "   #", "   #"],
    "5": ["####", "#   ", "### ", "   #", "### "],
    "6": [" ###", "#   ", "### ", "#  #", " ## "],
    "7": ["####", "   #", "  # ", " #  ", " #  "],
    "8": [" ## ", "#  #", " ## ", "#  #", " ## "],
    "9": [" ## ", "#  #", " ###", "   #", "## "],
    " ": ["  ", "  ", "  ", "  ", "  "],
    "!": ["#", "#", "#", " ", "#"],
    "?": ["## ", "  #", " # ", "   ", " # "],
    "-": ["   ", "   ", "###", "   ", "   "],
    ".": [" ", " ", " ", " ", "#"],
}


@command("figlet")
def cmd_figlet(state: dict, argv: list[str], stdin: list[str]) -> tuple[list[str], dict]:
    text = " ".join(argv[1:]) if len(argv) > 1 else " ".join(stdin)
    if not text:
        raise CommandError("figlet: no message (usage: figlet <text>)")
    rows = ["", "", "", "", ""]
    for ch in text.upper():
        glyph = _FONT.get(ch)
        if glyph is None:
            glyph = _FONT["?"]
        width = max(len(g) for g in glyph)
        for i in range(5):
            rows[i] += glyph[i].ljust(width) + " "
    return [r.rstrip() for r in rows], state
