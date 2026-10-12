# MeetPilot AI product requirements

## Purpose

Build a hosted web SaaS that turns live/recorded meetings into inspectable, editable, searchable organizational memory and an active voice co-pilot. Customers use the web dashboard without installing models or bot software. Local Ollama/Whisper/Piper services exist to reduce current development costs; production text intelligence will use OpenAI GPT APIs. Free hosting tiers are an early budget strategy, subject to actual workload limits.

The supported first-use flow is Clerk sign-in, workspace creation or manager-approved joining by unique code, recording upload/live bot dispatch, source-linked review, Ask MeetPilot and assigned follow-up work. All requested features and acceptance gates live in [Feature_Roadmap.md](Feature_Roadmap.md); hosting/scaling/marketing are in [SaaS_Deployment_Scaling_GoToMarket.md](SaaS_Deployment_Scaling_GoToMarket.md).

## Implemented behavior

- Workspaces, membership checks and an isolated sample workspace reachable through Explore Demo.
- Audio upload with validation and local storage; Celery processing with visible states, failure reason and retry.
- Local faster-whisper transcript segments with real timestamps. Default single speaker label does not represent actual diarization.
- Provider-selected schema-validated summary, executive sections, tasks and decisions; Ollama development default and an implemented OpenAI Responses adapter. Generated tasks/decisions carry transcript evidence and model/prompt metadata; users can correct interpretations.
- Provider-selected embeddings in PostgreSQL pgvector, document ingestion, workspace search, meeting chat and cross-source Ask MeetPilot with citations. OpenAI embeddings preserve vector(768) through explicit dimensions and separate index provenance.
- In-app processing notifications and first-party product events for selected activation actions.
- Official Vexa Lite live bot integration, custom audio bridge and Pilot voice panel: English wake acknowledgment, microphone/bot audio, multilingual questions, playback cancellation and voice selection. Source implementation does not establish production conversation quality.
- Manager-controlled documents/membership/settings, approved join requests, shared workspace-visible meetings and assignee-scoped teammate task access. Meeting speaker labels are not authentication.

## Acceptance and quality bar

A first meeting should complete without blocking the upload request; its transcript should remain persisted if later stages fail. Each visible failure should be diagnosable and retryable. Answers must cite authorized workspace records and state insufficient evidence when retrieval finds none. Users must be able to edit AI interpretations without changing source transcript evidence. Backend compile, frontend lint/build and automated tests must pass.

## Not yet complete

Hosted staging and production operations; private object storage; durable quota/cost enforcement; billing/subscriptions; retention/audit and confidential-meeting ACLs; reliable diarization; representative long multilingual audio/voice evaluation; all advanced templates, connectors, media, organizational brain and analytics features marked planned/partial in Feature_Roadmap.md. Clerk remains an external auth dependency. OpenAI adapters are implemented but intentionally inactive without server model/key configuration; live paid-provider quality and cost are not yet verified.
