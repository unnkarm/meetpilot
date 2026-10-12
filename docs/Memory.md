# Engineering memory

## Product direction — authoritative, 8 October 2026

- **MeetPilot is a hosted web SaaS. Nothing in the final customer experience requires a local installation.** The founder uses local services now because the development budget is limited, not because permanent offline execution is the product goal.
- Use suitable hosting free tiers during the initial stage; persistent browsers, databases, speech and inference still need measured compute and a realistic cost budget.
- Replace Ollama text intelligence with OpenAI GPT APIs for production. Keep the shared provider interfaces, workspace authorization and evidence validation. Do not hard-code a particular GPT model without evaluation/account availability.
- Current Ollama/Qwen, nomic, filesystem, Whisper and Piper defaults are the affordable development configuration. Hosted Whisper/Piper workers are also server-side processing; customers only use the dashboard.
- All requested features are tracked in **docs/Feature_Roadmap.md**. That document is the implementation backlog, not a claim that every feature is shipped. Read it before adding features or changing product scope.
- **docs/Cloud_AI.md** documents the implemented OpenAI text/embedding adapters and controlled migration. **docs/SaaS_Deployment_Scaling_GoToMarket.md** covers hosting, scaling, costs and launch.
- The working official Vexa Lite engine was restored at the founder's request. Preserve it as an internal hosted bot engine. The earlier request to permanently remove Vexa no longer describes the active integration.
- Do not start the full local Docker/model stack during source verification: the developer's PC overheats. Use compilation and isolated tests, and let the developer schedule live verification.

## Facts verified in repository

- Review tools now have workspace templates, personal queued artifacts and shared bookmarks, with a new migration f6a7b8c9d0e1. Five personas, cited email/chat digest drafts, audio chapters, task/blocker review, approximate speaking metrics, a personal cost estimate and opt-in transcript-gap/pacing playback are implemented. See docs/Review_Tools.md. Original base summaries are preserved; external messages are not sent. Model/provider and live UI quality still need deliberate verification.
- Review jobs use the processing queue, current membership checks, transcript fingerprints, per-user pending caps, UUID idempotency and worker run tokens. Drafts remain private to their creator; bookmarks follow current shared-meeting access and creator/manager deletion rules. Keep this separation when implementing further features.
- Review expansion verification (8 October 2026): 232 backend tests ran, 229 passed and three opt-in integrations skipped; 12 frontend tests, compilation, TypeScript lint, production build and diff checks passed. Migration upgrade/downgrade used isolated SQLite adapters. Actual PostgreSQL migration, model output quality and browser/live-call verification remain pending. No full stack or paid requests were started.

- Monolith: React 19/Vite/TypeScript/Tailwind/SWR/Clerk, FastAPI/Pydantic/SQLAlchemy, PostgreSQL pgvector, Redis/Celery, Docker Compose.
- backend/app/core/app_config.py is the central non-secret AI/processing configuration. backend/app/core/config.py retains secrets, connections and legacy integration settings.
- Default LLM is Ollama qwen3:4b-instruct; embeddings are Ollama nomic-embed-text-v2-moe, 768 dimensions; transcription is local multilingual faster-whisper base CPU int8; storage is local filesystem.
- OpenAI Responses and embedding adapters are selectable independently by server environment. They are not enabled by default. Keys are masked server settings, never frontend configuration. Selection does not trigger a startup request or automatic paid fallback.
- Default local transcript turns all use Speaker 1 pending real diarization. Never claim distinct voices are recognized on that path.
- Meeting worker persists transcript before embeddings/analysis. Tasks and decisions cite stored speech segments; summary has model/prompt metadata. The worker skips missing or weak cited evidence and unrecognized assignees.
- The existing 768-dimensional database schema is preserved. Cloud embeddings have a provider/model/dimension namespace; Ollama's historical labels remain compatible. Embedding model/provider switches require reindexing original text; dimension switches require a migration. Equal dimensions do not mean compatible vectors.
- Demo data is created in an isolated sample workspace. It is sample text and does not include audio.
- Fresh DBs need bootstrap plus Alembic; historical Alembic revisions lacked a full baseline. New revisions add processing/evidence and product events.
- Historical smoke checks: 32 backend tests passed in Docker; Qwen/nomic inference, short generated speech, document indexing, cited answers and synthetic long-audio chunking passed. These are historical evidence, not verification of the new cloud adapters or SaaS deployment.
- Recent multilingual/voice/access regression work passed 190 host backend tests with three opt-in integration skips, plus frontend checks. Representative long/noisy multilingual audio quality, staged cloud API accuracy/cost and production load remain unverified.
- SaaS provider foundation verification (8 October 2026): 210 tests ran, 207 passed and three opt-in integrations skipped; backend compilation and frontend lint/build passed. OpenAI requests were mocked. No paid requests, Docker startup or model downloads occurred; the existing frontend large-bundle warning remains.

## Operating commands

Follow README.md for scheduled local startup, model provisioning and Clerk configuration. Keep AI_PROVIDER=ollama and EMBEDDING_PROVIDER=ollama until a funded API migration is scheduled. Run python -m compileall -q backend/app backend/alembic and isolated backend contract/regression tests without starting services; run frontend npm run lint/build for frontend changes. See docs/Multilingual.md for language behavior and docs/Cloud_AI.md for provider configuration/reindexing.

## Guardrails

Preserve workspace filters, source evidence, verified identity boundaries and retry idempotency. All teammates may read workspace-visible meetings; members see their assigned tasks, and managers control documents/membership/integrations. Future sensitivity rules must also protect RAG, voice, media, sharing and external delivery. Never claim a heuristic or model inference as verified fact. Keep secrets outside source. Billing, cloud inference, private object storage and usage quotas are planned SaaS requirements; implement them through service interfaces and verified migration gates, without activating paid services automatically. Keep PostgreSQL/pgvector unless measurements justify another database.
