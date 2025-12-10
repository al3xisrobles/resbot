// src/components/Hero.tsx
import { format } from "date-fns";
import { SearchBar } from "@/components/SearchBar";
import { cn } from "@/lib/utils";
import { TIME_SLOTS } from "@/lib/time-slots";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import chooseIllustration from "@/assets/undraw_choose_5kz4.svg";
import timeManagementIllustration from "@/assets/undraw_time-management_4ss6.svg";
import mailSentIllustration from "@/assets/undraw_mail-sent_ujev.svg";
import GeometricPanelRight from "@/assets/GeometricPanelRight.svg";
import GeometricPanelLeft from "@/assets/GeometricPanelLeft.svg";

type HeroProps = {
  reservationForm: import("@/contexts/VenueContext").ReservationFormState;
  setReservationForm: (
    next: import("@/contexts/VenueContext").ReservationFormState
  ) => void;
};

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

export function Hero({ reservationForm, setReservationForm }: HeroProps) {
  return (
    <section className="min-h-[90vh] relative pt-12 pb-10 sm:pt-32 sm:pb-14 px-4 md:px-0">
      {/* Decorative geometric panels */}
      <div className="pointer-events-none absolute inset-0 overflow-y-visible overflow-x-hidden -z-10">
        {/* Right side panel */}
        <img
          src={GeometricPanelRight}
          alt=""
          aria-hidden="true"
          className="hidden md:block absolute -right-28 -top-6 opacity-30 max-w-xs lg:max-w-md"
        />

        {/* Left side panel, a bit lower */}
        <img
          src={GeometricPanelLeft}
          alt=""
          aria-hidden="true"
          className="hidden md:block absolute -left-28 top-1/5 opacity-30 max-w-xs lg:max-w-md"
        />
      </div>

      <div className="max-w-4xl mx-auto text-center z-20">
        <h1 className="relative text-5xl sm:text-6xl md:text-7xl font-extrabold z-10 tracking-tight">
          BOOK IMPO
          {/* <span className="relative inline-block">
            <img
              src={GlitchedPlate}
              alt="O"
              className="inline-block w-10 h-10 sm:w-16 sm:h-16 md:w-14 md:h-14 align-middle pointer-events-none select-none -mt-2 sm:-mt-3 ml-0.5 sm:ml-1"
            />
          </span> */}
          SSIBLE RESERVATIONS
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

        {/* Party size / date / time pills */}
        <div className="w-full max-w-xl flex flex-row gap-3 justify-center z-20">
          {/* Party size pill */}
          <Select
            value={reservationForm.partySize}
            onValueChange={(partySize) =>
              setReservationForm({ ...reservationForm, partySize })
            }
          >
            <SelectTrigger className="rounded-full">
              <SelectValue placeholder="Party size" />
            </SelectTrigger>
            <SelectContent>
              {Array.from({ length: 6 }, (_, i) => i + 1).map((size) => (
                <SelectItem key={size} value={size.toString()}>
                  {size} {size === 1 ? "person" : "people"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Date pill */}
          <Popover>
            <PopoverTrigger asChild>
              <button
                className={cn(
                  "flex h-9 w-full items-center justify-start rounded-full border bg-background px-3 py-2 text-sm shadow-xs ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer hover:bg-accent/50 transition-colors"
                )}
              >
                {reservationForm.date ? (
                  format(reservationForm.date, "EEE, MMM d")
                ) : (
                  <span>Pick a date</span>
                )}
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={reservationForm.date!}
                onSelect={(date) =>
                  setReservationForm({ ...reservationForm, date })
                }
              />
            </PopoverContent>
          </Popover>

          {/* Time pill */}
          <Select
            value={reservationForm.timeSlot}
            onValueChange={(timeSlot) =>
              setReservationForm({ ...reservationForm, timeSlot })
            }
          >
            <SelectTrigger className="rounded-full">
              <SelectValue placeholder="Time" />
            </SelectTrigger>
            <SelectContent>
              {TIME_SLOTS.map((slot) => (
                <SelectItem key={slot.value} value={slot.value}>
                  {slot.display}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* --- How Reservation Sniping Works placeholder --- */}
      <div className="mt-12 text-center w-full z-20">
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
