"""add live meeting fields to meetings table

Revision ID: 004_live_meeting_fields
Revises: 003_meeting_cascade_deletes
Create Date: 2026-08-08 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_live_meeting_fields'
down_revision: Union[str, None] = '003_meeting_cascade_deletes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Safely add 'in_progress' to PostgreSQL meetingstatus enum if it exists
    op.execute("""
        DO $$
        BEGIN
            ALTER TYPE meetingstatus ADD VALUE IF NOT EXISTS 'in_progress';
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$;
    """)

    # 2. Add source column to meetings (default 'upload')
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'meetings' AND column_name = 'source'
            ) THEN
                ALTER TABLE meetings ADD COLUMN source VARCHAR(32) DEFAULT 'upload' NOT NULL;
            END IF;
        END $$;
    """)

    # 3. Add native_meeting_id column to meetings
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'meetings' AND column_name = 'native_meeting_id'
            ) THEN
                ALTER TABLE meetings ADD COLUMN native_meeting_id VARCHAR(255) NULL;
            END IF;
        END $$;
    """)

    # 4. Add vexa_bot_id column to meetings
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'meetings' AND column_name = 'vexa_bot_id'
            ) THEN
                ALTER TABLE meetings ADD COLUMN vexa_bot_id VARCHAR(255) NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    pass
