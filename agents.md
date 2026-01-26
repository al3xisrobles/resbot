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
