import { Modal } from '../Modal';
import { useId, useState } from 'react';
import { BadgeCheck, Check, Clock3, Copy, KeyRound, LoaderCircle, LockKeyhole, RefreshCw, Shield, UserCheck, UserCog, Users } from 'lucide-react';
import useSWR from 'swr';
import { apiFetch, createWorkspaceApi } from '../../services/api';
import { ApiWorkspace, ApiWorkspaceMember } from '../../types';
import { isWorkspaceManager } from '../../utils/workspacePermissions';

export interface JoinRequest {
  id: string; workspace_id: string; workspace_name: string; user_id: string;
  name: string; email: string; email_verified?: boolean; status: 'pending' | 'approved' | 'rejected' | 'removed'; created_at: string;
}
type Props = { getToken: () => Promise<string | null>; onChange: () => Promise<unknown> };

export function JoinRequestList({ requests, onEnter, disabled = false }: {
  requests: JoinRequest[]; onEnter: (workspaceId: string) => void; disabled?: boolean;
}) {
  return <div className="space-y-2 text-sm">
    {requests.map(r => <div key={r.id} className="rounded-xl border border-line p-3 text-ink space-y-2">
      <div className="flex flex-wrap justify-between gap-2"><span>{r.workspace_name}</span>
        <span className={r.status === 'approved' ? 'text-emerald-700' : 'text-amber-700'}>
          {r.status === 'approved' ? 'Approved' : r.status === 'rejected' ? 'Declined · contact your manager' : r.status === 'removed' ? 'Access removed · request fresh approval' : 'Waiting for manager approval'}
        </span>
      </div>
      {r.status === 'approved' && <button disabled={disabled} onClick={() => onEnter(r.workspace_id)} className="rounded-lg bg-emerald-700 px-3 py-2 text-on-brand disabled:opacity-50">Enter workspace</button>}
    </div>)}
  </div>;
}

export function WorkspaceOnboarding({ getToken, onEnter, loading, loadError, onRetry, onBack, onSignOut }: {
  getToken: Props['getToken']; onEnter: (workspaceId: string) => Promise<void>;
  loading: boolean; loadError?: string; onRetry: () => void; onBack: () => void; onSignOut: () => void;
}) {
  const [joining, setJoining] = useState(false);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const { data: requests, error: requestsError, mutate } = useSWR<JoinRequest[]>(!loading && !loadError ? '/api/v1/workspaces/join-requests' : null,
    path => apiFetch(path, {}, getToken), { refreshInterval: 10000 });
  const enter = async (workspaceId: string) => {
    setBusy(true); setError('');
    try { await onEnter(workspaceId); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not open workspace'); }
    finally { setBusy(false); }
  };
  return <main className="min-h-screen bg-canvas text-ink flex items-center justify-center p-6">
    <section className="w-full max-w-xl rounded-xl border border-line bg-surface p-6 space-y-5">
      <h1 className="text-2xl font-bold">Welcome to MeetPilot</h1>
      {loading ? <p role="status" className="text-sm text-muted">Loading your workspaces…</p> : loadError ? <>
        <p role="alert" className="text-sm text-rose-700">{loadError}</p>
        <button onClick={onRetry} className="rounded-lg bg-brand px-4 py-2 text-sm text-on-brand">Retry connection</button>
      </> : <>
        <p className="text-sm text-muted">Joining your team? Use your manager's code and wait for approval. Creating an organization? Create a workspace to become its owner.</p>
        <button onClick={() => setJoining(true)} className="rounded-xl bg-brand px-4 py-3 text-sm font-bold text-on-brand">Join Workspace with Code</button>
        <JoinRequestList requests={requests || []} onEnter={id => void enter(id)} disabled={busy} />
        {requestsError && <p role="alert" className="text-sm text-rose-700">Could not load join requests. <button onClick={() => void mutate()} className="underline">Retry</button></p>}
        <form onSubmit={async e => {
          e.preventDefault(); if (busy || !name.trim()) return;
          setBusy(true); setError('');
          try { const workspace = await createWorkspaceApi(name.trim(), getToken); await onEnter(workspace.id); }
          catch (err) { setError(err instanceof Error ? err.message : 'Could not create workspace'); }
          finally { setBusy(false); }
        }} className="space-y-3 border-t border-line pt-5">
          <label className="block text-sm text-ink">New organization workspace
            <input value={name} onChange={e => setName(e.target.value)} maxLength={255} required placeholder="Your team or company name" className="mt-2 w-full rounded-xl border border-line bg-surface p-3 text-ink" />
          </label>
          <button disabled={busy || !name.trim()} className="rounded-lg bg-line px-4 py-2 text-sm disabled:opacity-50">{busy ? 'Please wait…' : 'Create workspace'}</button>
        </form>
      </>}
      {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
      <div className="flex gap-4 text-sm text-muted"><button onClick={onBack}>Back to home</button><button onClick={onSignOut}>Sign out</button></div>
    </section>
    {joining && <JoinWorkspaceModal getToken={getToken} onChange={async () => { await mutate(); onRetry(); }} onEnter={onEnter} onClose={() => setJoining(false)} />}
  </main>;
}

export function JoinWorkspaceModal({ getToken, onChange, onClose, onEnter }: Props & { onClose: () => void; onEnter: (workspaceId: string) => Promise<void> }) {
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const { data: requests, error: requestsError, mutate } = useSWR<JoinRequest[]>('/api/v1/workspaces/join-requests',
    path => apiFetch(path, {}, getToken), { refreshInterval: 10000 });
  return <Modal label="Join workspace" onClose={onClose} busy={busy}>
    <section className="space-y-4">
      <h2 className="font-bold text-ink">Join an organization workspace</h2>
      <p className="text-sm text-muted">Enter the code shared by your manager. You can enter the workspace after a manager approves your request.</p>
      <form onSubmit={async e => {
        e.preventDefault(); setBusy(true); setError('');
        try { await apiFetch('/api/v1/workspaces/join', { method: 'POST', body: JSON.stringify({ code: code.trim() }) }, getToken); setCode(''); await mutate(); await onChange(); }
        catch (err) { setError(err instanceof Error ? err.message : 'Request failed'); }
        finally { setBusy(false); }
      }} className="space-y-3">
        <label className="block text-sm text-ink">Workspace join code
          <input value={code} onChange={e => setCode(e.target.value)} autoComplete="off" required minLength={16}
            className="mt-2 w-full rounded-xl border border-line bg-surface p-3 text-ink" />
        </label>
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
        <button disabled={busy || code.trim().length < 16} className="rounded-xl bg-brand px-4 py-2 text-sm text-on-brand disabled:opacity-50">{busy ? 'Sending…' : 'Request to join'}</button>
      </form>
      {requestsError && <p role="alert" className="text-sm text-rose-700">Could not load your requests. <button onClick={() => void mutate()} className="underline">Retry</button></p>}
      <JoinRequestList requests={requests || []} disabled={busy} onEnter={id => {
        setBusy(true); setError('');
        void onEnter(id).then(onClose).catch(err => setError(err instanceof Error ? err.message : 'Could not open workspace')).finally(() => setBusy(false));
      }} />
      <button onClick={onClose} className="text-sm text-muted">Close</button>
    </section>
  </Modal>;
}

export function WorkspaceAccessPanel({ workspace, getToken, onChange, members }: Props & { workspace: ApiWorkspace; members: ApiWorkspaceMember[] }) {
  const headingId = useId();
  const manager = isWorkspaceManager(workspace.current_role);
  const owner = workspace.current_role === 'owner';
  const roleLabel = owner ? 'Owner' : manager ? 'Manager' : 'Teammate';
  const editableMembers = members.filter(member => member.role !== 'owner');
  const [issuedCode, setIssuedCode] = useState<{ code: string; expires_at: string } | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [codeDisabled, setCodeDisabled] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const busy = pendingAction !== null;
  const path = `/api/v1/workspaces/${workspace.id}/join-requests`;
  const { data: requests, error: requestsError, isLoading, isValidating, mutate } = useSWR<JoinRequest[]>(manager && !workspace.is_demo ? path : null,
    url => apiFetch(url, {}, getToken), { refreshInterval: 15000 });
  const run = async (key: string, action: () => Promise<unknown>, success: string) => {
    if (busy) return;
    setPendingAction(key); setError(''); setNotice('');
    try { await action(); await mutate(); await onChange(); setNotice(success); }
    catch (err) { setError(err instanceof Error ? err.message : 'Action failed'); }
    finally { setPendingAction(null); }
  };
  const copyCode = async () => {
    if (!issuedCode) return;
    setError('');
    try { await navigator.clipboard.writeText(issuedCode.code); setCopied(true); setNotice('Join code copied to clipboard.'); }
    catch { setError('Could not copy automatically. Select the code and copy it manually.'); }
  };
  const dateLabel = (value: string) => new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  const initials = (name: string) => name.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase() || '?';
  return <section className="mp-access" aria-labelledby={headingId}>
    <header className="mp-access-header">
      <div className="mp-access-title"><span className="mp-access-icon"><Shield size={20} aria-hidden="true" /></span><div>
        <h3 id={headingId}>Workspace access</h3><p>Bring your team in. Keep access in your control.</p>
      </div></div>
      <span className="mp-access-role"><span>Your role</span><strong>{roleLabel}</strong></span>
    </header>

    {manager && !workspace.is_demo && <div className="mp-access-grid">
      <section className="mp-access-card" aria-label="Invite your team">
        <div className="mp-access-card-heading"><KeyRound size={17} aria-hidden="true" /><h4>Invite your team</h4><span className="mp-access-badge"><LockKeyhole size={11} aria-hidden="true" />Approval required</span></div>
        <p className="mp-access-description">Share a join code. Teammates request access, and a manager approves who gets in.</p>
        {issuedCode ? <div className="mp-access-code-box">
          <div className="mp-access-code-caption"><span>Workspace join code</span><span className="mp-access-ready"><span />Ready to share</span></div>
          <div className="mp-access-code-row"><code tabIndex={0} aria-label="Workspace join code">{issuedCode.code}</code>
            <button type="button" className="mp-button mp-button-primary" disabled={busy} onClick={() => void copyCode()}>{copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}{copied ? 'Copied' : 'Copy code'}</button>
          </div>
          <p className="mp-access-expiry"><Clock3 size={13} aria-hidden="true" />Expires {dateLabel(issuedCode.expires_at)}</p>
        </div> : <div className="mp-access-code-placeholder"><KeyRound size={22} aria-hidden="true" /><div><strong>{codeDisabled ? 'Join code disabled' : 'Invite with a join code'}</strong><p>{codeDisabled ? 'Generate a new code when you’re ready to invite more teammates.' : 'Generate a code to share privately with your team.'}</p></div></div>}
        <div className="mp-access-code-actions">
          <button type="button" disabled={busy} onClick={() => void run('generate', async () => {
            const code = await apiFetch<{ code: string; expires_at: string }>(`/api/v1/workspaces/${workspace.id}/join-code`, { method: 'POST' }, getToken);
            setIssuedCode(code); setCopied(false); setCodeDisabled(false);
          }, 'A new join code is ready to share.')} className={`mp-button ${issuedCode ? 'mp-button-secondary' : 'mp-button-primary'}`}>
            {pendingAction === 'generate' ? <LoaderCircle size={14} className="animate-spin" aria-hidden="true" /> : issuedCode ? <RefreshCw size={14} aria-hidden="true" /> : <KeyRound size={14} aria-hidden="true" />}
            {pendingAction === 'generate' ? 'Generating…' : issuedCode ? 'Replace code' : 'Generate join code'}
          </button>
          <button type="button" disabled={busy || codeDisabled} onClick={() => void run('disable', async () => {
            await apiFetch(`/api/v1/workspaces/${workspace.id}/join-code`, { method: 'DELETE' }, getToken);
            setIssuedCode(null); setCopied(false); setCodeDisabled(true);
          }, 'Join code disabled. New requests need a fresh code.')} className="mp-button mp-access-disable">{pendingAction === 'disable' ? 'Disabling…' : 'Disable code'}</button>
        </div>
        <p className="mp-access-note">Valid for 30 days. Generating a new code invalidates any previous code.{issuedCode && ' Copy this code before leaving; it is shown only here.'}</p>
      </section>

      <section className="mp-access-card" aria-label="Pending join requests">
        <div className="mp-access-card-heading"><UserCheck size={17} aria-hidden="true" /><h4>Join requests</h4><span className="mp-access-count" aria-label={requestsError || isLoading ? 'Request count unavailable' : `${requests?.length ?? 0} pending requests`}>{requestsError || isLoading ? '—' : requests?.length ?? 0}</span>
          <button type="button" className="mp-icon-button" aria-label="Refresh join requests" title="Refresh requests" disabled={isValidating || busy} onClick={() => void mutate()}><RefreshCw size={14} className={isValidating ? 'animate-spin' : ''} aria-hidden="true" /></button>
        </div>
        <p className="mp-access-description">Review each person before giving them workspace access.</p>
        {isLoading && <div className="mp-access-empty" role="status"><LoaderCircle size={22} className="animate-spin" aria-hidden="true" /><p>Loading join requests…</p></div>}
        {requestsError ? <div className="mp-access-empty" role="alert"><p>Could not load join requests.</p><button type="button" onClick={() => void mutate()} className="mp-text-button">Try again</button></div> : !isLoading && requests?.length === 0 ? <div className="mp-access-empty"><span className="mp-access-empty-icon"><UserCheck size={24} aria-hidden="true" /></span><strong>You’re all caught up</strong><p>New requests will appear here when teammates use your join code.</p></div> : !isLoading && <div className="mp-access-requests">
          {requests?.map(request => <article key={request.id} className="mp-access-request">
            <div className="mp-access-person"><span className="mp-access-avatar" aria-hidden="true">{initials(request.name)}</span><div><strong>{request.name}</strong><p>{request.email}</p></div></div>
            <div className="mp-access-request-meta"><span className={`mp-access-verification ${request.email_verified ? 'is-verified' : ''}`}>{request.email_verified && <BadgeCheck size={12} aria-hidden="true" />}{request.email_verified ? 'Verified email' : 'Email not verified'}</span><span>Requested {dateLabel(request.created_at)}</span></div>
            {!request.email_verified && <p className="mp-access-note">Confirm this person’s identity before approving.</p>}
            <div className="mp-access-request-actions">
              <button type="button" disabled={busy} aria-label={`Approve ${request.name}`} onClick={() => void run(`approve-${request.id}`, () => apiFetch(`${path}/${request.id}/review`, { method: 'POST', body: JSON.stringify({ decision: 'approve' }) }, getToken), `${request.name} now has workspace access.`)} className="mp-button mp-button-primary">{pendingAction === `approve-${request.id}` ? 'Approving…' : 'Approve'}</button>
              <button type="button" disabled={busy} aria-label={`Decline ${request.name}`} onClick={() => void run(`reject-${request.id}`, () => apiFetch(`${path}/${request.id}/review`, { method: 'POST', body: JSON.stringify({ decision: 'reject' }) }, getToken), `${request.name}’s request was declined.`)} className="mp-button mp-button-secondary">{pendingAction === `reject-${request.id}` ? 'Declining…' : 'Decline'}</button>
            </div>
          </article>)}
        </div>}
      </section>
    </div>}
    {manager && workspace.is_demo && <p className="mp-access-demo">Join codes are unavailable in this sample workspace.</p>}

    <section className="mp-access-permissions" aria-label="Role permissions">
      <h4>Who can do what</h4>
      <div className="mp-access-permission-grid">
        <div><Shield size={16} aria-hidden="true" /><div><strong>Owner</strong><p>Full workspace control, including manager roles.</p></div></div>
        <div><UserCog size={16} aria-hidden="true" /><div><strong>Managers</strong><p>Manage knowledge, membership, and task assignments.</p></div></div>
        <div><Users size={16} aria-hidden="true" /><div><strong>Teammates</strong><p>Read all workspace meetings, use knowledge, and update their assigned tasks.</p></div></div>
      </div>
    </section>
    {owner && <section className="mp-access-member-roles" aria-label="Member roles">
      <div className="mp-access-roles-heading"><div><h4>Member roles</h4><p>Only the owner can change who manages this workspace.</p></div><span className="mp-access-badge">Owner only</span></div>
      {editableMembers.length ? <div className="mp-access-role-list">{editableMembers.map(member => <div key={member.user_id} className="mp-access-role-row">
        <div className="mp-access-person"><span className="mp-access-avatar" aria-hidden="true">{initials(member.name)}</span><div><strong>{member.name}</strong><p>{member.email}</p></div></div>
        <select aria-label={`Role for ${member.name}`} value={member.role} disabled={busy} onChange={event => {
          const role = event.target.value;
          void run(`role-${member.user_id}`, () => apiFetch(`/api/v1/workspaces/${workspace.id}/members/${member.user_id}`, { method: 'PATCH', body: JSON.stringify({ role }) }, getToken), `Role updated for ${member.name}.`);
        }}><option value="member">Teammate</option><option value="admin">Manager</option></select>
      </div>)}</div> : <p className="mp-access-role-empty"><Users size={16} aria-hidden="true" />Role controls will appear here when teammates join your workspace.</p>}
    </section>}
    {notice && <p role="status" className="mp-access-feedback"><Check size={15} aria-hidden="true" />{notice}</p>}
    {error && <p role="alert" className="mp-access-feedback is-error">{error}</p>}
  </section>;
}
