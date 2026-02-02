import * as Sentry from "@sentry/react";
import { useEffect } from "react";
import {
  LogOut,
  User,
  Calendar,
  UserCircle,
  Bookmark,
  Menu,
} from "lucide-react";
import ResbotLogoWithText from "../assets/ResbotLogoRedWithText.svg";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { SearchBar } from "@/components/SearchBar";
import { CitySelector } from "@/common/components/CitySelector";

export function Header() {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  async function handleLogout() {
    try {
      await logout();
    } catch (error) {
      console.error("Failed to log out:", error);
      Sentry.captureException(error);
    }
  }

  const isAuthPage =
    location.pathname === "/login" || location.pathname === "/signup";
  const isHomePage = location.pathname === "/";

  const isLoggedIn = !!currentUser;

  useEffect(() => {
    console.log("Current user in Header:", currentUser);
    console.log("Is logged in:", isLoggedIn);
  }, [currentUser, isLoggedIn]);

  // Whether we actually show a SearchBar in the header
  const showHeaderSearch = !isHomePage && isLoggedIn;

  return (
    <header className={`${!isHomePage && "border-b"} bg-card`}>
      <div className="container mx-auto px-4 py-4">
        {/* Desktop Layout */}
        {!showHeaderSearch ? (
          /* Home page - Centered navigation */
          <div className="hidden md:grid grid-cols-3 items-center gap-6">
            {/* Left: Logo and Title - Clickable */}
            <div
              className="flex items-center gap-3 cursor-pointer"
              onClick={() => navigate("/")}
            >
              <img src={ResbotLogoWithText} className="h-10" />
              <div>
                <h1 className="hidden">Resbot</h1>
              </div>
            </div>

            {/* Center: Navigation Menu */}
            <div className="flex justify-center">
              <NavigationMenu>
                <NavigationMenuList>
                  <NavigationMenuItem>
                    <NavigationMenuLink
                      asChild
                      className={`${navigationMenuTriggerStyle()} ${location.pathname === "/" ? "bg-accent" : ""
                        }`}
                    >
                      <Link to="/">Home</Link>
                    </NavigationMenuLink>
                  </NavigationMenuItem>
                  <NavigationMenuItem>
                    <NavigationMenuLink
                      asChild
                      className={`${navigationMenuTriggerStyle()} ${location.pathname === "/search" ? "bg-accent" : ""
                        }`}
                    >
                      <Link to="/search">All Restaurants</Link>
                    </NavigationMenuLink>
                  </NavigationMenuItem>
                </NavigationMenuList>
              </NavigationMenu>
            </div>

            {/* Right: City Selector, User Menu or Login Button */}
            <div className="flex items-center justify-end gap-4 z-9998">
              <CitySelector />
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
                    <DropdownMenuItem onClick={() => navigate("/profile")}>
                      <UserCircle className="mr-2 size-4" />
                      Profile
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => navigate("/reservations")}>
                      <Calendar className="mr-2 size-4" />
                      My Reservations
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => navigate("/bookmarks")}>
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
              ) : (
                !isAuthPage && (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      onClick={() => navigate("/login")}
                    >
                      Log in
                    </Button>
                    <Button onClick={() => navigate("/signup")}>Sign Up</Button>
                  </div>
                )
              )}
            </div>
          </div>
        ) : (
          /* Non-home pages - justify-between with SearchBar */
          <div className="hidden md:flex items-center justify-between gap-6 z-9998 bg-background">
            {/* Left: Logo and Title - Clickable */}
            <div
              className="flex items-center gap-3 cursor-pointer shrink-0"
              onClick={() => navigate("/")}
            >
              <img src={ResbotLogoWithText} className="h-10" />
              <div>
                <h1 className="hidden">Resbot</h1>
              </div>
            </div>

            {/* Center: Search Bar and Navigation Menu */}
            <div className="flex items-center gap-8 flex-1 justify-center">
              <SearchBar
                className="relative w-full max-w-md rounded-full border bg-background"
                inputClassName="h-12 sm:h-14 pl-6 pr-12 rounded-full text-sm sm:text-base"
              />
              <NavigationMenu>
                <NavigationMenuList>
                  <NavigationMenuItem>
                    <NavigationMenuLink
                      asChild
                      className={`${navigationMenuTriggerStyle()} ${location.pathname === "/" ? "bg-accent" : ""
                        }`}
                    >
                      <Link to="/">Home</Link>
                    </NavigationMenuLink>
                  </NavigationMenuItem>
                  <NavigationMenuItem>
                    <NavigationMenuLink
                      asChild
                      className={`${navigationMenuTriggerStyle()} ${location.pathname === "/search" ? "bg-accent" : ""
                        }`}
                    >
                      <Link to="/search">All Restaurants</Link>
                    </NavigationMenuLink>
                  </NavigationMenuItem>
                </NavigationMenuList>
              </NavigationMenu>
            </div>

            {/* Right: City Selector, User Menu or Login Button */}
            <div className="flex items-center shrink-0 gap-4">
              <CitySelector />
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
                    <DropdownMenuItem onClick={() => navigate("/profile")}>
                      <UserCircle className="mr-2 size-4" />
                      Profile
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => navigate("/reservations")}>
                      <Calendar className="mr-2 size-4" />
                      My Reservations
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => navigate("/bookmarks")}>
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
              ) : (
                !isAuthPage && (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      onClick={() => navigate("/login")}
                    >
                      Log in
                    </Button>
                    <Button onClick={() => navigate("/signup")}>Sign Up</Button>
                  </div>
                )
              )}
            </div>
          </div>
        )}

        {/* Mobile Layout */}
        <div className="flex md:hidden items-center justify-between gap-4">
          {/* Logo - Clickable */}
          <div
            className="flex items-center gap-2 cursor-pointer"
            onClick={() => navigate("/")}
          >
            <img src={ResbotLogoWithText} className="h-8" />
          </div>

          {/* Right: City Selector, Menu and User */}
          <div className="flex items-center gap-2">
            <div className="hidden sm:block">
              <CitySelector />
            </div>
            {/* Mobile Navigation Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon">
                  <Menu className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem onClick={() => navigate("/search")}>
                  See All Restaurants
                </DropdownMenuItem>
                {currentUser && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => navigate("/reservations")}>
                      <Calendar className="mr-2 size-4" />
                      My Reservations
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => navigate("/bookmarks")}>
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
                  <DropdownMenuItem onClick={() => navigate("/profile")}>
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
            ) : (
              !isAuthPage && (
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate("/login")}
                  >
                    Log in
                  </Button>
                  <Button size="sm" onClick={() => navigate("/signup")}>
                    Sign Up
                  </Button>
                </div>
              )
            )}
          </div>
        </div>

        {/* Mobile Search Bar (when not on home page) */}
        {showHeaderSearch && (
          <div className="mt-4 md:hidden">
            <SearchBar className="relative w-full" inputClassName="pr-10" />
          </div>
        )}
      </div>
    </header>
  );
}
