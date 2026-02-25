"""Add display_name to spawners

Revision ID: f460b0348206
Revises: be8ecf03ddac
Create Date: 2025-11-05 22:02:38.326220

"""

# revision identifiers, used by Alembic.
revision = 'f460b0348206'
down_revision = 'be8ecf03ddac'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.add_column(
        'spawners', sa.Column('display_name', sa.Unicode(length=255), nullable=True)
    )


def downgrade():
    op.drop_column('spawners', 'display_name')
