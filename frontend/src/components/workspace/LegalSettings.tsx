import { useAuth } from '@clerk/clerk-react';
import useSWR from 'swr';
import { apiFetch } from '../../services/api';
import type { PolicyAcceptanceStatus } from '../../utils/legal';
import { LegalLinks } from '../LegalLinks';

export function LegalSettings() {
  const { getToken } = useAuth();
  const { data, error } = useSWR<PolicyAcceptanceStatus>('/api/v1/legal/acceptance', path => apiFetch<PolicyAcceptanceStatus>(path, { cache: 'no-store' }, getToken));
  return <section aria-label="Trust and policies" className="border-t border-line mt-4 pt-4 px-3.5"><h3 className="text-xs font-semibold mb-2">Trust & policies</h3><LegalLinks newTab /><p className="text-xs text-muted mt-3 leading-relaxed">{error ? 'Acknowledgment status unavailable. Your saved agreement has not been changed.' : !data ? 'Loading acknowledgment status…' : data.accepted ? `Acknowledged${data.accepted_at ? ` on ${new Date(data.accepted_at).toLocaleDateString()}` : ''}. No further prompts.` : 'A one-time acknowledgment appears when you start your first action.'}</p>{data?.accepted_versions && <p className="text-xs text-muted mt-2">Accepted Terms version: {data.accepted_versions.terms}. Current policies remain available above.</p>}</section>;
}
