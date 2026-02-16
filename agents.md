# Feature Slicing Architecture

This project uses feature slicing with unidirectional data flow: `Common → Features → Pages → App`.

**Directory Structure:**

- `common/` - Shared utilities, components, hooks, atoms (no cross-layer imports)
- `features/` - Isolated feature modules (can import from `common/`, not other features)
- `pages/` - Page composition layer (composes features into pages)
- `app/` - Application entry point

**Key Rules:**

- Features cannot import from other features (use relative imports within a feature)
- Use `.private.ts/tsx` suffix for internal feature files
- Pages compose features; features are self-contained units
- Common layer contains truly shared code used by multiple features
- Whenever interacting with the resy API, be sure to use the logic inside functions/api/resy_client. Also ensure to look at the schemas for responses inside response_schemas.py.

---

# Python Backend Guidelines (`functions/` directory)

When working in the `functions/` directory, follow these pylint-compliant coding standards:

## Logging Best Practices

**Always use % formatting, NOT f-strings:**

```python
# ✅ Good
logger.error("Error fetching calendar: %s", e)
logger.info("User %s authenticated successfully", user_id)

# ❌ Bad
logger.error(f"Error fetching calendar: {e}")
logger.info(f"User {user_id} authenticated successfully")
```

**Why:** This avoids unnecessary string formatting when logging is disabled at certain levels, improving performance.

## Code Style

**Line Length:**

- Maximum 120 characters per line
- Break long lines using parentheses for multi-line expressions

**Import Order:**

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# ✅ Good
import logging
import time
from datetime import datetime

import requests
from firebase_functions.https_fn import on_request

from .utils import load_credentials
```

**Exception Handling:**

- Always use `from e` when re-raising exceptions to preserve traceback:

```python
# ✅ Good
except requests.exceptions.RequestException as e:
    logger.error("Request failed: %s", e)
    raise Exception("Failed to connect") from e
```

- Avoid catching bare `Exception` when possible (use specific exception types)
- Move `traceback` imports to top level, not inside exception handlers

## Code Quality

**Unused Variables/Arguments:**

- Prefix unused variables/arguments with `_`:

```python
def filter_side_effect(hits, _filters, seen_ids, **_kwargs):
    # _filters and _kwargs are intentionally unused
    return hits[:5], {}, seen_ids
```

**No-else-return:**

- Don't use `elif` after a `return` statement:

```python
# ✅ Good
if condition:
    return value
if other_condition:
    return other_value

# ❌ Bad
if condition:
    return value
elif other_condition:
    return other_value
```

**F-strings:**

- Don't use f-strings without interpolation:

```python
# ✅ Good
logger.info("Processing request")

# ❌ Bad
logger.info(f"Processing request")
```

**Requests Timeout:**

- Always include `timeout` parameter in `requests` calls:

```python
response = requests.get(url, headers=headers, timeout=30)
```

## Running Pylint

```bash
cd functions
source venv/bin/activate
pylint api/          # Check all API code
pylint api/tests/    # Check test files
```

**Target Score:** Maintain 9.5+/10 pylint rating

---

# Component Styling Consistency

**Design Tokens:** Use CSS custom properties from `index.css` for consistent rounding and sizing:

- `--radius-pill`: Fully rounded (hero controls, pills)
- `--radius-control`: Form controls (default selects, inputs)
- `--radius-surface`: Popovers, dropdowns, cards
- `--radius-inner`: Items, tags within containers
- `--height-control-sm/default/lg/xl`: Consistent component heights

**Component Variants:** Use variant props instead of custom classes:

- `Select`: `variant="pill"` for hero/pill style, default for forms
- `Input`: `variant="pill"` for search bars, default for forms
- `DatePickerTrigger`: Unified date picker button (replaces custom buttons)
- `Button`: Use size variants (`sm`, `default`, `lg`, `icon`, `icon-sm`, `icon-lg`)

**Rules:**

- Never use inline `rounded-full` or custom border-radius classes—use component variants
- Hero/search controls use `variant="pill"`, form controls use default
- All popovers/dropdowns use `--radius-surface` automatically
- Use `DatePickerTrigger` instead of custom date button implementations

---

# Sentry Error Monitoring & Logging

This project uses Sentry for error tracking, logging, and performance monitoring.

## Integration Level Required

**Full Integration Required:** When adding Sentry to new code or modifying existing code, implement comprehensive Sentry monitoring:

1. **Error Boundary**: Wrap the app with `Sentry.ErrorBoundary` to catch React rendering errors
2. **User Context**: Set user context (`Sentry.setUser`) on login/logout in AuthContext
3. **API Tracing**: Wrap all API calls with `Sentry.startSpan` for performance monitoring
4. **Exception Capture**: Add `Sentry.captureException(error)` to ALL catch blocks and error handlers
5. **React Router Integration**: Use Sentry's React Router integration for route change tracking

**When adding new features or modifying existing code:**

- All `try/catch` blocks must include `Sentry.captureException(error)`
- All API functions must be wrapped with `Sentry.startSpan` with appropriate `op` and `name`
- User actions (button clicks, form submissions) should use `Sentry.startSpan` for meaningful operations
- React component errors should be caught by the error boundary

## Error / Exception Tracking

Use `Sentry.captureException(error)` to capture an exception and log the error in Sentry.
Use this in try catch blocks or areas where exceptions are expected

## Tracing Examples

Spans should be created for meaningful actions within an applications like button clicks, API calls, and function calls
Ensure you are creating custom spans with meaningful names and operations
Use the `Sentry.startSpan` function to create a span
Child spans can exist within a parent span

### Custom Span instrumentation in component actions

```javascript
function TestComponent() {
  const handleTestButtonClick = () => {
    // Create a transaction/span to measure performance
    Sentry.startSpan(
      {
        op: "ui.click",
        name: "Test Button Click",
      },
      (span) => {
        const value = "some config";
        const metric = "some metric";

        // Metrics can be added to the span
        span.setAttribute("config", value);
        span.setAttribute("metric", metric);

        doSomething();
      }
    );
  };

  return (
    <button type="button" onClick={handleTestButtonClick}>
      Test Sentry
    </button>
  );
}
```

### Custom span instrumentation in API calls

```javascript
async function fetchUserData(userId) {
  return Sentry.startSpan(
    {
      op: "http.client",
      name: `GET /api/users/${userId}`,
    },
    async () => {
      const response = await fetch(`/api/users/${userId}`);
      const data = await response.json();
      return data;
    }
  );
}
```

## Logs

Where logs are used, ensure Sentry is imported using `import * as Sentry from "@sentry/react"`
Enable logging in Sentry using `Sentry.init({ enableLogs: true })`
Reference the logger using `const { logger } = Sentry`
Sentry offers a consoleLoggingIntegration that can be used to log specific console error types automatically without instrumenting the individual logger calls

### Logger Examples

`logger.fmt` is a template literal function that should be used to bring variables into the structured logs.

```javascript
logger.trace("Starting database connection", { database: "users" });
logger.debug(logger.fmt`Cache miss for user: ${userId}`);
logger.info("Updated profile", { profileId: 345 });
logger.warn("Rate limit reached for endpoint", {
  endpoint: "/api/results/",
  isEnterprise: false,
});
logger.error("Failed to process payment", {
  orderId: "order_123",
  amount: 99.99,
});
logger.fatal("Database connection pool exhausted", {
  database: "users",
  activeConnections: 100,
});
```
