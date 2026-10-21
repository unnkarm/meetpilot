import { legalDocuments } from '../utils/legal';

export function LegalLinks({ newTab = false }: { newTab?: boolean }) {
  return <nav aria-label="Legal" className="mp-legal-links">{legalDocuments.map(doc => <a key={doc.id} href={`/${doc.id}`} target={newTab ? '_blank' : undefined} rel={newTab ? 'noopener noreferrer' : undefined}>{doc.title}{newTab && <span className="sr-only"> (opens in a new tab)</span>}</a>)}</nav>;
}

