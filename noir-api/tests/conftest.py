"""pytest 共通フィクスチャ。

本物の DB ではなく in-memory SQLite を使い、get_session を差し替える。
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401  テーブルを metadata に登録
from app.main import app
from app.models.db import get_session


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine) -> Generator[TestClient, None, None]:
    def get_session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    yield TestClient(app)
    app.dependency_overrides.clear()
