# Project Requirements Document (PRD) — MeetPilot AI

## 1. Executive Summary
**MeetPilot AI** is an enterprise-grade, AI-powered meeting intelligence and knowledge extraction platform. It bridges the gap between spoken discussions and team execution by ingesting audio/video meeting recordings, providing diarized transcripts, generating executive summaries, extracting action items with assignee intelligence, and powering timestamped conversational Q&A over meeting archives.

---

## 2. Target Audience & Personas
- **Engineering Managers & Tech Leads**: Need clear accountability, automated task extraction from sprint planning, and architectural decisions tracked without manual note-taking.
- **Product Managers**: Require instant meeting synthesis, user interview takeaway extraction, and searchable feature requirement discussions.
- **Executive Leadership & Founders**: Rely on high-level executive summaries, strategic milestone tracking, and cross-team meeting visibility.
- **Remote / Distributed Teams**: Benefit from asynchronous meeting review, semantic cross-meeting search, and time-shifted collaboration.

---

## 3. Value Proposition & Key Differentiators
1. **Zero-Friction Ingestion**: Drag-and-drop audio recording uploads supporting MP3, WAV, M4A, and MP4 formats with real-time background processing via Celery & Redis.
2. **Speaker Diarization & Deep Transcript Analysis**: High-fidelity speech-to-text powered by Google Gemini with speaker segmentation and millisecond timestamp precision.
3. **Actionable Task & Decision Extraction**: Automatically identifies assignees, due dates, task priorities (High, Medium, Low), and consensus decisions directly from spoken dialogue.
4. **Interactive Meeting RAG Chat**: Conversational AI query engine that retrieves semantically relevant transcript chunks using pgvector cosine similarity and cites exact audio timestamps.
5. **Multi-Workspace & Role-Based Access**: Seamless organization management with Owner, Admin, Member, and Viewer permissions secured by Clerk authentication and JWT session verification.

---

## 4. Feature Requirements & Capabilities

### 4.1 Authentication & Workspace Management
- **Universal Auth**: Clerk-based single sign-on supporting Google, GitHub, Slack, and email magic links/passwords.
- **Just-In-Time Provisioning**: Automatic database user provisioning and token validation against Clerk JWKS.
- **Workspace Multitenancy**: Multi-workspace creation, switching, member invitations, and role management.

### 4.2 Meeting Ingestion & Audio Pipeline
- **Upload Flow**: Asynchronous file ingestion with background storage, metadata extraction, and immediate status queuing.
- **Background Worker**: Celery task pipeline managing `queued` → `transcribing` → `summarizing` → `completed` (or `failed`) states.
- **Resilient Fallback**: Automatic retry mechanisms, error logging, and user notifications on job failure.

### 4.3 AI Extraction & Analytics
- **Transcript Engine**: Speaker-labeled segments with accurate start/end timestamps and text search highlights.
- **Executive Summary**: 3-tiered summary structure containing Overview, Key Takeaways, and Next Steps.
- **Action Items (Kanban/Table)**: Extracted tasks with title, assignee, priority, status (`todo`, `in_progress`, `done`), and transcript citation.
- **Decisions Log**: Dedicated register for team decisions, consensus points, and architectural choices.

### 4.4 Semantic Search & Meeting Q&A (RAG)
- **Vector Search**: High-dimensional embeddings (`text-embedding-004`) stored in PostgreSQL using the `pgvector` extension.
- **Hybrid Query Engine**: Search across meetings, transcript segments, tasks, and decision outcomes with sub-second latency.
- **Citing Meeting Chat**: AI chat responses grounded in retrieved meeting context with clickable timestamp links that jump directly to the relevant audio segment.

---

## 5. Non-Functional Requirements
- **Security & Privacy**: Zero audio data leakage across workspace boundaries; tenant isolation strictly enforced at the database query level.
- **Performance**: Sub-100ms API response time for workspace queries; background processing completes within 1.5x of audio playback length.
- **Scalability**: Stateless FastAPI application tier with horizontal worker scaling via Celery and Redis.
- **Reliability**: 99.9% uptime target with graceful error handling and unhandled exception CORS compliance.
