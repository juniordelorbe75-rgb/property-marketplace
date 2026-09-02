# Property Marketplace

A full-stack marketplace for discovering, listing, saving, and discussing properties. Every authenticated account can act as both a buyer and a seller.

## Current capabilities

- Searchable, paginated property browsing with stable `PM-…` references
- Sale and rental listings in USD or DOP
- Multiple images, amenities, map links, favorites, and recently viewed listings
- Seller inventory, engagement statistics, availability controls, and safe updates
- Authenticated, duplicate-safe listing reports for scams, misleading details, duplicates, availability, and inappropriate content
- Allowlist-protected moderation queue with status filters, review notes, and stale-update protection
- Reversible moderator safety holds that hide a listing from discovery and pause new inquiries without deleting seller data
- Private buyer report history with review status, retained listing references, and no exposure of internal moderator notes
- Two-way buyer/seller inquiry conversations directly from the inbox
- Unread counts, visibility-aware refresh, reply drafts, and retry-safe messages
- App-wide offline and restored-connection notices that preserve access to loaded information
- Clear connection failures that distinguish safe reads from writes missing server confirmation
- Immediate message and unread-count refresh when a visible browser reconnects
- Snapshot-bounded read receipts that never clear a message newer than the conversation displayed
- Profile management with password-confirmed email changes, password rotation, session invalidation, and verified account deletion
- Optional Google, Facebook, and Yahoo sign-in with verified-email account linking and one-time callback codes
- Readiness checks, image maintenance, backup/restore scripts, and sanitized errors

Detailed architecture and reliability notes are in [PROJECT_GUIDE.md](PROJECT_GUIDE.md).

## Technology

- Backend: FastAPI, SQLAlchemy, PostgreSQL, Pydantic, and JWT authentication
- Frontend: React, React Router, and Vite
- Tests: Python `unittest` with isolated SQLite databases and Node's test runner

## Local setup

Prerequisites: Python with `venv`, Node.js with npm, and PostgreSQL.

```powershell
git clone https://github.com/juniordelorbe75-rgb/property-marketplace.git
cd property-marketplace
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and replace every placeholder. `DATABASE_URL` must point to an existing PostgreSQL database. `SECRET_KEY` should be random and at least 32 characters; a helper is included:

```powershell
.\scripts\generate-secret-key.ps1
```

### Social sign-in

Social buttons appear only for providers whose client ID and secret are set. Create
an OAuth web application with each provider, then copy its credentials into `.env`.
For local development, register these exact callback URLs:

- Google: `http://127.0.0.1:8000/auth/google/callback`
- Facebook: `http://127.0.0.1:8000/auth/facebook/callback`
- Yahoo: `http://127.0.0.1:8000/auth/yahoo/callback`

Set `FRONTEND_URL` to the browser-facing marketplace origin and
`OAUTH_REDIRECT_BASE_URL` to the public API origin. Production values must use
HTTPS. Request only the profile and email permissions shown on the provider's
consent screen. Existing accounts are linked only when the provider returns the
same verified email address; otherwise a new marketplace account is created.

To grant moderation access, copy the stable Account ID shown on the Account page into the comma-separated `ADMIN_USER_IDS` setting, then restart the backend. Leave it empty when no account should have administrator access; registration cannot choose or reuse an Account ID.

Install the frontend:

```powershell
Set-Location frontend
npm install
Set-Location ..
```

On Windows, start both development servers:

```powershell
.\run.bat
```

Open `http://127.0.0.1:5173`. The API runs at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

To run the servers separately:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1
```

## Verification

Run the complete local safety gate on Windows:

```powershell
.\scripts\check.ps1
```

Or run each part separately. Backend tests use temporary databases and do not modify the configured PostgreSQL database:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests
```

Frontend verification:

```powershell
Set-Location frontend
npm test
npm run lint
npm run build
```

Current baseline: 84 backend tests and 72 frontend tests.

GitHub Actions runs the same backend suite plus frontend tests, lint, and production build for every pull request and every push to `main`. Runs use read-only repository permissions, locked npm dependencies, bounded execution times, and cancellation of superseded work.

## Health and maintenance

- `GET /health` checks the API process.
- `GET /ready` checks database readiness without exposing connection details.
- `scripts/backup-database.ps1` creates PostgreSQL backups in the ignored `backups/` directory.
- `scripts/restore-database.ps1` restores a selected backup with confirmation safeguards.
- `backend.image_maintenance` identifies or removes old unreferenced uploaded images.

## Security notes

Never commit `.env`, database dumps, uploaded images, private keys, or access tokens. The repository ignores these local files. Use `.env.example` only as a template, and rotate `SECRET_KEY` between environments.

Passwords are hashed directly with bcrypt. New passwords are limited to 72 UTF-8 bytes so bcrypt never silently treats two different long passwords as equivalent.
