// src/components/Hero.tsx
import { motion } from "framer-motion";
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

// ==========================================
// CONTENT CONSTANTS
// ==========================================

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

// ==========================================
// ANIMATION CONSTANTS
// ==========================================

/** Easing curve for smooth pop-up animations (ease-out-quad) */
const EASE_OUT_QUAD: [number, number, number, number] = [
  0.25, 0.46, 0.45, 0.94,
];

/** Duration for hero content animations (heading, tagline) */
const HERO_CONTENT_DURATION = 0.5;

/** Duration for geometric panel fade-in animations */
const PANEL_DURATION = 0.8;

/** Duration for "How It Works" section title animation */
const SECTION_TITLE_DURATION = 0.4;

/** Duration for step card animations */
const CARD_DURATION = 0.3;

/** Stagger delay between hero items (heading → tagline → search bar → controls) */
const HERO_STAGGER_DELAY = 0.1;

/** Initial delay before hero animations start */
const HERO_INITIAL_DELAY = 0.1;

/** Stagger delay between step cards */
const CARD_STAGGER_DELAY = 0.12;

/** Initial delay before step cards animate */
const CARD_INITIAL_DELAY = 0.3;

/** Delay for right geometric panel */
const PANEL_RIGHT_DELAY = 0.2;

/** Delay for left geometric panel */
const PANEL_LEFT_DELAY = 0.3;

/** Delay for "How It Works" section wrapper */
const HOW_IT_WORKS_DELAY = 0.4;

/** Delay for "How It Works" section title */
const HOW_IT_WORKS_TITLE_DELAY = 0.5;

/** Y-offset for fade-up animations (smaller = subtler) */
const FADE_UP_OFFSET = 20;

/** Y-offset for card animations */
const CARD_FADE_UP_OFFSET = 30;

/** Scale for hidden state (slightly smaller for pop-up effect) */
const HIDDEN_SCALE = 0.95;

/** Scale for card hidden state */
const CARD_HIDDEN_SCALE = 0.92;

/** Hover lift amount for cards */
const CARD_HOVER_LIFT = -4;

/** Duration for card hover animation */
const CARD_HOVER_DURATION = 0.2;

// ==========================================
// ANIMATION VARIANTS
// ==========================================

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: HERO_STAGGER_DELAY,
      delayChildren: HERO_INITIAL_DELAY,
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
      duration: HERO_CONTENT_DURATION,
      ease: EASE_OUT_QUAD,
    },
  },
};

const cardContainerVariants = {
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
    y: CARD_FADE_UP_OFFSET,
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

// ==========================================
// COMPONENT
// ==========================================

export function Hero() {
  const [reservationForm, setReservationForm] = useAtom(reservationFormAtom);

  return (
    <section className="min-h-[85vh] sm:min-h-[80vh] md:min-h-[75vh] lg:min-h-[70vh] xl:min-h-0 relative pt-4 pb-10 sm:pt-20 sm:pb-16 md:pb-20 lg:pb-24 px-4 md:px-0">
      {/* Decorative geometric panels */}
      <div className="pointer-events-none absolute inset-0 overflow-y-visible overflow-x-hidden -z-10">
        {/* Right side panel */}
        <motion.img
          src={GeometricPanelRight}
          alt=""
          aria-hidden="true"
          initial={{ opacity: 0, scale: 0.9, x: 20 }}
          animate={{ opacity: 0.2, scale: 1, x: 0 }}
          transition={{
            duration: PANEL_DURATION,
            ease: EASE_OUT_QUAD,
            delay: PANEL_RIGHT_DELAY,
          }}
          className="hidden blur-2xl md:block absolute -right-28 -top-6 max-w-xs lg:max-w-md"
        />

        {/* Left side panel, a bit lower */}
        <motion.img
          src={GeometricPanelLeft}
          alt=""
          aria-hidden="true"
          initial={{ opacity: 0, scale: 0.9, x: -20 }}
          animate={{ opacity: 0.2, scale: 1, x: 0 }}
          transition={{
            duration: PANEL_DURATION,
            ease: EASE_OUT_QUAD,
            delay: PANEL_LEFT_DELAY,
          }}
          className="hidden md:block blur-2xl absolute -left-28 top-1/10 max-w-xs lg:max-w-md"
        />
      </div>

      <motion.div
        className="max-w-4xl mx-auto text-center z-20"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.h1
          className="relative text-5xl sm:text-6xl md:text-7xl font-extrabold z-10 tracking-tight"
          variants={itemVariants}
        >
          Book Impossible Reservations
        </motion.h1>
        <motion.p
          className="relative mt-3 text-sm sm:text-base w-[70%] mx-auto z-10 text-muted-foreground"
          variants={itemVariants}
        >
          Tell us where you want to eat—we monitor when reservations drop and
          instantly secure the reservation for you.
        </motion.p>
      </motion.div>

      {/* Search + controls */}
      <motion.div
        className="mt-8 flex flex-col items-center gap-4 z-20"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Search bar */}
        <motion.div
          className="w-full max-w-2xl md:px-0"
          variants={itemVariants}
        >
          <SearchBar
            className="relative rounded-full border bg-background"
            inputClassName="h-12 sm:h-14 pl-6 pr-12 rounded-full text-sm sm:text-base"
            placeholderText="Search restaurants or cuisines (e.g., Carbone)"
          />
        </motion.div>

        {/* Unified party size / date / time control */}
        <motion.div variants={itemVariants}>
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
        </motion.div>
      </motion.div>

      {/* --- How Reservation Sniping Works --- */}
      <motion.div
        className="mt-12 lg:mt-10 xl:mt-8 text-center w-full z-20"
        initial={{ opacity: 0, y: FADE_UP_OFFSET }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: HERO_CONTENT_DURATION,
          ease: EASE_OUT_QUAD,
          delay: HOW_IT_WORKS_DELAY,
        }}
      >
        <motion.p
          className="text-xs mb-4 font-medium tracking-[0.18em] uppercase text-muted-foreground"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: SECTION_TITLE_DURATION,
            ease: EASE_OUT_QUAD,
            delay: HOW_IT_WORKS_TITLE_DELAY,
          }}
        >
          How Reservation Sniping Works
        </motion.p>

        <motion.div
          className="grid grid-cols-1 lg:grid-cols-3 gap-4 mx-auto max-w-4xl"
          variants={cardContainerVariants}
          initial="hidden"
          animate="visible"
        >
          {HOW_IT_WORKS_STEPS.map((step) => (
            <motion.div
              key={step.id}
              variants={cardVariants}
              whileHover={{
                y: CARD_HOVER_LIFT,
                transition: { duration: CARD_HOVER_DURATION },
              }}
              className="flex flex-row gap-4 sm:gap-0 sm:flex-col items-center sm:text-center p-6 rounded-xl bg-card border border-border hover:border-primary/10 hover:shadow-sm transition-colors h-full"
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
            </motion.div>
          ))}
        </motion.div>
      </motion.div>
    </section>
  );
}
