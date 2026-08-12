import React, { useState } from 'react';
import { Bot, Github, Sparkles, Menu, X, ArrowRight } from 'lucide-react';
import { SignedIn, SignedOut, UserButton } from '@clerk/clerk-react';


import { MeetPilotLogo } from './Logo';

interface NavbarProps {
  onOpenGetStarted: () => void;
  onOpenWatchDemo: () => void;
  onOpenPricing: () => void;
  onOpenDocs: () => void;
  onOpenAbout: () => void;
  onOpenFeaturesModal: () => void;
  onOpenAuth: (mode?: 'signin' | 'signup') => void;
  onLaunchApp: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenGetStarted,
  onOpenPricing,
  onOpenDocs,
  onOpenAbout,
  onOpenFeaturesModal,
  onOpenAuth,
  onLaunchApp
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const scrollTo = (id: string) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-[#09090B]/90 border-b border-[#27272A] transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          <MeetPilotLogo className="h-9" />
        </div>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-1 text-xs font-medium text-slate-300">
          <button
            onClick={onOpenFeaturesModal}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[#18181b] transition-all cursor-pointer"
          >
            Features
          </button>
          <button
            onClick={() => scrollTo('how-it-works')}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[#18181b] transition-all cursor-pointer"
          >
            How it Works
          </button>
          <button
            onClick={onLaunchApp}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[#18181b] transition-all flex items-center gap-1.5 cursor-pointer text-[#8B5CF6] font-bold"
          >
            <span>App Workspace</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#8B5CF6] animate-pulse"></span>
          </button>
          <button
            onClick={onOpenPricing}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[#18181b] transition-all text-slate-400 hover:text-slate-200 flex items-center gap-1.5 cursor-pointer"
          >
            Pricing <span className="text-[10px] px-1.5 py-0.2 rounded bg-white/10 text-slate-300 font-mono">Coming Soon</span>
          </button>
          <button
            onClick={onOpenDocs}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[#18181b] transition-all cursor-pointer"
          >
            Docs
          </button>
          <button
            onClick={onOpenAbout}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[#18181b] transition-all cursor-pointer"
          >
            About
          </button>
        </nav>

        {/* Right Action Buttons */}
        <div className="hidden md:flex items-center gap-3">
          {import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ? (
            <>
              <SignedOut>
                <button
                  onClick={() => onOpenAuth('signin')}
                  className="text-xs font-bold text-slate-300 hover:text-white px-3.5 py-2 transition-colors cursor-pointer"
                >
                  Sign In
                </button>
              </SignedOut>
              <SignedIn>
                <UserButton afterSignOutUrl="/" />
              </SignedIn>
            </>
          ) : (
            <button
              onClick={() => onOpenAuth('signin')}
              className="text-xs font-bold text-slate-300 hover:text-white px-3.5 py-2 transition-colors cursor-pointer"
            >
              Sign In
            </button>
          )}

          <button
            onClick={onLaunchApp}
            className="relative group overflow-hidden px-4 py-2 rounded-xl text-xs font-bold text-white bg-[#8B5CF6] hover:bg-[#7c3aed] shadow-md shadow-[#8B5CF6]/20 transition-all duration-200 flex items-center gap-2 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-100 group-hover:rotate-12 transition-transform" />
            <span>Enter App</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>

        {/* Mobile menu trigger */}
        <div className="md:hidden flex items-center gap-2">
          <button
            onClick={onLaunchApp}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-[#8B5CF6] text-white"
          >
            Enter App
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-[#09090B]/95 backdrop-blur-2xl border-b border-[#27272A] px-4 pt-3 pb-6 space-y-3">
          <button
            onClick={() => { setMobileMenuOpen(false); onOpenFeaturesModal(); }}
            className="w-full text-left py-2 text-slate-200 text-sm font-medium"
          >
            Features
          </button>
          <button
            onClick={() => scrollTo('how-it-works')}
            className="w-full text-left py-2 text-slate-200 text-sm font-medium"
          >
            How it Works
          </button>
          <button
            onClick={() => { setMobileMenuOpen(false); onLaunchApp(); }}
            className="w-full text-left py-2 text-[#8B5CF6] text-sm font-bold"
          >
            Enter Workspace Application
          </button>
          <button
            onClick={() => { setMobileMenuOpen(false); onOpenPricing(); }}
            className="w-full text-left py-2 text-slate-300 text-sm font-medium flex items-center justify-between"
          >
            <span>Pricing</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-white/10 text-slate-300 font-mono">Coming Soon</span>
          </button>
          <button
            onClick={() => { setMobileMenuOpen(false); onOpenDocs(); }}
            className="w-full text-left py-2 text-slate-300 text-sm font-medium"
          >
            Docs
          </button>
          <button
            onClick={() => { setMobileMenuOpen(false); onOpenAbout(); }}
            className="w-full text-left py-2 text-slate-300 text-sm font-medium"
          >
            About
          </button>
          <div className="pt-2 border-t border-[#27272A] flex flex-col gap-2">
            <button
              onClick={() => { setMobileMenuOpen(false); onOpenAuth(); }}
              className="w-full py-2.5 rounded-xl bg-[#8B5CF6] text-white font-semibold text-sm text-center shadow-lg shadow-[#8B5CF6]/30"
            >
              Sign In
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
