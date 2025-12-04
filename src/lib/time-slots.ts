/**
 * Generate time slots in 15-minute intervals for the entire day
 */
export function generateTimeSlots() {
  const slots = [];
  for (let hour = 0; hour < 24; hour++) {
    // for testing
    for (let minute = 0; minute < 60; minute += 1) {
      // for (let minute = 0; minute < 60; minute += 15) {
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
