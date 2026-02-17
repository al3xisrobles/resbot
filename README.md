# Resbot

A full-stack web application for automating Resy restaurant reservations with real-time availability tracking and intelligent sniping.

## Features

- 🔍 **Smart Search** - Search restaurants by name, cuisine, neighborhood, and price range with map-based filtering
- 📅 **Availability Tracking** - Real-time reservation slot monitoring with calendar views
- ⚡ **Reservation Sniping** - Automated booking at exact drop times with millisecond precision
- 🔐 **Secure Authentication** - Firebase-based user authentication with per-user credential storage
- 📊 **Trending Insights** - Discover popular and top-rated restaurants
- 🗺️ **Interactive Maps** - Geographic search with Google Maps integration
- 🤖 **AI Summaries** - Gemini-powered restaurant insights and recommendations

## Tech Stack

### Frontend
- **React** + **TypeScript** - Type-safe UI components
- **Vite** - Fast build tooling
- **Tailwind CSS** + **shadcn/ui** - Modern, accessible component library
- **Firebase SDK** - Authentication and real-time data

### Backend
- **Firebase Cloud Functions** (Python) - Serverless API endpoints
- **Firestore** - User data and credential storage
- **Cloud Scheduler** - Precise timing for reservation drops
- **Google Gemini AI** - Restaurant recommendations
- **Google Maps API** - Venue photos and location data

## Project Structure

```
resy-bot/
├── src/                    # React frontend
│   ├── components/        # Reusable UI components
│   ├── pages/            # Route pages
│   ├── lib/              # API clients and interfaces
│   └── services/         # Firebase configuration
├── functions/             # Python Cloud Functions
│   ├── api/              # API endpoint modules
│   │   ├── onboarding.py # Resy account connection
│   │   ├── search.py     # Restaurant search
│   │   ├── venue.py      # Venue details
│   │   ├── snipe.py      # Reservation automation
│   │   └── utils.py      # Shared utilities
│   └── requirements.txt
└── firestore.rules       # Database security rules
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- Firebase CLI
- Google Cloud Project with APIs enabled:
  - Firestore
  - Cloud Functions
  - Cloud Scheduler
  - Maps API
  - Gemini API

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd resy-bot
   ```

2. **Install frontend dependencies**
   ```bash
   npm install
   ```

3. **Install backend dependencies**
   ```bash
   cd functions
   pip install -r requirements.txt
   cd ..
   ```

4. **Configure Firebase**
   - Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
   - Enable Authentication, Firestore, and Cloud Functions
   - Update `src/services/firebase.ts` with your Firebase config

5. **Set up environment variables**
   Create `functions/.env`:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   GOOGLE_MAPS_API_KEY=your_maps_api_key
   RESY_API_KEY=VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5
   ```

### Development

**Run frontend (with emulators)**
```bash
npm run dev
```

**Run Firebase emulators**
```bash
firebase emulators:start
```

**Deploy Cloud Functions**
```bash
firebase deploy --only functions
```

## How It Works

### Resy Account Connection

1. User signs up with Firebase Authentication
2. User navigates to `/onboarding` and enters Resy credentials
3. Backend authenticates with Resy API using static API key
4. Auth token and payment info stored in Firestore (password never saved)
5. All future API calls use stored credentials per user

### Reservation Sniping

1. User selects restaurant, date, time, and party size
2. Snipe job created in Firestore with target drop time
3. Cloud Scheduler triggers Cloud Function at precise moment
4. Function polls Resy API with sub-second timing
5. Reservation automatically booked when slots become available
6. User notified of success/failure

## Security

- ✅ Passwords never stored (only OAuth tokens)
- ✅ Row-level security via Firestore rules
- ✅ Per-user credential isolation
- ✅ CORS protection on all endpoints
- ✅ Authentication required for all operations

## API Endpoints

### Cloud Functions

- `POST /start_resy_onboarding` - Connect Resy account
- `GET /search` - Search restaurants
- `GET /search_map` - Map-based search
- `GET /venue` - Venue details
- `GET /calendar` - Availability calendar
- `POST /run_snipe` - Execute reservation snipe
- `GET /climbing` - Trending restaurants
- `GET /top_rated` - Top-rated restaurants

All endpoints accept `userId` parameter for authenticated requests.

## License

MIT
