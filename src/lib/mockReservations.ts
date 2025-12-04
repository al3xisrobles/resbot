export interface Reservation {
  id: string
  venueId: string
  venueName: string
  venueImage: string
  date: string
  time: string
  partySize: number
  status: 'Scheduled' | 'Succeeded' | 'Failed'
  attemptedAt?: number
  note?: string
}

export const mockReservations: Reservation[] = [
  // Scheduled
  {
    id: '1',
    venueId: '5',
    venueName: 'Carbone',
    venueImage: 'https://resizer.otstatic.com/v2/photos/wide-huge/1/25703939.jpg',
    date: '2025-12-05',
    time: '19:00',
    partySize: 2,
    status: 'Scheduled',
  },
  {
    id: '2',
    venueId: '229',
    venueName: 'Don Angie',
    venueImage: 'https://resizer.otstatic.com/v2/photos/wide-huge/2/47761355.jpg',
    date: '2025-12-08',
    time: '18:30',
    partySize: 4,
    status: 'Scheduled',
  },
  {
    id: '3',
    venueId: '1505',
    venueName: 'I Sodi',
    venueImage: 'https://resizer.otstatic.com/v2/photos/wide-huge/1/24041461.jpg',
    date: '2025-12-10',
    time: '20:00',
    partySize: 2,
    status: 'Scheduled',
  },

  // Succeeded
  {
    id: '4',
    venueId: '7',
    venueName: '4 Charles Prime Rib',
    venueImage: 'https://resizer.otstatic.com/v2/photos/wide-huge/2/47654029.jpg',
    date: '2025-11-28',
    time: '19:30',
    partySize: 2,
    status: 'Succeeded',
    attemptedAt: Date.now() - 2 * 24 * 60 * 60 * 1000,
  },
  {
    id: '5',
    venueId: '9088',
    venueName: 'Gage & Tollner',
    venueImage: 'https://resizer.otstatic.com/v2/photos/wide-huge/2/61705076.jpg',
    date: '2025-11-25',
    time: '18:00',
    partySize: 4,
    status: 'Succeeded',
    attemptedAt: Date.now() - 5 * 24 * 60 * 60 * 1000,
  },
  {
    id: '6',
    venueId: '58506',
    venueName: 'Cote',
    venueImage: 'https://resizer.otstatic.com/v2/photos/wide-huge/2/52863456.jpg',
    date: '2025-11-22',
    time: '19:00',
    partySize: 3,
    status: 'Succeeded',
    attemptedAt: Date.now() - 8 * 24 * 60 * 60 * 1000,
  },
  {
    id: '7',
    venueId: '64306',
    venueName: 'Laser Wolf',
    venueImage: 'https://resizer.otstatic.com/v2/photos/wide-huge/5/67586895.jpg',
    date: '2025-11-20',
    time: '20:00',
    partySize: 2,
    status: 'Succeeded',
    attemptedAt: Date.now() - 10 * 24 * 60 * 60 * 1000,
  },

  // Failed
  {
    id: '8',
    venueId: '63495',
    venueName: 'Torrisi',
    venueImage: 'https://resizer.otstatic.com/v2/photos/wide-huge/4/66725524.jpg',
    date: '2025-11-30',
    time: '19:00',
    partySize: 2,
    status: 'Failed',
    attemptedAt: Date.now() - 1 * 24 * 60 * 60 * 1000,
    note: 'No availability found',
  },
  {
    id: '9',
    venueId: '62739',
    venueName: 'The Four Horsemen',
    venueImage: 'https://resizer.otstatic.com/v2/photos/wide-huge/2/66031672.jpg',
    date: '2025-11-29',
    time: '18:30',
    partySize: 4,
    status: 'Failed',
    attemptedAt: Date.now() - 2 * 24 * 60 * 60 * 1000,
    note: 'Booking window closed',
  },
  {
    id: '10',
    venueId: '56242',
    venueName: 'Lilia',
    venueImage: 'https://resizer.otstatic.com/v2/photos/wide-huge/3/63843803.jpg',
    date: '2025-11-27',
    time: '19:30',
    partySize: 2,
    status: 'Failed',
    attemptedAt: Date.now() - 3 * 24 * 60 * 60 * 1000,
    note: 'All slots taken',
  },
]
