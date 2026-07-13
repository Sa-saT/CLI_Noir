"""WebSocket フレームの Pydantic モデル（設計指示書 § 7）。

受信フレーム: auth / exec / resume / complete。送信フレームは dict で構築する
（hello / result / event）。フロントは style→CSS クラス変換のみ行い、色の意味付けは
サーバーが決める（§ 7）。
"""

from typing import Literal

from pydantic import BaseModel


class AuthFrame(BaseModel):
    type: Literal["auth"]
    token: str


class ExecFrame(BaseModel):
    type: Literal["exec"]
    id: int
    command: str


class ResumeFrame(BaseModel):
    type: Literal["resume"]
    commit_id: int


Style = Literal["normal", "error", "warning", "emphasis", "success"]


def state_summary(state: dict) -> dict:
    """hello / result で返す最小 state（§ 7）。"""
    return {
        "current_path": state.get("current_path", "/root"),
        "remote_mode": state.get("remote_mode", False),
        "ssh_host": state.get("ssh_host"),
    }


def style_for(line: str) -> Style:
    if line.startswith("Error:"):
        return "error"
    if line.startswith("Warning:"):
        return "warning"
    if line.startswith("Mission Complete") or line.endswith("all checks passed"):
        return "success"
    return "normal"
