"""encrypted_auth_state

Revision ID: 3ec6993fe20c
Revises: af4cbdb2d13c
Create Date: 2017-07-28 16:44:40.413648

"""

# revision identifiers, used by Alembic.
revision = '3ec6993fe20c'
down_revision = 'af4cbdb2d13c'
branch_labels = None
depends_on = None

import warnings

from alembic import op
import sqlalchemy as sa
from jupyterhub.orm import JSONDict


def upgrade():
    try:
        op.drop_column('users', 'auth_state')
    except sa.exc.OperationalError as e:
        # sqlite3 can't drop columns
        warnings.warn("Failed to drop column: %s" % e)
    op.add_column('users', sa.Column('encrypted_auth_state', sa.types.LargeBinary))


def downgrade():
    op.drop_column('users', 'encrypted_auth_state')
    op.add_column('users', sa.Column('auth_state', JSONDict))
    
