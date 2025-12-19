"""Add role templates and assignments

Revision ID: 02ab39de9059
Revises: fdd3ef1ac2cd
Create Date: 2025-12-19 11:53:37.306703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '02ab39de9059'
down_revision: Union[str, Sequence[str], None] = 'fdd3ef1ac2cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define enum for migration
access_scope_enum = postgresql.ENUM('SELF', 'INDIVIDUALS', 'GROUP', 'HIERARCHY', 'ALL', name='access_scope', create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum type first
    access_scope_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table('role_templates',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('org_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_system', sa.Boolean(), nullable=False),
    sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('default_access_scope', access_scope_enum, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('employee_role_assignments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('employee_id', sa.Integer(), nullable=False),
    sa.Column('role_template_id', sa.UUID(), nullable=False),
    sa.Column('access_scope', access_scope_enum, nullable=False),
    sa.Column('accessible_employee_ids', postgresql.ARRAY(sa.Integer()), nullable=True),
    sa.Column('accessible_groups', postgresql.ARRAY(sa.String()), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
    sa.ForeignKeyConstraint(['role_template_id'], ['role_templates.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('employee_role_assignments')
    op.drop_table('role_templates')
    access_scope_enum.drop(op.get_bind(), checkfirst=True)
