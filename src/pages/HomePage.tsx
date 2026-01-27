// src/pages/HomePage.tsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, Star, Search } from "lucide-react";
import { toast } from "sonner";

import { getTrendingRestaurants, getTopRatedRestaurants } from "@/lib/api";
import type { TrendingRestaurant } from "@/lib/interfaces";
import { useAtom } from "jotai";
import { reservationFormAtom } from "@/atoms/reservationAtoms";
import { RestaurantGridCard } from "@/components/RestaurantGridCard";
import {
  getTrendingRestaurantsCache,
  saveTrendingRestaurantsCache,
  getTopRatedRestaurantsCache,
  saveTopRatedRestaurantsCache,
} from "@/services/firebase";
import { useAuth } from "@/contexts/AuthContext";
import { Hero } from "@/components/Hero";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export function HomePage() {
  const navigate = useNavigate();
  const auth = useAuth();
  const [trendingRestaurants, setTrendingRestaurants] = useState<
    TrendingRestaurant[]
  >([]);
  const [loadingTrending, setLoadingTrending] = useState(false);
  const [topRatedRestaurants, setTopRatedRestaurants] = useState<
    TrendingRestaurant[]
  >([]);
  const [loadingTopRated, setLoadingTopRated] = useState(false);
  const [reservationForm] = useAtom(reservationFormAtom);

  const handleSelectVenue = (venueId: string) => {
    navigate(`/venue?id=${venueId}`);
  };

  // Fetch trending restaurants on mount
  useEffect(() => {
    const fetchTrending = async () => {
      setLoadingTrending(true);
      try {
        const cachedData = await getTrendingRestaurantsCache();

        if (cachedData) {
          console.log("Using cached trending restaurants");
          setTrendingRestaurants(cachedData);
        } else {
          console.log("Fetching fresh trending restaurants");
          const userId = auth.currentUser?.uid ?? null;
          const data = await getTrendingRestaurants(userId, 10);
          setTrendingRestaurants(data);
          await saveTrendingRestaurantsCache(data);
        }
      } catch (err) {
        console.error("Failed to fetch trending restaurants:", err);
      } finally {
        setLoadingTrending(false);
      }
    };

    fetchTrending();
  }, [auth.currentUser]);

  // Fetch top-rated restaurants on mount
  useEffect(() => {
    const fetchTopRated = async () => {
      setLoadingTopRated(true);
      try {
        const cachedData = await getTopRatedRestaurantsCache();

        if (cachedData) {
          console.log("Using cached top-rated restaurants");
          setTopRatedRestaurants(cachedData);
        } else {
          console.log("Fetching fresh top-rated restaurants");
          const userId = auth.currentUser?.uid ?? null;
          const data = await getTopRatedRestaurants(userId, 10);
          setTopRatedRestaurants(data);
          await saveTopRatedRestaurantsCache(data);
        }
      } catch (err) {
        console.error("Failed to fetch top-rated restaurants:", err);
      } finally {
        setLoadingTopRated(false);
      }
    };

    fetchTopRated();
  }, [auth.currentUser]);

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        {/* HERO */}
        <Hero />

        {/* Trending Restaurants */}
        <div className="container mx-auto px-4 py-4 pb-12">
          <section>
            <div className="flex items-center gap-2 z-20">
              <TrendingUp className="size-6 text-primary" />
              <h2 className="text-2xl font-bold">Trending Restaurants</h2>
            </div>
            <p className="text-sm pb-6 pt-2 text-muted-foreground">
              Popular restaurants climbing on Resy right now
            </p>

            {loadingTrending ? (
              <div className="flex items-center justify-center h-[400px]">
                <p className="text-muted-foreground">
                  Loading trending restaurants...
                </p>
              </div>
            ) : trendingRestaurants.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                {trendingRestaurants.map((restaurant) => {
                  const hasAllReservationDetails =
                    reservationForm.date &&
                    reservationForm.timeSlot &&
                    reservationForm.partySize;

                  return (
                    <RestaurantGridCard
                      key={restaurant.id}
                      id={restaurant.id}
                      name={restaurant.name}
                      type={restaurant.type}
                      priceRange={restaurant.priceRange}
                      location={[
                        restaurant.location.neighborhood,
                        restaurant.location.locality,
                      ]
                        .filter(Boolean)
                        .join(", ")}
                      imageUrl={restaurant.imageUrl}
                      onClick={() => handleSelectVenue(restaurant.id)}
                      showPlaceholder={!hasAllReservationDetails}
                    />
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[400px]">
                <div className="text-center space-y-3">
                  <Search className="size-12 text-muted-foreground mx-auto opacity-20" />
                  <p className="text-muted-foreground text-lg">
                    No trending restaurants available
                  </p>
                </div>
              </div>
            )}
          </section>

          {/* Top Rated Restaurants */}
          <section className="mt-12">
            <div className="flex items-center gap-2">
              <Star className="size-6 text-primary" />
              <h2 className="text-2xl font-bold">Top Rated Restaurants</h2>
            </div>
            <p className="text-sm pb-6 pt-2 text-muted-foreground">
              The highest-rated restaurants on Resy right now
            </p>

            {loadingTopRated ? (
              <div className="flex items-center justify-center h-[400px]">
                <p className="text-muted-foreground">
                  Loading top-rated restaurants...
                </p>
              </div>
            ) : topRatedRestaurants.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                {topRatedRestaurants.map((restaurant, index) => {
                  // const hasAllReservationDetails =
                  //   reservationForm.date &&
                  //   reservationForm.timeSlot &&
                  //   reservationForm.partySize;

                  return (
                    <RestaurantGridCard
                      key={index}
                      id={restaurant.id}
                      name={restaurant.name}
                      type={restaurant.type}
                      priceRange={restaurant.priceRange}
                      location={[
                        restaurant.location.neighborhood,
                        restaurant.location.locality,
                      ]
                        .filter(Boolean)
                        .join(", ")}
                      imageUrl={restaurant.imageUrl}
                      onClick={() => handleSelectVenue(restaurant.id)}
                    // showPlaceholder={!hasAllReservationDetails}
                    />
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[400px]">
                <div className="text-center space-y-3">
                  <Star className="size-12 text-muted-foreground mx-auto opacity-20" />
                  <p className="text-muted-foreground text-lg">
                    No top-rated restaurants available
                  </p>
                </div>
              </div>
            )}
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
