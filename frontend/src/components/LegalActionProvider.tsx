import { useCallback, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { Loader2 } from 'lucide-react';
import { useSWRConfig } from 'swr';
import { apiFetch } from '../services/api';
import { PolicyActionCancelled, registerPolicyRequester } from '../services/legalConsent';
import { recognizesPolicyCopy, type PolicyAcceptanceStatus } from '../utils/legal';
import { Modal } from './Modal';

type Pending = { resolve: () => void; reject: (error: Error) => void };

export function LegalActionProvider({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();
  const { mutate } = useSWRConfig();
  const accepted = useRef(false);
  const pending = useRef<Pending | null>(null);
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<PolicyAcceptanceStatus | null>(null);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const finish = useCallback(() => {
    accepted.current = true;
    const waiting = pending.current; pending.current = null;
    setOpen(false); setStatus(null); setChecked(false);
    waiting?.resolve();
  }, []);

  const load = useCallback(async (waiting: Pending) => {
    setError(''); setStatus(null); setChecked(false); setBusy(true);
    try {
      const result = await apiFetch<PolicyAcceptanceStatus>('/api/v1/legal/acceptance', { cache: 'no-store' }, getToken);
      if (pending.current !== waiting) return;
      if (result.accepted) { void mutate('/api/v1/legal/acceptance', result, false); finish(); return; }
      setStatus(result); setOpen(true);
    } catch (err) {
      if (pending.current !== waiting) return;
      setError(err instanceof Error ? err.message : 'Could not load policy status.'); setOpen(true);
    } finally { if (pending.current === waiting || !pending.current) setBusy(false); }
  }, [getToken, finish, mutate]);

  const request = useCallback(() => {
    if (accepted.current) return Promise.resolve();
    // Preserve only the initiating action, so repeated clicks cannot queue work.
    if (pending.current) return Promise.reject(new PolicyActionCancelled());
    return new Promise<void>((resolve, reject) => {
      const waiting = { resolve, reject }; pending.current = waiting;
      void load(waiting);
    });
  }, [load]);

  useLayoutEffect(() => {
    const unregister = registerPolicyRequester(request);
    return () => {
      unregister();
      const waiting = pending.current; pending.current = null;
      waiting?.reject(new PolicyActionCancelled());
    };
  }, [request]);

  function cancel() {
    const waiting = pending.current; pending.current = null;
    setOpen(false); setStatus(null); setChecked(false); setError('');
    waiting?.reject(new PolicyActionCancelled());
  }

  async function agree() {
    if (!status || !checked || !recognizesPolicyCopy(status.policies) || busy) return;
    const waiting = pending.current;
    setBusy(true); setError('');
    try {
      const receipt = await apiFetch<{ accepted_at: string; bundle: string; accepted_versions: PolicyAcceptanceStatus['accepted_versions'] }>('/api/v1/legal/acceptance', { method: 'POST', body: JSON.stringify({ bundle: status.policies.bundle, terms_agreed: true, privacy_acknowledged: true, recording_responsibilities_acknowledged: true }) }, getToken);
      if (pending.current === waiting) {
        void mutate('/api/v1/legal/acceptance', { ...status, accepted: true, accepted_at: receipt.accepted_at, accepted_bundle: receipt.bundle, accepted_versions: receipt.accepted_versions }, false);
        finish();
      }
    } catch (err) { if (pending.current === waiting) setError(err instanceof Error ? err.message : 'Could not save acknowledgment.'); }
    finally { setBusy(false); }
  }

  return <>{children}{open && <Modal label="Before your first action" onClose={cancel} busy={busy} className="mp-legal-prompt"><p className="mp-eyebrow">One-time acknowledgment</p><h2 className="mp-modal-title">Before your first action</h2><p className="mp-modal-description">Review how MeetPilot processes your information. After you agree, we’ll continue your action. You won’t be asked again; the policies stay in Settings.</p>{status && <><div className="mp-policy-notice"><div><strong>{status.policies.published ? 'Your recording responsibilities' : 'Development draft · operator details pending'}</strong><p>{status.policies.published ? 'Establish authority, notify participants and obtain the permissions required for each recording. Host admission alone does not establish participant consent.' : 'MeetPilot is not registered yet. Use non-confidential test content until operator details and production safeguards are finalized.'}</p></div></div><div className="mp-legal-checks"><label className="mp-consent"><input type="checkbox" checked={checked} disabled={busy} onChange={e => setChecked(e.target.checked)} /><span>I agree to the <a href="/terms" target="_blank" rel="noopener noreferrer">Terms of Service</a> and acknowledge the <a href="/privacy" target="_blank" rel="noopener noreferrer">Privacy Policy</a> and <a href="/recording-policy" target="_blank" rel="noopener noreferrer">Recording Policy</a>. I will establish authorization, notify participants and obtain required permissions before recording or uploading. This acknowledgment is not other participants’ consent.</span></label></div>{!recognizesPolicyCopy(status.policies) && <p role="alert" className="mp-error-state">Update the app before acknowledging this policy revision.</p>}</>}{!status && !error && <p role="status"><Loader2 size={15} className="inline animate-spin" />Loading policies…</p>}{error && <div role="alert" className="mp-error-state"><p>{error}</p><button className="mp-button mp-button-secondary" disabled={busy} onClick={() => { if (pending.current) void load(pending.current); }}>Reload policies</button></div>}<div className="mp-modal-actions"><button className="mp-button mp-button-secondary" disabled={busy} onClick={cancel}>Not now</button><button className="mp-button mp-button-primary" disabled={!status || !checked || !recognizesPolicyCopy(status.policies) || busy} onClick={() => void agree()}>{busy ? 'Saving…' : 'Agree & continue'}</button></div></Modal>}</>;
}
