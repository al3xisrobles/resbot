import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ScrollToTop } from "@/components/ScrollToTop";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { HomePage } from "@/pages/HomePage";
import { VenueDetailPage } from "@/pages/VenueDetailPage";
import { SearchPage } from "@/pages/SearchPage";
import { BookmarkedRestaurantsPage } from "@/pages/BookmarkedRestaurantsPage";
import { ReservationsPage } from "@/pages/ReservationsPage";
import { LoginPage } from "@/pages/LoginPage";
import { SignupPage } from "@/pages/SignupPage";
import { OnboardingPage } from "@/pages/OnboardingPage";
import { VenueProvider } from "@/contexts/VenueContext";
import { AuthProvider } from "@/contexts/AuthContext";
import ProfilePage from "./pages/ProfilePage";
// Firebase is initialized in services/firebase.ts
import "@/services/firebase";

function App() {
  return (
    <AuthProvider>
      <VenueProvider>
        <BrowserRouter>
          <ScrollToTop />
          <div className="h-screen flex flex-col overflow-hidden">
            <Header />

            <Routes>
              {/* Public routes */}
              <Route path="/" element={<HomePage />} />
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

            {window.location.pathname !== "/search" && <Footer />}
          </div>
          <Toaster position="top-left" />
        </BrowserRouter>
      </VenueProvider>
    </AuthProvider>
  );
}

export default App;
