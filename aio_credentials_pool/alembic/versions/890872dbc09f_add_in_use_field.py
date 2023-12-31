"""Add in_use field

Revision ID: 890872dbc09f
Revises: 70f77cac5a07
Create Date: 2023-12-16 17:05:53.996947

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '890872dbc09f'
down_revision = '70f77cac5a07'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('credentials', sa.Column('in_use', sa.Boolean(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('credentials', 'in_use')
    # ### end Alembic commands ###
