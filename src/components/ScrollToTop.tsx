import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

export function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    // Scroll to top immediately (no animation)
    window.scrollTo(0, 0)
  }, [pathname])

  return null
}
