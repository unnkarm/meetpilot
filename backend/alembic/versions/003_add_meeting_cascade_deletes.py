"""add cascade deletes to meeting relationships

Revision ID: 003_meeting_cascade_deletes
Revises: 002_workspace_integrations
Create Date: 2026-08-08 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_meeting_cascade_deletes'
down_revision: Union[str, None] = '002_workspace_integrations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely drop and recreate FK constraints with ON DELETE CASCADE in PostgreSQL
    # Notifications
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_meeting_id_fkey;
            ALTER TABLE notifications
                ADD CONSTRAINT notifications_meeting_id_fkey
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$;
    """)

    # Tasks
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_meeting_id_fkey;
            ALTER TABLE tasks
                ADD CONSTRAINT tasks_meeting_id_fkey
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$;
    """)

    # Decisions
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE decisions DROP CONSTRAINT IF EXISTS decisions_meeting_id_fkey;
            ALTER TABLE decisions
                ADD CONSTRAINT decisions_meeting_id_fkey
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$;
    """)

    # Transcript Segments
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE transcript_segments DROP CONSTRAINT IF EXISTS transcript_segments_meeting_id_fkey;
            ALTER TABLE transcript_segments
                ADD CONSTRAINT transcript_segments_meeting_id_fkey
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$;
    """)

    # Meeting Summaries
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE meeting_summaries DROP CONSTRAINT IF EXISTS meeting_summaries_meeting_id_fkey;
            ALTER TABLE meeting_summaries
                ADD CONSTRAINT meeting_summaries_meeting_id_fkey
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$;
    """)

    # Meeting Participants
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE meeting_participants DROP CONSTRAINT IF EXISTS meeting_participants_meeting_id_fkey;
            ALTER TABLE meeting_participants
                ADD CONSTRAINT meeting_participants_meeting_id_fkey
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$;
    """)

    # Chat Messages
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chat_messages_meeting_id_fkey;
            ALTER TABLE chat_messages
                ADD CONSTRAINT chat_messages_meeting_id_fkey
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$;
    """)


def downgrade() -> None:
    pass
