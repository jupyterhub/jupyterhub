"""added display_name column

Revision ID: add181e97222
Revises: 0eee8c825d24
Create Date: 2022-01-07 14:29:28.721364

"""

# revision identifiers, used by Alembic.
revision = 'add181e97222'
down_revision = '0eee8c825d24'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    engine = op.get_bind().engine
    tables = sa.inspect(engine).get_table_names()
    if 'groups' in tables:
        op.add_column('groups', sa.Column('display_name', sa.Unicode(255)))


def downgrade():
    op.drop_column('groups', sa.Column('display_name'))
