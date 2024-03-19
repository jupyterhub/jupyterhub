"""user.created and spawner.started

Revision ID: 99a28a4418e1
Revises: 56cc5a70207e
Create Date: 2018-03-21 14:27:17.466841

"""

# revision identifiers, used by Alembic.
revision = '99a28a4418e1'
down_revision = '56cc5a70207e'
branch_labels = None
depends_on = None


from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op


def utcnow():
    return datetime.now(timezone.utc)._replace(tzinfo=None)


def upgrade():
    op.add_column('users', sa.Column('created', sa.DateTime, nullable=True))
    c = op.get_bind()
    # fill created date with current time
    now = utcnow()
    c.execute(
        f"""
        UPDATE users
        SET created='{now}'
        """
    )

    tables = sa.inspect(c.engine).get_table_names()

    if 'spawners' in tables:
        op.add_column('spawners', sa.Column('started', sa.DateTime, nullable=True))
        # fill started value with now for running servers
        c.execute(
            f"""
            UPDATE spawners
            SET started='{now}'
            WHERE server_id IS NOT NULL
            """
        )


def downgrade():
    op.drop_column('users', 'created')
    op.drop_column('spawners', 'started')
