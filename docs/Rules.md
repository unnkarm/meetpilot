# Governance & Coding Rules — MeetPilot AI

## 1. Core Principles
1. **Zero Guesswork**: Never invent fake API keys, unverified library methods, or inconsistent database column names.
2. **Build Verification Mandate**: After every single code modification, verify that both the backend (`python -m py_compile backend/app/main.py`) and the frontend (`npm run lint` and `npm run build` in `frontend/`) compile with zero errors.
3. **Preserve Comments & Docstrings**: Maintain existing comments, documentation strings, and file headers unless explicitly requested otherwise.
4. **Tenant Isolation**: Every database query touching meetings, transcripts, tasks, and search MUST filter by `workspace_id` to guarantee multi-tenant security.

---

## 2. Frontend Engineering Rules

### 2.1 Technology Constraints
- **Framework**: React 19 + TypeScript.
- **Styling**: Tailwind CSS with custom utilities and CSS variables in `frontend/src/index.css`.
- **Icons**: Use `lucide-react` exclusively for icons.
- **Authentication**: Use `@clerk/clerk-react` components (`<ClerkProvider>`, `<SignIn>`, `<SignUp>`, `<UserButton>`, `<SignedIn>`, `<SignedOut>`, `useUser()`, `useAuth()`, `useClerk()`).

### 2.2 UI & Design Standards
- **Dark Mode Aesthetic**: Deep obsidian background (`#09090B`), subtle panel containers (`#111113`, `#121217`), sharp borders (`#27272A`, `#2D2D3B`), and electric purple primary accents (`#8B5CF6`).
- **No Layout Jitter**: All interactive elements, dropdowns, and modals must have fixed bounding boxes, proper z-indexing, and overflow control to prevent clipping.
- **Clerk Theme Integrity**: Custom Clerk CSS overrides in `index.css` must maintain full social button contrast, non-conflicting grid alignment, and clean badge placement.

---

## 3. Backend Engineering Rules

### 3.1 Framework & API Standards
- **Framework**: FastAPI with Python 3.11+.
- **Validation**: Pydantic v2 schemas for all request payloads and response models.
- **ORM**: SQLAlchemy 2.0 mapped columns (`Mapped[...] = mapped_column(...)`).
- **CORS Handling**: Always maintain explicit localhost/dev origins and global exception handlers so 500 errors include CORS headers and never get blocked by browser CORS policy.

### 3.2 Database & Migrations
- **Primary Keys**: Use UUIDv4 (`UUID(as_uuid=True)`) for all database primary keys.
- **Vectors**: Store embeddings with `Vector(768)` for pgvector cosine distance search.
- **Indexes**: Explicit indexes on foreign keys (`workspace_id`, `meeting_id`, `user_id`, `clerk_id`).

### 3.3 Background Tasks & Error Handling
- **Celery Pipeline**: Never execute heavy audio processing or LLM calls inside FastAPI request-response cycles. Offload all transcription and summarization to Celery workers.
- **Graceful Failures**: If background processing fails, set `status = "failed"`, record the error message in the meeting record, and log full stack traces.

---

## 4. AI & Agent Collaboration Guidelines
- **Clickable Links**: All file paths and symbol references in agent responses must use valid GitHub markdown links (e.g. `[main.py](file:///path/to/main.py)`).
- **Proactive Verification**: When modifying any code, proactively run validation commands in the terminal without asking unnecessary permissions.
- **State Updates**: Keep `Memory.md` updated with completed changes and current state so future sessions maintain perfect context continuity.
