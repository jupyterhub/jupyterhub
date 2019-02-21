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


from alembic import op
import sqlalchemy as sa

from datetime import datetime


def upgrade():
    op.add_column('users', sa.Column('created', sa.DateTime, nullable=True))
    c = op.get_bind()
    # fill created date with current time
    now = datetime.utcnow()
    c.execute(
        """
        UPDATE users
        SET created='%s'
        """
        % (now,)
    )

    tables = c.engine.table_names()

    if 'spawners' in tables:
        op.add_column('spawners', sa.Column('started', sa.DateTime, nullable=True))
        # fill started value with now for running servers
        c.execute(
            """
            UPDATE spawners
            SET started='%s'
            WHERE server_id IS NOT NULL
            """
            % (now,)
        )


def downgrade():
    op.drop_column('users', 'created')
    op.drop_column('spawners', 'started')
