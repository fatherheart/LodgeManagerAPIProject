"""add_cancelled_to_ownership_invite_status

Revision ID: 3b4c5d6e7f8a
Revises: 220040393ee8
Create Date: 2026-09-05 15:00:00.000000

Adds the CANCELLED state to the ownershipinvitestatus enum.
In SQLite, enums are stored as VARCHAR with CHECK constraints.
Batch mode is required to recreate the constraint with the new value.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b4c5d6e7f8a'
down_revision: Union[str, Sequence[str], None] = '220040393ee8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add CANCELLED to ownership_invites.status enum."""
    with op.batch_alter_table('ownership_invites', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum('ACTIVE', 'CONSUMED', 'EXPIRED', name='ownershipinvitestatus'),
            type_=sa.Enum('ACTIVE', 'CONSUMED', 'EXPIRED', 'CANCELLED', name='ownershipinvitestatus'),
            existing_nullable=True,
            nullable=True
        )


def downgrade() -> None:
    """Remove CANCELLED from ownership_invites.status enum."""
    with op.batch_alter_table('ownership_invites', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum('ACTIVE', 'CONSUMED', 'EXPIRED', 'CANCELLED', name='ownershipinvitestatus'),
            type_=sa.Enum('ACTIVE', 'CONSUMED', 'EXPIRED', name='ownershipinvitestatus'),
            existing_nullable=True,
            nullable=True
        )
