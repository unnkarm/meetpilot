import { SignIn, useAuth } from '@clerk/clerk-react';
import { Loader2 } from 'lucide-react';
import { MeetPilotLogo } from './Logo';
import { clerkAppearance } from './AuthModal';
import { useTheme } from './ThemeProvider';
import { SWRConfig } from 'swr';
import { LegalActionProvider } from './LegalActionProvider';
import { LegalLinks } from './LegalLinks';
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { theme, palette } = useTheme();
  const CLERK_APPEARANCE = clerkAppearance(theme, palette);
  const { isLoaded, isSignedIn, userId } = useAuth();
  if (!isLoaded) return <div className="min-h-screen bg-canvas flex items-center justify-center flex-col gap-5"><MeetPilotLogo className="h-9" /><p role="status" className="flex gap-2 items-center text-sm text-muted"><Loader2 size={15} className="animate-spin" />Loading your workspace…</p></div>;
  if (!isSignedIn) return <div className="min-h-screen bg-canvas flex items-center justify-center p-6"><div className="w-full max-w-md rounded-xl bg-surface border border-line p-8 shadow-sm"><div className="mb-8"><MeetPilotLogo className="h-8" /></div><SignIn routing="hash" fallbackRedirectUrl="/app" appearance={CLERK_APPEARANCE} /><LegalLinks newTab /></div></div>;
  return <SWRConfig key={userId} value={{ provider: () => new Map() }}><LegalActionProvider key={userId}>{children}</LegalActionProvider></SWRConfig>;
}
