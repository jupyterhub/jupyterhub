"""token tracking

Revision ID: 56cc5a70207e
Revises: 1cebaf56856c
Create Date: 2017-12-19 15:21:09.300513

"""
# revision identifiers, used by Alembic.
revision = '56cc5a70207e'
down_revision = '1cebaf56856c'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

import logging

logger = logging.getLogger('alembic')


def upgrade():
    tables = op.get_bind().engine.table_names()
    op.add_column('api_tokens', sa.Column('created', sa.DateTime(), nullable=True))
    op.add_column(
        'api_tokens', sa.Column('last_activity', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'api_tokens', sa.Column('note', sa.Unicode(length=1023), nullable=True)
    )
    if 'oauth_access_tokens' in tables:
        op.add_column(
            'oauth_access_tokens', sa.Column('created', sa.DateTime(), nullable=True)
        )
        op.add_column(
            'oauth_access_tokens',
            sa.Column('last_activity', sa.DateTime(), nullable=True),
        )
        if op.get_context().dialect.name == 'sqlite':
            logger.warning(
                "sqlite cannot use ALTER TABLE to create foreign keys. Upgrade will be incomplete."
            )
        else:
            op.create_foreign_key(
                None,
                'oauth_access_tokens',
                'oauth_clients',
                ['client_id'],
                ['identifier'],
                ondelete='CASCADE',
            )
            op.create_foreign_key(
                None,
                'oauth_codes',
                'oauth_clients',
                ['client_id'],
                ['identifier'],
                ondelete='CASCADE',
            )


def downgrade():
    op.drop_constraint(None, 'oauth_codes', type_='foreignkey')
    op.drop_constraint(None, 'oauth_access_tokens', type_='foreignkey')
    op.drop_column('oauth_access_tokens', 'last_activity')
    op.drop_column('oauth_access_tokens', 'created')
    op.drop_column('api_tokens', 'note')
    op.drop_column('api_tokens', 'last_activity')
    op.drop_column('api_tokens', 'created')
