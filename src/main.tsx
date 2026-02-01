import * as Sentry from "@sentry/react";
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

Sentry.init({
    dsn: "https://cade39a580854ed15d42ad3b988a6c79@o4510779754610688.ingest.us.sentry.io/4510779764768768",
    // Setting this option to true will send default PII data to Sentry.
    // For example, automatic IP address collection on events
    sendDefaultPii: true,
    // Enable logs
    enableLogs: true,
    // 100% trace sampling to capture every request
    tracesSampleRate: 1.0,
    // Enable trace propagation to backend
    tracePropagationTargets: [
        "localhost",
        /^https:\/\/us-central1-resybot-bd2db\.cloudfunctions\.net/,
        /^http:\/\/127\.0\.0\.1:5001/,
    ],
    // Send console.log, console.warn, and console.error calls as logs to Sentry
    integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.consoleLoggingIntegration({ levels: ["log", "warn", "error"] }),
    ],
});

const container = document.getElementById('root')!;
const root = createRoot(container);
root.render(<App />);
