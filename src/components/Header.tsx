import { LogOut, User, Calendar, UserCircle, Bookmark, Menu } from 'lucide-react'
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
import { SearchBar } from '@/components/SearchBar'

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
  const isHomePage = location.pathname === '/' || location.pathname === '/search'

  return (
    <header className="fixed top-0 left-0 right-0 z-9998 border-b bg-card">
      <div className="container mx-auto px-4 py-4">
        {/* Desktop Layout */}
        {isHomePage ? (
          /* Home page - Centered navigation */
          <div className="hidden md:grid grid-cols-3 items-center gap-6">
            {/* Left: Logo and Title - Clickable */}
            <div
              className="flex items-center gap-3 cursor-pointer"
              onClick={() => navigate('/')}
            >
              <img src={ResbotLogo} className='w-10'/>
              <div>
                <h1 className="text-3xl font-bold text-foreground">Resbot</h1>
                <p className="hidden xl:block text-sm text-muted-foreground">Automated NYC Restaurant Reservations</p>
              </div>
            </div>

            {/* Center: Navigation Menu */}
            <div className="flex justify-center">
              <NavigationMenu>
                <NavigationMenuList>
                  <NavigationMenuItem>
                    <Link to="/">
                      <NavigationMenuLink className={`${navigationMenuTriggerStyle()} ${location.pathname === '/' ? 'bg-accent' : ''}`}>
                        Home
                      </NavigationMenuLink>
                    </Link>
                  </NavigationMenuItem>
                  <NavigationMenuItem>
                    <Link to="/search">
                      <NavigationMenuLink className={`${navigationMenuTriggerStyle()} ${location.pathname === '/search' ? 'bg-accent' : ''}`}>
                        All Restaurants
                      </NavigationMenuLink>
                    </Link>
                  </NavigationMenuItem>
                </NavigationMenuList>
              </NavigationMenu>
            </div>

            {/* Right: User Menu or Login Button */}
            <div className="flex justify-end z-9998">
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
        ) : (
          /* Non-home pages - justify-between with SearchBar */
          <div className="hidden md:flex items-center justify-between gap-6 z-9998 bg-background">
            {/* Left: Logo and Title - Clickable */}
            <div
              className="flex items-center gap-3 cursor-pointer shrink-0"
              onClick={() => navigate('/')}
            >
              <img src={ResbotLogo} className='w-10'/>
              <div>
                <h1 className="text-3xl font-bold text-foreground">Resbot</h1>
                <p className="text-sm text-muted-foreground">Automated Restaurant Reservations</p>
              </div>
            </div>

            {/* Center: Search Bar and Navigation Menu */}
            <div className="flex items-center gap-8 flex-1 justify-center">
              <SearchBar
                className="relative w-full max-w-md"
                inputClassName="pr-10 py-6"
              />
              <NavigationMenu>
                <NavigationMenuList>
                  <NavigationMenuItem>
                    <Link to="/">
                      <NavigationMenuLink className={`${navigationMenuTriggerStyle()} ${location.pathname === '/' ? 'bg-accent' : ''}`}>
                        Home
                      </NavigationMenuLink>
                    </Link>
                  </NavigationMenuItem>
                  <NavigationMenuItem>
                    <Link to="/search">
                      <NavigationMenuLink className={`${navigationMenuTriggerStyle()} ${location.pathname === '/search' ? 'bg-accent' : ''}`}>
                        All Restaurants
                      </NavigationMenuLink>
                    </Link>
                  </NavigationMenuItem>
                </NavigationMenuList>
              </NavigationMenu>
            </div>

            {/* Right: User Menu or Login Button */}
            <div className="flex shrink-0">
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
        )}

        {/* Mobile Layout */}
        <div className="flex md:hidden items-center justify-between gap-4">
          {/* Logo - Clickable */}
          <div
            className="flex items-center gap-2 cursor-pointer"
            onClick={() => navigate('/')}
          >
            <img src={ResbotLogo} className='w-8'/>
            <h1 className="text-xl font-bold text-foreground">Resbot</h1>
          </div>

          {/* Right: Menu and User */}
          <div className="flex items-center gap-2">
            {/* Mobile Navigation Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon">
                  <Menu className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem onClick={() => navigate('/search')}>
                  See All Restaurants
                </DropdownMenuItem>
                {currentUser && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => navigate('/reservations')}>
                      <Calendar className="mr-2 size-4" />
                      My Reservations
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => navigate('/bookmarks')}>
                      <Bookmark className="mr-2 size-4" />
                      Bookmarked Restaurants
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* User Menu or Login */}
            {currentUser ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon">
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
                  <DropdownMenuItem onClick={handleLogout}>
                    <LogOut className="mr-2 size-4" />
                    Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : !isAuthPage && (
              <Button size="sm" onClick={() => navigate('/login')}>
                Log in
              </Button>
            )}
          </div>
        </div>

        {/* Mobile Search Bar (when not on home page) */}
        {!isHomePage && (
          <div className="mt-4 md:hidden">
            <SearchBar
              className="relative w-full"
              inputClassName="pr-10"
            />
          </div>
        )}
      </div>
    </header>
  )
}
