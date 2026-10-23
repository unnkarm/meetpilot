// Used exclusively by tests/ui/vite.config.ts. Never imported by the production app.
import type { ReactNode } from 'react';
const user = { id: 'fixture-clerk-user', fullName: 'Alex Morgan', firstName: 'Alex', username: 'alex', primaryEmailAddress: { emailAddress: 'alex@example.test' }, imageUrl: undefined };
const getToken = async () => 'fixture-session-token';
const signedIn = () => !new URLSearchParams(location.search).has('signedOut');
export const useUser = () => ({ user: signedIn() ? user : null, isSignedIn: signedIn(), isLoaded: true });
export const useAuth = () => ({ getToken, isSignedIn: signedIn(), isLoaded: true, userId: signedIn() ? user.id : null });
export const useClerk = () => ({ signOut: () => location.assign('/?signedOut=1') });
export const ClerkProvider = ({ children }: { children: ReactNode }) => <>{children}</>;
export const SignIn = () => <div>Authentication fixture</div>;
export const SignUp = SignIn;
