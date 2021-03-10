"""rbac

Revision ID: 833da8570507
Revises: 4dc2d5a8c53c
Create Date: 2021-02-17 15:03:04.360368

"""
# revision identifiers, used by Alembic.
revision = '833da8570507'
down_revision = '4dc2d5a8c53c'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # FIXME: currently drops all api tokens and forces recreation!
    # this ensures a consistent database, but requires:
    # 1. all servers to be stopped for upgrade (maybe unavoidable anyway)
    # 2. any manually issued/stored tokens to be re-issued

    # tokens loaded via configuration will be recreated on launch and unaffected
    op.drop_table('api_tokens')
    op.drop_table('oauth_access_tokens')
    return
    # TODO: explore in-place migration. This seems hard!
    # 1. add new columns in api tokens
    # 2. fill default fields (client_id='jupyterhub') for all api tokens
    # 3. copy oauth tokens into api tokens
    # 4. give oauth tokens 'identify' scopes

    c = op.get_bind()
    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    with op.batch_alter_table(
        "api_tokens",
        naming_convention=naming_convention,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                'client_id',
                sa.Unicode(255),
                # sa.ForeignKey('oauth_clients.identifier', ondelete='CASCADE'),
                nullable=True,
            ),
        )
        # batch_cursor = op.get_bind()
        # batch_cursor.execute(
        #     """
        #     UPDATE api_tokens
        #     SET client_id='jupyterhub'
        #     WHERE client_id IS NULL
        #     """
        # )
        batch_op.create_foreign_key(
            "fk_api_token_client_id",
            # 'api_tokens',
            'oauth_clients',
            ['client_id'],
            ['identifier'],
            ondelete='CASCADE',
        )

    c.execute(
        """
            UPDATE api_tokens
            SET client_id='jupyterhub'
            WHERE client_id IS NULL
        """
    )

    op.add_column(
        'api_tokens',
        sa.Column(
            'grant_type',
            sa.Enum(
                'authorization_code',
                'implicit',
                'password',
                'client_credentials',
                'refresh_token',
                name='granttype',
            ),
            server_default='authorization_code',
            nullable=False,
        ),
    )
    op.add_column(
        'api_tokens', sa.Column('refresh_token', sa.Unicode(length=255), nullable=True)
    )
    op.add_column(
        'api_tokens', sa.Column('session_id', sa.Unicode(length=255), nullable=True)
    )

    # TODO: migrate OAuth tokens into APIToken table

    op.drop_index('ix_oauth_access_tokens_prefix', table_name='oauth_access_tokens')
    op.drop_table('oauth_access_tokens')


def downgrade():
    # delete OAuth tokens for non-jupyterhub clients
    # drop new columns from api tokens
    op.drop_constraint(None, 'api_tokens', type_='foreignkey')
    op.drop_column('api_tokens', 'session_id')
    op.drop_column('api_tokens', 'refresh_token')
    op.drop_column('api_tokens', 'grant_type')
    op.drop_column('api_tokens', 'client_id')
    # FIXME: only drop tokens whose client id is not 'jupyterhub'
    # until then, drop all tokens
    op.drop_table("api_tokens")

    op.drop_table('api_token_role_map')
    op.drop_table('service_role_map')
    op.drop_table('user_role_map')
    op.drop_table('roles')
