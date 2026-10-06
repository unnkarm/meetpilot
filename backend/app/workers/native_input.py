"""X11 input for the local headed meeting browser.

Google Meet checks for real pointer activity on the join form. The worker runs
under Xvfb and sends XTEST events through xdotool instead of CDP clicks.
"""

import asyncio
import math
import random
import logging

logger = logging.getLogger(__name__)


async def _xdotool(*args: str) -> str:
    process = await asyncio.create_subprocess_exec(
        "xdotool", *args, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        output, error = await asyncio.wait_for(process.communicate(), timeout=5)
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise RuntimeError(f"X11 input timed out: {' '.join(args)}") from None
    if process.returncode:
        raise RuntimeError(f"X11 input failed: {error.decode(errors='replace')[:200]}")
    return output.decode(errors="replace")


async def _page_origin(page) -> tuple[float, float, float]:
    """Calibrate the real screen pointer against browser client coordinates."""
    metrics = await page.evaluate("""() => ({
      dpr: window.devicePixelRatio || 1, sx: window.screenX, sy: window.screenY,
      width: window.innerWidth, height: window.innerHeight,
    })""")
    dpr = metrics["dpr"]
    probe_x = round((metrics["sx"] + metrics["width"] * 0.5) * dpr)
    probe_y = round((metrics["sy"] + metrics["height"] * 0.55) * dpr)
    await _xdotool("mousemove", "--sync", str(probe_x - 30), str(probe_y - 30))
    await page.evaluate("""() => {
      window.__meetpilotMouse = null;
      window.addEventListener('mousemove', e => {
        window.__meetpilotMouse = {x: e.clientX, y: e.clientY};
      }, {capture: true, once: true});
    }""")
    await _xdotool("mousemove", "--sync", str(probe_x), str(probe_y))
    await asyncio.sleep(0.12)
    observed = await page.evaluate("window.__meetpilotMouse")
    if not observed:
        raise RuntimeError("X11 pointer did not reach the meeting page")
    return probe_x - observed["x"] * dpr, probe_y - observed["y"] * dpr, dpr


async def click(page, locator) -> None:
    """Move across the X display, verify the target, then press a native button."""
    await page.bring_to_front()
    await locator.scroll_into_view_if_needed(timeout=3000)
    box = await locator.bounding_box(timeout=3000)
    if not box or box["width"] < 2 or box["height"] < 2:
        raise RuntimeError("Meeting control has no visible bounds")
    offset_x, offset_y, dpr = await _page_origin(page)
    target_x = round(offset_x + (box["x"] + box["width"] / 2) * dpr)
    target_y = round(offset_y + (box["y"] + box["height"] / 2) * dpr)
    pointer = await _xdotool("getmouselocation", "--shell")
    coords = dict(line.split("=", 1) for line in pointer.splitlines() if "=" in line)
    start_x, start_y = int(coords["X"]), int(coords["Y"])
    steps = max(7, min(18, math.ceil(math.dist((start_x, start_y), (target_x, target_y)) / 70)))
    for index in range(1, steps + 1):
        t = index / steps
        eased = t * t * (3 - 2 * t)
        x = round(start_x + (target_x - start_x) * eased)
        y = round(start_y + (target_y - start_y) * eased)
        await _xdotool("mousemove", "--sync", str(x), str(y))
        await asyncio.sleep(random.uniform(0.012, 0.028))
    # Check the actual screen pointer against the live element bounds. A stale
    # browser window offset must fail loudly instead of clicking elsewhere.
    pointer = await _xdotool("getmouselocation", "--shell")
    coords = dict(line.split("=", 1) for line in pointer.splitlines() if "=" in line)
    page_x = (int(coords["X"]) - offset_x) / dpr
    page_y = (int(coords["Y"]) - offset_y) / dpr
    box = await locator.bounding_box(timeout=3000)
    if not box or not (box["x"] <= page_x <= box["x"] + box["width"]
                       and box["y"] <= page_y <= box["y"] + box["height"]):
        raise RuntimeError("X11 pointer missed the meeting control")
    if not await locator.evaluate("(el, point) => { const hit = document.elementFromPoint(point[0], point[1]); return hit === el || !!hit && el.contains(hit); }", [page_x, page_y]):
        raise RuntimeError("Another element covers the meeting control")
    # Xvfb has no window manager to select the browser window automatically.
    # Without XSetInputFocus the DOM sees pointer events, but XTEST keystrokes
    # disappear and Google's name field remains empty.
    await _xdotool("windowfocus", coords["WINDOW"])
    await asyncio.sleep(random.uniform(0.05, 0.13))
    await _xdotool("mousedown", "1")
    await asyncio.sleep(random.uniform(0.05, 0.12))
    await _xdotool("mouseup", "1")


async def fill(page, locator, value: str) -> None:
    try:
        await click(page, locator)
        await _xdotool("key", "--clearmodifiers", "ctrl+a")
        await _xdotool("type", "--clearmodifiers", "--delay", "45", value)
        await asyncio.sleep(0.1)
    except Exception as exc:
        logger.warning("Native name input unavailable (%s); using verified Playwright input", type(exc).__name__)
    if await locator.input_value() != value:
        await locator.fill(value, timeout=3000)
        await locator.dispatch_event("change")
    if await locator.input_value() != value:
        raise RuntimeError("The meeting name field did not accept the bot name")

