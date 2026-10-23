import { useEffect, useState } from 'react';
import { Video, Clipboard, Loader2 } from 'lucide-react';
import { startLiveMeeting } from '../services/api';
import type { ApiMeetingDetail } from '../types';
import { MeetingLanguageSelect } from './workspace/MeetingLanguageDisplay';
import { Modal } from './Modal';
interface Props { isOpen: boolean; onClose: () => void; workspaceId: string; getToken?: () => Promise<string | null>; onSuccess: (meeting: ApiMeetingDetail) => void; initialMeetingUrl?: string }
export function LiveMeetingModal({ isOpen, onClose, workspaceId, getToken, onSuccess, initialMeetingUrl }: Props) {
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');
  const [language, setLanguage] = useState('en');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { if (isOpen) { setUrl(initialMeetingUrl || ''); setError(''); } }, [isOpen, initialMeetingUrl]);
  const code = /^[a-z]{3}-[a-z]{4}-[a-z]{3}$/i.test(url.trim());
  const valid = code || (() => { try { const parsed = new URL(url.trim()); return parsed.protocol === 'https:' && parsed.pathname !== '/' && ['meet.google.com', 'teams.microsoft.com', 'teams.live.com', 'zoom.us'].some(host => parsed.hostname === host || (host === 'zoom.us' && parsed.hostname.endsWith('.zoom.us'))); } catch { return false; } })();
  if (!isOpen) return null;
  return <Modal label="Join a live meeting" onClose={onClose} busy={busy}><span className="mp-modal-icon"><Video size={22} /></span><p className="mp-eyebrow">Live assistant</p><h2 className="mp-modal-title">Bring MeetPilot to your meeting.</h2><p className="mp-modal-description">Capture the conversation and keep decisions, summaries and next steps together.</p><form className="mp-form" onSubmit={async e => { e.preventDefault(); if (!valid || busy) return; setBusy(true); setError(''); try { const created = await startLiveMeeting(workspaceId, code ? `https://meet.google.com/${url.trim()}` : url.trim(), title.trim() || undefined, getToken, language); onSuccess(created); onClose(); setTitle(''); } catch (err) { setError(err instanceof Error ? err.message : 'Could not start the meeting assistant.'); } finally { setBusy(false); } }}><label>Meeting link<div className="flex gap-2"><input className="mp-field flex-1 min-w-0" value={url} onChange={e => setUrl(e.target.value)} required placeholder="https://meet.google.com/abc-defg-hij" /><button type="button" className="mp-button mp-button-secondary" aria-label="Paste meeting link" onClick={async () => { try { setUrl((await navigator.clipboard.readText()).trim()); } catch { setError('Clipboard access unavailable. Paste the link into the field.'); } }}><Clipboard size={15} /></button></div><small>Google Meet, Microsoft Teams or Zoom web meeting.</small></label><label>Meeting title <span className="text-muted font-normal">(optional)</span><input className="mp-field" value={title} onChange={e => setTitle(e.target.value)} maxLength={200} placeholder="e.g. Weekly product review" /></label><MeetingLanguageSelect value={language} onChange={setLanguage} /><div className="mp-admission-note"><strong>The host may need to admit the assistant.</strong><p>Keep the call active. Restricted meetings may require an invited bot account configured by your workspace operator.</p></div>{error && <div role="alert" className="mp-error-state">{error}</div>}<div className="mp-modal-actions"><button type="button" className="mp-button mp-button-secondary" onClick={onClose} disabled={busy}>Cancel</button><button className="mp-button mp-button-primary" disabled={!valid || busy}>{busy ? <><Loader2 size={15} className="animate-spin" />Requesting assistant…</> : <><Video size={15} />Join meeting</>}</button></div></form></Modal>;
}
