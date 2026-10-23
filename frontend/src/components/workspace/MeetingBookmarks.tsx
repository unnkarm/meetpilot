import React, { useCallback, useEffect, useState } from 'react';
import useSWR from 'swr';
import { BookmarkPlus, Trash2 } from 'lucide-react';
import { apiFetch } from '../../services/api';
import type { MeetingBookmark } from '../../types/review';
import { formatTimeSeconds } from '../../utils/speakerUtils';
import { useMeetingText } from './MeetingLanguageDisplay';

interface Props {
  meetingId: string; actorId: string; getToken: () => Promise<string | null>;
  position: number; hasTranscript: boolean; isLive?: boolean; onSeek: (seconds: number) => void;
}
const labels = { decision: 'Crucial decision', followup: 'Follow-up needed', highlight: 'Highlight' };

export function MeetingBookmarks({ meetingId, actorId, getToken, position, hasTranscript, isLive, onSeek }: Props) {
  const endpoint = `/api/v1/meetings/${meetingId}/bookmarks`;
  const { data, error: loadError, mutate } = useSWR<MeetingBookmark[]>([endpoint, actorId], ([url]: [string, string]) => apiFetch(url, {}, getToken), { refreshInterval: isLive ? 5000 : 0 });
  const [label, setLabel] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const displayText = useMeetingText();
  const save = useCallback(async (kind: keyof typeof labels) => {
    if (!hasTranscript || busy) return;
    setBusy(true); setError('');
    try {
      await apiFetch(endpoint, { method: 'POST', body: JSON.stringify({ id: crypto.randomUUID(), kind, label: label.trim() || labels[kind], position_seconds: position }) }, getToken);
      setLabel(''); await mutate();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not save bookmark.'); }
    finally { setBusy(false); }
  }, [hasTranscript, busy, endpoint, label, position, getToken, mutate]);
  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (!event.altKey || !event.shiftKey || event.ctrlKey || event.metaKey || event.repeat ||
          target?.isContentEditable || target?.closest('input, textarea, select')) return;
      const kind = ({ KeyD: 'decision', KeyF: 'followup', KeyH: 'highlight' } as const)[event.code as 'KeyD' | 'KeyF' | 'KeyH'];
      if (kind) { event.preventDefault(); void save(kind); }
    };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, [save]);
  const remove = async (id: string) => {
    setError('');
    try { await apiFetch(`${endpoint}/${id}`, { method: 'DELETE' }, getToken); await mutate(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not remove bookmark.'); }
  };
  return <section className="rounded-xl border border-line bg-surface p-5 space-y-3">
    <h3 className="font-semibold text-ink flex items-center gap-2"><BookmarkPlus className="w-4 h-4 text-brand" />Meeting bookmarks</h3>
    <p className="text-sm text-muted">{isLive ? 'Marks the latest captured speech' : 'Marks the current playback position'} · {formatTimeSeconds(position)} · Alt+Shift+D/F/H</p>
    <input aria-label="Bookmark note" maxLength={160} value={label} onChange={e => setLabel(e.target.value)} placeholder="Optional note" className="w-full rounded-lg border border-line bg-surface p-2 text-sm text-ink" />
    <div className="flex flex-wrap gap-2">{(Object.keys(labels) as (keyof typeof labels)[]).map(kind => <button key={kind} disabled={busy || !hasTranscript} onClick={() => void save(kind)} className="rounded-lg border border-brand/30 px-3 py-2 text-sm text-brand disabled:opacity-40">{labels[kind]}</button>)}</div>
    {!hasTranscript && <p className="text-sm text-muted">Available after the first saved transcript turn.</p>}
    {(error || loadError) && <p role="alert" className="text-sm text-rose-700">{error || loadError.message}</p>}
    <ul className="space-y-2 max-h-64 overflow-y-auto">{data?.map(item => <li key={item.id} className="flex justify-between items-center gap-2 text-sm">
      <button onClick={() => onSeek(item.position_seconds)} className="text-left text-ink"><span className="font-mono text-brand mr-2">{formatTimeSeconds(item.position_seconds)}</span>{displayText(item.label)}</button>
      {item.can_delete && <button aria-label={`Delete bookmark ${item.label}`} onClick={() => void remove(item.id)} className="p-2 text-muted hover:text-rose-700"><Trash2 className="w-3.5 h-3.5" /></button>}
    </li>)}</ul>
  </section>;
}
