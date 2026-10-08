"""Exercise the local bot/audio/model pipeline without joining an external call.

Run in the meeting_bot container with DISPLAY=:99. This uses a Chromium WebRTC
loopback and generated speech, so it needs neither a meeting nor cloud APIs.
"""

import asyncio
import base64
import io
import os
from pathlib import Path
import subprocess
import wave

from playwright.async_api import async_playwright

from app.core.app_config import APP_CONFIG
from app.services.ai_provider import get_ai_provider
from app.services.embedding_provider import embed_text
from app.services.native_meeting import CAPTURE_SCRIPT
from app.services.pilot_streaming_stt import StreamingSpeechBuffer, get_stt_provider
from app.services.pilot_tts import get_tts_provider


def generated_speech() -> bytes:
    source = subprocess.check_output(["espeak-ng", "--stdout", "Hey Pilot, review the database migration."])
    return subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-ar", "16000", "-ac", "1",
         "-f", "s16le", "pipe:1"],
        input=source, stdout=subprocess.PIPE, check=True,
    ).stdout


def use_worker_display() -> None:
    """Reuse the worker's current X display, which can change after restart."""
    if os.environ.get("DISPLAY"):
        return
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            command = (process / "cmdline").read_bytes()
            if b"celery" not in command or b"meeting_bot" not in command:
                continue
            entries = (process / "environ").read_bytes().split(b"\0")
            env = dict(entry.split(b"=", 1) for entry in entries if b"=" in entry)
            if b"DISPLAY" in env and b"XAUTHORITY" in env:
                os.environ["DISPLAY"] = env[b"DISPLAY"].decode()
                os.environ["XAUTHORITY"] = env[b"XAUTHORITY"].decode()
                return
        except (OSError, ValueError):
            continue
    raise RuntimeError("The meeting bot has no active Xvfb display")


async def verify_browser_capture(wav: bytes) -> None:
    use_worker_display()
    frames = []
    received = asyncio.Event()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path="/usr/bin/chromium", headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--autoplay-policy=no-user-gesture-required"],
        )
        context = await browser.new_context()

        async def on_frame(_source, track_id, samples, timestamp, hint=None):
            frames.append((track_id, samples, timestamp))
            received.set()

        await context.expose_binding("__meetpilotFrame", on_frame)
        await context.add_init_script(CAPTURE_SCRIPT)
        page = await context.new_page()
        try:
            await page.route("http://localhost/smoke", lambda route: route.fulfill(body="<html><body>Offline WebRTC fixture</body></html>", content_type="text/html"))
            await page.goto("http://localhost/smoke")
            await page.evaluate("""async () => {
              const ctx = new AudioContext();
              const oscillator = ctx.createOscillator();
              const destination = ctx.createMediaStreamDestination();
              oscillator.connect(destination);
              oscillator.start();
              const sender = new RTCPeerConnection({iceServers: []});
              const receiver = new RTCPeerConnection({iceServers: []});
              sender.onicecandidate = e => { if (e.candidate) receiver.addIceCandidate(e.candidate); };
              receiver.onicecandidate = e => { if (e.candidate) sender.addIceCandidate(e.candidate); };
              sender.addTrack(destination.stream.getAudioTracks()[0], destination.stream);
              const offer = await sender.createOffer();
              await sender.setLocalDescription(offer);
              await receiver.setRemoteDescription(offer);
              const answer = await receiver.createAnswer();
              await receiver.setLocalDescription(answer);
              await sender.setRemoteDescription(answer);
              window.__smokeConnections = [sender, receiver, ctx, oscillator];
            }""")
            await asyncio.wait_for(received.wait(), timeout=15)
            assert await page.evaluate("window.__meetpilotCaptureMode") == "audio_worklet"
            assert not await page.evaluate("window.__meetpilotCaptureErrors")
            assert frames[0][0] and 0 < len(frames[0][1]) <= 8192
            assert await page.evaluate("window.__meetpilotRemoteTrackCount") >= 1
            await page.evaluate("wav => window.__meetpilotPlayWav(wav)", base64.b64encode(wav).decode())
            print(f"browser_capture=ok frames={len(frames)} virtual_mic_playback=ok")
        finally:
            await context.close()
            await browser.close()


async def main() -> None:
    pcm = generated_speech()
    buffer = StreamingSpeechBuffer(get_stt_provider())
    events = []
    for offset in range(0, len(pcm), 3200):
        events.extend(buffer.feed(pcm[offset:offset + 3200]))
    events.extend(buffer.feed(bytes(32000)))
    final = [event.text for event in events if event.type == "final_transcript"]
    assert final and final[0].strip(), "Local Whisper produced no final speech turn"
    print(f"offline_stt=ok final={final[0]!r}")

    vector = embed_text("database migration", "RETRIEVAL_QUERY")
    assert len(vector) == APP_CONFIG.embeddings.dimensions
    print(f"ollama_embedding=ok dimensions={len(vector)}")

    reply = get_ai_provider().chat("Reply with exactly READY and no other text.")
    assert reply.strip(), "Local Qwen produced an empty answer"
    print(f"ollama_qwen=ok response={reply[:60]!r}")

    chunks = [chunk async for chunk in get_tts_provider().synthesize_chunks("Ready to help.", "en")]
    assert chunks
    with wave.open(io.BytesIO(chunks[0]), "rb") as reader:
        assert reader.getnchannels() == 1 and reader.getsampwidth() == 2
        assert reader.getframerate() == 24000 and reader.getnframes() > 0
        assert len(chunks[0]) == 44 + reader.getnframes() * 2
    print(f"piper_tts=ok wav_bytes={len(chunks[0])}")
    await verify_browser_capture(chunks[0])


if __name__ == "__main__":
    asyncio.run(main())
