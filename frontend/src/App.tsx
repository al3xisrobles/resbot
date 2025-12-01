import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'sonner'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { ScrollToTop } from '@/components/ScrollToTop'
import { HomePage } from '@/pages/HomePage'
import { VenueDetailPage } from '@/pages/VenueDetailPage'
import { SearchResultsPage } from '@/pages/SearchResultsPage'
import { BookmarkedRestaurantsPage } from '@/pages/BookmarkedRestaurantsPage'
import { LoginPage } from '@/pages/LoginPage'
import { SignupPage } from '@/pages/SignupPage'
import { VenueProvider } from '@/contexts/VenueContext'
import { AuthProvider } from '@/contexts/AuthContext'
// Firebase is initialized in services/firebase.ts
import '@/services/firebase'

function App() {
  return (
    <AuthProvider>
      <VenueProvider>
        <BrowserRouter>
          <ScrollToTop />
          <div className="min-h-screen bg-background flex flex-col mb-24">
            <Header />

            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
              <Route path="/" element={<HomePage />} />
              <Route path="/venue" element={<VenueDetailPage />} />
              <Route path="/search-results" element={<SearchResultsPage />} />
              <Route path="/bookmarks" element={<BookmarkedRestaurantsPage />} />
            </Routes>

            <Footer />
          </div>
          <Toaster />
        </BrowserRouter>
      </VenueProvider>
    </AuthProvider>
  )
}

export default App
