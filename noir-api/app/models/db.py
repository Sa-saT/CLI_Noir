"""DB エンジン / セッション（SQLModel）。

settings.database_url からエンジンを生成し、FastAPI の依存として get_session を提供する。
テーブル定義は同 package 内（User / MissionState）に追加していく。
"""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.settings import settings

# SQLite の場合のみ check_same_thread=False が必要。
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, echo=settings.debug, connect_args=connect_args)


def get_session() -> Generator[Session, None, None]:
    """FastAPI 依存注入用のセッション供給。"""
    with Session(engine) as session:
        yield session
