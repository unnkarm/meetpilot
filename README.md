# MeetPilot AI

MeetPilot turns meetings into searchable workspace knowledge and an active voice co-pilot. **The product target is hosted web SaaS:** customers use a browser without installing models or bot software. Local Ollama, faster-whisper, Piper and filesystem services are the affordable development setup. Production text intelligence will use OpenAI GPT APIs through the shared provider interface.

See the [complete feature roadmap](docs/Feature_Roadmap.md), [cloud AI migration](docs/Cloud_AI.md), and [SaaS deployment/scaling/marketing plan](docs/SaaS_Deployment_Scaling_GoToMarket.md). Planned features and production requirements are labeled separately from the implemented beta.

## Current product flow

Sign in with Clerk, create a workspace, upload a recording, and watch it move through queued, transcribing, embedding, analyzing and completed states. A completed meeting has timestamped transcript turns, a summary, tasks and decisions. Users can edit the interpretations, ask questions with source citations, search workspace knowledge, add documents, and manage tasks. Failed or stale jobs show a retry action. A clearly marked sample workspace is available through **Explore Demo**. Live meetings use the self-hosted Vexa engine; imported recordings use the local upload pipeline.

The default local transcriber labels speech as **Speaker 1** because it does not identify distinct voices. Its timestamps are real Whisper segment times. The optional Hugging Face path can provide diarization if separately configured. Do not treat a speaker label as verified identity. Review all AI output before using it.

## Local setup (PowerShell)

Install Docker Desktop and create a Clerk application with JWT/JWKS access. Clerk is currently required for sign-in; local AI does not remove that auth dependency.

~~~powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
~~~

Fill in the real Clerk values in both files: backend CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY and CLERK_JWKS_URL; frontend VITE_CLERK_PUBLISHABLE_KEY. CLERK_ISSUER_URL can be set explicitly or derived from a Frontend API JWKS URL ending in `/.well-known/jwks.json`. Keep those files private. If the files already exist, edit them instead of replacing working credentials.

~~~powershell
python backend/scripts/setup_vexa.py
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3:4b-instruct
docker compose exec ollama ollama pull nomic-embed-text-v2-moe
docker compose up --build -d
docker compose ps
~~~

Open http://localhost:3000. API health: http://localhost:8000/health. First startup also initializes pgvector and applies Alembic migrations. The backend image bundles the default faster-whisper base model and Piper voice during build. Pull the Ollama models once while online; Docker volumes retain them for later offline inference. Compose connects the backend to its Ollama service by default. For a host-installed Ollama, set OLLAMA_URL to http://host.docker.internal:11434 before Compose startup.

## Meeting review tools

Completed meetings now include a **Review tools** tab: five summary personas and
manager-managed workspace templates, cited email/Slack/Teams drafts, audio chapters,
bookmarks, task/blocker review, approximate speaking metrics and a personal cost
calculator. Live meetings also have bookmark buttons/shortcuts. The audio player
offers opt-in transcript-gap skipping and adaptive pacing. Generation uses the
existing processing worker and selected AI provider; no external message is sent.

Apply migration `f6a7b8c9d0e1` and restart the API/processing worker/frontend when
ready. See [Review tools](docs/Review_Tools.md) for usage, privacy, limits and setup.

## Configuration

Change non-secret defaults in [backend/app/core/app_config.py](backend/app/core/app_config.py). This controls LLM and embedding providers/models, temperature, token/context limits, transcription model and chunking, retrieval top K and distance threshold, upload limits, local storage path, worker concurrency and polling defaults. Endpoint URL may be overridden by OLLAMA_URL. Credentials, DB/Redis addresses and Clerk details belong in backend/.env. The selected embedding model must output **768 dimensions**, matching the existing pgvector columns. Changing dimensions requires a schema migration and reindex. Existing vectors from another model are excluded from current model retrieval; reprocess or reindex them.

Default providers and models:

| Capability | Current default | Notes |
| --- | --- | --- |
| LLM | Ollama qwen3:4b-instruct | JSON schema output plus Pydantic validation and retry |
| Embeddings | Ollama nomic-embed-text-v2-moe | Multilingual, 768 dimensions |
| Transcription | Local faster-whisper base, CPU int8 | Real ASR, no invented fallback text |
| Speaker labeling | Single unknown speaker | Multi-speaker diarization is not local by default |
| Storage | Local filesystem | Docker audio volume; local:// references |
| Retrieval | PostgreSQL pgvector plus keyword matching | Workspace filters on sources |

Generation and embeddings each support `ollama` and `openai`. Development defaults remain Ollama. Set server-side `AI_PROVIDER=openai`, `OPENAI_API_KEY` and an explicit account-available `OPENAI_CHAT_MODEL` when ready to use the Responses API. Embeddings can migrate separately through `EMBEDDING_PROVIDER=openai`; their provider/model namespace requires reindexing. No cloud request or automatic paid fallback is triggered at startup. See [Cloud AI](docs/Cloud_AI.md) for migration, costs and unfinished production controls. Optional legacy Gemini transcription remains outside the default path.

After changing an existing installation from the old embedding model, run
`docker compose exec -T backend python -m app.database.reindex_embeddings`
to re-embed stored original-language transcript and document text. See [multilingual processing](docs/Multilingual.md) for language behavior, migration, and verified limits.

## Pilot Phase 1 backend

Pilot now builds a bounded, meeting-scoped context from the latest stored live transcript turns, recent tasks/decisions, and selectively saved memory. Its authenticated endpoints are `GET /api/v1/meetings/{meeting_id}/pilot/context`, `POST /api/v1/meetings/{meeting_id}/pilot/ask` with `{"question":"What did we just agree on?"}`, and `POST /api/v1/meetings/{meeting_id}/pilot/action` with `{"command":"Hey Pilot, create a task for John to update the API docs"}`. The question endpoint uses the configured AI provider and workspace retriever plus recent unembedded turns; answers require valid source citations. The action endpoint accepts only a direct command from an authenticated manager and requires a unique workspace-member assignee.

The live meeting flow uses the official self-hosted Vexa Lite engine in `vexa`, with a dedicated `meeting_bot` Celery bridge queue. Vexa owns Chromium admission, remote audio capture, and speaker detection; local faster-whisper performs STT, and MeetPilot retains Ollama/Qwen, pgvector RAG and Piper TTS. Each workspace receives a separate Vexa service identity/key. Only confirmed transcript turns become evidence. Speaker labels do not establish a verified workspace identity. See [Vexa operations](backend/PilotVoice.md) for startup, host admission and diagnostics.


Tune `PILOT_ENABLED`, `PILOT_CONTEXT_WINDOW`, `PILOT_MEMORY_ENABLED`, `PILOT_MEMORY_CONFIDENCE_THRESHOLD`, `PILOT_IDENTITY_CONFIDENCE_THRESHOLD`, and `PILOT_OBSERVABILITY_ENABLED` in private `backend/.env`; examples are in `backend/.env.example`. The live passive classifier currently recognizes a narrow set of explicit English phrases. Multilingual transcript preservation, retrieval, and question-language answers use the existing multilingual stack; passive extraction in other languages requires representative recordings and additional validated rules or a bounded model strategy.

For a local manual check after starting a native live meeting, set `MEETPILOT_TOKEN` in the shell to a valid Clerk bearer token and run:

```powershell
python backend/scripts/pilot_smoke.py --meeting-id <meeting-uuid> --question "What did we just agree on?"
```

The script prints context counts, a cited text answer, and no token. Add `--skip-question` to check only the context. `--action "Hey Pilot, create a task for John to update the API docs"` **creates a real task** and requires John to be a unique workspace member. A nonmember should receive HTTP 403. Use `docker compose logs -f backend meeting_bot` for local processing logs. Guest admission, meeting-site DOM changes, and speaker hints require a real call test on each platform; a browser smoke test alone does not prove those paths.

After building the image and pulling the Ollama models, this check exercises local WebRTC capture, a final Whisper turn, Ollama embeddings and chat, Piper WAV output, and virtual microphone playback without a meeting URL:

~~~powershell
docker compose cp backend/scripts/offline_pipeline_smoke.py meeting_bot:/tmp/offline_pipeline_smoke.py
docker compose exec -T meeting_bot sh -c 'PYTHONPATH=/app python /tmp/offline_pipeline_smoke.py'
docker compose cp backend/scripts/offline_intent_smoke.py backend:/tmp/offline_intent_smoke.py
docker compose exec -T backend sh -c 'PYTHONPATH=/app python /tmp/offline_intent_smoke.py'
~~~

The second script creates temporary synthetic meeting evidence, checks cited live and historical answers, verifies task assignment and outsider denial, then rolls back the database transaction.

## Verification

~~~powershell
python -m compileall -q backend/app backend/alembic
cd frontend
npm ci
npm run lint
npm run build
cd ..
docker compose run --rm --no-deps -e MEETPILOT_RUN_PILOT_INTEGRATION=1 -v ./backend/tests:/app/tests backend python -m unittest discover -s tests -q
~~~

The Docker test command assumes backend/.env and backend/.env.vexa exist and the backend image has been built. The backend suite and frontend lint/build pass; the multilingual PostgreSQL/Ollama integration test is opt-in. Fresh and existing-schema disposable PostgreSQL migrations passed. Local Qwen and nomic inference, a complete worker pass on short offline-generated speech, document indexing, cited cross-source answers, and server-side outsider denial were exercised. FFmpeg chunking was checked on 15, 30 and 60 minute synthetic silence. A real user recording uploaded through the browser, long-recording ASR quality/performance, multi-speaker diarization, and optional integrations have **not** been verified end to end.

## Troubleshooting

- **Meeting stays queued:** check docker compose logs celery_worker and backend; a failed queue dispatch appears as failed and can be retried.
- **Ollama connection/model error:** check docker compose ps, docker compose exec ollama ollama list, and that the shell OLLAMA_URL matches your topology. Failure remains visible on the meeting.
- **Whisper model missing:** the image build downloads and bundles the default `base` model. Rebuild while online if it is absent; runtime transcription uses local files only. A different `WHISPER_MODEL` must also be provisioned locally.
- **No useful result or unsupported task:** local models can omit or invent interpretations, especially in less represented languages. Evidence checks discard unsupported cited tasks/decisions; use another installed Ollama model through `OLLAMA_CHAT_MODEL` after testing.
- **Existing local database:** preserve Docker volumes and back up data before replacing local environments. Fresh startup bootstraps missing tables then applies migrations.

## Scope and limitations

There is no billing or cloud storage requirement for inference. The beta still depends on Clerk for authentication, and joining Google Meet, Teams, or Zoom requires a network connection to that service. The offline smoke test checks local components, not external meeting admission. Local multi-speaker diarization, robust speech quality across accents/noisy recordings, selected document/meeting RAG scopes, full long-audio testing, and production hardening remain. The demo contains text records, not a playable recording. The single default LLM is small, so manual review matters.

See [Architecture](docs/Architecture.md), [PRD](docs/PRD.md), [Phases](docs/Phases.md), and [Memory](docs/Memory.md). Some older per-feature documents describe historical Gemini/hosted designs; these four documents and this README describe the current local beta.
