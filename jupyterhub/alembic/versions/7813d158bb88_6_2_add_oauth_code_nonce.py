"""6.2: add oauth_code.nonce

Revision ID: 7813d158bb88
Revises: f460b0348206
Create Date: 2026-10-22 14:54:48.896784

"""

# revision identifiers, used by Alembic.
revision = '7813d158bb88'
down_revision = 'f460b0348206'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.add_column(
        'oauth_codes', sa.Column('nonce', sa.Unicode(length=64), nullable=True)
    )


def downgrade():
    op.drop_column('oauth_codes', 'nonce')
