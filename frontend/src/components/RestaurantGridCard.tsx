import { useState } from 'react'
import { MapPin, Bookmark } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Toggle } from '@/components/ui/toggle'

export interface RestaurantGridCardProps {
  id: string
  name: string
  type?: string
  priceRange: number
  location?: string
  imageUrl?: string | null
  onClick?: () => void
}

export function RestaurantGridCard({
  id,
  name,
  type,
  priceRange,
  location,
  imageUrl,
  onClick
}: RestaurantGridCardProps) {
  const [isBookmarked, setIsBookmarked] = useState(false)

  const handleBookmarkClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsBookmarked(!isBookmarked)
  }

  return (
    <Card
      className="cursor-pointer hover:shadow-lg pt-0 pb-2 transition-all group overflow-hidden"
      onClick={onClick}
    >
      {/* Image */}
      <div className="relative aspect-[4/3] w-full bg-muted overflow-hidden">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
            <MapPin className="size-12" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="px-4 pb-2 space-y-1">
        {/* Name and Price */}
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold text-base line-clamp-1 group-hover:text-primary transition-colors">
            {name}
          </h3>
          {priceRange > 0 && (
            <span className="text-sm text-muted-foreground font-medium flex-shrink-0">
              {'$'.repeat(priceRange)}
            </span>
          )}
        </div>

        {/* Type */}
        {type && type !== "N/A" && (
          <p className="text-sm text-muted-foreground line-clamp-1">{type}</p>
        )}

        {/* Location */}
        <div className='items-center flex flex-row justify-between'>
          {location && (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <MapPin className="size-3.5 flex-shrink-0" />
              <span className="line-clamp-1">{location}</span>
            </div>
          )}

          <Toggle
            pressed={isBookmarked}
            onPressedChange={setIsBookmarked}
            onClick={handleBookmarkClick}
            aria-label="Toggle bookmark"
            size="sm"
            variant="outline"
            className="bg-white/90 hover:bg-white data-[state=on]:bg-white data-[state=on]:*:[svg]:fill-primary data-[state=on]:*:[svg]:stroke-primary h-9 w-9 p-0"
          >
            <Bookmark className="size-4" />
          </Toggle>
        </div>
      </div>
    </Card>
  )
}
