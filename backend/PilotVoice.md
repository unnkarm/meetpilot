# MeetPilot with the upstream Vexa engine

## Start

```powershell
python backend/scripts/setup_vexa.py
docker compose up -d --build
docker compose ps
```

The credential setup is idempotent. Keep `backend/.env.vexa` private and retain it across restarts. Vexa has its own Postgres database, password-protected Redis bus, S3-compatible recording storage, Xvfb, Chromium and PulseAudio. The dedicated `meeting_bot` queue manages the bridge; it no longer launches the custom native join worker. The official Lite image is pinned by digest. Source and adapter provenance are in `deploy/vexa/UPSTREAM.md`.

MeetPilot: http://localhost:3000
Vexa gateway health: http://localhost:18056/health
Local bot browser: http://localhost:6080/vnc.html?autoconnect=true&resize=scale
Vexa operator terminal: http://localhost:18057

The Vexa operator terminal has deployment-level access. Keep its loopback binding. Backend admin credentials and workspace API keys are never sent to the MeetPilot browser.

## Join and stop

Start a meeting from MeetPilot with an active Google Meet, Teams, or Zoom link. Admit **MeetPilot AI Bot** when the host receives its request. `awaiting_admission` is a waiting state; `active` is the upstream confirmation of admission. The browser console shows the actual upstream browser.

Guest admission depends on the meeting's settings and host. The successful Google Meet test used Vexa guest entry; this is not proof of Google account session persistence. The old native `save_bot_auth.py` profile does not configure Vexa. Restricted account-only calls require Vexa's `remote-browser` provisioning and workspace-specific credentials before enabling authenticated mode; do not share one account session across workspaces.

Stopping in MeetPilot sends the upstream leave request. The bridge drains confirmed turns, downloads the owned final recording, and queues local intelligence. Existing speaker labels and timestamps are retained; local audio transcription is only a recovery path when no confirmed turns survived.

An upstream `completed` callback also finalizes a meeting automatically. An expired bridge lease is reacquired only when no other worker owns it; a superseded worker exits without stopping the bot or changing meeting status. Capture interruptions are stored separately from analysis errors. When evidence survives a disconnection, it is still analyzed and shown in the past meeting with an interruption warning. A join failure with no captured evidence remains a failed bot session. The bridge worker waits for Vexa health before resuming existing meetings.

If the whole stack was stopped during analysis, a local operator can resume one ended meeting without waiting for the stale-job timer:

```powershell
docker compose exec -T meeting_bot python /app/scripts/recover_ended_meeting.py MEETING_UUID
```

The command checks active workers and the owned provider lifecycle before requeuing existing evidence. Add `--normal-end` only when the host confirms a normal ending despite a stale provider failure.

## Speech and intelligence

With Pilot Voice started, say **Pilot**, **Hey Pilot**, **Hi Pilot**, **Hello Pilot**, **OK Pilot**, or **MeetPilot**. The first recognized partial name triggers **Yes sir.** without waiting for the AI answer. Its short acknowledgement is generated locally and cached at startup. You can keep speaking your question during the acknowledgement, or ask within the next ten seconds. Partial/final retransmissions of the same utterance do not repeat the acknowledgement. Recognition still depends on local Whisper and the incoming transcript cadence.

Live meetings now default to **Meeting bot (live calls)** in Pilot Voice. Say **“Pilot, give me a summary of the meeting”** or **“What key points have we discussed?”**. The recap uses original transcript evidence across the meeting timeline plus source-linked agreements and commitments. Long meetings use bounded excerpts; coverage metadata records sampling, and the model must not claim an exhaustive recap. Recent questions such as **“What did we just discuss?”** use recent unembedded turns directly, avoiding an embedding-model switch before the answer.

Replies use conversational sentences. Internal source handles such as `S11` are removed from answers; citations remain under **Sources** in the panel with speaker names, timestamps and quotes. Ordinary technical references such as AWS S3 are preserved. Missing evidence produces an uncertainty response rather than an invented meeting fact.

After a reply, the same named meeting participant can ask a follow-up for 30 seconds without another wake phrase, for example **“Make it shorter”** or **“Explain the second point”**. The authenticated microphone permits unlabelled follow-ups. Unknown meeting speakers need a wake phrase for a new turn. Brief user/assistant history resolves references; fresh workspace-scoped evidence remains required for factual answers. Ordinary nearby statements do not count as meeting follow-up questions.

Pilot starts retrieval while **Yes sir** plays. Repeating an in-flight question does not discard its answer; one distinct next question can wait behind it. Speaking during playback stops the older reply and captures the new turn. Cancellation stops synthesis/playback and releases the shared voice lock before another reply starts. Failed browser playback is reported as a failure, rather than acknowledged as successful audio.

Microphone capture keeps 200 ms of leading audio, emits its first partial after 600 ms of speech, and assigns a stable utterance ID. Questions can run for up to 30 seconds. The silence cutoff defaults to 700 ms; set `PILOT_SILENCE_END_MS=900` in `backend/.env` if your natural pauses split microphone questions. This setting affects dashboard microphone capture, not Vexa's live-call capture pipeline.

The upstream Google Meet capture defaults can wait 15 seconds before submitting isolated short speech. The launcher now requests minimum audio of 0.4 seconds, submissions every 1 second, and an idle timeout of 1.5 seconds, retaining two-pass transcript confirmation. These are supported upstream `BOT_SPEAKER_*` controls. The launcher checks the image's compiled configuration and logs a warning when it cannot confirm support; changes in the reference checkout alone do not change the pinned image. Actual latency still requires a live test. To reduce repeated recognition work on a busy CPU, override `BOT_SPEAKER_SUBMIT_INTERVAL_SEC=2` in `backend/.env.vexa` before starting a new bot. No credentials need to change.

After a live meeting ends, stop its voice session and start **My microphone** for questions about the saved meeting. Replies play in the browser, rather than being sent to the departed bot.

In **Settings → Bot Voice**, preview and save **Lessac** or **Ryan**. Both neural models are bundled for offline execution. Owners and admins can change the workspace voice; members can preview it. A saved voice applies to the next spoken reply, including the wake acknowledgement.

Vexa posts 16kHz mono PCM WAV chunks to the private local Whisper adapter. That endpoint accepts only a generated service token and uses locally installed model files. Piper streams 24kHz mono PCM into Vexa's virtual microphone through its existing TTS playback module; espeak-ng is the fallback. Chromium's remote output sink is separate from the TTS microphone sink.

Pilot's **My microphone** option uses local energy-based interruption. **Meeting bot** consumes upstream partial and confirmed transcript events. Its interruption latency depends on Vexa's partial transcript cadence; it is not an immediate raw PCM VAD callback. Voice output ACK is emitted after paplay exits, not after synthesis. Interruption aborts pending TTS HTTP and kills active playback. Verified workspace actions remain restricted to the authenticated user's microphone; remote speaker names are not account identities.

## Verify

```powershell
python -m compileall -q backend/app backend/alembic backend/scripts
docker compose run --rm --no-deps -e MEETPILOT_RUN_PILOT_INTEGRATION=1 -v ./backend/tests:/app/tests backend python -m unittest discover -s tests -q
docker compose exec -T vexa /opt/venvs/meeting/bin/python /meetpilot/speech_smoke.py
cd frontend
npm run lint
npm run build
```

The speech smoke test uses real local Piper and upstream paplay. It tests process completion and interruption without opening another meeting. A real meeting test is still needed to validate platform admission and remote audio. Google Meet admission, live named transcripts, and recording download were exercised in this setup. Teams and Zoom have not yet been exercised live.

### October 8 conversational fixes

The conversation/answer/capture fixes were checked locally with mock speech/model providers, fake Redis, SQLite, and protocol tests: 135 backend tests passed, one PostgreSQL integration test was skipped, 13 Node playback tests passed, and eight frontend language/access tests passed. Backend compilation, TypeScript checking, and the frontend production build passed. The build retains its existing large-bundle warning. Docker, Ollama and meeting bots stayed stopped. These checks verify routing, source separation, access boundaries, frame preservation, cancellation and playback acknowledgements; they do not measure real Whisper/Qwen accuracy or live latency on this computer.

When ready, rebuild the frontend and restart the Python services. The Vexa adapter files are mounted from `deploy/vexa` and load when a bot starts, so stop and rejoin any existing bot. A full local refresh is:

```powershell
docker compose up -d --build
docker compose restart backend meeting_bot celery_worker
```

Then start Pilot Voice and try, once each:

1. **“Pilot”**, pause for **“Yes sir”**, then **“Give me a summary of this meeting.”**
2. **“Make it shorter.”** within the follow-up window.
3. **“Pilot, what did we just decide?”** after discussing a real decision.
4. Start another question while Pilot is speaking; the old audio should stop.

Check the **Heard/Hearing** text and **Sources** if an answer is unexpected. Local model size, CPU load and transcript quality still affect responsiveness; these source changes do not establish parity with GPT's real-time voice service.

### October 8 mixed English/Bengali/Hindi follow-up

Choose **Mixed / auto · English, Bengali, Hindi + others** for a code-switched meeting. English remains the default for a new meeting. The microphone, live-call and recording Whisper paths now use multilingual transcription without translating the stored evidence. **Pilot / Hey Pilot** and **Yes sir** stay English; the question and subsequent same-speaker follow-up can be Bengali or Hindi. Replies follow the question's language, with localized uncertainty when sources are missing. See [Multilingual processing](../docs/Multilingual.md) for examples and language overrides.

The private Vexa voice token carries the reply language together with the selected voice and playback correlation ID. Native-script speech uses local espeak-ng unless a matching Hindi/Bengali Piper model is installed and configured. The two bundled Piper models remain English voices. Script switching keeps technical terms and source quotes intact, and shared Indic punctuation does not trigger a voice change.

Confirmed live decisions, commitments, explicit deadlines and labelled blockers now support native Bengali/Hindi signals. Final analysis retains live decisions and completed/assigned tasks. Structured items from all transcript windows survive the bounded prose-summary roll-up, including different decisions about the same topic. Native task creation still requires an authenticated manager, a uniquely resolved workspace member and exact request text; meeting audio is not an account authorization method.

Validation after these changes: **190 backend tests passed, three integration checks skipped**, 13 Node playback tests passed and eight frontend language/access tests passed. Backend compilation, TypeScript checking and the production build passed; the existing large-bundle warning remains. Tests used fake model/speech providers, fake Redis, SQLite and protocol fixtures. Installed language libraries were used for language metadata checks; speech model weights were not downloaded or loaded. Docker, Ollama and meeting bots stayed stopped. Real code-switched audio accuracy and response latency still need the short meeting test described in the multilingual guide.

Rebuild the Python images when ready: the faster-whisper minimum is now **1.2.1**. Restart the frontend/backend/worker services and rejoin the bot after selecting the meeting language. Optional new Piper voices need to be installed locally before their environment paths are enabled.

## Diagnose

```powershell
docker compose logs --tail 100 vexa meeting_bot backend
docker compose exec vexa supervisorctl status
docker compose exec vexa sh -c 'ls /tmp/vexa-workloads'
```

`vexa` being healthy checks the gateway. Also inspect the runtime and meeting-api through supervisorctl when bots cannot start. Browser logs are in `/tmp/vexa-workloads/` inside the engine. The workspace-scoped MeetPilot `bot-status` endpoint reports the upstream lifecycle. A bad private S3 endpoint used to disable recordings; storage now uses the valid `vexa-storage` hostname and an idempotent bucket initialization service.
