import React from 'react';
import { X, Bot, Shield, AlertTriangle } from 'lucide-react';
import { SignIn, SignUp } from '@clerk/clerk-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: 'signin' | 'signup';
}

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

export const CLERK_APPEARANCE = {
  layout: {
    socialButtonsVariant: 'blockButton' as const,
    socialButtonsPlacement: 'top' as const,
    showOptionalFields: false,
  },
  variables: {
    colorPrimary: '#8B5CF6',
    colorBackground: '#121217',
    colorText: '#FFFFFF',
    colorTextSecondary: '#94A3B8',
    colorInputBackground: '#181822',
    colorInputText: '#FFFFFF',
    colorNeutral: '#FFFFFF',
    colorDanger: '#EF4444',
    colorSuccess: '#10B981',
    colorWarning: '#F59E0B',
    borderRadius: '0.75rem',
    fontFamily: 'Plus Jakarta Sans, Inter, system-ui, -apple-system, sans-serif',
    fontSize: '0.875rem',
  },
  elements: {
    rootBox: 'w-full',
    cardBox: 'bg-transparent shadow-none border-0 p-0 w-full',
    card: 'bg-transparent shadow-none border-0 p-0 w-full',
    headerTitle: 'hidden',
    headerSubtitle: 'hidden',
    socialButtons: 'w-full pt-3 mb-2.5',
    socialButtonsIconButtonGroup: 'w-full',
    socialButtonsBlockButton:
      'bg-[#1A1A22] border border-[#2D2D3B] hover:bg-[#242430] hover:border-[#8B5CF6] text-white font-semibold transition-all duration-150 py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-2 shadow-sm text-center relative overflow-hidden h-11 w-full',
    socialButtonsBlockButton__google: 'w-full',
    socialButtonsBlockButton__github: 'w-full',
    socialButtonsBlockButton__slack: 'w-full',
    socialButtonsProvider__google: 'w-full',
    socialButtonsProvider__github: 'w-full',
    socialButtonsProvider__slack: 'w-full',
    socialButtonsBlockButtonText: 'text-white font-semibold text-xs tracking-wide',
    socialButtonsBlockButtonArrow: 'text-slate-400',
    socialButtonsIconButton:
      'bg-[#1A1A22] border border-[#2D2D3B] hover:bg-[#242430] hover:border-[#8B5CF6] text-white p-2.5 rounded-xl transition-all h-11 w-full flex items-center justify-center gap-2',
    socialButtonsIconButton__google: 'w-full',
    socialButtonsIconButton__github: 'w-full',
    socialButtonsIconButton__slack: 'w-full',
    socialButtonsBlockButtonBadge:
      'bg-[#8B5CF6] text-white text-[10px] font-bold px-2 py-0.5 rounded-full absolute right-3 top-1/2 -translate-y-1/2 shadow-sm leading-tight pointer-events-none',
    dividerRow: 'my-2.5 w-full flex items-center justify-center col-span-2',
    dividerLine: 'bg-[#3F3F50] h-px',
    dividerText: 'text-[10px] font-mono uppercase tracking-widest text-slate-400 bg-[#121217] px-2.5 font-bold',
    formField: 'mb-2.5 w-full',
    formFieldLabel: 'text-xs font-semibold text-slate-200 mb-1 block',
    formFieldInput:
      'bg-[#181822] border border-[#363648] focus:border-[#8B5CF6] focus:ring-2 focus:ring-[#8B5CF6]/25 text-white placeholder:text-slate-400 rounded-xl px-3.5 py-2.5 text-xs transition-all outline-none w-full font-medium h-11',
    formButtonPrimary:
      'bg-gradient-to-r from-[#8B5CF6] to-[#7C3AED] hover:from-[#7C3AED] hover:to-[#6D28D9] text-white font-bold text-xs h-11 px-4 rounded-xl shadow-lg shadow-[#8B5CF6]/25 hover:shadow-[#8B5CF6]/40 transition-all duration-150 cursor-pointer active:scale-[0.99] w-full mt-2.5',
    footerAction: 'mt-2.5 text-center flex items-center justify-center gap-1.5',
    footerActionText: 'text-xs text-slate-400',
    footerActionLink: 'text-xs font-bold text-[#8B5CF6] hover:text-[#A78BFA] transition-colors ml-1',
    identityPreview: 'bg-[#1A1A22] border border-[#2D2D3B] rounded-xl p-3',
    identityPreviewText: 'text-white font-semibold text-xs',
    identityPreviewEditButton: 'text-xs font-bold text-[#8B5CF6] hover:text-[#A78BFA]',
    formFieldAction: 'text-xs font-medium text-[#8B5CF6] hover:text-[#A78BFA]',
    formFieldSuccessText: 'text-xs text-emerald-400 font-medium',
    formFieldErrorText: 'text-xs text-rose-400 font-medium mt-1',
    alert: 'bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl text-xs p-3',
    badge: 'bg-[#8B5CF6]/20 border border-[#8B5CF6]/40 text-[#8B5CF6] text-[10px] font-mono px-2 py-0.5 rounded-full font-bold',
    footer: 'border-t border-[#272733] pt-3 mt-3 pb-1 flex flex-col items-center gap-1.5',
  },
};

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  initialMode = 'signin',
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/85 backdrop-blur-xl animate-fadeIn overflow-y-auto">
      
      {/* Outer Card Container with clean containment */}
      <div className="relative w-full max-w-[520px] my-auto max-h-[92vh] overflow-hidden rounded-3xl bg-[#121217] border border-[#272733] shadow-[0_0_90px_-20px_rgba(139,92,246,0.4)] p-6 sm:p-8 flex flex-col">
        
        {/* Ambient Top Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-24 bg-gradient-to-b from-[#8B5CF6]/25 to-transparent blur-3xl pointer-events-none" />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-3.5 right-3.5 z-20 p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          aria-label="Close modal"
        >
          <X className="w-4 h-4" />
        </button>

        {!PUBLISHABLE_KEY ? (
          /* ── No Clerk Key Setup ── */
          <div className="flex flex-col items-center text-center gap-3 relative z-10 py-4">
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-white mb-1">Clerk Key Not Configured</h3>
              <p className="text-xs text-slate-400">
                Add your Clerk Publishable Key to <code className="bg-white/10 px-1 py-0.5 rounded text-[#8B5CF6]">frontend/.env</code>.
              </p>
            </div>
            <div className="w-full bg-[#1A1A22] border border-[#2D2D3B] rounded-xl p-2.5 text-left font-mono text-[11px] text-slate-300 select-all">
              VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
            </div>
          </div>
        ) : (
          /* ── Seamless Clerk Auth Card ── */
          <div className="relative z-10 flex flex-col">
            
            {/* Top Brand Pill */}
            <div className="flex items-center justify-between pb-3.5 mb-2 border-b border-[#272733]/70">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-xl bg-[#8B5CF6] p-px shadow-md shadow-[#8B5CF6]/30">
                  <div className="w-full h-full bg-[#121217] rounded-[10px] flex items-center justify-center">
                    <Bot className="w-3.5 h-3.5 text-[#8B5CF6]" />
                  </div>
                </div>
                <span className="font-extrabold text-sm text-white tracking-tight">MeetPilot AI</span>
              </div>
            </div>

            {/* Embedded Clerk Form */}
            <div className="w-full">
              {initialMode === 'signup' ? (
                <SignUp
                  routing="hash"
                  fallbackRedirectUrl="/"
                  appearance={CLERK_APPEARANCE}
                />
              ) : (
                <SignIn
                  routing="hash"
                  fallbackRedirectUrl="/"
                  appearance={CLERK_APPEARANCE}
                />
              )}
            </div>

          </div>
        )}

      </div>
    </div>
  );
};
