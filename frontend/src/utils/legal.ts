// Bump together with backend/app/services/legal_policies.py when copy changes.
export const POLICY_VERSION = '2026-10-12.1';
export type LegalDocument = 'terms' | 'privacy' | 'recording-policy';
export const legalDocuments: { id: LegalDocument; title: string; description: string }[] = [
  { id: 'terms', title: 'Terms of Service', description: 'Your responsibilities and the limited permission MeetPilot needs to process your content.' },
  { id: 'privacy', title: 'Privacy Policy', description: 'What the service processes, who can access it and how to request control over your information.' },
  { id: 'recording-policy', title: 'Recording Policy', description: 'Authorization, participant notice and responsible use of meeting recording and AI assistance.' },
];
export interface PolicyMetadata {
  versions: { terms: string; privacy: string; recording: string };
  operator: { name: string; address: string; privacy_email: string; jurisdiction: string; processing: string; retention: string };
  published: boolean;
  bundle: string;
}
export interface PolicyAcceptanceStatus { policies: PolicyMetadata; accepted: boolean; accepted_at: string | null; accepted_versions?: PolicyMetadata['versions'] | null; accepted_bundle?: string | null }
export function recognizesPolicyCopy(metadata: PolicyMetadata) {
  return Object.values(metadata.versions).every(version => version === POLICY_VERSION);
}
