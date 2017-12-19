"""Add session_id to auth tokens

Revision ID: 1cebaf56856c
Revises: 3ec6993fe20c
Create Date: 2017-12-07 14:43:51.500740

"""

# revision identifiers, used by Alembic.
revision = '1cebaf56856c'
down_revision = '3ec6993fe20c'
branch_labels = None
depends_on = None

import logging
logger = logging.getLogger('alembic')

from alembic import op
import sqlalchemy as sa

tables = ('oauth_access_tokens', 'oauth_codes')

def add_column_if_table_exists(table, column):
    try:
        op.add_column(table, column)
    except (sa.exc.OperationalError, sa.exc.ProgrammingError) as e:
        # check if it failed because the table doesn't exist
        # if that's the case, do nothing
        ctx = op.get_context()
        try:
            ctx.execute('SELECT 1 FROM {table} LIMIT 1'.format(table=table))
        except Exception as e2:
            if type(e) is type(e2) and e.args == e2.args:
                # table doesn't exist, no need to upgrade
                # because jupyterhub will create it on launch
                logger.warning("Skipping upgrade of absent table: %s" % e)
                return
        # if we got here, adding column failed, but selecting from the table succeeded
        # it was a real error
        raise

def upgrade():
    ctx = op.get_context()
    for table in tables:
        add_column_if_table_exists(table, sa.Column('session_id', sa.Unicode(255)))


def downgrade():
    # sqlite cannot downgrade because of limited ALTER TABLE support (no DROP COLUMN)
    for table in tables:
        op.drop_column(table, 'session_id')
