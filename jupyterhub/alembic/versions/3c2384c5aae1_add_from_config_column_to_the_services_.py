"""Add from_config column to the services table

Revision ID: 3c2384c5aae1
Revises: 0eee8c825d24
Create Date: 2023-02-27 16:22:26.196231
"""

# revision identifiers, used by Alembic.
revision = '3c2384c5aae1'
down_revision = '0eee8c825d24'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    engine = op.get_bind().engine
    tables = sa.inspect(engine).get_table_names()
    if 'services' in tables:
        op.add_column(
            'services',
            sa.Column('from_config', sa.Boolean, nullable=True, default=True),
        )
        op.execute('UPDATE services SET from_config = true')


def downgrade():
    op.drop_column('services', sa.Column('from_config'))
