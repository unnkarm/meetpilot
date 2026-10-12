# Meeting review tools

Implemented in source on 8 October 2026. These features use the existing hosted
service architecture and AIProvider interface: Ollama for inexpensive development,
OpenAI when configured. No additional paid account is required for development.

## Using the features

Open a completed meeting (or a failed meeting with saved results) and select
**Review tools** beside the existing summary/transcript/tasks/chat tabs.

1. **Summary lens:** choose engineering standup, sales MEDDIC/BANT, executive
   briefing, 1-on-1 feedback or customer interview. Managers can add, edit and
   delete workspace templates. Approved members can select them.
2. **Follow-up draft:** select email, Slack or Teams and internal/client audience.
   Choose meeting language, English, Bengali or Hindi. Generated paragraphs cite
   saved speech. Edit the copy and copy it manually; edits to that copy are not
   persisted, and no message is sent by this feature.
3. **Timeline chapters:** generate topic headings/key points; click a heading to
   seek the recording. All chapter boundaries come from stored transcript turns.
4. **Bookmarks:** mark a decision, follow-up or highlight with an optional note.
   In past meetings the marker uses current playback position; during live calls
   it uses the latest captured speech timestamp. Shortcuts are **Alt+Shift+D/F/H**
   while focus is outside text inputs. Members can remove their own bookmarks;
   managers can remove any meeting bookmark.
5. **Risk review:** see missing verified task owners/deadlines and cited summary
   blockers. Members see only their assigned task records; managers see all.
   A missing field or mentioned blocker does not prove a missed commitment.
6. **Speaking metrics:** talk share, approximate words/minute, filler/question
   cues, longest continuous speech and overlapping speaker-seconds. Unknown
   speaker labels remain unknown; overlap is not an identified interruption.
7. **Cost estimate:** enter average hourly cost/person and participant count.
   This uses your assumptions and recording duration, in the rate's currency.
   It does not store compensation inputs or measure ROI/employee performance.
8. **Playback:** enable **Skip silence (transcript gaps)** and/or **Adaptive
   speed** below the recording controls. Both default off. Skip uses speech
   timestamps with padding; untranscribed sounds may be skipped. It does not
   skip the untranscribed tail. Adaptive speed uses approximate transcript
   pacing, preserves your base speed between turns and can be turned off.

Hinglish/Benglish display preferences also apply to review text. Citation storage
retains the original speech and timestamps.

## Draft processing and evidence

Review generation is a durable Celery task on the existing **processing** queue,
separate from the meeting bot queue. The API returns a queued draft and the UI
polls its status; HTTP requests do not wait through full generation. Drafts are
personal to their creator, including their saved source excerpts. Other workspace
members cannot read those artifacts, while the original meeting remains shared
according to the existing workspace policy.

The worker validates citations against each authorized input window, derives
chapter times on the server, checks current membership between windows and before
publishing, and rejects source changes. Current input limits are **16 windows of
12,000 UTF-8 bytes** with intact turns. Oversized input fails explicitly rather
than silently dropping turns. Window processing coverage is not a claim that AI
found every fact. Review output against its real source quotes.

UUID requests are idempotent. A per-member, per-workspace limit allows three
pending drafts, with row locking before admission. Failed drafts can retry;
queued/processing jobs become retryable after 20 minutes without a checkpoint.
Run tokens prevent an old worker from overwriting a later retry. Deleting a draft
cancels remaining work at the next checkpoint; a model request already in progress
may finish before that checkpoint. Completed drafts can be regenerated.

The shared base meeting summary/tasks/decisions are not replaced by these drafts.
Transcript fingerprint checks mark older artifacts stale when speech changes.
Workspace-wide AI billing/cost quotas, integration sends, sentiment inference,
voice enrollment and other remaining roadmap features are not implemented here.

## Enable the schema and worker when ready

This task does not start the full stack because the development PC overheats.
Back up the database first and apply the new Alembic revision
`f6a7b8c9d0e1` in the configured backend environment:

```powershell
# From backend/, with dependencies and the database available:
python -m alembic upgrade head
# Or, after the development database/backend are already running:
docker compose exec -T backend python -m alembic upgrade head
docker compose restart backend celery_worker
```

Restart/redeploy the frontend to load the new tab and playback controls. Existing
development Compose also runs bootstrap/migrations on backend startup. Use a
single migration job for hosted deployments. Do not run the migration concurrently
from several API replicas.

New tables: `summary_templates`, `meeting_artifacts`, `meeting_bookmarks`.
The migration accepts fresh/bootstrap-created tables and existing installations.
Its isolated test uses SQLite with PostgreSQL-type adapters; production PostgreSQL
execution remains to be verified when the stack is deliberately started.

## Verification

On 8 October 2026, the focused backend regression suite ran **232 tests: 229
passed and 3 opt-in integrations skipped**, including 22 new review tests.
All **12 frontend tests** passed. Backend bytecode compilation, frontend
TypeScript lint, production build and `git diff --check` passed. The build
retains its existing warning for a JavaScript bundle larger than 500 kB.

Automated tests exercise real SQL/HTTP permissions, evidence rejection, full
chapter turn coverage, original speaker/quote/time links, pending-job limits,
idempotency, queue failures, revoked membership, stale transcripts/workers and
migration upgrade/downgrade. Playback tests cover overlapping intervals, padding,
large gaps, tail preservation, invalid ranges and speed limits. AI and queues are
mocked: these checks do not establish actual model output quality or a live browser
walkthrough. No paid requests or Docker startup are part of verification.

See [the feature roadmap](Feature_Roadmap.md) for features still planned or partial.
