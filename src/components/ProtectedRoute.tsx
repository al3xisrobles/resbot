import { Navigate } from "react-router-dom";
import { useAtomValue } from "jotai";
import { useAuth } from "@/contexts/AuthContext";
import { isOnboardedAtom, isAuthLoadingAtom } from "@/atoms/authAtoms";
import { LoaderSpinner } from "@/components/ui/loader-spinner";
import * as Sentry from "@sentry/react";

function RouteLoadingScreen() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background">
      <LoaderSpinner size="lg" />
    </div>
  );
}

/**
 * Route guard that requires authentication only
 * Returns null while auth is loading to prevent premature redirects
 * Redirects to /login if not authenticated (after auth state resolves)
 */
export function AuthenticatedRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const isAuthLoading = useAtomValue(isAuthLoadingAtom);
  
  // Try to get auth context, but handle gracefully if it's not available yet
  let currentUser = null;
  try {
    const auth = useAuth();
    currentUser = auth.currentUser;
  } catch (error) {
    // If auth context is not available yet (e.g., during HMR), show loading screen
    Sentry.captureException(error);
    console.warn("Auth context not available in AuthenticatedRoute, showing loading screen");
    return <RouteLoadingScreen />;
  }

  // Wait for auth state to resolve before making routing decisions
  if (isAuthLoading) {
    return <RouteLoadingScreen />;
  }

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

/**
 * Route guard that requires authentication + Resy onboarding
 * Returns null while auth is loading to prevent premature redirects
 * Redirects to /login if not authenticated (after auth state resolves)
 * Redirects to /connect-resy if authenticated but not onboarded
 */
export function OnboardedRoute({ children }: { children: React.ReactNode }) {
  const isOnboarded = useAtomValue(isOnboardedAtom);
  const isAuthLoading = useAtomValue(isAuthLoadingAtom);
  
  // Try to get auth context, but handle gracefully if it's not available yet
  let currentUser = null;
  try {
    const auth = useAuth();
    currentUser = auth.currentUser;
  } catch (error) {
    // If auth context is not available yet (e.g., during HMR), show loading screen
    Sentry.captureException(error);
    console.warn("Auth context not available in OnboardedRoute, showing loading screen");
    return <RouteLoadingScreen />;
  }

  // Wait for auth state to resolve before making routing decisions
  if (isAuthLoading) {
    return <RouteLoadingScreen />;
  }

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  if (!isOnboarded) {
    return <Navigate to="/connect-resy" replace />;
  }

  return <>{children}</>;
}

/**
 * Route guard that requires authentication and redirects to /connect-resy if not onboarded
 * Returns null while auth is loading to prevent premature redirects
 * This is similar to AuthenticatedRoute but also checks onboarding status
 */
export function AuthenticatedOnboardedRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const isOnboarded = useAtomValue(isOnboardedAtom);
  const isAuthLoading = useAtomValue(isAuthLoadingAtom);
  
  // Try to get auth context, but handle gracefully if it's not available yet
  let currentUser = null;
  try {
    const auth = useAuth();
    currentUser = auth.currentUser;
  } catch (error) {
    // If auth context is not available yet (e.g., during HMR), show loading screen
    Sentry.captureException(error);
    console.warn("Auth context not available in AuthenticatedOnboardedRoute, showing loading screen");
    return <RouteLoadingScreen />;
  }

  // Wait for auth state to resolve before making routing decisions
  if (isAuthLoading) {
    return <RouteLoadingScreen />;
  }

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  if (!isOnboarded) {
    return <Navigate to="/connect-resy" replace />;
  }

  return <>{children}</>;
}

/**
 * Route guard for guest-only pages (login, signup)
 * Returns null while auth is loading to prevent premature redirects
 * Redirects to / if already authenticated (after auth state resolves)
 */
export function GuestOnlyRoute({ children }: { children: React.ReactNode }) {
  const isAuthLoading = useAtomValue(isAuthLoadingAtom);
  
  // Try to get auth context, but handle gracefully if it's not available yet
  let currentUser = null;
  try {
    const auth = useAuth();
    currentUser = auth.currentUser;
  } catch (error) {
    // If auth context is not available yet (e.g., during HMR), show loading screen
    Sentry.captureException(error);
    console.warn("Auth context not available in GuestOnlyRoute, showing loading screen");
    return <RouteLoadingScreen />;
  }

  // Wait for auth state to resolve before making routing decisions
  if (isAuthLoading) {
    return <RouteLoadingScreen />;
  }

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
