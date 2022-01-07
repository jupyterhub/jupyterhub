"""added properties column

Revision ID: 0eee8c825d24
Revises: 833da8570507
Create Date: 2021-09-15 14:04:09.067024

"""
# revision identifiers, used by Alembic.
revision = '0eee8c825d24'
down_revision = '833da8570507'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from jupyterhub.orm import JSONDict


def upgrade():
    engine = op.get_bind().engine
    tables = sa.inspect(engine).get_table_names()
    if 'groups' in tables:
        op.add_column('groups', sa.Column('properties', JSONDict))


def downgrade():
    op.drop_column('groups', sa.Column('properties'))
