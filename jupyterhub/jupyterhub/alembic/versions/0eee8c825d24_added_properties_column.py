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

    try:
        op.add_column("groups", sa.Column("properties", JSONDict))
        print("Added column!")
    except:
        print(
            "The properties column could not have been added. Perhaps because it is already existing."
        )

    print("Alembic Upgrade took place!")


def downgrade():

    try:
        op.drop_column("groups", "properties")
        print("Removed column!")
    except:
        print(
            "The properties column could not have been removed. Perhaps because it is not existing."
        )

    print("Alembic downgrade took place!")
