import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ScrollToTop } from "@/components/ScrollToTop";
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

            <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/onboarding" element={<OnboardingPage />} />
                <Route path="/" element={<HomePage />} />
                <Route path="/venue" element={<VenueDetailPage />} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route
                  path="/bookmarks"
                  element={<BookmarkedRestaurantsPage />}
                />
                <Route path="/reservations" element={<ReservationsPage />} />
              </Routes>
            </main>

            {window.location.pathname !== "/search" && <Footer />}
          </div>
          <Toaster position="top-left" />
        </BrowserRouter>
      </VenueProvider>
    </AuthProvider>
  );
}

export default App;
