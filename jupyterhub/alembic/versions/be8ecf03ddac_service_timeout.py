"""empty message

Revision ID: be8ecf03ddac
Revises: 4621fec11365
Create Date: 2025-11-24 16:12:05.681152

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "be8ecf03ddac"
down_revision = "4621fec11365"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "services",
        sa.Column(
            "timeout", sa.Integer(), default=30, server_default="30", nullable=False
        ),
    )


def downgrade():
    op.drop_column("services", "timeout")
