import * as Sentry from "@sentry/react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { Header } from "@/components/Header";
import { ScrollToTop } from "@/components/ScrollToTop";
import {
  AuthenticatedRoute,
  OnboardedRoute,
} from "@/components/ProtectedRoute";
import { useAtomValue } from "jotai";
import { isOnboardedAtom } from "@/atoms/authAtoms";
import { Navigate } from "react-router-dom";
import { HomePage } from "@/pages/HomePage";
import { VenueDetailPage } from "@/pages/routes/venue/VenueDetailPage";
import { SearchPage } from "@/pages/SearchPage";
import { BookmarkedRestaurantsPage } from "@/pages/BookmarkedRestaurantsPage";
import { ReservationsPage } from "@/pages/ReservationsPage";
import { LoginPage } from "@/pages/LoginPage";
import { SignupPage } from "@/pages/SignupPage";
import { OnboardingPage } from "@/pages/OnboardingPage";
import { VenueProvider } from "@/contexts/VenueContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { ResySessionProvider } from "@/contexts/ResySessionContext";
import { ResySessionExpiredModal } from "@/components/ResySessionExpiredModal";
import ProfilePage from "./pages/ProfilePage";
// Firebase is initialized in services/firebase.ts
import "@/services/firebase";

// Note: React Router v7 integration may require different setup
// For now, using BrowserRouter directly with ErrorBoundary for error tracking

// Wrapper component for onboarding page that redirects if already onboarded
function OnboardingPageWrapper() {
  const isOnboarded = useAtomValue(isOnboardedAtom);
  if (isOnboarded) {
    return <Navigate to="/" replace />;
  }
  return <OnboardingPage />;
}

function AppContent() {
  const location = useLocation();
  const isHomePage = location.pathname === "/";

  // For home page, header and footer are part of the scrollable content
  // For other pages, they are sticky
  if (isHomePage) {
    return (
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header />

      <Routes>
        {/* Guest-only routes - redirect if authenticated */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Public routes */}
        <Route path="/search" element={<SearchPage />} />

        {/* Authenticated routes - require authentication only */}
        <Route
          path="/connect-resy"
          element={
            <AuthenticatedRoute>
              <OnboardingPageWrapper />
            </AuthenticatedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <OnboardedRoute>
              <ProfilePage />
            </OnboardedRoute>
          }
        />

        {/* Onboarded routes - require authentication + Resy onboarding */}
        <Route
          path="/venue"
          element={
            <OnboardedRoute>
              <VenueDetailPage />
            </OnboardedRoute>
          }
        />
        <Route
          path="/bookmarks"
          element={
            <OnboardedRoute>
              <BookmarkedRestaurantsPage />
            </OnboardedRoute>
          }
        />
        <Route
          path="/reservations"
          element={
            <OnboardedRoute>
              <ReservationsPage />
            </OnboardedRoute>
          }
        />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <Sentry.ErrorBoundary
      fallback={({ error, resetError }) => (
        <div className="flex min-h-screen items-center justify-center p-4">
          <div className="max-w-md w-full space-y-4 text-center">
            <h1 className="text-2xl font-bold">Something went wrong</h1>
            <p className="text-muted-foreground">
              We're sorry, but something unexpected happened. Please try refreshing the page.
            </p>
            <div className="flex gap-2 justify-center">
              <button
                onClick={resetError}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Try again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90"
              >
                Reload page
              </button>
            </div>
            {process.env.NODE_ENV === "development" && (
              <details className="mt-4 text-left">
                <summary className="cursor-pointer text-sm text-muted-foreground">
                  Error details
                </summary>
                <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto">
                  {error?.toString()}
                </pre>
              </details>
            )}
          </div>
        </div>
      )}
      showDialog={false}
    >
      <AuthProvider>
        <ResySessionProvider>
          <VenueProvider>
            <BrowserRouter>
              <ScrollToTop />
              <AppContent />
              <ResySessionExpiredModal />
              <Toaster position="top-left" />
            </BrowserRouter>
          </VenueProvider>
        </ResySessionProvider>
      </AuthProvider>
    </Sentry.ErrorBoundary>
  );
}

export default App;
