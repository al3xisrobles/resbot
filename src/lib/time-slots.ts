/**
 * Generate time slots in 15-minute intervals for the entire day
 */

const useEmulators =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

export function generateTimeSlots() {
  const slots = [];
  const minuteIncrement = useEmulators ? 1 : 15;
  for (let hour = 0; hour < 24; hour++) {
    for (let minute = 0; minute < 60; minute += minuteIncrement) {
      const hour12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
      const period = hour < 12 ? "AM" : "PM";
      const display = `${hour12}:${minute
        .toString()
        .padStart(2, "0")} ${period}`;
      slots.push({ value: `${hour}:${minute}`, display, hour, minute });
    }
  }
  return slots;
}

export const TIME_SLOTS = generateTimeSlots();
