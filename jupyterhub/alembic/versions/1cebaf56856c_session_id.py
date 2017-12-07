"""Add session_id to auth tokens

Revision ID: 1cebaf56856c
Revises: 3ec6993fe20c
Create Date: 2017-12-07 14:43:51.500740

"""

# revision identifiers, used by Alembic.
revision = '1cebaf56856c'
down_revision = '3ec6993fe20c'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

tables = ('oauth_access_tokens', 'oauth_codes')

def upgrade():
    for table in tables:
        op.add_column(table, sa.Column('session_id', sa.Unicode(255)))


def downgrade():
    # sqlite cannot downgrade because of limited ALTER TABLE support (no DROP COLUMN)
    for table in tables:
        op.drop_column(table, 'session_id')
