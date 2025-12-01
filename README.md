# Resy Bot

A comprehensive automated reservation system for Resy with both a Python backend API and a modern React web interface. Automatically search for and book restaurant reservations as soon as they become available.

## Overview

Resy-Bot leverages Resy's API endpoints to make automated reservation calls right when reservations become available. The system consists of:

- **Backend**: Python-based automation engine with Flask API
- **Frontend**: Modern React web interface with AI-powered insights
- **Firebase**: Real-time database for caching restaurant data

## Features

### Backend

- **Automated Reservations** - Book tables the moment they become available
- **Venue Search** - Look up restaurant details by venue ID
- **Timed Execution** - Schedule reservation attempts for specific drop times
- **Interactive CLI** - Beautiful console interface with guided prompts
- **REST API** - Flask server for web interface integration
- **AI Insights** - Google Gemini-powered reservation recommendations

### Frontend

- **Resy-Themed Design** - Professional red color scheme matching Resy's brand
- **Responsive Layout** - Works on desktop, tablet, and mobile
- **Restaurant Search** - Search and view detailed venue information
- **Reservation Management** - Create and configure automated reservations
- **AI-Powered Insights** - Get intelligent reservation tips and recommendations
- **Restaurant Photos** - View high-quality venue images
- **Firebase Caching** - Fast loading with persistent data storage
- **Social Links** - Quick access to Google Maps and Resy

## Tech Stack

### Backend

- **Python 3.x** - Core language
- **Flask** - REST API framework
- **Pydantic** - Request/response serialization
- **Requests** - HTTP client for Resy API
- **Rich** - Beautiful console output
- **Questionary** - Interactive CLI prompts
- **Google Generative AI** - AI-powered insights

### Frontend

- **React 19** - Modern React with the compiler
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **Tailwind CSS v4** - Utility-first styling
- **shadcn/ui** - High-quality component library
- **Lucide React** - Beautiful icons
- **Firebase** - Realtime Database for caching
- **date-fns** - Date formatting and manipulation

## Quick Start

### Prerequisites

- Python 3.x
- Node.js 16+ and npm
- Resy account credentials

### Backend Setup

1. Navigate to the backend directory:

```bash
cd backend
```

2. Run the setup script (recommended):

```bash
./setup.sh
```

Or set up manually:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

3. Create a `credentials.json` file:

```json
{
  "api_key": "<api-key>",
  "token": "<api-token>",
  "payment_method_id": <payment-method>,
  "email": "<email>",
  "password": "<password>"
}
```

4. Set up environment variables in `.env`:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
```

Note: The Google Places API key is required for Google Maps link generation. Get your API key from the [Google Cloud Console](https://console.cloud.google.com/) and enable the Places API.

5. Start the Flask server:

```bash
./start_server.sh
```

The API will be available at `http://localhost:3001`

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Configuration

### Backend Configuration

#### ResyConfig (credentials.json)

Specifies credentials for your Resy account. Find these values in the Network tab of your browser's developer tools:

- `api_key` - Found in request headers under `Authorization` as `ResyAPI api_key="<api-key>"`
- `token` - Found in request headers under `X-Resy-Auth-Token`
- `payment_method_id` - Found in the request body to the `/3/book` endpoint
- `email` - Your Resy account email
- `password` - Your Resy account password

#### TimedReservationRequest

For automated timed reservations, create a JSON file with this structure:

```json
{
  "reservation_request": {
    "party_size": 4,
    "venue_id": 12345,
    "window_hours": 1,
    "prefer_early": false,
    "ideal_date": "2023-03-30",
    "days_in_advance": 14,
    "ideal_hour": 19,
    "ideal_minute": 30,
    "preferred_type": "Dining Room"
  },
  "expected_drop_hour": "10",
  "expected_drop_minute": "0"
}
```

**Field Descriptions:**

- `party_size` - Number of guests
- `venue_id` - Restaurant ID (found in Network tab, `/2/config` endpoint URL params)
- `window_hours` - Hours before/after ideal time to search
- `prefer_early` - Prefer earlier slot when two slots are equidistant
- `ideal_date` - Target reservation date (don't use with `days_in_advance`)
- `days_in_advance` - Days from now when reservation opens (don't use with `ideal_date`)
- `ideal_hour` - Preferred hour (24-hour format)
- `ideal_minute` - Preferred minute
- `preferred_type` - Optional seating type filter
- `expected_drop_hour` - Hour when reservations open
- `expected_drop_minute` - Minute when reservations open

### Firebase Configuration

Firebase is pre-configured in the frontend. The Realtime Database caches:

- AI-powered reservation insights
- Restaurant photos
- Social links (Google Maps, Resy)

Data persists across sessions and users, reducing API calls and improving load times.

## Usage

### Backend

#### Interactive Mode (Recommended)

Run the interactive console UI:

```bash
cd backend
python main.py
```

Features:

- 🔍 Search for restaurant info by venue ID
- 📅 Make reservations with guided prompts
- Easy navigation with arrow keys and Enter

#### File-Based Mode

Run with a reservation config file:

```bash
python main.py -r reservation.json
```

With custom credentials:

```bash
python main.py -c custom_credentials.json -r reservation.json
```

The application waits until the specified drop time to begin searching and automatically books when a slot is found.

#### API Server

Start the Flask server:

```bash
./start_server.sh
```

**Available Endpoints:**

- `GET /api/search?query={venue_name}` - Search for restaurants
- `GET /api/venue/{venue_id}` - Get venue details
- `POST /api/gemini-search` - Get AI-powered insights
- `GET /api/calendar/{venue_id}?party_size={size}` - Get availability
- `GET /api/venue-photo/{venue_id}` - Get venue photo
- `POST /api/reservation` - Create a reservation

#### Help

View all CLI options:

```bash
python main.py --help
```

### Frontend

1. Start the backend server (see above)
2. Start the frontend dev server: `npm run dev`
3. Open `http://localhost:5173` in your browser

**Main Features:**

- **Search Page** - Search restaurants and view details
- **Venue Detail Page** - View AI insights, photos, and make reservations
- **AI Insights** - Get smart recommendations for booking
- **Calendar View** - See available time slots
- **One-Click Reserve** - Automated reservation booking

## Project Structure

```
resy-bot/
├── backend/
│   ├── api/                    # API modules (formerly resy_bot)
│   │   ├── __init__.py
│   │   ├── api_access.py      # Resy API client
│   │   ├── constants.py       # Configuration constants
│   │   ├── errors.py          # Custom exceptions
│   │   ├── logging.py         # Logging utilities
│   │   ├── manager.py         # Reservation manager
│   │   ├── model_builders.py  # Request builders
│   │   ├── models.py          # Pydantic models
│   │   └── selectors.py       # Slot selection logic
│   ├── app.py                 # Flask API server
│   ├── main.py                # CLI entry point
│   ├── requirements.txt       # Python dependencies
│   ├── setup.sh              # Setup script
│   ├── start_server.sh       # Server startup script
│   └── credentials.json      # Resy credentials (not in git)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/           # shadcn/ui components
│   │   │   ├── Header.tsx
│   │   │   └── Footer.tsx
│   │   ├── contexts/
│   │   │   └── VenueContext.tsx  # Global state
│   │   ├── lib/
│   │   │   ├── api.ts        # API client
│   │   │   ├── utils.ts      # Utilities
│   │   │   └── time-slots.ts # Time slot helpers
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   └── VenueDetailPage.tsx
│   │   ├── services/
│   │   │   └── firebase.ts   # Firebase integration
│   │   ├── App.tsx           # Main component
│   │   ├── main.tsx          # Entry point
│   │   └── index.css         # Global styles
│   ├── package.json
│   └── vite.config.ts
│
└── README.md                  # This file
```

## API Documentation

### Backend API Endpoints

#### GET /api/search

Search for restaurants by name.

**Query Parameters:**

- `query` (string) - Restaurant name to search

**Response:**

```json
{
  "results": [
    {
      "id": 12345,
      "name": "Restaurant Name",
      "type": "Cuisine Type",
      "location": "Neighborhood"
    }
  ]
}
```

#### GET /api/venue/{venue_id}

Get detailed venue information.

**Response:**

```json
{
  "id": 12345,
  "name": "Restaurant Name",
  "type": "Cuisine Type",
  "price_range": 3,
  "location": {
    "neighborhood": "Downtown",
    "address": "123 Main St"
  },
  "rating": 4.5
}
```

#### POST /api/gemini-search

Get AI-powered reservation insights.

**Request Body:**

```json
{
  "venue_name": "Restaurant Name",
  "venue_id": "12345"
}
```

**Response:**

```json
{
  "answer_text": "This restaurant is known for...",
  "groundingChunks": [...],
  "webSearchQueries": [...]
}
```

#### GET /api/calendar/{venue_id}

Get available time slots.

**Query Parameters:**

- `party_size` (integer) - Number of guests

**Response:**

```json
{
  "slots": [
    {
      "date": "2023-03-30",
      "time": "19:30",
      "available": true,
      "config_id": "abc123"
    }
  ]
}
```

#### POST /api/reservation

Create a reservation.

**Request Body:**

```json
{
  "venue_id": 12345,
  "party_size": 2,
  "date": "2023-03-30",
  "time": "19:30",
  "config_id": "abc123"
}
```

## Color Theme

The interface uses Resy's signature red color scheme:

- **Primary Color**: Red (`oklch(0.55 0.22 25)`)
- **Background**: Light gray (`oklch(0.99 0 0)`)
- **Card Background**: White (`oklch(1 0 0)`)

## Development

### Backend Development

**Run tests:**

```bash
cd backend
pytest
```

**Linting:**

```bash
flake8
```

### Frontend Development

**Type checking:**

```bash
npm run build
```

**Linting:**

```bash
npm run lint
```

**Add new shadcn/ui components:**

```bash
npx shadcn@latest add [component-name]
```

### Building for Production

**Backend:**
The Flask server is production-ready. For deployment, consider using Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:3001 app:app
```

**Frontend:**

```bash
npm run build
npm run preview
```

Build output will be in `frontend/dist/`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT

## Acknowledgments

- Thanks to Resy for their API
- Built with shadcn/ui component library
- AI insights powered by Google Gemini
- Icons from Lucide React

## Support

For issues, questions, or contributions, please open an issue on GitHub.
