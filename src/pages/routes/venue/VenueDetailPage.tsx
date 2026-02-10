import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useAtom } from "jotai";
import { motion } from "framer-motion";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import {
    SidebarProvider,
    Sidebar,
    SidebarContent,
    SidebarInset,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { SkeletonRect } from "@/components/ui/skeleton";
import ResbotLogo from "@/assets/ResbotLogoRedWithText.svg";
import { useVenueData } from "@/features/venue-details/api/useVenueData";
import { VenueHeader } from "@/features/venue-details/components/VenueHeader";
import { VenueInfo } from "@/features/venue-details/components/VenueInfo";
import { PhotoCarousel } from "@/features/venue-details/components/PhotoCarousel";
import { VenueDetailsSkeleton } from "@/features/venue-details/components/VenueDetailsSkeleton";
import { PhotoCarouselSkeleton } from "@/features/venue-details/components/PhotoCarouselSkeleton";
import { useAiInsights } from "@/features/ai-insights/api/useAiInsights";
import { AiInsightsSection } from "@/features/ai-insights/components/AiInsightsSection";
import { AiInsightsSkeleton } from "@/features/ai-insights/components/AiInsightsSkeleton";
import { useCalendarData } from "@/features/availability-calendar/api/useCalendarData";
import { CalendarWithSlots } from "@/features/availability-calendar/components/CalendarWithSlots";
import { CalendarSkeleton } from "@/features/availability-calendar/components/CalendarSkeleton";
import { useScheduleReservation } from "@/features/reservation/api/useScheduleReservation";
import { ReservationForm } from "@/features/reservation/components/ReservationForm";
import { reservationFormAtom, type ReservationFormState } from "@/features/reservation/atoms/reservationFormAtom";

// ==========================================
// ANIMATION CONSTANTS
// ==========================================

/** Easing curve for smooth pop-up animations (ease-out-quad) */
const EASE_OUT_QUAD: [number, number, number, number] = [
    0.25, 0.46, 0.45, 0.94,
];

/** Duration for quick pop-up animations */
const POPUP_DURATION = 0.35;

/** Stagger delay between items */
const STAGGER_DELAY = 0.08;

/** Initial delay before animations start */
const INITIAL_DELAY = 0.05;

/** Y-offset for fade-up animations */
const FADE_UP_OFFSET = 15;

/** Scale for hidden state */
const HIDDEN_SCALE = 0.97;

// ==========================================
// ANIMATION VARIANTS
// ==========================================

const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: {
            staggerChildren: STAGGER_DELAY,
            delayChildren: INITIAL_DELAY,
        },
    },
};

const itemVariants = {
    hidden: {
        opacity: 0,
        y: FADE_UP_OFFSET,
        scale: HIDDEN_SCALE,
    },
    visible: {
        opacity: 1,
        y: 0,
        scale: 1,
        transition: {
            duration: POPUP_DURATION,
            ease: EASE_OUT_QUAD,
        },
    },
};

export function VenueDetailPage() {
    const [searchParams] = useSearchParams();
    const venueId = searchParams.get("id");
    const [reservationForm, setReservationForm] = useAtom(reservationFormAtom);
    const [reserveOnEmulation, setReserveOnEmulation] = useState(false);

    // Default to today's date if no date is selected
    useEffect(() => {
        if (!reservationForm.date) {
            const today = new Date();
            // Reset time to midnight to avoid timezone issues
            today.setHours(0, 0, 0, 0);
            setReservationForm((prev: ReservationFormState) => ({ ...prev, date: today }));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Only run once on mount

    // Fetch venue data
    const {
        venueData,
        loadingVenue,
        venueError,
        venueLinks,
        loadingLinks,
    } = useVenueData(venueId);

    // Fetch AI insights
    const {
        aiSummary,
        loadingAi,
        aiError,
        aiLastUpdated,
        refreshAiSummary,
    } = useAiInsights(venueId, venueData?.name || null);

    // Fetch calendar data
    const { calendarData, loadingCalendar, calendarError } = useCalendarData(
        venueId,
        reservationForm.partySize
    );

    // Track if we've loaded initial data to avoid showing skeletons on updates
    const [hasInitialData, setHasInitialData] = useState(false);

    useEffect(() => {
        if (venueData && calendarData && venueLinks && !hasInitialData) {
            setHasInitialData(true);
        }
    }, [venueData, calendarData, venueLinks, hasInitialData]);

    // Memoize callbacks to prevent CalendarWithSlots from re-rendering
    const handleDateSelect = useCallback((date: Date | undefined) => {
        setReservationForm((prev) => ({ ...prev, date }));
    }, [setReservationForm]);

    const handleTimeSlotSelect = useCallback((timeSlot: string) => {
        setReservationForm((prev) => ({ ...prev, timeSlot }));
    }, [setReservationForm]);

    // Schedule reservation
    const {
        scheduleReservation,
        loadingSubmit,
        error,
        reservationScheduled,
    } = useScheduleReservation(venueId, reservationForm, reserveOnEmulation);

    // Critical loading state - show main content once venue, calendar, and links are loaded
    // After initial load, don't show skeletons on calendar updates (party size changes)
    const isLoadingCritical = !hasInitialData && (loadingVenue || loadingCalendar || loadingLinks);

    if (!venueId) {
        return (
            <div className="container mx-auto px-4 py-24">
                <Alert variant="destructive">
                    <AlertCircle className="size-4" />
                    <AlertDescription>No venue ID provided</AlertDescription>
                </Alert>
            </div>
        );
    }

    return (
        <SidebarProvider defaultOpen={true}>
            <Sidebar collapsible="none" className="w-1/2 h-[calc(100vh-90px)] **:data-[sidebar=sidebar]:bg-white!">
                <SidebarContent className="overflow-y-auto h-full flex flex-col pt-12 pb-12">
                    <div
                        className="max-w-[650px] w-full ml-auto space-y-4 flex flex-col flex-1"
                        style={{ padding: "0 3rem 0 2rem" }}
                    >
                        {/* Restaurant Details */}
                        {isLoadingCritical ? (
                            <VenueDetailsSkeleton />
                        ) : (
                            <motion.div
                                variants={containerVariants}
                                initial="hidden"
                                animate="visible"
                                className="space-y-4"
                            >
                                {venueError && (
                                    <motion.div variants={itemVariants}>
                                        <Alert variant="destructive">
                                            <AlertCircle className="size-4" />
                                            <AlertDescription>{venueError}</AlertDescription>
                                        </Alert>
                                    </motion.div>
                                )}

                                {venueData && (
                                    <>
                                        <motion.div variants={itemVariants}>
                                            <VenueHeader venueData={venueData} />
                                        </motion.div>
                                        <motion.div variants={itemVariants}>
                                            <Separator />
                                        </motion.div>
                                        <motion.div variants={itemVariants}>
                                            <VenueInfo
                                                venueData={venueData}
                                                venueLinks={venueLinks}
                                                loadingLinks={loadingLinks}
                                            />
                                        </motion.div>
                                    </>
                                )}
                            </motion.div>
                        )}

                        {/* Availability Calendar */}
                        <div className="mt-6">
                            {isLoadingCritical ? (
                                <CalendarSkeleton />
                            ) : (
                                <motion.div
                                    initial={{ opacity: 0, y: FADE_UP_OFFSET, scale: HIDDEN_SCALE }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    transition={{
                                        duration: POPUP_DURATION,
                                        ease: EASE_OUT_QUAD,
                                        delay: INITIAL_DELAY + STAGGER_DELAY * 3,
                                    }}
                                >
                                    <CalendarWithSlots
                                        calendarData={calendarData}
                                        calendarError={calendarError}
                                        reservationForm={reservationForm}
                                        venueId={venueId}
                                        resyLink={venueLinks?.resy || null}
                                        onDateSelect={handleDateSelect}
                                        onTimeSlotSelect={handleTimeSlotSelect}
                                    />
                                </motion.div>
                            )}
                        </div>

                        {/* Footer */}
                        {isLoadingCritical ? (
                            <div className="mt-auto pt-8 text-center flex justify-center flex-row items-center gap-4">
                                <SkeletonRect width={80} height={20} rounding="8" />
                                <span className="flex items-center h-4">
                                    <Separator orientation="vertical" className="h-full opacity-30" />
                                </span>
                                <SkeletonRect width={120} height={16} rounding="8" />
                            </div>
                        ) : (
                            <motion.div
                                initial={{ opacity: 0, y: FADE_UP_OFFSET, scale: HIDDEN_SCALE }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                transition={{
                                    duration: POPUP_DURATION,
                                    ease: EASE_OUT_QUAD,
                                    delay: INITIAL_DELAY + STAGGER_DELAY * 4,
                                }}
                                className="mt-auto pt-8 text-center flex justify-center flex-row items-center gap-4 text-sm text-muted-foreground"
                            >
                                <div className="flex items-center justify-center gap-2">
                                    <img src={ResbotLogo} className="h-5 grayscale" />
                                </div>
                                <span className="flex items-center h-4">
                                    <Separator orientation="vertical" className="h-full" />
                                </span>
                                <p>
                                    Built by{" "}
                                    <a
                                        href="https://www.linkedin.com/in/alexisdrobles"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="underline hover:text-primary"
                                    >
                                        Alexis Robles
                                    </a>
                                </p>
                            </motion.div>
                        )}
                    </div>
                </SidebarContent>
            </Sidebar>
            <SidebarInset className="overflow-y-auto w-1/2 bg-background shadow-[-20px_0_30px_-10px_rgba(0,0,0,0.08)] h-screen">
                <div className="pt-12 pb-32">
                    <div
                        className="max-w-[650px] w-full space-y-6"
                        style={{ paddingLeft: "3rem", paddingRight: "2rem" }}
                    >
                        {/* Restaurant Photos Carousel */}
                        {isLoadingCritical ? (
                            <PhotoCarouselSkeleton />
                        ) : (
                            venueData && (
                                <motion.div
                                    initial={{ opacity: 0, y: FADE_UP_OFFSET, scale: HIDDEN_SCALE }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    transition={{
                                        duration: POPUP_DURATION,
                                        ease: EASE_OUT_QUAD,
                                        delay: INITIAL_DELAY,
                                    }}
                                >
                                    <PhotoCarousel venueData={venueData} venueId={venueId} />
                                </motion.div>
                            )
                        )}

                        {/* Reservation Insights */}
                        <motion.div
                            initial={{ opacity: 0, y: FADE_UP_OFFSET, scale: HIDDEN_SCALE }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            transition={{
                                duration: POPUP_DURATION,
                                ease: EASE_OUT_QUAD,
                                delay: INITIAL_DELAY + STAGGER_DELAY,
                            }}
                            className="space-y-4"
                        >
                            {isLoadingCritical ? (
                                <AiInsightsSkeleton />
                            ) : (
                                <AiInsightsSection
                                    aiSummary={aiSummary}
                                    loadingAi={loadingAi}
                                    aiError={aiError}
                                    aiLastUpdated={aiLastUpdated}
                                    onRefresh={refreshAiSummary}
                                />
                            )}
                        </motion.div>

                        {/* Make a Reservation */}
                        {!isLoadingCritical && (
                            <motion.div
                                initial={{ opacity: 0, y: FADE_UP_OFFSET, scale: HIDDEN_SCALE }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                transition={{
                                    duration: POPUP_DURATION,
                                    ease: EASE_OUT_QUAD,
                                    delay: INITIAL_DELAY + STAGGER_DELAY * 2,
                                }}
                                className="pb-8"
                            >
                                <ReservationForm
                                    reservationForm={reservationForm}
                                    setReservationForm={setReservationForm}
                                    onSchedule={scheduleReservation}
                                    loadingSubmit={loadingSubmit}
                                    error={error}
                                    reservationScheduled={reservationScheduled}
                                    reserveOnEmulation={reserveOnEmulation}
                                    setReserveOnEmulation={setReserveOnEmulation}
                                />
                            </motion.div>
                        )}
                    </div>
                </div>
            </SidebarInset>
        </SidebarProvider>
    );
}
