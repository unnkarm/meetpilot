import { Loader2, Shield } from 'lucide-react';
import { MeetPilotLogo } from './Logo';
import { CLERK_APPEARANCE } from './AuthModal';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * ProtectedRoute: Renders children only for authenticated users.
 * While Clerk is loading → show spinner.
 * If unauthenticated → show embedded Clerk sign-in wall.
 */
const isProduction = import.meta.env.PROD;

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isLoaded, isSignedIn } = useAuth();

  // Clerk hasn't resolved session yet
  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-[#09090B] flex items-center justify-center flex-col gap-4">
        <MeetPilotLogo className="h-14 justify-center" iconOnly={true} />
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 text-[#8B5CF6] animate-spin" />
          <p className="text-xs text-slate-400 font-mono">Verifying secure session...</p>
        </div>
      </div>
    );
  }

  // User is NOT authenticated → show sign-in wall
  if (!isSignedIn) {
    return (
      <div className="min-h-screen bg-[#09090B] flex items-center justify-center p-3 sm:p-4 relative overflow-y-auto">
        {/* Ambient Radial Background */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(139,92,246,0.18),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(14,165,233,0.10),transparent_30%)]" />
        
        <div className="w-full max-w-[480px] my-auto max-h-[94vh] relative z-10">
          
          {/* Card Container with clean containment and uniform border-radius */}
          <div
            className={`rounded-2xl bg-[#121217] border border-[#272733] p-6 sm:p-8 sm:pb-9 shadow-[0_0_90px_-20px_rgba(139,92,246,0.4)] relative overflow-hidden flex flex-col ${
              isProduction ? 'is-production' : 'is-development'
            }`}
          >
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-24 bg-gradient-to-b from-[#8B5CF6]/20 to-transparent blur-2xl pointer-events-none" />
            
            {/* Top Brand Header */}
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-[#272733]/80 relative z-10">
              <MeetPilotLogo className="h-8" />
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#8B5CF6]/10 border border-[#8B5CF6]/20 text-[10px] font-semibold text-[#A78BFA]">
                <Shield className="w-3 h-3 text-[#8B5CF6]" />
                <span>Protected Workspace</span>
              </div>
            </div>

            <div className="relative z-10">
              <SignIn
                routing="hash"
                fallbackRedirectUrl="/"
                appearance={CLERK_APPEARANCE}
              />
            </div>
          </div>

        </div>
      </div>
    );
  }

  // Authenticated → render the protected content
  return <>{children}</>;
};
