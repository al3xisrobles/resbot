# Resy Bot Frontend

Professional web interface for the Resy Bot reservation system.

## Features

- 🔍 **Restaurant Search** - Look up restaurant details by venue ID
- 📅 **Reservation Management** - Create and configure automated reservations
- 🎨 **Resy-Themed Design** - Professional red color scheme matching Resy's brand
- 📱 **Responsive Layout** - Works on desktop, tablet, and mobile

## Tech Stack

- **React 19** - Modern React with the compiler
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **Tailwind CSS v4** - Utility-first styling
- **shadcn/ui** - High-quality component library
- **Lucide React** - Beautiful icons

## Quick Start

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
src/
├── components/
│   └── ui/              # shadcn/ui components
│       ├── button.tsx
│       ├── card.tsx
│       ├── input.tsx
│       ├── label.tsx
│       ├── tabs.tsx
│       └── select.tsx
├── lib/
│   └── utils.ts         # Utility functions
├── App.tsx              # Main application component
├── main.tsx             # Application entry point
└── index.css            # Global styles and theme
```

## Color Theme

The interface uses Resy's signature red color scheme:

- **Primary Color**: Red (`oklch(0.55 0.22 25)`)
- **Background**: Light gray (`oklch(0.99 0 0)`)
- **Card Background**: White (`oklch(1 0 0)`)

## Components

### Restaurant Search Tab

- Search restaurants by venue ID
- Display restaurant information:
  - Name and type
  - Price range
  - Address and neighborhood
  - Rating

### Make Reservation Tab

Configure reservation details:

- **Basic Info**: Venue ID, party size
- **Date & Time**: Reservation date, hour, minute
- **Preferences**: Time window, seating type
- **Drop Time**: When reservations open

## API Integration

Currently, the UI uses placeholder functions. To integrate with the Python backend:

1. Set up a FastAPI/Flask server in the backend
2. Create API endpoints for:
   - `/api/venue/{venue_id}` - Get restaurant info
   - `/api/reservation` - Submit reservation request
3. Replace placeholder functions in `App.tsx` with actual API calls

## Development

### Adding New Components

Use shadcn/ui CLI to add components:

```bash
npx shadcn@latest add [component-name]
```

### Styling

This project uses Tailwind CSS v4 with the `@tailwindcss/vite` plugin. Styles are configured in `src/index.css`.

### Type Safety

TypeScript is configured for strict type checking. Run type checks with:

```bash
npm run build
```

## License

MIT
