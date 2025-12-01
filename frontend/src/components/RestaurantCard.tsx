import { useState } from 'react'
import { MapPin, ChevronRight, Bookmark } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Toggle } from '@/components/ui/toggle'

export interface RestaurantCardProps {
  id: string
  name: string
  type?: string
  priceRange: number
  location?: string
  imageUrl?: string | null
  onClick?: () => void
  showBookmark?: boolean
}

export function RestaurantCard({
  id,
  name,
  type,
  priceRange,
  location,
  imageUrl,
  onClick,
  showBookmark = false
}: RestaurantCardProps) {
  const [isBookmarked, setIsBookmarked] = useState(false)

  const handleBookmarkClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsBookmarked(!isBookmarked)
  }

  return (
    <Card
      className="cursor-pointer hover:border-primary hover:shadow-md transition-all group overflow-hidden"
      onClick={onClick}
    >
      <div className="flex gap-4 p-4">
        {/* Left: Image Thumbnail */}
        {showBookmark && (
          <div className="flex-shrink-0 w-24 h-24 rounded-lg overflow-hidden bg-muted">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                }}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                <MapPin className="size-8" />
              </div>
            )}
          </div>
        )}

        {/* Middle: Restaurant Details */}
        <div className="flex-1 min-w-0">
          <div className="space-y-1.5">
            {/* Name */}
            <h3 className="text-lg font-semibold group-hover:text-primary transition-colors truncate">
              {name}
            </h3>

            {/* Type and Price Range */}
            <div className="flex items-center gap-2 text-sm">
              {type && type !== "N/A" && (
                <span className="text-muted-foreground">{type}</span>
              )}
              {priceRange > 0 && (
                <>
                  {type && type !== "N/A" && (
                    <span className="text-muted-foreground">•</span>
                  )}
                  <span className="text-muted-foreground font-medium">
                    {'$'.repeat(priceRange)}
                  </span>
                </>
              )}
            </div>

            {/* Location */}
            {location && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <MapPin className="size-3.5 flex-shrink-0" />
                <span className="truncate">{location}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Bookmark or Arrow */}
        <div className="flex items-center gap-2">
          {showBookmark ? (
            <Toggle
              pressed={isBookmarked}
              onPressedChange={setIsBookmarked}
              onClick={handleBookmarkClick}
              aria-label="Toggle bookmark"
              size="sm"
              variant="outline"
              className="data-[state=on]:bg-transparent data-[state=on]:*:[svg]:fill-primary data-[state=on]:*:[svg]:stroke-primary h-8"
            >
              <Bookmark className="size-4" />
            </Toggle>
          ) : (
            <ChevronRight className="size-6 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all shrink-0" />
          )}
        </div>
      </div>
    </Card>
  )
}
