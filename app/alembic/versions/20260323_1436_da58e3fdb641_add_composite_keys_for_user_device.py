"""Add composite keys for user device

Revision ID: da58e3fdb641
Revises: 20260321_120000
Create Date: 2026-03-23 14:36:47.943927

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'da58e3fdb641'
down_revision: Union[str, None] = '20260321_120000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop the old foreign key on refresh_tokens
    op.drop_constraint('refresh_tokens_device_id_fkey', 'refresh_tokens', type_='foreignkey')

    # 2. Drop the old primary key on user_devices
    op.drop_constraint('user_devices_pkey', 'user_devices', type_='primary')

    # 3. Create the new composite primary key on user_devices
    op.create_primary_key('user_devices_pkey', 'user_devices', ['id', 'user_id'])

    # 4. Re-add the composite foreign key on refresh_tokens
    op.create_foreign_key(
        'refresh_tokens_device_id_user_id_fkey',
        'refresh_tokens',
        'user_devices',
        ['device_id', 'user_id'],
        ['id', 'user_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Revert all changes
    op.drop_constraint('refresh_tokens_device_id_user_id_fkey', 'refresh_tokens', type_='foreignkey')
    op.drop_constraint('user_devices_pkey', 'user_devices', type_='primary')
    op.create_primary_key('user_devices_pkey', 'user_devices', ['id'])
    op.create_foreign_key(
        'refresh_tokens_device_id_fkey',
        'refresh_tokens',
        'user_devices',
        ['device_id'],
        ['id'],
        ondelete='CASCADE'
    )
    # ### end Alembic commands ###
