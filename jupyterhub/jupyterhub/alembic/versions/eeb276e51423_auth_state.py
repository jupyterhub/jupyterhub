"""auth_state

Adds auth_state column to Users table.

Revision ID: eeb276e51423
Revises: 19c0846f6344
Create Date: 2016-04-11 16:06:49.239831
"""
# revision identifiers, used by Alembic.
revision = 'eeb276e51423'
down_revision = '19c0846f6344'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from jupyterhub.orm import JSONDict


def upgrade():
    op.add_column('users', sa.Column('auth_state', JSONDict))


def downgrade():
    # sqlite cannot downgrade because of limited ALTER TABLE support (no DROP COLUMN)
    op.drop_column('users', 'auth_state')
