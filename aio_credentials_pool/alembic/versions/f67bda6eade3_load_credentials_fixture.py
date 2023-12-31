"""Load credentials fixture

Revision ID: f67bda6eade3
Revises: 890872dbc09f
Create Date: 2023-12-16 18:00:00.644327

"""
import json
from pathlib import Path

from alembic import op

from models import Credential

# revision identifiers, used by Alembic.
revision = 'f67bda6eade3'
down_revision = '890872dbc09f'
branch_labels = None
depends_on = None


CREDENTIALS_JSON_PATH = Path(__file__).parent.parent.parent / 'fixtures' / 'credentials.json'


def load_credentials_data():
    with Path(CREDENTIALS_JSON_PATH).open() as file:
        data = json.load(file)
        op.bulk_insert(Credential.__table__, data)


def upgrade() -> None:
    load_credentials_data()


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
