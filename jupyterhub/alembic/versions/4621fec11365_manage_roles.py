"""manage roles

Revision ID: 4621fec11365
Revises: 3c2384c5aae1
Create Date: 2024-04-09 09:28:13.576059

"""

# revision identifiers, used by Alembic.
revision = '4621fec11365'
down_revision = '3c2384c5aae1'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    engine = op.get_bind().engine
    tables = sa.inspect(engine).get_table_names()
    for table in ['group_role_map', 'roles', 'service_role_map', 'user_role_map']:
        if table not in tables:
            continue
        # create column and assign existing rows with False
        # since they are not managed
        op.add_column(
            table,
            sa.Column(
                'managed_by_auth',
                sa.Boolean(),
                server_default=sa.sql.False_(),
                nullable=False,
            ),
        )


def downgrade():
    engine = op.get_bind().engine
    tables = sa.inspect(engine).get_table_names()
    for table in ['group_role_map', 'roles', 'service_role_map', 'user_role_map']:
        if table not in tables:
            continue
        op.drop_column(table, 'managed_by_auth')
