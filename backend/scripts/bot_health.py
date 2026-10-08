"""Check the same X display as the worker, including after container restart."""
import json
import os
import subprocess
from pathlib import Path

os.environ.update(json.loads(Path("/tmp/meetpilot-display.json").read_text()))
subprocess.run(["xdpyinfo"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(["pactl", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
processes = [p for p in Path("/proc").iterdir() if p.name.isdigit()]
assert any(b"celery" in (p / "cmdline").read_bytes() for p in processes if (p / "cmdline").exists()), "Bot queue worker is absent"
