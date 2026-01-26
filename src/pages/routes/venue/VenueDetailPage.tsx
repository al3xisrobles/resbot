import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useAtom } from "jotai";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import {
    SidebarProvider,
    Sidebar,
    SidebarContent,
    SidebarInset,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
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
import { reservationFormAtom } from "@/features/reservation/atoms/reservationFormAtom";

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
            setReservationForm((prev) => ({ ...prev, date: today }));
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

    // Schedule reservation
    const {
        scheduleReservation,
        loadingSubmit,
        error,
        reservationScheduled,
    } = useScheduleReservation(venueId, reservationForm, reserveOnEmulation);

    // Critical loading state - show main content once venue, calendar, and links are loaded
    // AI insights can load separately and show their own skeleton
    const isLoadingCritical = loadingVenue || loadingCalendar || loadingLinks;

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
                        className="max-w-[650px] w-full ml-auto space-y-4"
                        style={{ padding: "0 3rem 0 2rem" }}
                    >
                        {/* Restaurant Details */}
                        {isLoadingCritical ? (
                            <VenueDetailsSkeleton />
                        ) : (
                            <>
                                {venueError && (
                                    <Alert variant="destructive">
                                        <AlertCircle className="size-4" />
                                        <AlertDescription>{venueError}</AlertDescription>
                                    </Alert>
                                )}

                                {venueData && (
                                    <div className="space-y-4">
                                        <VenueHeader venueData={venueData} />
                                        <Separator />
                                        <VenueInfo
                                            venueData={venueData}
                                            venueLinks={venueLinks}
                                            loadingLinks={loadingLinks}
                                        />
                                    </div>
                                )}
                            </>
                        )}

                        {/* Availability Calendar */}
                        <div className="mt-6">
                            {isLoadingCritical ? (
                                <CalendarSkeleton />
                            ) : (
                                <CalendarWithSlots
                                    calendarData={calendarData}
                                    calendarError={calendarError}
                                    reservationForm={reservationForm}
                                    venueId={venueId}
                                    resyLink={venueLinks?.resy || null}
                                    onDateSelect={(date) =>
                                        setReservationForm({ ...reservationForm, date })
                                    }
                                    onTimeSlotSelect={(timeSlot) =>
                                        setReservationForm({ ...reservationForm, timeSlot })
                                    }
                                />
                            )}
                        </div>
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
                            venueData && <PhotoCarousel venueData={venueData} venueId={venueId} />
                        )}

                        {/* Reservation Insights */}
                        <div className="space-y-4">
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
                        </div>

                        {/* Make a Reservation */}
                        {!isLoadingCritical && (
                            <div className="pb-8">
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
                            </div>
                        )}
                    </div>
                </div>
            </SidebarInset>
        </SidebarProvider>
    );
}
