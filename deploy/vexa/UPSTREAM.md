# Vexa engine used by MeetPilot

Source: https://github.com/vexa-ai/vexa

The upstream checkout in `vexa/` is preserved without edits at
`18e7ac1d6a0201d1489ce30b12b6f7138067a598`.
The deployed official Lite image is separately pinned to
`vexaai/vexa-lite:v012@sha256:945628e54d843cf6286a823ca8e226f2b3c48eb948ad2f895e64eb867b7a0d55`.
The image and source revision are separate artifacts; no claim is made that the
published image was built from this exact commit.

Relevant upstream packages are `core/meetings/services/bot`, the Google Meet,
Teams and Zoom capture modules, `remote-browser`, `core/runtime`, the gateway,
meeting-api, identity/admin-api, and `deploy/lite`. Their workspace dependencies
are why the whole source checkout is retained instead of copying isolated DOM
selectors into another bot implementation.

MeetPilot adapters live here and in `backend/app/services/vexa_client.py` and
`backend/app/workers/vexa_meeting.py`. They provision workspace keys, connect
local Whisper/Piper, persist confirmed evidence, and copy authenticated audio.
The local supervisor config is upstream's Lite config with admin-api bound to
the private Docker network so the backend can provision scoped service keys.
No admin API or Redis port is exposed on the host.

The launch adapter enables the existing invocation.v1 voice feature and directs
Chromium output to a sink separate from the virtual microphone. The Node preload
reports the real paplay process exit over the private bus and aborts pending TTS
HTTP requests on `speak_stop`. `voice_controls.cjs` replaces the upstream speech
callback's blind microphone toggle with an explicit, verified on/off operation;
it skips settings buttons and does not toggle an already-correct state. This is
loaded by the same preload for new bots. It leaves the upstream join and capture
modules unchanged. Run `docker compose exec -T vexa node --test
/meetpilot/test_voice_controls.cjs` for the microphone regression checks.

A paplay completion acknowledgement confirms local playback only. Participant
audibility must also be checked in a live meeting; it cannot be inferred from
the audio process exiting successfully.

To reproduce the reference checkout:

```powershell
git clone https://github.com/vexa-ai/vexa.git vexa
git -C vexa checkout 18e7ac1d6a0201d1489ce30b12b6f7138067a598
```

Retain upstream license notices in `vexa/` when redistributing its source or image.
