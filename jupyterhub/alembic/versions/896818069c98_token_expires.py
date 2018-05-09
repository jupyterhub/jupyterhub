"""Add APIToken.expires_at

Revision ID: 896818069c98
Revises: d68c98b66cd4
Create Date: 2018-05-07 11:35:58.050542

"""

# revision identifiers, used by Alembic.
revision = '896818069c98'
down_revision = 'd68c98b66cd4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('api_tokens', sa.Column('expires_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('api_tokens', 'expires_at')
