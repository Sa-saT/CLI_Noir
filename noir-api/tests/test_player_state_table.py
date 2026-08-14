"""PlayerState テーブルのスモークテスト（Part5 P3-01）。

user_id 単位で 1 レコードの永続統合ワールド state を保持できること、
user_id に UNIQUE 制約が効いていることを確認する。API/WS 層はまだ
MissionState を使う（カットオーバーは P3-09/P3-10）ため、ここでは
テーブル定義そのものの健全性のみを検証する。
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import create_user
from app.models import PlayerState, default_state


def test_player_state_round_trip(session: Session) -> None:
    user = create_user(session, "detective01", "secret")
    state = default_state()
    state["current_path"] = "/root/desk"

    row = PlayerState(user_id=user.id, data=state)
    session.add(row)
    session.commit()
    session.refresh(row)

    fetched = session.exec(
        select(PlayerState).where(PlayerState.user_id == user.id)
    ).one()
    assert fetched.data["current_path"] == "/root/desk"


def test_player_state_user_id_is_unique(session: Session) -> None:
    user = create_user(session, "detective02", "secret")
    session.add(PlayerState(user_id=user.id, data=default_state()))
    session.commit()

    session.add(PlayerState(user_id=user.id, data=default_state()))
    with pytest.raises(IntegrityError):
        session.commit()
