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

## Diagnose

```powershell
docker compose logs --tail 100 vexa meeting_bot backend
docker compose exec vexa supervisorctl status
docker compose exec vexa sh -c 'ls /tmp/vexa-workloads'
```

`vexa` being healthy checks the gateway. Also inspect the runtime and meeting-api through supervisorctl when bots cannot start. Browser logs are in `/tmp/vexa-workloads/` inside the engine. The workspace-scoped MeetPilot `bot-status` endpoint reports the upstream lifecycle. A bad private S3 endpoint used to disable recordings; storage now uses the valid `vexa-storage` hostname and an idempotent bucket initialization service.
