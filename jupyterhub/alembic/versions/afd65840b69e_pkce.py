"""pkce

Revision ID: afd65840b69e
Revises: 4621fec11365
Create Date: 2024-10-21 11:14:43.079782

"""

# revision identifiers, used by Alembic.
revision = 'afd65840b69e'
down_revision = '4621fec11365'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    engine = op.get_bind().engine
    tables = sa.inspect(engine).get_table_names()
    if 'oauth_codes' not in tables:
        return
    op.add_column(
        'oauth_codes',
        sa.Column('code_challenge', sa.Unicode(length=255), nullable=True),
    )
    op.add_column(
        'oauth_codes',
        sa.Column('code_challenge_method', sa.Unicode(length=64), nullable=True),
    )


def downgrade():
    engine = op.get_bind().engine
    tables = sa.inspect(engine).get_table_names()
    if 'oauth_codes' not in tables:
        return
    op.drop_column('oauth_codes', 'code_challenge_method')
    op.drop_column('oauth_codes', 'code_challenge')
