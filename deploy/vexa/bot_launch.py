"""Enable local voice on Vexa's existing invocation.v1 and run the upstream bot."""
import json
import os
import subprocess
from voice_capture_config import configure_capture_environment

# runtime.v1 deliberately filters inherited secrets. This file is visible only
# inside the local container; neither it nor invocation credentials reach the UI.
with open("/run/meetpilot-vexa.env", encoding="utf-8") as stream:
    values = dict(line.strip().split("=", 1) for line in stream if "=" in line and not line.startswith("#"))
for name in ("TTS_SERVICE_URL", "TTS_API_TOKEN"):
    os.environ[name] = values[name]
bot_root = "/app/core/meetings/services/bot"
# Process runtimes can filter inherited env. Read only the supported non-secret
# capture controls from the same mounted config; explicit runtime values win.
configure_capture_environment(os.environ, values, bot_root, report=lambda message: print(message, flush=True))
invocation = json.loads(os.environ["VEXA_BOT_CONFIG"])
invocation["voiceAgentEnabled"] = True
os.environ["VEXA_BOT_CONFIG"] = json.dumps(invocation)
os.environ["DISPLAY"] = ":99"
# Chromium's remote meeting output must never feed the TTS virtual microphone.
subprocess.run(["pactl", "load-module", "module-null-sink", "sink_name=meeting_output"],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(["pactl", "set-default-sink", "meeting_output"], check=True)
os.chdir(bot_root)
os.execvp("node", ["node", "--require", "/meetpilot/voice_events.cjs", "dist/index.js"])
