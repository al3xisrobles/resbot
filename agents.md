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
