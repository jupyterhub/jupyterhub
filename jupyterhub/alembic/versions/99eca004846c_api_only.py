"""api_only

Add api_only column to users table.

Revision ID: 99eca004846c
Revises: eeb276e51423
Create Date: 2016-06-03 14:49:54.451090

"""

# revision identifiers, used by Alembic.
revision = '99eca004846c'
down_revision = 'eeb276e51423'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('users', sa.Column('api_only', sa.Boolean))


def downgrade():
    # sqlite cannot downgrade because of limited ALTER TABLE support (no DROP COLUMN)
    op.drop_column('users', 'api_only')
