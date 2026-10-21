import { SignIn, SignUp } from '@clerk/clerk-react';
import { MeetPilotLogo } from './Logo';
import { Modal } from './Modal';
import { LegalLinks } from './LegalLinks';
import { useTheme } from './ThemeProvider';
import { paletteColor, type ColorPalette, type ResolvedTheme } from '../utils/theme';
export const clerkAppearance = (theme: ResolvedTheme, palette: ColorPalette) => ({
  layout: { socialButtonsVariant: 'blockButton' as const, socialButtonsPlacement: 'top' as const, showOptionalFields: false },
  variables: { colorPrimary: paletteColor(palette, theme), colorBackground: theme === 'dark' ? '#11151c' : '#fcf8ef', colorText: theme === 'dark' ? '#e3ecf3' : '#1d303e', colorTextSecondary: theme === 'dark' ? '#a0b1bf' : '#5b6873', colorInputBackground: theme === 'dark' ? '#090b10' : '#fcf8ef', colorInputText: theme === 'dark' ? '#e3ecf3' : '#1d303e', colorNeutral: theme === 'dark' ? '#e3ecf3' : '#1d303e', colorDanger: theme === 'dark' ? '#f4a0ac' : '#b53940', colorSuccess: theme === 'dark' ? '#75d7bf' : '#176b5e', borderRadius: '0.5rem', fontFamily: 'Inter, system-ui, sans-serif', fontSize: '0.875rem' },
  elements: { rootBox: 'w-full', cardBox: 'shadow-none border-0 w-full', card: 'shadow-none border-0 p-0 w-full', socialButtonsBlockButton: 'border border-line rounded-lg bg-surface text-ink hover:bg-surface-muted', formFieldInput: 'border border-line rounded-lg bg-surface text-ink', formButtonPrimary: 'bg-brand text-on-brand rounded-lg shadow-none', footer: 'bg-surface', footerActionLink: 'text-brand', headerTitle: 'text-ink font-semibold', headerSubtitle: 'text-muted' },
});
export function AuthModal({ isOpen, onClose, initialMode = 'signin' }: { isOpen: boolean; onClose: () => void; initialMode?: 'signin' | 'signup' }) {
  const { theme, palette } = useTheme();
  const CLERK_APPEARANCE = clerkAppearance(theme, palette);
  if (!isOpen) return null;
  return <Modal label={initialMode === 'signup' ? 'Create your MeetPilot account' : 'Sign in to MeetPilot'} onClose={onClose} className="mp-auth-modal"><div className="mb-7"><MeetPilotLogo className="h-8" /></div><LegalLinks newTab />{!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ? <div role="alert"><h2 className="mp-modal-title">Sign-in is unavailable</h2><p className="mp-modal-description">Authentication has not been configured for this deployment. Contact the workspace operator.</p></div> : initialMode === 'signup' ? <SignUp routing="hash" fallbackRedirectUrl="/app" appearance={CLERK_APPEARANCE} /> : <SignIn routing="hash" fallbackRedirectUrl="/app" appearance={CLERK_APPEARANCE} />}</Modal>;
}
