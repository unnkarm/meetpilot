"""Supervise the local X11 desktop, audio server, and dedicated Celery queue."""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

DISPLAY_STATE = Path("/tmp/meetpilot-display.json")
children = []
stopping = False


def stop(_signum=None, _frame=None):
    global stopping
    stopping = True


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    subprocess.run(["xdpyinfo"], check=True, stdout=subprocess.DEVNULL)
    DISPLAY_STATE.write_text(json.dumps({key: os.environ[key] for key in ("DISPLAY", "XAUTHORITY") if key in os.environ}))
    DISPLAY_STATE.chmod(0o600)
    try:
        children.append(subprocess.Popen(["fluxbox", "-display", os.environ["DISPLAY"]]))
        children.append(subprocess.Popen(["pulseaudio", "--daemonize=no", "--exit-idle-time=-1", "--log-target=stderr"]))
        for _ in range(50):
            if subprocess.run(["pactl", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            if children[-1].poll() is not None:
                raise RuntimeError("PulseAudio exited during startup")
            time.sleep(0.1)
        else:
            raise RuntimeError("PulseAudio failed to become ready")
        subprocess.run(["pactl", "load-module", "module-null-sink", "sink_name=meetpilot_tts"], check=True)
        subprocess.run(["pactl", "load-module", "module-remap-source", "master=meetpilot_tts.monitor", "source_name=meetpilot_virtual_mic"], check=True)
        subprocess.run(["pactl", "set-default-source", "meetpilot_virtual_mic"], check=True)
        # WebAudio handles bot TTS injection. The physical mic graph stays silent.
        children.append(subprocess.Popen(["celery", "-A", "app.core.celery_app.celery_app", "worker", "-Q", "meeting_bot", "--concurrency=1", "--loglevel=info"]))
        print("MeetPilot bot runtime ready: Xvfb, Fluxbox, PulseAudio, meeting_bot queue", flush=True)
        while not stopping:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A required bot runtime process exited")
            time.sleep(0.5)
    finally:
        DISPLAY_STATE.unlink(missing_ok=True)
        # Celery must stop before its display/audio disappear.
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


if __name__ == "__main__":
    main()
