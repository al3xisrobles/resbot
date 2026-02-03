// src/pages/HomePage.tsx
import * as Sentry from "@sentry/react";
import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, Star, Search } from "lucide-react";

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

// ==========================================
// ANIMATION CONSTANTS
// ==========================================

/** Easing curve for smooth pop-up animations (ease-out-quad) */
const EASE_OUT_QUAD: [number, number, number, number] = [0.25, 0.46, 0.45, 0.94];

/** Duration for section entrance animations */
const SECTION_DURATION = 0.5;

/** Duration for header (title + subtitle) animations */
const HEADER_DURATION = 0.4;

/** Duration for individual restaurant card animations */
const CARD_DURATION = 0.45;

/** Stagger delay between cards in a grid */
const CARD_STAGGER_DELAY = 0.06;

/** Initial delay before cards start animating after header */
const CARD_INITIAL_DELAY = 0.1;

/** Y-offset for section fade-up animation */
const SECTION_FADE_OFFSET = 20;

/** Y-offset for header fade-up animation */
const HEADER_FADE_OFFSET = 12;

/** Y-offset for card fade-up animation */
const CARD_FADE_OFFSET = 24;

/** Scale for hidden card state (slightly smaller for pop-up effect) */
const CARD_HIDDEN_SCALE = 0.96;

/** Viewport margin for triggering animations (negative = triggers before fully in view) */
const VIEWPORT_TRIGGER_MARGIN = "-50px";

/** Viewport margin for card grid animations */
const CARD_VIEWPORT_MARGIN = "-30px";

// ==========================================
// ANIMATION VARIANTS
// ==========================================

const sectionVariants = {
  hidden: { opacity: 0, y: SECTION_FADE_OFFSET },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: SECTION_DURATION,
      ease: EASE_OUT_QUAD,
    },
  },
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: CARD_STAGGER_DELAY,
      delayChildren: CARD_INITIAL_DELAY,
    },
  },
};

const cardVariants = {
  hidden: { 
    opacity: 0, 
    y: CARD_FADE_OFFSET,
    scale: CARD_HIDDEN_SCALE,
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: CARD_DURATION,
      ease: EASE_OUT_QUAD,
    },
  },
};

const headerVariants = {
  hidden: { opacity: 0, y: HEADER_FADE_OFFSET },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: HEADER_DURATION,
      ease: EASE_OUT_QUAD,
    },
  },
};

// ==========================================
// COMPONENT
// ==========================================

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
        Sentry.captureException(err);
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
        Sentry.captureException(err);
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
        <div className="container mx-auto px-4 pt-8 sm:pt-12 md:pt-16 lg:pt-12 xl:pt-16 pb-12">
          <motion.section
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: VIEWPORT_TRIGGER_MARGIN }}
            variants={sectionVariants}
          >
            <motion.div 
              className="flex items-center gap-2 z-20"
              variants={headerVariants}
            >
              <TrendingUp className="size-6 text-primary" />
              <h2 className="text-2xl font-bold">Trending Restaurants</h2>
            </motion.div>
            <motion.p 
              className="text-sm pb-6 pt-2 text-muted-foreground"
              variants={headerVariants}
            >
              Popular restaurants climbing on Resy right now
            </motion.p>

            {loadingTrending ? (
              <div className="flex items-center justify-center h-[400px]">
                <p className="text-muted-foreground">
                  Loading trending restaurants...
                </p>
              </div>
            ) : trendingRestaurants.length > 0 ? (
              <motion.div 
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6"
                variants={containerVariants}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: CARD_VIEWPORT_MARGIN }}
              >
                {trendingRestaurants.map((restaurant) => {
                  const hasAllReservationDetails =
                    reservationForm.date &&
                    reservationForm.timeSlot &&
                    reservationForm.partySize;

                  return (
                    <motion.div key={restaurant.id} variants={cardVariants}>
                      <RestaurantGridCard
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
                    </motion.div>
                  );
                })}
              </motion.div>
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
          </motion.section>

          {/* Top Rated Restaurants */}
          <motion.section 
            className="mt-12"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: VIEWPORT_TRIGGER_MARGIN }}
            variants={sectionVariants}
          >
            <motion.div 
              className="flex items-center gap-2"
              variants={headerVariants}
            >
              <Star className="size-6 text-primary" />
              <h2 className="text-2xl font-bold">Top Rated Restaurants</h2>
            </motion.div>
            <motion.p 
              className="text-sm pb-6 pt-2 text-muted-foreground"
              variants={headerVariants}
            >
              The highest-rated restaurants on Resy right now
            </motion.p>

            {loadingTopRated ? (
              <div className="flex items-center justify-center h-[400px]">
                <p className="text-muted-foreground">
                  Loading top-rated restaurants...
                </p>
              </div>
            ) : topRatedRestaurants.length > 0 ? (
              <motion.div 
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6"
                variants={containerVariants}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: CARD_VIEWPORT_MARGIN }}
              >
                {topRatedRestaurants.map((restaurant, index) => (
                  <motion.div key={index} variants={cardVariants}>
                    <RestaurantGridCard
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
                    />
                  </motion.div>
                ))}
              </motion.div>
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
          </motion.section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
