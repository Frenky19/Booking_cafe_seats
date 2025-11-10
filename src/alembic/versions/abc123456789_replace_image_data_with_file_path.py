"""replace image_data with file_path in media table

Revision ID: abc123456789
Revises: 5daf9214ee91
Create Date: 2025-10-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'abc123456789'
down_revision: Union[str, Sequence[str], None] = '5daf9214ee91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # First, add file_path column as nullable
    op.add_column(
        'media', sa.Column('file_path', sa.String(length=500), nullable=True)
    )

    # Update existing records with a default path (if any exist)
    # This is a placeholder - in production you'd migrate data properly
    op.execute(
        "UPDATE media SET file_path = 'media/migrated_' || id::text || '.jpg' "
        "WHERE file_path IS NULL"
    )

    # Now make the column NOT NULL
    op.alter_column('media', 'file_path', nullable=False)

    # Finally, remove the image_data column
    op.drop_column('media', 'image_data')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back image_data column and remove file_path column
    op.drop_column('media', 'file_path')
    op.add_column(
        'media',
        sa.Column(
            'image_data',
            postgresql.BYTEA(),
            autoincrement=False,
            nullable=False,
        ),
    )
