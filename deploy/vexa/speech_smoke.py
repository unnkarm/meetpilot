"""Exercise real upstream TTS playback and cancellation without joining a call."""
import json
import os
import subprocess
import time

import redis

values = dict(line.strip().split("=", 1) for line in open("/run/meetpilot-vexa.env", encoding="utf-8")
              if "=" in line and not line.startswith("#"))
environment = {**os.environ, "TTS_SERVICE_URL": values["TTS_SERVICE_URL"], "TTS_API_TOKEN": values["TTS_API_TOKEN"],
               "VEXA_BOT_CONFIG": json.dumps({"meeting_id": 999999, "redisUrl": values["VEXA_REDIS_URL"]})}
with redis.Redis.from_url(values["VEXA_REDIS_URL"]) as bus:
    for interrupt in (False, True):
        with bus.pubsub(ignore_subscribe_messages=True) as sub:
            sub.subscribe("meetpilot:voice:999999")
            code = """
import { createTtsPlayback } from '/app/core/meetings/services/bot/dist/tts-playback.js';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { createClient } = require('/app/core/meetings/services/bot/node_modules/redis');
const tts = createTtsPlayback(console.log);
const controls = createClient({ url: JSON.parse(process.env.VEXA_BOT_CONFIG).redisUrl });
await controls.connect();
await controls.subscribe('bot_commands:meeting:999999', (raw) => {
  if (JSON.parse(raw).action === 'speak_stop') tts.stop();
});
await tts.speak(process.env.SMOKE_TEXT, 'smoke');
// Upstream resolves speak on exit; the adapter publishes the ACK on close.
await new Promise(resolve => setTimeout(resolve, 500));
process.exit(0);
"""
            text = "The local meeting assistant is ready." if not interrupt else " ".join(["Testing speech interruption during local audio playback."] * 10)
            proc = subprocess.Popen(["node", "--require", "/meetpilot/voice_events.cjs", "--input-type=module", "-e", code],
                                    env={**environment, "SMOKE_TEXT": text})
            deadline = time.monotonic() + 45
            events = []
            while time.monotonic() < deadline:
                raw = sub.get_message(timeout=0.5)
                if not raw:
                    continue
                event = json.loads(raw["data"])
                events.append(event["type"])
                if event["type"] == "playback_started" and interrupt:
                    bus.publish("bot_commands:meeting:999999", json.dumps({"action": "speak_stop"}))
                if event["type"] in {"playback_complete", "playback_interrupted", "playback_failed"}:
                    break
            expected = "playback_interrupted" if interrupt else "playback_complete"
            if expected not in events:
                proc.kill()
                proc.wait()
                raise AssertionError(f"Expected {expected}, received {events}")
            proc.wait(timeout=10)
            print(json.dumps({"test": "barge_in" if interrupt else "neural_tts", "events": events}))
