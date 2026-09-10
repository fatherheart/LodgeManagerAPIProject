"""add room_id and accepted_by_tenant_id to invites

Revision ID: 2a3b4c5d6e7f
Revises: 1fddb7f6cce4
Create Date: 2026-08-24 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, Sequence[str], None] = '1fddb7f6cce4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('invites', schema=None) as batch_op:
        batch_op.add_column(sa.Column('room_id', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('accepted_by_tenant_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_invites_room_id', 'rooms', ['room_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key('fk_invites_accepted_by_tenant_id', 'tenant_profiles', ['accepted_by_tenant_id'], ['id'], ondelete='SET NULL')
        batch_op.drop_column('lodge_id')



def downgrade() -> None:
    with op.batch_alter_table('invites', schema=None) as batch_op:
        batch_op.add_column(sa.Column('lodge_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key('fk_invites_lodge_id', 'lodges', ['lodge_id'], ['id'], ondelete='CASCADE')
        batch_op.drop_constraint('fk_invites_accepted_by_tenant_id', type_='foreignkey')
        batch_op.drop_constraint('fk_invites_room_id', type_='foreignkey')
        batch_op.drop_column('accepted_by_tenant_id')
        batch_op.drop_column('room_id')
