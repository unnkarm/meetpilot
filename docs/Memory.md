# Project Memory & Active Context — MeetPilot AI

## 1. Project Snapshot
- **Repository**: `meetpilot-ai`
- **Application**: AI-driven Meeting Intelligence, Speaker Diarization, Task Extraction, and RAG Knowledge Platform.
- **Frontend Stack**: React 19, TypeScript, Vite, SWR, `@clerk/clerk-react`, Tailwind CSS v4, Lucide Icons.
- **Backend Stack**: Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL + `pgvector`, Redis, Celery, Google Gemini 2.0 Flash (`text-embedding-004`), Fernet Encryption at Rest.

---

## 2. Completed Implementations & Active Architecture

### 2.1 In-Browser Recording & Meeting Intelligence Exports
- In-browser `MediaRecorder` live audio capture with waveform visualization, real-time stopwatch (`00:00`), session naming, and direct submission into `POST /api/v1/meetings/upload`.
- Meeting exports: Clean Markdown (`.md`) download and printable PDF executive summary report (`@media print` styled).

### 2.2 Third-Party Integrations Hub (Discord, Google Calendar, Zoom)
- **Fernet Encryption at Rest**: `app/core/encryption.py` ensures webhook URLs and OAuth access/refresh tokens are encrypted in PostgreSQL.
- **Discord Integration**: Workspace admin configures Discord Webhook URL; automatically posts meeting executive summaries and action items on Celery completion.
- **Google Calendar Integration**: Scoped OAuth flow with automatic synchronization of assigned task due dates to Google Calendar events.
- **Zoom Cloud Recordings Importer**: Zoom OAuth integration with cloud recordings picker modal to fetch and feed recordings directly into Gemini speech diarization.
- **Live Connection State**: `activeTab === 'integrations'` renders real connected/disconnected states with masked credentials and instant disconnect/revocation actions.

### 2.3 Distributed Redis Rate Limiter & Celery Exponential Backoff with Jitter
- **Shared Redis Token Bucket**: `app/core/rate_limiter.py` provides an atomic sliding-window token bucket in Redis shared across all Celery worker processes/containers, enforcing global concurrency and RPM ceilings under Gemini Free Tier limits.
- **Exponential Backoff & Jitter**: Celery task `process_meeting` is configured with `autoretry_for=(RateLimitError,)`, `retry_backoff=True`, `retry_backoff_max=120`, `retry_jitter=True`, and `max_retries=5`, smoothing out concurrent bursts across distributed workers without failure.

### 2.4 Long Audio Chunking, Sequential Speaker Continuity & Seam Deduplication
- **Audio Chunker**: `app/services/audio_chunker.py` slices long recordings (>15m) into sequential overlapping chunks (15-minute windows with 15-second acoustic overlap).
- **Sequential Speaker Continuity Prompt**: `transcribe_audio` processes chunks in chronological order, carrying forward recognized speaker descriptions (`known_speakers`) into subsequent chunk prompts to maintain voice identity consistency across seams.
- **Overlap Seam Deduplication**: `dedupe_overlap_segments` eliminates duplicated segments in the overlap window, preserving chunk N's high-context segments.
- **Batched Vectors**: `embed_texts` processes segments in batches of 100 into PostgreSQL `pgvector`, cutting vector embedding roundtrips.
- **Transparency UI Badge**: `AppWorkspace.tsx` flags recordings >15m with a `"Long Recording (>15m) • Speaker Continuity Enabled"` indicator.

### 2.5 Full-Stack Dashboard De-Mocking & Live SWR Wiring


- The frontend is 100% wired to the live FastAPI backend via typed SWR hooks (`useWorkspaces`, `useWorkspaceMembers`, `useMeetings`, `useMeetingDetail`, `useMeetingSummary`, `useMeetingTranscript`, `useMeetingDecisions`, `useMeetingTasks`, `useWorkspaceTasks`, `useWorkspaceIntegrations`, `useMeetingChat`, `useNotifications`, `useSearch`).
- Deleted `src/data/mockData.ts` and `src/components/SecureWorkspace.tsx` with zero remaining mock references.
- Built explicit UI states for empty workspace, queued jobs, processing meetings (with 5-second polling), completed insights, and failed processing with failure reason display.

### 2.4 Clerk-First Authentication & Identity Synchronization
- Clerk is the exclusive source of truth for user authentication.
- Removed legacy `password_hash` column from SQLAlchemy models and PostgreSQL (`001_remove_password_hash_clerk_auth.py` migration).
- Just-In-Time user sync (`get_current_user` in `backend/app/api/deps.py`) parses Clerk JWT claims, client headers (`X-User-Email`, `X-User-Name`, `X-User-Avatar`), and Clerk REST API to maintain accurate profile data in PostgreSQL.

### 2.6 PostgreSQL Cascade Deletion & Foreign Key Integrity
- **Database-Level ON DELETE CASCADE**: Created and applied Alembic migration `003_add_meeting_cascade_deletes.py`.
- **SQLAlchemy Cascade Models**: Configured `cascade="all, delete-orphan", passive_deletes=True` on `Meeting` relationships and `ForeignKey("meetings.id", ondelete="CASCADE")` across `Notification`, `Task`, `Decision`, `TranscriptSegment`, `MeetingSummary`, `MeetingParticipant`, and `ChatMessage`.
- Deleting a meeting cleanly deletes all associated action items, decisions, embeddings, chat history, summaries, and notifications without foreign key constraint violations or orphaned records.


---

## 3. Environment & Running Services
- **Frontend Dev Server**: `http://localhost:3000` (`npm run dev`)
- **Backend API**: `http://localhost:8000` (`uvicorn app.main:app --reload`)
- **API Swagger Documentation**: `http://localhost:8000/docs`
- **Docker Compose**: `docker compose up --build` (Postgres on `:5433`, Redis on `:6380`, Backend on `:8000`, Frontend on `:3000`)
