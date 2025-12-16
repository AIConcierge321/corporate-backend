"""Fix_policy_status_enum_case

Revision ID: eac31eaee70b
Revises: 4eba7dfdd594
Create Date: 2025-12-16 12:25:12.773067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eac31eaee70b'
down_revision: Union[str, Sequence[str], None] = '4eba7dfdd594'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('bookings', 'policy_status')
    sa.Enum(name='policy_status').drop(op.get_bind())
    
    new_enum = sa.Enum('pass', 'warn', 'block', name='policy_status')
    new_enum.create(op.get_bind())
    
    op.add_column('bookings', sa.Column('policy_status', new_enum, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bookings', 'policy_status')
    sa.Enum(name='policy_status').drop(op.get_bind())
    
    old_enum = sa.Enum('PASS', 'WARN', 'BLOCK', name='policy_status')
    old_enum.create(op.get_bind())
    
    op.add_column('bookings', sa.Column('policy_status', old_enum, nullable=True))
