"""0.8 changes

- encrypted auth_state
- remove proxy/hub data from db

OAuth data was also added in this revision,
but no migration to do because they are entirely new tables,
which will be created on launch.

Revision ID: 3ec6993fe20c
Revises: af4cbdb2d13c
Create Date: 2017-07-28 16:44:40.413648

"""
# revision identifiers, used by Alembic.
revision = '3ec6993fe20c'
down_revision = 'af4cbdb2d13c'
branch_labels = None
depends_on = None

import logging

logger = logging.getLogger('alembic')

from alembic import op
import sqlalchemy as sa
from jupyterhub.orm import JSONDict


def upgrade():
    # proxy/table info is no longer in the database
    op.drop_table('proxies')
    op.drop_table('hubs')

    # drop some columns no longer in use
    try:
        op.drop_column('users', 'auth_state')
        # mysql cannot drop _server_id without also dropping
        # implicitly created foreign key
        if op.get_context().dialect.name == 'mysql':
            op.drop_constraint('users_ibfk_1', 'users', type_='foreignkey')
        op.drop_column('users', '_server_id')
    except sa.exc.OperationalError:
        # this won't be a problem moving forward, but downgrade will fail
        if op.get_context().dialect.name == 'sqlite':
            logger.warning(
                "sqlite cannot drop columns. Leaving unused old columns in place."
            )
        else:
            raise

    op.add_column('users', sa.Column('encrypted_auth_state', sa.types.LargeBinary))


def downgrade():
    # drop all the new tables
    engine = op.get_bind().engine
    for table in ('oauth_clients', 'oauth_codes', 'oauth_access_tokens', 'spawners'):
        if engine.has_table(table):
            op.drop_table(table)

    op.drop_column('users', 'encrypted_auth_state')

    op.add_column('users', sa.Column('auth_state', JSONDict))
    op.add_column(
        'users', sa.Column('_server_id', sa.Integer, sa.ForeignKey('servers.id'))
    )
