"""Create playerstate table (Part5 P3-01: persistent world state, additive)

Revision ID: a1b2c3d4e5f6
Revises: c300ce029dad
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c300ce029dad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    MissionState (user_id + mission_id 単位) は Part5 カットオーバー
    （P3-09/P3-10）まで残す。ここでは PlayerState (user_id 単位。永続統合
    ワールド state) を追加するのみ（追加 → カットオーバー方式）。
    """
    op.create_table('playerstate',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('data', sa.JSON(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_playerstate_user_id'), 'playerstate', ['user_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_playerstate_user_id'), table_name='playerstate')
    op.drop_table('playerstate')
