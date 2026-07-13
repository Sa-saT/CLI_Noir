"""FastAPI アプリ生成・ルータ登録のエントリポイント。

起動: `uvicorn app.main:app --reload --port 8000`
OpenAPI: http://localhost:8000/docs

各ルータ・WS の中身は未実装（context/03_pending_items.md 参照）。
本ファイルは配線のみを担い、機能は app/api・app/ws 側に実装する。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, missions, state
from app.settings import settings
from app.ws import terminal

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HTTP ルータ（読み取り中心。state 書き込みは WS evaluator のみ） ---
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(missions.router, prefix="/api/missions", tags=["missions"])
# state は missions のサブリソース: /api/missions/{id}/state/（設計指示書 § 6）
app.include_router(state.router, prefix="/api/missions", tags=["state"])

# --- WebSocket: /ws/terminal ---
app.include_router(terminal.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    """疎通確認用の最小エンドポイント。"""
    return {"status": "ok"}
