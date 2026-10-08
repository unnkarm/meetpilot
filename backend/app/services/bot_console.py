"""Temporary local browser console for operator sign-in and visible challenges."""
import os
import signal
import subprocess
from contextlib import contextmanager


@contextmanager
def browser_console():
    helpers = []
    try:
        helpers.append(subprocess.Popen([
            "x11vnc", "-display", os.environ["DISPLAY"], "-auth", os.environ["XAUTHORITY"],
            "-localhost", "-rfbport", "5900", "-nopw", "-forever", "-shared", "-quiet",
        ], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        helpers.append(subprocess.Popen([
            "websockify", "--web=/usr/share/novnc/", "6080", "localhost:5900",
        ], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        yield
    finally:
        for helper in reversed(helpers):
            if helper.poll() is None:
                os.killpg(helper.pid, signal.SIGTERM)
                try:
                    helper.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(helper.pid, signal.SIGKILL)
                    helper.wait()
