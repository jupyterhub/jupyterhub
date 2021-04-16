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
    # FIXME, maybe: currently drops all api tokens and forces recreation!
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


def downgrade():
    # delete OAuth tokens for non-jupyterhub clients
    # drop new columns from api tokens
    op.drop_constraint(None, 'api_tokens', type_='foreignkey')
    op.drop_column('api_tokens', 'session_id')
    op.drop_column('api_tokens', 'client_id')

    # FIXME: only drop tokens whose client id is not 'jupyterhub'
    # until then, drop all tokens
    op.drop_table("api_tokens")

    op.drop_table('api_token_role_map')
    op.drop_table('service_role_map')
    op.drop_table('user_role_map')
    op.drop_table('roles')
