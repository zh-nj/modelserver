"""add additional_parameters to model_configs

Revision ID: 003
Revises: 002
Create Date: 2025-01-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    """添加additional_parameters字段到model_configs表"""
    op.add_column('model_configs', sa.Column('additional_parameters', sa.Text(), nullable=True, comment='附加启动参数'))

def downgrade():
    """移除additional_parameters字段"""
    op.drop_column('model_configs', 'additional_parameters')