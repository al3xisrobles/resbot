import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { HomePage } from '@/pages/HomePage'
import { VenueDetailPage } from '@/pages/VenueDetailPage'
import { VenueProvider } from '@/contexts/VenueContext'
// Firebase is initialized in services/firebase.ts
import '@/services/firebase'

function App() {
  return (
    <VenueProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-background flex flex-col">
          <Header />

          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/venue" element={<VenueDetailPage />} />
          </Routes>

          <Footer />
        </div>
      </BrowserRouter>
    </VenueProvider>
  )
}

export default App
