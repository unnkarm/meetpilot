import { useState } from 'react';
import useSWR from 'swr';
import { apiFetch } from '../../services/api';
import { ApiWorkspaceMember } from '../../types';

interface Identity { speaker_label: string; user_id: string | null; evidence: string; ambiguous?: boolean }
export function MeetingIdentities({ meetingId, members, getToken }: { meetingId: string; members: ApiWorkspaceMember[]; getToken: () => Promise<string | null> }) {
  const path = `/api/v1/meetings/${meetingId}/identities`;
  const { data, mutate } = useSWR<Identity[]>(path, url => apiFetch<Identity[]>(url, {}, getToken));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  return <details className="rounded-xl border border-line bg-surface p-4 space-y-3 text-sm">
    <summary className="font-semibold text-ink cursor-pointer">Participant identity mapping</summary>
    <p className="text-muted">Meet display names can be changed or duplicated. Confirm the workspace account for a speaker only when you know who they are. This attribution helps task extraction; it does not authenticate voice commands.</p>
    {data?.map(row => <label key={row.speaker_label} className="flex flex-wrap justify-between items-center gap-2 text-ink"><span>{row.speaker_label} · {row.ambiguous ? 'Duplicate label; assign tasks directly by account' : row.evidence.replaceAll('_', ' ')}</span>
      <select aria-label={`Workspace identity for ${row.speaker_label}`} value={row.user_id || ''} disabled={busy || row.ambiguous} onChange={async e => {
        setBusy(true); setError('');
        try { await apiFetch(path, { method: 'PATCH', body: JSON.stringify({ speaker_label: row.speaker_label, user_id: e.target.value || null }) }, getToken); await mutate(); }
        catch (err) { setError(err instanceof Error ? err.message : 'Could not confirm identity'); }
        finally { setBusy(false); }
      }} className="rounded-lg bg-surface p-2"><option value="">Unverified / external participant</option>{members.map(m => <option key={m.user_id} value={m.user_id}>{m.name} · {m.email}</option>)}</select>
    </label>)}
    {error && <p role="alert" className="text-rose-700">{error}</p>}
  </details>;
}
