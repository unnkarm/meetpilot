# MeetPilot product and engineering roadmap

**Direction confirmed by the founder: 8 October 2026.**

MeetPilot is being built as a **hosted, multi-tenant web SaaS**. Customers use a
browser; they do not install Docker, Ollama, Whisper, or bot software. Local
services exist only to make development affordable. Production text intelligence
will replace Ollama with OpenAI GPT APIs. Hosting free tiers are an initial cost
strategy, not a promise of unlimited free compute or inference.

This document includes **every feature in the supplied feature breakdown**.
“Planned” means not shipped. “Partial” means an existing building block needs
additional implementation and verification. Provider contract tests do not prove
deployment or live-call performance. This roadmap supersedes earlier permanent
offline/local-only restrictions in the project notes.

## 1. Deployment and provider strategy

| Component | Affordable development now | Hosted product target | Release dependency |
| --- | --- | --- | --- |
| Dashboard | React/Vite on localhost | Hosted HTTPS dashboard and landing page | Production auth, SPA routing, secure microphone/WebSockets |
| API | FastAPI in development Compose | Containerized API on persistent compute | Private connections, CORS, rate limits, migrations and monitoring |
| Meeting engine | Official Vexa Lite with MeetPilot overlay | Isolated browser workers operated by MeetPilot | Admission, audio capture, per-call capacity reservation and recovery |
| Chat/analysis | Ollama Qwen | OpenAI GPT through the shared AIProvider interface | Server key, explicit model, usage limits, evidence regression tests |
| Retrieval embeddings | Ollama nomic, vector(768) | OpenAI embeddings or another measured hosted provider | Provider/model namespace, full reindex, multilingual retrieval evaluation |
| STT/TTS | faster-whisper and Piper/espeak on developer hardware | Hosted speech workers; evaluate speech APIs for latency and cost later | No model loading on customer devices; measured end-to-end voice quality |
| Files | Development filesystem volume | Private object storage | Authorized uploads/playback, shared-worker downloads, deletion and retention |
| Data/queues | Local PostgreSQL/Redis | Managed/private PostgreSQL with pgvector and durable queues | TLS, pooling, backup restore, leases and idempotent jobs |

Vexa is the current browser engine following the founder's request to restore
the working upstream implementation. It is an internal hosted engine, not a
customer installation requirement. Do not remove it again as a side effect of
the SaaS transition. The abandoned native joiner is not the active integration.

The text and embedding OpenAI adapters are implemented behind existing service
interfaces. They remain inactive with the current Ollama defaults. See
[Cloud AI configuration and migration](Cloud_AI.md). Object storage, production
quotas and billing are **not** implemented by those adapters.

## 2. Shared requirements for all features

**Policy foundation, 12 October 2026 — source-implemented, development draft:**
Public Terms, Privacy and Recording pages plus a one-time first-action account
acknowledgment are implemented. No signup/entry or repeat prompts; Settings shows
the receipt and current policies. Live/uploads check the saved receipt, with
no per-recording checkbox. Operator identification,
reviewed production terms, a DPA, actual provider/retention disclosures and
deletion/security operations remain launch dependencies. No participant-consent
verification or compliance certification is claimed. See `Legal_Policies.md`.

- Enforce current workspace membership and role/sensitivity permissions before
  retrieval, generation, playback, export or external delivery. Filter before
  ranking, limits and model prompts.
- Keep original transcript evidence. Generated facts, tasks, decisions and
  chapters cite stored segment IDs, speaker labels and real timestamps. Weak
  or absent evidence produces an uncertainty response.
- Treat transcripts, documents, custom templates and integration data as
  untrusted input. Model output cannot grant permissions or execute arbitrary
  tools. Validate all tool arguments and check permission again at execution.
- Managers control knowledge documents, workspace configuration, membership and
  integrations. Teammates may read all **workspace-visible** meetings and use
  shared knowledge; task access is limited to their assigned work. Existing
  visibility remains the default. Future confidential meetings narrow it.
- Separate meeting speaker labels from authenticated identity. A display name,
  guessed voice match or wake phrase does not authenticate a workspace member.
- Make generated suggestions reviewable. External sends and writes use explicit
  user action or a manager-configured automation policy, with an audit record.
- Use durable jobs, bounded queues, idempotency keys, revisions, cancellation and
  usage accounting. Never silently replace human corrections or completed work.
- Meter model tokens, speech/meeting minutes, storage, connector calls and retries
  per workspace. Cap both cost and concurrent browser sessions before public signup.
- Support English, Bengali, Hindi and code-switched speech, preserving original
  evidence. Evaluate quality rather than promising perfect recall or human latency.

## 3. Advanced AI and post-meeting intelligence

| ID | Feature and complete scope | Current status | Delivery and acceptance gate |
| --- | --- | --- | --- |
| AI-01 | Summary personas: engineering standup, sales MEDDIC/BANT, executive one-minute briefing, 1-on-1 feedback and customer interview; workspace custom templates | Implemented in source; model quality/live UI verification pending | Five personas, manager template CRUD, snapshot instructions and source-linked private drafts. No invented qualification fields; generation needs a running configured worker/provider. See Review_Tools.md. |
| AI-02 | Client/internal follow-up emails and Slack/Teams digest drafts | Implemented draft generation; connector sending remains planned | Audience/format/language selection, cited paragraphs, editable non-persisted copy; no automatic external delivery. Drafts run on the processing queue. |
| AI-03 | Sentiment trajectory, friction, escalation and alignment cues | Planned | Transcript-based contextual cues with timestamped quotes and confidence; user correction; no claim to diagnose emotion or personality; multilingual reviewed evaluation |
| AI-04 | Topic clusters and audio/video timeline chapters with headings and key points | Implemented for audio in source; video and quality evaluation pending | Persisted topic chapters cover every input turn; source-linked key points and server-derived times; click to seek existing recording. Bounded UTF-8 windows fail explicitly on overflow. |
| AI-05 | Speaker embeddings and optional learned member voice profiles | Planned; default upload path has one unknown speaker | Hosted diarization worker behind an interface; evaluate Pyannote/Silero-compatible components and licenses; enrollment consent, revoke/delete, confidence and manual verification; never use voice matching as login or authorization |
| AI-06 | Risk/blocker radar: unresolved disagreement, missing owner/deadline and mentioned risks | Partial: role-filtered task gaps and cited blocker review now implemented | Review tools show missing verified owner/deadline and grounded summary blockers. Unresolved disagreement analysis and resolve/dismiss workflow remain planned. |

## 4. Live meeting co-pilot

| ID | Feature and complete scope | Current status | Delivery and acceptance gate |
| --- | --- | --- | --- |
| LIVE-01 | In-call HUD with pricing/roadmap fact support and relevant document popups | Planned; shared RAG and live panels exist | Authenticated event stream; source snippets, document versions and links; confidence/debounce to avoid noisy alerts; clarify that a retrieved document is evidence, not universal fact checking |
| LIVE-02 | Decision/follow-up/highlight bookmarks with buttons and keyboard shortcuts | Implemented in source; live UI verification pending | Shared persisted bookmarks, timestamp bounds/segment anchors, UUID idempotency, creator/manager deletion and Alt+Shift+D/F/H. Live marker uses latest captured speech; past marker uses player position. |
| LIVE-03 | Live translation and multilingual subtitles | Partial: multilingual original transcripts and language/display options | Original speech plus selectable translated captions; per-turn source linkage and language labels; ordered updates and bounded latency; translated text cannot replace original decision evidence |
| LIVE-04 | Smart mute and RNNoise/DeepFilterNet noise preprocessing | Planned | Hosted streaming preprocessor with fixed PCM contract; preserve original recording; avoid suppressing soft speech and code-switching; benchmark latency and noise samples; avoid muting real participants automatically |
| LIVE-05 | Whisper hallucination filters and PII/secret scrubbing before indexing | Partial: silence/signal checks; no comprehensive PII pipeline | Shared redaction before embeddings, remote model context and connector sends; detect card/SSN/credential patterns; separate authorized original/redacted views; handle chunk boundaries, deletion and multilingual false positives; report remaining detection limits |

Voice quality remains a release gate across this group: prompt English wake
phrases including “Pilot”, cached “Yes sir”, follow-up turns, Bengali/Hindi replies,
audible microphone output and barge-in. Test speech recognition latency separately
from model and playback latency. A provider change alone does not prove GPT-like
conversation.

## 5. Workflow automations and ecosystem

| ID | Feature and complete scope | Current status | Delivery and acceptance gate |
| --- | --- | --- | --- |
| FLOW-01 | Bidirectional Jira, Linear, GitHub Issues, Notion and Asana task sync | Planned | Shared connector interface; workspace OAuth/install ownership; stable task/external-ID mapping; source links; signed inbound events; retries, reconciliation, conflict policy and loop prevention; deliver providers incrementally |
| FLOW-02 | Salesforce and HubSpot contact/deal call logs, next steps and stage updates | Planned | Manager configuration; explicit verified contact mapping; authorized recording links; review stage changes; field mapping and idempotent sync; minimum OAuth scopes |
| FLOW-03 | Slack/Teams digests, assignment mentions and `/pilot ask` | Planned | Map chat identities to approved members; task notifications only to authorized recipients; private meeting scope respected; command authentication and connector uninstall cleanup |
| FLOW-04 | Outlook/Office 365 calendar and auto-join rules alongside Google Calendar | Partial: Google Calendar integration exists | Microsoft OAuth and refresh lifecycle; manager rules for external guests/internal sprint reviews; recurring occurrence IDs, time zones, exclusions and cancellation; verify admission eligibility; reserve capacity before auto-join |
| FLOW-05 | Zapier/Make and custom `meeting.completed`, `task.created`, `decision.logged` webhooks | Planned | Durable transactional outbox; signed versioned payloads; endpoint ownership, SSRF protections, bounded retries and delivery logs; idempotent event IDs; publish only after database commit |

Implement connector adapters without coupling business services to individual
vendor SDKs. Each provider needs real sandbox/account verification before its
status changes to shipped. Do not fabricate synced records in demo environments.

## 6. Media and interactive review

| ID | Feature and complete scope | Current status | Delivery and acceptance gate |
| --- | --- | --- | --- |
| MEDIA-01 | Video and screen-share recording/playback with slide/code OCR | Planned; audio capture/player exist | Consent/capacity policy, synchronized media timebase, private objects and range playback; OCR with frame evidence and deduplication; screen text is untrusted data; measure storage and compute cost |
| MEDIA-02 | Inline transcript corrections and updated embeddings | Planned; summary/task/decision interpretation edits exist | Source-preserving transcript revisions; editor permissions/audit; revision-aware asynchronous reindex; invalidate affected generated artifacts; prevent stale citations; replay retains original audio |
| MEDIA-03 | Snip & Share audio/video clips, typically 30 seconds, with privacy controls | Planned | Validated source ranges; bounded FFmpeg job; default private access; revocable expiring shares; permission checked on every playback; redact/exclude restricted content and delete derived clips with source |
| MEDIA-04 | Skip silence and pacing-based playback speed | Implemented transcript-based controls; acoustic calibration pending | Opt-in padded speech-interval skip and deterministic pacing speed. Original fixed speed remains available. Transcript gaps are not acoustic silence detection; untranscribed sound may be skipped. Tail is preserved. |

## 7. Organizational memory

| ID | Feature and complete scope | Current status | Delivery and acceptance gate |
| --- | --- | --- | --- |
| BRAIN-01 | Recurring series timeline and task carryover | Planned; cross-meeting RAG exists | Calendar series IDs/manual grouping; verified occurrence links; only authorized tasks; carryover is unfinished work, not an invented renewed commitment |
| BRAIN-02 | Projects/people/clients/decisions knowledge graph | Planned | Workspace entity/edge records with source evidence and reversible merge; authenticated graph explorer; privacy filters before traversal; begin with PostgreSQL, no separate graph database required |
| BRAIN-03 | Cross-meeting contradictions and duplicate detection | Planned; same-meeting revised decisions remain distinct | Retrieve relevant historical evidence; show both quotes and dates; distinguish intentional revision from conflict; review/resolve queue; do not auto-delete decisions or merge different owners |
| BRAIN-04 | Weekly executive digest/newsletter | Planned | Manager-defined schedule/time zone; recipient-specific permissions; cite source meetings; completed milestones need task history; draft/review or explicit automatic-send policy; idempotent digest periods |

## 8. Analytics, coaching and meeting health

| ID | Feature and complete scope | Current status | Delivery and acceptance gate |
| --- | --- | --- | --- |
| DATA-01 | Talk/listen ratio, filler counts, question rate, interruptions and monologues | Partial: talk share, pacing, filler/question cues, overlaps and monologues implemented | Transcript-derived approximate metrics with identity/overlap disclaimers. Verified interruption/coaching interpretation and stronger multilingual calibration remain. |
| DATA-02 | Meeting cost/fatigue and suggestions for async updates | Partial: personal assumption-based cost estimate implemented | Hourly-rate/participant inputs stay in browser; labels estimate and currency assumptions. Team fatigue, ROI and async recommendations remain planned. |
| DATA-03 | Completion velocity/accountability views | Planned | Task completion timestamps and status history; account for reopened tasks/carryover and censored unfinished tasks; managers see workspace aggregates, members their own; do not infer employee performance from raw counts |

## 9. Governance and hosted enterprise operation

| ID | Feature and complete scope | Current status | Delivery and acceptance gate |
| --- | --- | --- | --- |
| GOV-01 | Workspace-visible, private/invitee-only and manager-only meetings | Partial: workspace RBAC and manager-approved join codes | Keep workspace-visible default; explicit invite ACLs; creator/manager rules; apply sensitivity consistently to lists, transcripts, files, RAG, voice, graph, digests, exports, shares and connectors; removed members lose access immediately |
| GOV-02 | Access audit and configurable N-day retention | Planned | Append-only scoped audit for listens/exports/admin changes; avoid logging raw PII; retention jobs delete application/engine objects, derived clips, vectors and voice profiles; retries and legal-hold design; documented backup-expiry boundary |

Enterprise private-cloud deployments may be evaluated later for customers who
request them. They are not the default product or a requirement to install on a
customer laptop. Do not claim legal/compliance certification from feature presence.

## 10. Delivery sequence and dependencies

| Release | Scope | Exit gate |
| --- | --- | --- |
| S0 — SaaS foundation | This full roadmap and durable product direction; configurable OpenAI text/embedding adapters; provider provenance and migration guide | Offline contract tests, backend compilation; no paid request required |
| S1 — Hosted private alpha | Staging deployment, private object adapter, durable queues, global/per-workspace admission, cost ledger and caps, backups; baseline audit/redaction | Full real meeting and upload paths; removed-member denial; restore on another host; no public operational ports |
| S2 — Review intelligence | First slice implemented: personas/templates, follow-up drafts, chapters, bookmarks, task/blocker review, metrics and playback. Transcript editing/reindex is still planned. | SQL/HTTP and playback contracts verified; actual provider quality, PostgreSQL migration and browser walkthrough remain gates. See Review_Tools.md. |
| S3 — Live quality and governance | LIVE-01/03/04/05, AI-05, GOV-01/02 | Real voice/admission/barge-in benchmarks; consent/enrollment/deletion; complete sensitivity tests across every retrieval and delivery path |
| S4 — Connected work and organization brain | FLOW-01–05, BRAIN-01–04, DATA-02/03 | Sandbox connector flows, signed callbacks, outbox retry/replay; permission-safe recurring history and digest tests |
| S5 — Rich media and coaching | MEDIA-01/03, AI-03; richer DATA-01 | Media storage quotas, synchronization, clip revocation, OCR privacy; sentiment/coaching evaluation and user correction |

Releases are dependency stages, not promised dates. Features can advance in
smaller slices, but acceptance gates cannot be replaced with placeholder UI or
mock model responses. Public paid signup requires quotas, abuse controls,
privacy/deletion and operational recovery; billing is planned as part of S1/public
launch preparation, not excluded permanently.

### Data and service additions

- Implemented: `summary_templates`, `meeting_artifacts` (with instruction snapshots,
  source fingerprints and run tokens) and `meeting_bookmarks`.
- Transcript revisions, generation provenance and source revision references.
- `integration_connections`, encrypted tokens, external resource mappings,
  event outbox and delivery attempts.
- Meeting series, evidence-linked entities/edges and conflict-review records.
- Meeting ACL/sensitivity, scoped audit events and retention/deletion jobs.
- Idempotent workspace usage/cost ledger, plans and capacity reservations.
- Media object/clip metadata, redaction versions and optional speaker enrollment.

Introduce these through reviewed Alembic migrations and service boundaries. Do
not add all tables without the routes, authorization, jobs and cleanup needed to
make each feature usable.

## 11. Verification policy

During development, run compilation and mocked contract/regression tests without
starting the full stack. The developer's machine overheats under the full workload.
Cloud provider tests must use fixtures unless an actual funded integration run is
scheduled. Production readiness additionally requires staging migrations, quota
enforcement, browser admission, audible two-way voice, and paid API evaluation.

Track three separate facts: **implemented in source**, **verified automatically**,
and **verified in a real hosted meeting**. Never mark the last one from a build.

See [deployment, scaling and marketing](SaaS_Deployment_Scaling_GoToMarket.md),
[current architecture](Architecture.md), [engineering memory](Memory.md),
[access audit](Workspace_Access_Audit.md) and [delivery status](Phases.md).


## Frontend delivery update — 12 October 2026

The SaaS visual redesign and frontend feature connections are implemented in source:
responsive shell, meeting library/filtering, task creation/status management, sourced
knowledge/search navigation, complete printable meeting reports, accessible dialogs
and Calendar/Zoom OAuth return screens. Existing review, voice, workspace approval
and manager controls are retained and restyled. Isolated browser walkthroughs use
fixture APIs; this does not mark the hosted integrations or launch as verified.
See [frontend delivery and verification](Frontend_SaaS_Redesign.md).
