import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { useUser } from '@clerk/clerk-react';
import { LandingPage } from './components/LandingPage';
import { ProductInfoDialog } from './components/ProductInfoDialog';
import { AuthModal } from './components/AuthModal';
const AppWorkspace = lazy(() => import('./components/AppWorkspace').then(module => ({ default: module.AppWorkspace })));
import { IntegrationCallback } from './components/IntegrationCallback';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LegalPage } from './components/LegalPage';
import { legalDocuments } from './utils/legal';

export default function App() {
  const { isSignedIn } = useUser();
  const [path, setPath] = useState(window.location.pathname.toLowerCase().replace(/\/$/, '') || '/');
  const [view, setView] = useState<'landing' | 'app'>('landing');
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin');
  const [info, setInfo] = useState<'guide' | null>(null);
  const callbackProvider = path.match(/^\/oauth\/(google|zoom)\/callback$/)?.[1] as 'google' | 'zoom' | undefined;
  const legalDocument = legalDocuments.find(doc => path === `/${doc.id}`)?.id;
  const previousSignedIn = useRef<boolean | undefined>(undefined);
  const closeInfo = useCallback(() => setInfo(null), []);
  useEffect(() => {
    function route() {
      const path = window.location.pathname.toLowerCase();
      setPath(path.replace(/\/$/, '') || '/');
      if (/sign-up|signup|register/.test(path)) { setAuthMode('signup'); setAuthOpen(true); }
      else if (/sign-in|signin|login/.test(path)) { setAuthMode('signin'); setAuthOpen(true); }
      else if (/^\/(app|workspace|dashboard)(\/|$)/.test(path)) setView('app');
      else setView('landing');
    }
    route(); window.addEventListener('popstate', route);
    return () => window.removeEventListener('popstate', route);
  }, []);
  useEffect(() => {
    // A new sign-in opens the workspace; returning home remains possible afterwards.
    if (!callbackProvider && !legalDocument && isSignedIn && !previousSignedIn.current) { setAuthOpen(false); setView('app'); setPath('/app'); window.history.replaceState({}, '', '/app'); }
    if (!legalDocument && isSignedIn === false && previousSignedIn.current) { setView('landing'); setPath('/'); window.history.replaceState({}, '', '/'); }
    previousSignedIn.current = isSignedIn;
  }, [isSignedIn, callbackProvider, legalDocument]);
  const launch = () => {
    setInfo(null);
    if (!isSignedIn) { setAuthMode('signin'); setAuthOpen(true); return; }
    setView('app'); setPath('/app'); window.history.pushState({}, '', '/app'); window.scrollTo(0, 0);
  };
  if (legalDocument) return <LegalPage document={legalDocument} />;
  if (callbackProvider) return <ProtectedRoute><IntegrationCallback provider={callbackProvider} /></ProtectedRoute>;
  if (view === 'app') return <ProtectedRoute><Suspense fallback={<div role="status" className="mp-empty min-h-screen">Loading workspace…</div>}><AppWorkspace onBackToLanding={() => { setView('landing'); setPath('/'); window.history.pushState({}, '', '/'); window.scrollTo(0, 0); }} /></Suspense></ProtectedRoute>;
  return <><LandingPage signedIn={!!isSignedIn} onLaunch={launch} onSignIn={() => { setAuthMode('signin'); setAuthOpen(true); }} onSignUp={() => { setAuthMode('signup'); setAuthOpen(true); }} onGuide={() => setInfo('guide')} /><AuthModal isOpen={authOpen} onClose={() => setAuthOpen(false)} initialMode={authMode} /><ProductInfoDialog mode={info} onClose={closeInfo} onLaunch={launch} /></>;
}
