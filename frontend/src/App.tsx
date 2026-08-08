import React, { useState, useEffect } from 'react';
import { useUser } from '@clerk/clerk-react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { TrustedBy } from './components/TrustedBy';
import { ProblemSection } from './components/ProblemSection';
import { SolutionSection } from './components/SolutionSection';
import { HowItWorks } from './components/HowItWorks';
import { DashboardPreview } from './components/DashboardPreview';
import { FeatureGrid } from './components/FeatureGrid';
import { AIChatDemo } from './components/AIChatDemo';
import { CTASection } from './components/CTASection';
import { Footer } from './components/Footer';

import { GetStartedModal } from './components/GetStartedModal';
import { WatchDemoModal } from './components/WatchDemoModal';
import { PricingModal } from './components/PricingModal';
import { DocsDrawer } from './components/DocsDrawer';
import { PrivacyModal } from './components/PrivacyModal';
import { AboutModal } from './components/AboutModal';
import { AuthModal } from './components/AuthModal';
import { FeaturesModal } from './components/FeaturesModal';
import { AppWorkspace } from './components/AppWorkspace';
import { ProtectedRoute } from './components/ProtectedRoute';

export default function App() {
  const { isSignedIn } = useUser();
  const [viewMode, setViewMode] = useState<'landing' | 'app'>('landing');

  const [getStartedOpen, setGetStartedOpen] = useState(false);
  const [watchDemoOpen, setWatchDemoOpen] = useState(false);
  const [pricingOpen, setPricingOpen] = useState(false);
  const [docsOpen, setDocsOpen] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin');
  const [featuresOpen, setFeaturesOpen] = useState(false);

  // Handle direct URL routes (/sign-up, /sign-in, /app, etc.)
  useEffect(() => {
    const handleRoute = () => {
      const path = window.location.pathname.toLowerCase();
      const hash = window.location.hash.toLowerCase();

      if (path.includes('sign-up') || path.includes('signup') || path.includes('register') || hash.includes('sign-up')) {
        setAuthMode('signup');
        setAuthOpen(true);
      } else if (path.includes('sign-in') || path.includes('signin') || path.includes('login') || hash.includes('sign-in')) {
        setAuthMode('signin');
        setAuthOpen(true);
      } else if (path.includes('/app') || path.includes('/workspace') || path.includes('/dashboard')) {
        if (isSignedIn) {
          setViewMode('app');
        } else {
          setAuthMode('signin');
          setAuthOpen(true);
        }
      }
    };

    handleRoute();
    window.addEventListener('popstate', handleRoute);
    return () => window.removeEventListener('popstate', handleRoute);
  }, [isSignedIn]);

  // Auto-launch workspace when Clerk signs user in
  useEffect(() => {
    if (isSignedIn && viewMode === 'landing') {
      setAuthOpen(false);
      setViewMode('app');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    if (!isSignedIn && viewMode === 'app') {
      setViewMode('landing');
    }
  }, [isSignedIn, viewMode]);

  const handleOpenAuth = (mode: 'signin' | 'signup' = 'signin') => {
    setAuthMode(mode);
    setAuthOpen(true);
  };

  const handleLaunchWorkspace = () => {
    if (!isSignedIn) {
      handleOpenAuth('signin');
      return;
    }

    setViewMode('app');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (viewMode === 'app') {
    return (
      <ProtectedRoute>
        <AppWorkspace onBackToLanding={() => setViewMode('landing')} />
      </ProtectedRoute>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090B] text-slate-100 font-sans selection:bg-[#8B5CF6]/30 selection:text-white antialiased overflow-x-hidden">
      
      {/* Top Navbar */}
      <Navbar
        onOpenGetStarted={() => setGetStartedOpen(true)}
        onOpenWatchDemo={() => setWatchDemoOpen(true)}
        onOpenPricing={() => setPricingOpen(true)}
        onOpenDocs={() => setDocsOpen(true)}
        onOpenAbout={() => setAboutOpen(true)}
        onOpenFeaturesModal={() => setFeaturesOpen(true)}
        onOpenAuth={(mode) => handleOpenAuth(mode || 'signin')}
        onLaunchApp={handleLaunchWorkspace}
      />

      <main>
        {/* 1 & 2. Hero Section */}
        <Hero
          onOpenGetStarted={() => setGetStartedOpen(true)}
          onOpenWatchDemo={() => setWatchDemoOpen(true)}
        />

        {/* 3. Trusted By / Built With */}
        <TrustedBy />

        {/* 4. Problem Section */}
        <ProblemSection />

        {/* 5. Solution Section */}
        <SolutionSection
          onOpenGetStarted={() => setGetStartedOpen(true)}
        />

        {/* 6. How It Works */}
        <HowItWorks />

        {/* 7. Dashboard Preview (Interactive Workspace Replica) */}
        <DashboardPreview />

        {/* 8. Feature Grid */}
        <FeatureGrid />

        {/* 9. AI Chat Demo */}
        <AIChatDemo />

        {/* 10. CTA Section */}
        <CTASection
          onOpenGetStarted={() => setGetStartedOpen(true)}
        />
      </main>

      {/* 11. Footer */}
      <Footer
        onOpenPrivacy={() => setPrivacyOpen(true)}
        onOpenDocs={() => setDocsOpen(true)}
        onOpenPricing={() => setPricingOpen(true)}
      />

      {/* Modals & Overlays */}
      <GetStartedModal
        isOpen={getStartedOpen}
        onClose={() => setGetStartedOpen(false)}
        onLaunchWorkspace={handleLaunchWorkspace}
      />

      <WatchDemoModal
        isOpen={watchDemoOpen}
        onClose={() => setWatchDemoOpen(false)}
      />

      <PricingModal
        isOpen={pricingOpen}
        onClose={() => setPricingOpen(false)}
        onOpenGetStarted={() => setGetStartedOpen(true)}
      />

      <DocsDrawer
        isOpen={docsOpen}
        onClose={() => setDocsOpen(false)}
      />

      <PrivacyModal
        isOpen={privacyOpen}
        onClose={() => setPrivacyOpen(false)}
      />

      <AboutModal
        isOpen={aboutOpen}
        onClose={() => setAboutOpen(false)}
        onOpenGetStarted={() => setGetStartedOpen(true)}
      />

      <AuthModal
        isOpen={authOpen}
        onClose={() => setAuthOpen(false)}
        initialMode={authMode}
      />

      <FeaturesModal
        isOpen={featuresOpen}
        onClose={() => setFeaturesOpen(false)}
        onOpenGetStarted={() => setGetStartedOpen(true)}
      />

    </div>
  );
}
