// src/components/Hero.tsx
import { SearchBar } from "@/components/SearchBar";
import { TIME_SLOTS } from "@/lib/time-slots";
import { useAtom } from "jotai";
import { reservationFormAtom } from "@/atoms/reservationAtoms";
import { UnifiedSearchControls } from "@/components/ui/unified-search-controls";
import chooseIllustration from "@/assets/undraw_choose_5kz4.svg";
import timeManagementIllustration from "@/assets/undraw_time-management_4ss6.svg";
import mailSentIllustration from "@/assets/undraw_mail-sent_ujev.svg";
import GeometricPanelRight from "@/assets/GeometricPanelRight.svg";
import GeometricPanelLeft from "@/assets/GeometricPanelLeft.svg";

const HOW_IT_WORKS_STEPS = [
  {
    id: 1,
    title: "Plan Your Snipe",
    description: "Pick the restaurant, date, time window, and party size.",
    image: chooseIllustration,
    alt: "Choose",
  },
  {
    id: 2,
    title: "We Snipe at Drop Time",
    description:
      "At the exact drop time, our bot finds the best slot and races to book it instantly.",
    image: timeManagementIllustration,
    alt: "Time Management",
  },
  {
    id: 3,
    title: "Get Notified",
    description:
      "You'll receive an email from Resy if we secure the reservation. If not, we'll explain happened.",
    image: mailSentIllustration,
    alt: "Mail Sent",
  },
];

export function Hero() {
  const [reservationForm, setReservationForm] = useAtom(reservationFormAtom);
  return (
    <section className="min-h-[85vh] sm:min-h-[80vh] md:min-h-[75vh] lg:min-h-[70vh] xl:min-h-0 relative pt-4 pb-10 sm:pt-20 sm:pb-16 md:pb-20 lg:pb-24 px-4 md:px-0">
      {/* Decorative geometric panels */}
      <div className="pointer-events-none absolute inset-0 overflow-y-visible overflow-x-hidden -z-10">
        {/* Right side panel */}
        <img
          src={GeometricPanelRight}
          alt=""
          aria-hidden="true"
          className="hidden blur-2xl md:block absolute -right-28 -top-6 opacity-20 max-w-xs lg:max-w-md"
        />

        {/* Left side panel, a bit lower */}
        <img
          src={GeometricPanelLeft}
          alt=""
          aria-hidden="true"
          className="hidden md:block blur-2xl absolute -left-28 top-1/10 opacity-20 max-w-xs lg:max-w-md"
        />
      </div>

      <div className="max-w-4xl mx-auto text-center z-20">
        <h1 className="relative text-5xl sm:text-6xl md:text-7xl font-extrabold z-10 tracking-tight">
          Book Impossible Reservations
          {/* BOOK IMP
          <span className="relative inline-block">
            <img
              src={GlitchedPlate}
              alt="O"
              className="inline-block w-10 h-10 sm:w-16 sm:h-16 md:w-14 md:h-14 align-middle pointer-events-none select-none -mt-2 sm:-mt-3 ml-0.5 sm:ml-1"
            />
          </span>
          SSIBLE RESERVATIONS */}
        </h1>
        <p className="relative mt-3 text-sm sm:text-base w-[70%] mx-auto z-10 text-muted-foreground">
          Tell us where you want to eat—we monitor when reservations drop and
          instantly secure the reservation for you.
        </p>
      </div>

      {/* Search + controls */}
      <div className="mt-8 flex flex-col items-center gap-4 z-20">
        {/* Search bar */}
        <div className="w-full max-w-2xl md:px-0">
          <SearchBar
            className="relative rounded-full border bg-background"
            inputClassName="h-12 sm:h-14 pl-6 pr-12 rounded-full text-sm sm:text-base"
            placeholderText="Search restaurants or cuisines (e.g., Carbone)"
          />
        </div>

        {/* Unified party size / date / time control */}
        <UnifiedSearchControls
          partySize={reservationForm.partySize}
          onPartySizeChange={(partySize) =>
            setReservationForm({ ...reservationForm, partySize })
          }
          date={reservationForm.date}
          onDateChange={(date) =>
            setReservationForm({ ...reservationForm, date })
          }
          timeSlot={reservationForm.timeSlot}
          onTimeSlotChange={(timeSlot) =>
            setReservationForm({ ...reservationForm, timeSlot })
          }
          timeSlots={TIME_SLOTS}
          showSearchButton={false}
        />
      </div>

      {/* --- How Reservation Sniping Works placeholder --- */}
      <div className="mt-12 lg:mt-10 xl:mt-8 text-center w-full z-20">
        <p className="text-xs mb-4 font-medium tracking-[0.18em] uppercase text-muted-foreground">
          How Reservation Sniping Works
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mx-auto max-w-4xl">
          {HOW_IT_WORKS_STEPS.map((step) => (
            <div
              key={step.id}
              className="flex flex-row gap-4 sm:gap-0 sm:flex-col items-center sm:text-center p-6 rounded-xl bg-card border border-border hover:border-primary/10 hover:shadow-sm transition-all h-full"
            >
              <div className="shrink-0 w-24 h-24 sm:w-full sm:h-46 bg-muted/40 rounded-lg flex items-center justify-center mb-0 sm:mb-4 p-2 sm:p-8">
                <img
                  src={step.image}
                  alt={step.alt}
                  className="w-32 h-32 object-contain"
                />
              </div>
              <div className="flex flex-col gap-2 items-start sm:items-center">
                <h3 className="font-semibold text-base">
                  {step.id}. {step.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
