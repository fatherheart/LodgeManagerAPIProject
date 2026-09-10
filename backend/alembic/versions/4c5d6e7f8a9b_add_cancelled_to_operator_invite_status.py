"""add_cancelled_to_operator_invite_status

Revision ID: 4c5d6e7f8a9b
Revises: 3b4c5d6e7f8a
Create Date: 2026-09-05 23:00:00.000000

Adds the CANCELLED state to the operatorinvitestatus enum.
In SQLite, enums are stored as VARCHAR with CHECK constraints.
Batch mode is required to recreate the constraint with the new value.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c5d6e7f8a9b'
down_revision: Union[str, Sequence[str], None] = '3b4c5d6e7f8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add CANCELLED to operator_invites.status enum."""
    with op.batch_alter_table('operator_invites', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum('ACTIVE', 'ACCEPTED', 'EXPIRED', name='operatorinvitestatus'),
            type_=sa.Enum('ACTIVE', 'ACCEPTED', 'EXPIRED', 'CANCELLED', name='operatorinvitestatus'),
            existing_nullable=True,
            nullable=True
        )


def downgrade() -> None:
    """Remove CANCELLED from operator_invites.status enum."""
    with op.batch_alter_table('operator_invites', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum('ACTIVE', 'ACCEPTED', 'EXPIRED', 'CANCELLED', name='operatorinvitestatus'),
            type_=sa.Enum('ACTIVE', 'ACCEPTED', 'EXPIRED', name='operatorinvitestatus'),
            existing_nullable=True,
            nullable=True
        )
