import { useEffect, useRef, useState } from 'react';
import useSWR from 'swr';
import { apiFetch } from '../../services/api';

type VoiceSettings = {
  voice_id: string;
  can_edit: boolean;
  voices: { id: string; label: string; available: boolean }[];
};
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function PilotVoiceSettings({ workspaceId, getToken }: {
  workspaceId: string; getToken: () => Promise<string | null>;
}) {
  const endpoint = `/api/v1/workspaces/${workspaceId}/pilot/settings`;
  const { data, error, mutate } = useSWR(endpoint,
    url => apiFetch<VoiceSettings>(url, {}, getToken), { revalidateOnFocus: false });
  const [selected, setSelected] = useState('');
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [message, setMessage] = useState('');
  const [actionError, setActionError] = useState('');
  const player = useRef<HTMLAudioElement | null>(null);
  const audioUrl = useRef<string | null>(null);
  const previewRequest = useRef<AbortController | null>(null);

  const stopPreview = () => {
    previewRequest.current?.abort();
    player.current?.pause();
    player.current = null;
    if (audioUrl.current) URL.revokeObjectURL(audioUrl.current);
    audioUrl.current = null;
  };
  useEffect(() => { setSelected(data?.voice_id || ''); }, [data?.voice_id, workspaceId]);
  useEffect(() => () => stopPreview(), [workspaceId]);

  const save = async () => {
    setSaving(true); setMessage(''); setActionError('');
    try {
      await apiFetch(endpoint, { method: 'PATCH', body: JSON.stringify({ voice_id: selected }) }, getToken);
      await mutate();
      setMessage('Voice saved. Pilot will use it for its next spoken reply.');
    } catch (err) { setActionError(err instanceof Error ? err.message : 'Could not save voice'); }
    finally { setSaving(false); }
  };
  const preview = async () => {
    stopPreview(); setPreviewing(true); setActionError('');
    const controller = new AbortController();
    previewRequest.current = controller;
    try {
      const token = await getToken();
      if (!token) throw new Error('Sign in to preview a voice');
      const response = await fetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/pilot/voice-preview`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_id: selected }), signal: controller.signal,
      });
      if (!response.ok) throw new Error('Could not preview this voice');
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      audioUrl.current = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl.current);
      player.current = audio;
      audio.onended = () => { setPreviewing(false); stopPreview(); };
      audio.onerror = () => { setActionError('Could not play this preview'); setPreviewing(false); stopPreview(); };
      await audio.play();
    } catch (err) {
      if (!controller.signal.aborted) {
        setActionError(err instanceof Error ? err.message : 'Could not preview voice');
        setPreviewing(false);
      }
    }
  };

  if (error) return <p role="alert" className="text-sm text-red-700">Could not load bot voice settings.</p>;
  if (!data) return <p className="text-sm text-muted">Loading bot voices…</p>;
  return <section className="space-y-4">
    <h3 className="text-sm font-bold text-ink uppercase tracking-wider">Bot Voice</h3>
    <p className="text-sm text-muted">Choose the voice Pilot uses for this workspace. Say “Pilot” or “Hey Pilot” to hear “Yes sir” before asking your question.</p>
    <label className="block text-sm text-ink">Voice
      <select value={selected} onChange={event => { stopPreview(); setPreviewing(false); setSelected(event.target.value); setMessage(''); }}
        disabled={!data.can_edit || saving} className="mt-2 block w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink disabled:opacity-60">
        {data.voices.map(voice => <option key={voice.id} value={voice.id} disabled={!voice.available}>
          {voice.label}{voice.available ? '' : ' (unavailable)'}
        </option>)}
      </select>
    </label>
    <div className="flex gap-3">
      <button type="button" onClick={preview} disabled={previewing || !selected || !data.voices.some(v => v.id === selected && v.available)}
        className="rounded-lg border border-line px-4 py-2 text-sm text-ink disabled:opacity-50">{previewing ? 'Playing…' : 'Preview voice'}</button>
      <button type="button" onClick={save} disabled={!data.can_edit || saving || !selected || selected === data.voice_id}
        className="rounded-lg bg-brand px-4 py-2 text-sm text-on-brand disabled:opacity-50">{saving ? 'Saving…' : 'Save voice'}</button>
    </div>
    {!data.can_edit && <p className="text-sm text-muted">Only workspace owners and admins can change the bot voice.</p>}
    {message && <p role="status" className="text-sm text-green-700">{message}</p>}
    {actionError && <p role="alert" className="text-sm text-red-700">{actionError}</p>}
  </section>;
}
