import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { Header } from "@/components/Header";
import { ScrollToTop } from "@/components/ScrollToTop";
import { ProtectedRoute } from "@/components/ProtectedRoute";
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
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Protected routes - require authentication */}
        <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
        <Route path="/venue" element={<ProtectedRoute><VenueDetailPage /></ProtectedRoute>} />
        <Route path="/search" element={<ProtectedRoute><SearchPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/bookmarks" element={<ProtectedRoute><BookmarkedRestaurantsPage /></ProtectedRoute>} />
        <Route path="/reservations" element={<ProtectedRoute><ReservationsPage /></ProtectedRoute>} />
      </Routes>
    </div>
  );
}

function App() {
  return (
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
  );
}

export default App;
