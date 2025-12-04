export function BookmarkedRestaurantsPage() {
  return (
    <div className="h-screen bg-background pt-32 overflow-y-auto">
      <main className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-[400px]">
          <div className="text-center space-y-3">
            <h1 className="text-3xl font-bold tracking-tight">Bookmarked Restaurants</h1>
            <p className="text-muted-foreground">
              Your bookmarked restaurants will appear here
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
