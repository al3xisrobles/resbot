import { Navigate } from "react-router-dom";
import { useAtomValue } from "jotai";
import { useAuth } from "@/contexts/AuthContext";
import { isOnboardedAtom } from "@/atoms/authAtoms";

/**
 * Route guard that requires authentication only
 * Redirects to /login if not authenticated
 */
export function AuthenticatedRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { currentUser } = useAuth();

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

/**
 * Route guard that requires authentication + Resy onboarding
 * Redirects to /login if not authenticated
 * Redirects to /onboarding if authenticated but not onboarded
 */
export function OnboardedRoute({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();
  const isOnboarded = useAtomValue(isOnboardedAtom);

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  if (!isOnboarded) {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
}

/**
 * Route guard for guest-only pages (login, signup)
 * Redirects to / if already authenticated
 */
export function GuestOnlyRoute({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();

  if (currentUser) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

/**
 * Legacy ProtectedRoute - kept for backward compatibility
 * @deprecated Use AuthenticatedRoute or OnboardedRoute instead
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return <AuthenticatedRoute>{children}</AuthenticatedRoute>;
}
