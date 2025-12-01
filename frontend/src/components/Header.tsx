import { LogOut, User, Calendar, UserCircle, Bookmark } from 'lucide-react'
import ResbotLogo from '../assets/ResbotLogo.svg';
import { useAuth } from '@/contexts/AuthContext'
import { Button } from './ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  navigationMenuTriggerStyle,
} from '@/components/ui/navigation-menu'
import { useNavigate, useLocation, Link } from 'react-router-dom'

export function Header() {
  const { currentUser, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  async function handleLogout() {
    try {
      await logout()
    } catch (error) {
      console.error('Failed to log out:', error)
    }
  }

  // Hide login button on login/signup pages
  const isAuthPage = location.pathname === '/login' || location.pathname === '/signup'

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b bg-card">
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-3 items-center">
          {/* Left: Logo and Title - Clickable */}
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => navigate('/')}
          >
            <img src={ResbotLogo} className='w-10'/>
            <div>
              <h1 className="text-3xl font-bold text-foreground">Resbot</h1>
              <p className="text-sm text-muted-foreground">Automated Restaurant Reservations</p>
            </div>
          </div>

          {/* Center: Navigation Menu */}
          <div className="flex justify-center">
            <NavigationMenu>
              <NavigationMenuList>
                <NavigationMenuItem>
                  <Link to="/">
                    <NavigationMenuLink className={navigationMenuTriggerStyle()}>
                      Search Restaurants
                    </NavigationMenuLink>
                  </Link>
                </NavigationMenuItem>
                <NavigationMenuItem>
                  <Link to="/search-by-date">
                    <NavigationMenuLink className={navigationMenuTriggerStyle()}>
                      Search by Date
                    </NavigationMenuLink>
                  </Link>
                </NavigationMenuItem>
              </NavigationMenuList>
            </NavigationMenu>
          </div>

          {/* Right: User Menu or Login Button */}
          <div className="flex justify-end">
            {currentUser ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="w-12 h-12">
                    <User className="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end">
                  <DropdownMenuLabel>
                    {currentUser.displayName || currentUser.email}
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate('/profile')}>
                    <UserCircle className="mr-2 size-4" />
                    Profile
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate('/reservations')}>
                    <Calendar className="mr-2 size-4" />
                    My Reservations
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => navigate('/bookmarks')}>
                    <Bookmark className="mr-2 size-4" />
                    Bookmarked Restaurants
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout}>
                    <LogOut className="mr-2 size-4" />
                    Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : !isAuthPage && (
              <Button onClick={() => navigate('/login')}>
                Log in
              </Button>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
