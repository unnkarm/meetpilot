// Registered only in an authenticated workspace. Nothing runs at registration.
let requester: (() => Promise<void>) | null = null;

export class PolicyActionCancelled extends Error {
  constructor() { super('Action cancelled.'); this.name = 'PolicyActionCancelled'; }
}

export function registerPolicyRequester(next: () => Promise<void>) {
  requester = next;
  return () => { if (requester === next) requester = null; };
}

export async function ensurePolicyAcceptance(): Promise<void> {
  if (!requester) throw new Error('Open your workspace to continue.');
  await requester();
}

export function requiresPolicyAcceptance(endpoint: string, method = 'GET') {
  const path = new URL(endpoint, 'http://meetpilot.invalid').pathname;
  if (/^\/api\/v1\/(legal|auth)(\/|$)/.test(path)) return false;
  // OAuth return completes the user's already-initiated exchange without a prompt.
  if (/^\/api\/v1\/integrations\/(google|zoom)\/callback$/.test(path)) return false;
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())) return true;
  return path === '/api/v1/search';
}
