"""merge_heads

Revision ID: b6b9e5a3cbd3
Revises: 20260507_02, 3933ccdc85ea
Create Date: 2026-05-07 22:11:37.649043

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6b9e5a3cbd3'
down_revision: Union[str, Sequence[str], None] = ('20260507_02', '3933ccdc85ea')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
