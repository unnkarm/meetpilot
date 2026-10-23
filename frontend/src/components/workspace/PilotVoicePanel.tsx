import { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../../services/api';
import { createPilotCapture } from '../../utils/pilotAudio';
import { useMeetingText } from './MeetingLanguageDisplay';

const API_BASE = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000';

type Session = { session_id: string; state: string };
type Citation = { speaker?: string; timestamp?: string; start_time?: number; end_time?: number; snippet?: string; title?: string; filename?: string };
const STATE_LABELS: Record<string, string> = {
  LISTENING: 'Listening', WAKE_DETECTED: 'Listening for your question',
  CAPTURING_QUERY: 'Listening for your question', PROCESSING: 'Thinking',
  SPEAKING: 'Speaking', ERROR: 'Needs attention', IDLE: 'Off',
};
const timestamp = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;

export function PilotVoicePanel({ meetingId, getToken, isLive = false }: {
  meetingId: string; getToken: () => Promise<string | null>; isLive?: boolean;
}) {
  const displayText = useMeetingText();
  const [status, setStatus] = useState('Off');
  const [answer, setAnswer] = useState('');
  const [transcript, setTranscript] = useState('');
  const [partial, setPartial] = useState(false);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [error, setError] = useState('');
  const [inputSource, setInputSource] = useState<'microphone' | 'meeting'>(isLive ? 'meeting' : 'microphone');
  const session = useRef<Session | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const mic = useRef<MediaStream | null>(null);
  const context = useRef<AudioContext | null>(null);
  const processor = useRef<AudioWorkletNode | null>(null);
  const player = useRef<HTMLAudioElement | null>(null);
  const audioUrl = useRef<string | null>(null);
  const playbackId = useRef<string | null>(null);
  const ready = useRef(false);

  const stopPlayback = () => {
    const audio = player.current;
    if (audio) {
      audio.onended = null;
      audio.onerror = null;
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
    }
    player.current = null;
    playbackId.current = null;
    if (audioUrl.current) URL.revokeObjectURL(audioUrl.current);
    audioUrl.current = null;
  };

  const cleanup = () => {
    ready.current = false;
    processor.current?.disconnect();
    processor.current?.port.close();
    processor.current = null;
    mic.current?.getTracks().forEach(track => track.stop());
    mic.current = null;
    void context.current?.close();
    context.current = null;
    stopPlayback();
    socket.current?.close();
    socket.current = null;
  };

  useEffect(() => () => { cleanup(); }, []);
  useEffect(() => {
    if (!isLive && !session.current && inputSource === 'meeting') setInputSource('microphone');
  }, [isLive, inputSource, status]);

  const stop = async () => {
    cleanup();
    const active = session.current;
    session.current = null;
    setStatus('Off');
    if (active) {
      try {
        await apiFetch(`/api/v1/meetings/${meetingId}/pilot/sessions/${active.session_id}`,
          { method: 'DELETE' }, getToken);
      } catch { /* Expired sessions are already stopped. */ }
    }
  };

  const start = async () => {
    setError('');
    setStatus('Starting');
    try {
      const token = await getToken();
      if (!token) throw new Error('Sign in to use Pilot');
      const active = await apiFetch<Session>(`/api/v1/meetings/${meetingId}/pilot/sessions`,
        { method: 'POST' }, getToken);
      session.current = active;
      if (inputSource === 'microphone') {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      mic.current = stream;
      const audioContext = new AudioContext({ sampleRate: 16000 });
      context.current = audioContext;
      await audioContext.resume();
      const source = audioContext.createMediaStreamSource(stream);
      const node = await createPilotCapture(audioContext);
      processor.current = node;
      node.port.onmessage = event => {
        if (!ready.current || socket.current?.readyState !== WebSocket.OPEN) return;
        socket.current.send(event.data);
      };
      source.connect(node);
      node.connect(audioContext.destination);
      }
      const endpoint = new URL(API_BASE);
      endpoint.protocol = endpoint.protocol === 'https:' ? 'wss:' : 'ws:';
      endpoint.pathname = `/api/v1/meetings/${meetingId}/pilot/audio`;
      const ws = new WebSocket(endpoint.toString());
      ws.binaryType = 'blob';
      socket.current = ws;
      ws.onopen = () => ws.send(JSON.stringify({ token, session_id: active.session_id, input_source: inputSource }));
      ws.onmessage = async event => {
        if (event.data instanceof Blob) {
          const interactionId = playbackId.current;
          if (!interactionId) return;
          stopPlayback();
          playbackId.current = interactionId;
          audioUrl.current = URL.createObjectURL(event.data);
          const audio = new Audio(audioUrl.current);
          player.current = audio;
          const acknowledge = (detail?: string) => {
            if (playbackId.current !== interactionId || ws.readyState !== WebSocket.OPEN) return;
            playbackId.current = null;
            ws.send(JSON.stringify({ type: detail ? 'playback_failed' : 'playback_complete', interaction_id: interactionId, detail }));
          };
          audio.onended = () => acknowledge();
          audio.onerror = () => { const detail = 'The browser could not decode Pilot audio.'; setError(detail); acknowledge(detail); };
          try { await audio.play(); } catch {
            if (playbackId.current !== interactionId) return; // Barge-in cancelled this audio.
            const detail = 'The browser blocked Pilot playback. Stop Pilot, then start it again to enable audio.';
            setError(detail); acknowledge(detail);
          }
          return;
        }
        const message = JSON.parse(event.data);
        if (message.type === 'ready') { ready.current = true; setStatus(message.session.state); }
        if (message.type === 'wake_detected') { ready.current = true; setError(''); setStatus('CAPTURING_QUERY'); }
        if (message.type === 'wake_acknowledged') { setAnswer(message.text); setCitations([]); }
        if (message.type === 'audio_started') { stopPlayback(); playbackId.current = message.interaction_id; }
        if (message.type === 'pilot_interrupted') {
          stopPlayback();
          ready.current = true;
          setStatus('CAPTURING_QUERY');
        }
        if (message.type === 'state') {
          setStatus(message.session.state);
          ready.current = ['LISTENING', 'CAPTURING_QUERY', 'PROCESSING', 'SPEAKING'].includes(message.session.state);
        }
        if (message.type === 'partial_transcript') { setTranscript(message.text); setPartial(true); }
        if (message.type === 'final_transcript') { setTranscript(message.text); setPartial(false); }
        if (message.type === 'query_received' || message.type === 'query_queued') { setTranscript(message.text); setPartial(false); setError(''); }
        if (message.type === 'answer') { setAnswer(message.answer); setCitations(message.citations || []); }
        if (message.type === 'error') setError(message.detail);
      };
      ws.onclose = () => {
        // A stopped connection may close after a newly started one is ready.
        if (socket.current !== ws) return;
        cleanup();
        if (session.current) setStatus('Disconnected');
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pilot could not start');
      await stop();
    }
  };

  return <div className="p-4 rounded-xl border border-brand/30 bg-surface space-y-2">
    <div className="flex items-center justify-between gap-3">
      <div><strong className="text-ink">Pilot voice</strong><p className="text-sm text-muted">Say “Pilot”, then ask in English, Bengali or Hindi. You can follow up after its reply.</p></div>
      <button type="button" disabled={status === 'Starting'} onClick={session.current ? stop : start} className="px-4 py-2 rounded-lg bg-brand text-on-brand text-sm disabled:opacity-50">
        {session.current ? 'Stop Pilot' : 'Start Pilot'}
      </button>
    </div>
    <label className="block text-sm text-ink">Listen through
      <select value={inputSource} disabled={!!session.current} onChange={event => setInputSource(event.target.value as 'microphone' | 'meeting')} className="ml-2 rounded bg-line p-1 text-ink">
        <option value="microphone">My microphone</option>
        <option value="meeting" disabled={!isLive}>Meeting bot (live calls)</option>
      </select>
    </label>
    <p className="text-sm text-muted" aria-live="polite">{STATE_LABELS[status] || status}</p>
    {transcript && <p className="text-sm text-ink" title={transcript}>{partial ? 'Hearing' : 'Heard'}: {displayText(transcript)}{partial ? ' …' : ''}</p>}
    {answer && <p className="text-sm text-ink whitespace-pre-line">Pilot: {displayText(answer)}</p>}
    {citations.length > 0 && <details className="text-sm text-muted">
      <summary className="cursor-pointer">Sources ({citations.length})</summary>
      <ul className="mt-2 space-y-2">{citations.map((citation, index) => <li key={index}>
        <span className="text-ink">{citation.speaker || citation.title || citation.filename || 'Meeting evidence'}{citation.timestamp ? ` · ${citation.timestamp}` : typeof citation.start_time === 'number' ? ` · ${timestamp(citation.start_time)}` : ''}</span>
        {citation.snippet && <p className="mt-1">“{displayText(citation.snippet)}”</p>}
      </li>)}</ul>
    </details>}
    {error && <p className="text-sm text-red-700" role="alert">{error}</p>}
  </div>;
}
