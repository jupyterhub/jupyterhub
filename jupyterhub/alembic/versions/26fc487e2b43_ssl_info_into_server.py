"""SSL info into server

Revision ID: 26fc487e2b43
Revises: 896818069c98
Create Date: 2018-05-17 10:33:52.022786

"""

# revision identifiers, used by Alembic.
revision = '26fc487e2b43'
down_revision = '896818069c98'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('servers', sa.Column('certfile', sa.Unicode(4096)))
    op.add_column('servers', sa.Column('keyfile', sa.Unicode(4096)))
    op.add_column('servers', sa.Column('cafile', sa.Unicode(4096)))


def downgrade():
    op.drop_column('servers', 'certfile')
    op.drop_column('servers', 'keyfile')
    op.drop_column('servers', 'cafile')
