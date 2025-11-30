import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { type VenueData } from '@/lib/api'

interface RestaurantCardProps {
  data: VenueData
}

export function RestaurantCard({ data }: RestaurantCardProps) {
  return (
    <Card className="mt-6 border-primary/20 bg-accent/30">
      <CardHeader>
        <CardTitle className="text-2xl">{data.name}</CardTitle>
        <CardDescription>Venue ID: {data.venue_id}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Type</p>
            <p className="text-foreground">{data.type}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-muted-foreground">Price Range</p>
            <p className="text-foreground">{'$'.repeat(data.price_range)}</p>
          </div>
          <div className="col-span-2">
            <p className="text-sm font-medium text-muted-foreground">Address</p>
            <p className="text-foreground">{data.address}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-muted-foreground">Neighborhood</p>
            <p className="text-foreground">{data.neighborhood}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-muted-foreground">Rating</p>
            <p className="text-foreground">{data.rating}/5.0</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
