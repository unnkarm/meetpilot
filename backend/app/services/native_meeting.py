"""Local browser-bot contracts and conservative live meeting signals."""

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.services.pilot_phase1 import classify_live_statement


@dataclass(frozen=True)
class MeetingTarget:
    platform: str
    url: str
    native_id: str


def parse_meeting_target(raw: str) -> MeetingTarget:
    """Validate meeting links without losing passcodes or tenant context."""
    cleaned = (raw or "").strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    parsed = urlparse(cleaned)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Use an HTTPS meeting URL without credentials or a custom port")
    if host not in {"meet.google.com", "teams.microsoft.com", "teams.live.com", "zoom.us", "meet.jit.si"} and not host.endswith((".zoom.us", ".jit.si")):
        raise ValueError("Use an HTTPS Google Meet, Teams, Zoom, or Jitsi meeting URL")
    
    path = parsed.path.strip("/")
    if not path:
        raise ValueError("Meeting URL has no meeting identifier")

    if host == "meet.google.com":
        platform = "google_meet"
        if not re.fullmatch(r"[a-z]{3}-[a-z]{4}-[a-z]{3}", path.lower()):
            raise ValueError("Use the Google Meet link containing a code such as abc-defg-hij")
        native_id = path.lower()
        query = [(k, v) for k, v in parse_qsl(parsed.query) if k != "hl"] + [("hl", "en")]
        canonical_url = urlunparse(("https", host, f"/{native_id}", "", urlencode(query), ""))
    elif "teams" in host:
        platform = "teams"
        native_id = path[:255]
        canonical_url = urlunparse(("https", host, parsed.path, "", parsed.query, parsed.fragment))
    elif "zoom" in host:
        platform = "zoom"
        native_id = path[:255]
        canonical_url = urlunparse(("https", host, parsed.path, "", parsed.query, parsed.fragment))
    elif "jit.si" in host:
        platform = "jitsi"
        native_id = path.split("/")[-1]
        canonical_url = urlunparse(("https", host, parsed.path, "", parsed.query, parsed.fragment))
    else:
        raise ValueError("Unsupported meeting host")

    return MeetingTarget(platform, canonical_url, native_id)


def native_insights(text: str, recent_turns: list[str], *, owner_verified: bool = False) -> list[dict]:
    """Emit alerts only from explicit evidence; never run Qwen on every turn."""
    result = []
    candidate = classify_live_statement(text)
    if candidate and candidate.kind in {"task", "commitment"} and not owner_verified:
        # A spoken name is not a canonical workspace identity.
        result.append({"kind": "unassigned_action", "text": "Action needs a verified owner", "confidence": 0.9})
    if re.search(r"\b(?:the goal (?:today|of this meeting) is|our objective is|we need to decide)\b", text, re.I):
        result.append({"kind": "agenda_objective", "text": "Objective stated", "confidence": 0.8})
    if re.search(r"\b(?:we(?:'re| are) blocked by|the blocker is|this is blocked on)\b", text, re.I):
        result.append({"kind": "agenda_blocker", "text": "Blocker raised", "confidence": 0.8})
    if re.search(r"\b(?:let's follow up on|we should follow up on|follow up with)\b", text, re.I):
        result.append({"kind": "agenda_follow_up", "text": "Follow-up proposed", "confidence": 0.75})
    dates = set(re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", text))
    for prior in recent_turns[-10:]:
        previous_dates = set(re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", prior))
        if dates and previous_dates and dates != previous_dates:
            shared = set(re.findall(r"[a-z]{5,}", text.casefold())) & set(re.findall(r"[a-z]{5,}", prior.casefold()))
            if len(shared - {"about", "before", "after", "deadline"}) >= 2:
                result.append({"kind": "timeline_risk", "text": "Different dates mentioned for a similar topic", "confidence": 0.55})
                break
    return result


# Runs in Chromium before the meeting page creates its WebRTC connections.
# Each remote track is tapped once. A persistent WebAudio destination replaces
# the bot microphone so WAV playback can be injected without capturing itself.
CAPTURE_SCRIPT = r"""
(() => {
  if (window.__meetpilotInstalled) return;
  window.__meetpilotInstalled = true;

  // Keep the browser's actual platform, plugins and WebGL identity. Ad hoc
  // Windows renderer spoofing on Linux created an inconsistent fingerprint.
  window.__meetpilotCaptureErrors = [];
  window.__meetpilotCaptureMode = 'audio_worklet';
  const captured = new Set();
  const energy = new Map();
  window.__meetpilotRemoteTrackCount = 0;
  const OriginalPC = window.RTCPeerConnection;
  const NativeGUM = navigator.mediaDevices?.getUserMedia?.bind(navigator.mediaDevices);
  let micContext, micDestination;
  function virtualMic() {
    const existing = micDestination?.stream.getAudioTracks()[0];
    if (existing?.readyState === 'live') return existing;
    micContext = new AudioContext({sampleRate: 48000});
    micDestination = micContext.createMediaStreamDestination();
    const oscillator = micContext.createOscillator();
    const gain = micContext.createGain(); gain.gain.value = 0;
    oscillator.connect(gain).connect(micDestination);
    oscillator.start();
    return micDestination.stream.getAudioTracks()[0];
  }
  let activeSpeech = null;
  window.__meetpilotStopWav = () => {
    if (activeSpeech) {
      try { activeSpeech.stop(); } catch (_) {}
      activeSpeech = null;
    }
  };
  window.__meetpilotPlayWav = async (base64) => {
    window.__meetpilotStopWav();
    virtualMic();
    const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
    const decoded = await micContext.decodeAudioData(bytes.buffer);
    const source = micContext.createBufferSource();
    source.buffer = decoded;
    source.connect(micDestination);
    await micContext.resume();
    activeSpeech = source;
    return new Promise(resolve => {
      source.onended = () => {
        if (activeSpeech === source) activeSpeech = null;
        source.disconnect();
        resolve();
      };
      source.start();
    });
  };
  if (NativeGUM) navigator.mediaDevices.getUserMedia = async (constraints) => {
    const stream = await NativeGUM(constraints);
    if (constraints?.audio) {
      stream.getAudioTracks().forEach(track => { stream.removeTrack(track); track.stop(); });
      stream.addTrack(virtualMic());
    }
    return stream;
  };
  const workletCode = `
    class MeetPilotPCM extends AudioWorkletProcessor {
      constructor() { super(); this.pcm = new Int16Array(1024); this.offset = 0; }
      process(inputs) {
        const channels = inputs[0];
        if (!channels?.length) return true;
        for (let i = 0; i < channels[0].length; i++) {
          let value = 0;
          for (const channel of channels) value += channel[i] / channels.length;
          value = Math.max(-1, Math.min(1, value));
          this.pcm[this.offset++] = value < 0 ? value * 32768 : value * 32767;
          if (this.offset === this.pcm.length) {
            this.port.postMessage(this.pcm, [this.pcm.buffer]);
            this.pcm = new Int16Array(1024); this.offset = 0;
          }
        }
        return true;
      }
    }
    registerProcessor('meetpilot-pcm', MeetPilotPCM);
  `;
  function speakerHint(trackId, samples) {
    const now = Date.now();
    const rms = Math.sqrt(samples.reduce((sum, x) => sum + x * x, 0) / samples.length);
    energy.set(trackId, {rms, at: now});
    const active = [...energy.values()].filter(item => now - item.at < 250 && item.rms >= 350);
    if (active.length !== 1 || rms < 350) return null;
    const names = new Set();
    for (const element of document.querySelectorAll('[data-is-speaking="true"], [aria-label*=" is speaking" i], [aria-label*=" is talking" i]')) {
      const tile = element.closest('[data-participant-id]') || element;
      const raw = tile.getAttribute('data-participant-name') || tile.getAttribute('data-self-name') || element.getAttribute('aria-label') || '';
      const name = raw.replace(/\b(is speaking|speaking|is talking|talking)\b/ig, '').replace(/[,:-]+$/g, '').trim();
      if (name && name.length <= 80) names.add(name);
    }
    return names.size === 1 ? [...names][0] : null;
  }
  async function capture(track) {
    if (!track || track.kind !== 'audio' || captured.has(track.id)) return;
    captured.add(track.id);
    window.__meetpilotRemoteTrackCount += 1;
    const ctx = new AudioContext({sampleRate: 16000});
    let source, processor, mute;
    const dispose = () => {
      captured.delete(track.id);
      energy.delete(track.id);
      source?.disconnect(); processor?.disconnect(); mute?.disconnect();
      ctx.close().catch(() => {});
    };
    track.addEventListener('ended', dispose, {once: true});
    try {
      if (!ctx.audioWorklet || ctx.sampleRate !== 16000) throw new Error('16kHz AudioWorklet unavailable');
      const url = URL.createObjectURL(new Blob([workletCode], {type: 'text/javascript'}));
      try { await ctx.audioWorklet.addModule(url); } finally { URL.revokeObjectURL(url); }
      if (track.readyState !== 'live') { dispose(); return; }
      source = ctx.createMediaStreamSource(new MediaStream([track]));
      processor = new AudioWorkletNode(ctx, 'meetpilot-pcm', {numberOfInputs: 1, numberOfOutputs: 1});
      processor.port.onmessage = event => {
        Promise.resolve(window.__meetpilotFrame?.(track.id, Array.from(event.data), Date.now(), speakerHint(track.id, event.data))).catch(error => {
          window.__meetpilotCaptureErrors.push(String(error).slice(0, 120));
        });
      };
      source.connect(processor);
      mute = ctx.createGain(); mute.gain.value = 0;
      processor.connect(mute).connect(ctx.destination);
      await ctx.resume();
    } catch (error) {
      window.__meetpilotCaptureErrors.push(String(error).slice(0, 120));
      dispose();
    }
  }
  if (OriginalPC) {
    function WrappedPC(...args) {
      const pc = new OriginalPC(...args);
      pc.addEventListener('track', event => capture(event.track));
      return pc;
    }
    WrappedPC.prototype = OriginalPC.prototype;
    Object.setPrototypeOf(WrappedPC, OriginalPC);
    window.RTCPeerConnection = WrappedPC;
  }
  // Meet may render participant audio as media elements instead of exposing
  // individual track events to this page world. Use that path only when the
  // WebRTC hook has observed no remote audio, avoiding duplicate transcripts.
  setInterval(() => {
    if (captured.size) return;
    document.querySelectorAll('audio').forEach(el => {
      const stream = el.srcObject;
      if (stream && typeof stream.getAudioTracks === 'function') {
        stream.getAudioTracks().forEach(capture);
      }
    });
  }, 2000);
})();
"""
