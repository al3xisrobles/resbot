import { UtensilsCrossed } from 'lucide-react'

export function Header() {
  return (
    <header className="border-b bg-card shadow-sm">
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center gap-3">
          <UtensilsCrossed className="size-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold text-foreground">Resbot</h1>
            <p className="text-sm text-muted-foreground">Automated Restaurant Reservations</p>
          </div>
        </div>
      </div>
    </header>
  )
}
