import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { CheckCircle2, AlertCircle, Loader2, ArrowRight } from 'lucide-react';
import { MeetPilotLogo } from './Logo';
import { exchangeGoogleOAuthApi, exchangeZoomOAuthApi } from '../services/api';
import { oauthKey, validateOAuthAttempt, type OAuthProvider } from '../utils/integrationOAuth';
export function IntegrationCallback({ provider }: { provider: OAuthProvider }) {
  const { getToken, userId } = useAuth();
  const started = useRef(false);
  const [result, setResult] = useState<'connecting' | 'success' | 'error'>('connecting');
  const [message, setMessage] = useState('Completing your connection…');
  useEffect(() => {
    if (started.current || !userId) return;
    started.current = true;
    void (async () => {
      try {
        const params = new URLSearchParams(location.search);
        const attempt = validateOAuthAttempt(JSON.parse(sessionStorage.getItem(oauthKey(provider)) || 'null'), params.get('state'), userId);
        const code = params.get('code');
        // Clear credentials from the address bar as soon as they have been read.
        history.replaceState({}, '', location.pathname);
        if (params.has('error')) throw new Error('Authorization was declined. You can try again from Integrations.');
        if (!code) throw new Error('The provider did not return an authorization code.');
        const integration = await (provider === 'google' ? exchangeGoogleOAuthApi : exchangeZoomOAuthApi)(attempt.workspaceId, code, getToken);
        if (!integration.is_connected) throw new Error('The provider did not complete the connection. Please try again.');
        sessionStorage.removeItem(oauthKey(provider));
        setResult('success'); setMessage(`${provider === 'google' ? 'Google Calendar' : 'Zoom'} is connected to your workspace.`);
        window.opener?.postMessage({ type: 'meetpilot:integration-connected', provider, workspaceId: attempt.workspaceId }, location.origin);
      } catch (err) { history.replaceState({}, '', location.pathname); setResult('error'); setMessage(err instanceof Error ? err.message : 'Could not complete this connection.'); }
    })();
  }, [provider, getToken, userId]);
  return <div className="min-h-screen bg-canvas grid place-items-center p-6"><section className="bg-surface border border-line rounded-xl p-9 max-w-md w-full text-center space-y-5"><MeetPilotLogo className="h-8" /><div className="flex justify-center">{result === 'connecting' ? <Loader2 className="animate-spin text-brand" /> : result === 'success' ? <CheckCircle2 className="text-brand" /> : <AlertCircle className="text-rose-700" />}</div><h1 className="text-xl font-semibold">{result === 'success' ? 'You’re connected.' : result === 'error' ? 'Connection wasn’t completed.' : 'Connecting your workspace'}</h1><p role={result === 'error' ? 'alert' : 'status'} className="text-sm text-muted">{message}</p>{result !== 'connecting' && <a className="mp-button mp-button-primary" href="/app">Return to workspace <ArrowRight size={15} /></a>}{window.opener && result !== 'connecting' && <button className="block mx-auto text-sm text-muted" onClick={() => window.close()}>Close this window</button>}</section></div>;
}
