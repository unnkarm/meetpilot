# System Architecture — MeetPilot AI

## 1. High-Level Architecture Overview

MeetPilot AI is architected as a high-performance, asynchronous web application consisting of a modern React/Vite single-page application frontend, a FastAPI REST service, a PostgreSQL database with `pgvector` for semantic search, and an asynchronous Celery task queue backed by Redis for audio processing and Google Gemini AI orchestration.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Frontend (React 19 + Vite)                    │
│    - Clerk Auth (Google, GitHub, Slack)                               │
│    - Interactive Workspace, Kanban Board, AI Meeting Chat              │
│    - Real-time Audio Transcript Player & Deep-Link Search              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST / Bearer JWT
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                           Backend (FastAPI)                            │
│    - Token Verification (Clerk JWKS / PyJWT)                           │
│    - Workspace, User, Meeting, and Task REST Endpoints                 │
│    - CORS Middleware & Global Exception Handling                       │
└──────────────┬────────────────────────────────────────────┬────────────┘
               │                                            │
       SQLAlchemy / pgvector                        Redis Task Queue
               │                                            │
               ▼                                            ▼
┌──────────────────────────────┐            ┌────────────────────────────┐
│   PostgreSQL + pgvector      │            │   Celery Background Worker │
│  - Users & Workspaces        │            │  - Audio Transcoder        │
│  - Meeting Transcripts       │            │  - Google Gemini 2.0 Flash │
│  - 768-dim Vector Embeddings │            │  - Summarizer & Extractor  │
│  - Tasks & Decisions         │            └────────────────────────────┘
└──────────────────────────────┘
```

---

## 2. Technical Stack

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Frontend UI** | React 19, TypeScript, Tailwind CSS v4, Lucide Icons | Responsive SPA with dark mode aesthetic |
| **Auth & Security** | `@clerk/clerk-react`, PyJWT, OAuth2 Bearer Tokens | Multi-provider SSO & secure session management |
| **Backend API** | Python 3.11+, FastAPI, Pydantic v2 | High-throughput async REST API |
| **ORM & DB** | PostgreSQL 16+, SQLAlchemy 2.0, pgvector | Relational data store & vector similarity search |
| **Worker & Queue**| Redis 7+, Celery 5+ | Asynchronous meeting audio processing pipeline |
| **Distributed Rate Limiting** | Configurable Redis Sliding Window | Global multi-worker rate limiting (configurable RPM/TPM/RPD) |
| **Speech-to-Text & Diarization** | Local Speech Diarization & Audio Chunking | Acoustic speaker segmentation with 0 API cost |
| **Vector Search & Embeddings** | Zero-Cost Local Embeddings (768-dim) | High-fidelity dense vectors in PostgreSQL pgvector |
| **AI & LLM** | Google Gemini 2.5 Flash (Single-Pass) | Unified Overview, Takeaways, Next Steps, Tasks, Decisions |
| **Integrations & Security** | Fernet AES Encryption, Discord, Google Calendar, Zoom | Encrypted credentials, digest dispatch, event sync & cloud import |





---

## 3. Directory Structure

```
meetpilot-ai/
├── README.md                    # System Overview & Quickstart
├── docs/                        # Architecture, PRD, Phases, Memory & Rules docs
│   ├── Architecture.md
│   ├── Design.md
│   ├── Memory.md
│   ├── PRD.md
│   ├── Phases.md
│   └── Rules.md
├── docker-compose.yml           # Multi-container local orchestration (Postgres, Redis, Backend, Worker, Frontend)
│
├── backend/
│   ├── alembic/                 # Alembic database migration revisions (001_remove_password_hash_clerk_auth.py)
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py          # Session validation, Clerk profile sync, DB dependencies
│   │   │   └── routes/          # REST routes (auth, workspaces, meetings, tasks, search, chat, users)
│   │   ├── core/
│   │   │   ├── config.py        # Settings, CORS configuration, Pydantic settings
│   │   │   └── security.py      # Clerk JWKS RS256 & JWT verification logic
│   │   ├── database/            # Base metadata & SQLAlchemy session engine
│   │   ├── models/              # SQLAlchemy database models (User, Workspace, Meeting, Task, Decision)
│   │   ├── schemas/             # Pydantic request & response validation schemas
│   │   ├── services/            # Gemini client, audio processing & vector embeddings
│   │   └── workers/             # Celery background meeting processing pipeline
│   ├── storage/                 # Local audio file storage directory
│   ├── alembic.ini              # Alembic database migration config
│   ├── Dockerfile               # Backend container definition
│   └── requirements.txt         # Python dependencies
│
└── frontend/
    ├── src/
    │   ├── components/          # Reusable UI components (Navbar, Hero, AuthModal, AppWorkspace, ProtectedRoute)
    │   ├── data/                # Landing page technology stack & feature tokens (landingData.ts)
    │   ├── services/            # SWR hooks & API mutation client (`apiFetch`)
    │   ├── types/               # TypeScript interfaces & API models
    │   ├── App.tsx              # Main routing & state coordinator
    │   ├── main.tsx             # Root mounting & ClerkProvider
    │   └── index.css            # Custom CSS, Clerk styling & animation tokens
    ├── Dockerfile               # Frontend container definition
    ├── package.json             # NPM dependencies (SWR, Clerk, Lucide) & scripts
    └── vite.config.ts           # Vite bundler configuration

```

---

## 4. End-to-End Audio Processing Pipeline

1. **Upload (`POST /api/v1/meetings/upload`)**:
   - Multipart audio upload receives audio file.
   - Saves file to `./storage/`, creates DB `Meeting` record with status `queued`.
   - Dispatches Celery task `process_meeting.delay(meeting_id)`.

2. **Celery Worker Execution**:
   - Task updates status to `transcribing`.
   - Calls Google Gemini Audio API (`gemini-2.0-flash`) for diarized transcription with millisecond timestamps.
   - Generates text embeddings using `text-embedding-004` (768 dimensions) for each segment and writes to `transcript_segments` with pgvector.

3. **Intelligence Extraction**:
   - Status transitions to `summarizing`.
   - Gemini produces executive summary (Overview, Key Takeaways, Next Steps).
   - Gemini extracts tasks (assignee, priority, due date) and team decisions.
   - Marks meeting status as `completed`.

4. **Meeting RAG & Chat (`POST /api/v1/meetings/{id}/chat`)**:
   - Converts user question to embedding.
   - Performs cosine distance similarity search in `transcript_segments` via pgvector.
   - Synthesizes answer citing exact timestamp references.
