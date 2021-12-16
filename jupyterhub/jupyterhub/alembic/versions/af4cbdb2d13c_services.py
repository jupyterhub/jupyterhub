"""services

Revision ID: af4cbdb2d13c
Revises: eeb276e51423
Create Date: 2016-07-28 16:16:38.245348

"""
# revision identifiers, used by Alembic.
revision = 'af4cbdb2d13c'
down_revision = 'eeb276e51423'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('api_tokens', sa.Column('service_id', sa.Integer))


def downgrade():
    # sqlite cannot downgrade because of limited ALTER TABLE support (no DROP COLUMN)
    op.drop_column('api_tokens', 'service_id')
