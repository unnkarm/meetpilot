# Architecture: development implementation and hosted SaaS target

**Product direction, 8 October 2026:** the final product is a hosted web SaaS.
Local services are the inexpensive development environment. The target replaces
Ollama text inference with OpenAI GPT APIs. Customers use a browser without model
or Docker installation. See Feature_Roadmap.md for the complete feature scope and
Cloud_AI.md for the implemented provider switch and migration.

## Runtime

- React 19, TypeScript, Vite, Tailwind and SWR frontend on port 3000; Clerk supplies authentication tokens.
- FastAPI backend on port 8000 verifies identity and workspace membership at API boundaries.
- PostgreSQL 16 with pgvector stores users, workspaces, meetings, transcript segments, summaries, tasks, decisions, documents, embeddings, notifications and product events.
- Redis brokers Celery work. The worker transcribes and analyzes uploaded recordings outside the request path.
- Ollama serves Qwen and nomic in the default development setup. OpenAI text and embedding adapters are selectable independently. faster-whisper runs inside speech/processing workers; recordings currently use filesystem storage.
- Official Vexa Lite is the active meeting engine, with a MeetPilot overlay for audio/voice integration and a dedicated meeting_bot Celery bridge. Vexa's PostgreSQL, Redis and recording storage are separate from application records. Legacy native-browser code and optional remote transcription are not the active default live path.

## Upload and processing

1. An authenticated workspace member uploads a supported audio file. The API validates size/type, writes it to local storage, creates a queued meeting, and sends a Celery job.
2. An atomic queued claim prevents duplicate deliveries. The worker records transcribing, transcribed, embedding, analyzing and completed states, plus timestamps and failures.
3. FFmpeg/ffprobe inspect and split long audio without decoding the entire recording into Python memory. faster-whisper extracts timestamped speech; overlap is deduplicated. Chunk failures are explicit. Default speaker identity is unknown and displayed as Speaker 1.
4. Transcript segments commit before embedding or LLM analysis so source speech survives later failures.
5. The configured embedding provider creates 768-dimensional vectors from original text, with index provenance. The generation provider produces schema-constrained insights; Pydantic validates them. Tasks/decisions need a real cited segment and exact source quote; assignees resolve only through workspace/participant checks. Neither schema validation nor changing models guarantees factual recall.
6. Retries can restart failed or stale jobs. Existing matching transcript rows are reused. Reanalysis reconciles generated records while preserving verified/completed tasks and live decisions; it must not erase human work. Processing logs carry meeting/workspace identifiers.

## Knowledge and authorization

KnowledgeRetriever combines pgvector and keyword matching across meeting transcripts, document chunks, tasks, decisions and selective Pilot memory. Queries filter source records by workspace, with an optional current-meeting scope. Grounded answers use source IDs from the retrieved set and return insufficient evidence when none is found. Source citations carry timestamps or document details. Old embeddings from another model are excluded from current vector retrieval.

Pilot reads recent stored transcript turns and bounded timeline evidence for meeting questions/recaps, and uses the shared retriever for workspace memory. Explicit decisions/tasks and source-linked facts, commitments and deadlines are stored separately from original speech. Passive assignments require a linked participant; explicit manager commands validate the assignee. Display names and speaker labels do not prove authenticated identity.

The authenticated Pilot voice WebSocket supports microphone audio or the meeting bot audio bridge. StreamingSpeechBuffer feeds local faster-whisper, then intent routing and evidence-grounded generation; Piper/native fallback WAVs return to browser playback or the bot's virtual microphone. Playback acknowledgments, turn cancellation/barge-in and cached wake responses are implemented. English wake calls can precede Bengali/Hindi questions. Real-call responsiveness/accuracy still require representative audio evaluation. Timing logs avoid raw speech; capture failures remain distinct from analysis failures and natural meeting endings.

API routes check Clerk identity and fresh workspace membership for meetings, documents, chat and search. Managers control membership and knowledge documents; teammates can use shared knowledge and see every workspace-visible meeting. Task visibility is manager-or-assignee. Joining by workspace code creates a pending request until manager approval. Audio is authorized before serving a file; display-name matching never grants membership. Demo data remains isolated.

StorageProvider currently implements only LocalStorageProvider. A private cloud adapter must cover upload, authorized range playback, worker downloads, derived files and deletion; adding an R2 URL does not implement shared storage.

## Configuration and schema

Non-secret defaults live in backend/app/core/app_config.py; working-directory .env is loaded without overriding injected environment values. Secrets/connections live in core/config.py. AI_PROVIDER and EMBEDDING_PROVIDER select independent adapters. OPENAI_CHAT_MODEL is explicit; OPENAI_API_KEY is masked and server-only. The cloud adapter requests Structured Outputs and rejects incomplete/refused responses while retaining existing evidence checks. Cloud HTTP errors omit response bodies/keys. No automatic paid fallback exists.

PostgreSQL uses vector(768). OpenAI indexes use provider/model/dimension provenance, while historic Ollama labels remain compatible. Reindex original transcripts/documents when switching embeddings; changing chat alone needs no reindex. Migrations now also cover voice settings, capture errors, language and workspace approval. Fresh databases currently bootstrap pgvector/tables before Alembic; production needs a single reviewed migration job.

## Hosted target (not deployed by these changes)

The HTTPS frontend connects to hosted API/WebSocket replicas. Private PostgreSQL,
durable queues, shared object storage and isolated bot hosts provide persistent
workspace data. Speech workers process audio on our servers; OpenAI supplies text
intelligence through the provider boundary. Customers do not run this stack.

Before splitting hosts, implement object storage, session ownership/leases,
capacity reservations, usage/cost caps, scoped audit/retention and secrets handling.
Drain active meetings during releases. Current development Compose contains local
ports, mounts and Ollama dependencies and is not a production deployment manifest.

## Boundaries and unresolved work

The default upload path cannot distinguish speakers; live engine labels are not
verified identities. Cloud provider contracts are implemented, but no funded GPT
accuracy/latency test or hosted deployment is implied. Reliable long/noisy
multilingual recordings, integration callbacks, tenant load/recovery and real
production migrations remain release gates. Billing, quotas and private cloud
storage are planned SaaS work, not permanently excluded requirements.
