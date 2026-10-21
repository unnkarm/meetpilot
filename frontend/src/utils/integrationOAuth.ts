import { getGoogleAuthUrlApi, getZoomAuthUrlApi } from '../services/api';
export type OAuthProvider = 'google' | 'zoom';
export interface OAuthAttempt { state: string; workspaceId: string; actorId: string; createdAt: number }
export const oauthKey = (provider: OAuthProvider) => `meetpilot:oauth:${provider}`;
export function validateOAuthAttempt(attempt: OAuthAttempt | null, state: string | null, actorId: string, now = Date.now()): OAuthAttempt {
  if (!attempt || !state || attempt.state !== state || !attempt.workspaceId || attempt.actorId !== actorId || now - attempt.createdAt > 600000 || now < attempt.createdAt) throw new Error('This connection request has expired or does not match your account. Start again from Integrations.');
  return attempt;
}
export function beginIntegrationOAuth(provider: OAuthProvider, workspaceId: string, actorId: string, getToken: () => Promise<string | null>) {
  const attempt: OAuthAttempt = { state: crypto.randomUUID(), workspaceId, actorId, createdAt: Date.now() };
  sessionStorage.setItem(oauthKey(provider), JSON.stringify(attempt));
  // Open synchronously from the click, before the API request, to avoid popup blocking.
  const popup = window.open('', 'meetpilot-oauth', 'width=560,height=720');
  const ready = (async () => {
    try {
      const { url } = await (provider === 'google' ? getGoogleAuthUrlApi : getZoomAuthUrlApi)(workspaceId, getToken);
      const target = new URL(url);
      const expectedHost = provider === 'google' ? 'accounts.google.com' : 'zoom.us';
      if (target.protocol !== 'https:' || target.hostname !== expectedHost) throw new Error('The server returned an invalid authorization URL.');
      target.searchParams.set('state', attempt.state);
      if (popup) { if (popup.closed) throw new Error('Authorization window was closed. Try connecting again.'); popup.location.href = target.toString(); }
      else window.location.assign(target.toString());
    } catch (err) { sessionStorage.removeItem(oauthKey(provider)); popup?.close(); throw err; }
  })();
  return { popup, ready };
}
