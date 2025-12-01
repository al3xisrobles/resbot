import { useState, useEffect } from 'react'
import { MapPin } from 'lucide-react'

export interface SearchResultItemProps {
  id: string
  name: string
  type?: string
  priceRange: number
  location?: string
  imageUrl?: string | null
  onClick?: () => void
}

export function SearchResultItem({
  name,
  type,
  priceRange,
  location,
  imageUrl,
  onClick
}: SearchResultItemProps) {
  const [imageLoaded, setImageLoaded] = useState(false)
  const [imageError, setImageError] = useState(false)

  useEffect(() => {
    if (!imageUrl) {
      // If no image URL, show the item immediately
      setImageLoaded(true)
      return
    }

    // Preload the image
    const img = new Image()
    img.onload = () => setImageLoaded(true)
    img.onerror = () => {
      setImageError(true)
      setImageLoaded(true)
    }
    img.src = imageUrl
  }, [imageUrl])

  // Don't render until image is loaded
  if (!imageLoaded) {
    return null
  }

  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-3 hover:bg-accent transition-colors rounded-md"
    >
      <div className="flex items-start gap-3">
        {/* Image Thumbnail */}
        {imageUrl && !imageError && (
          <div className="shrink-0 w-16 h-16 rounded-md overflow-hidden bg-muted">
            <img
              src={imageUrl}
              alt={name}
              className="w-full h-full object-cover"
              onError={(e) => {
                e.currentTarget.style.display = 'none'
              }}
            />
          </div>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-semibold text-sm truncate">{name}</h4>
            {priceRange > 0 && (
              <span className="text-xs text-muted-foreground font-medium flex-shrink-0">
                {'$'.repeat(priceRange)}
              </span>
            )}
          </div>

          {type && type !== "N/A" && (
            <p className="text-xs text-muted-foreground truncate mb-1">{type}</p>
          )}

          {location && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <MapPin className="size-3 flex-shrink-0" />
              <span className="truncate">{location}</span>
            </div>
          )}
        </div>
      </div>
    </button>
  )
}
