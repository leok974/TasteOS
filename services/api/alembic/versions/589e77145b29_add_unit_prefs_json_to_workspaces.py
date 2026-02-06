"""add unit_prefs_json to workspaces

Revision ID: 589e77145b29
Revises: 6518be12fb93
Create Date: 2026-02-06 14:47:23.296567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '589e77145b29'
down_revision: Union[str, None] = '6518be12fb93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    op.add_column('workspaces', sa.Column('unit_prefs_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))


def downgrade() -> None:
    op.drop_column('workspaces', 'unit_prefs_json')
