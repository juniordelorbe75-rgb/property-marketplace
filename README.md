# Property Marketplace

A full-stack marketplace for discovering, listing, saving, and discussing properties. Every authenticated account can act as both a buyer and a seller.

## Current capabilities

- Searchable, paginated property browsing with stable `PM-…` references
- Sale and rental listings in USD or DOP
- Multiple images, amenities, map links, favorites, and recently viewed listings
- Seller inventory, engagement statistics, availability controls, and safe updates
- Two-way buyer/seller inquiry conversations directly from the inbox
- Unread counts, visibility-aware refresh, reply drafts, and retry-safe messages
- App-wide offline and restored-connection notices that preserve access to loaded information
- Clear connection failures that distinguish safe reads from writes missing server confirmation
- Immediate message and unread-count refresh when a visible browser reconnects
- Snapshot-bounded read receipts that never clear a message newer than the conversation displayed
- Profile management, password rotation, session invalidation, and verified account deletion
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

Current baseline: 74 backend tests and 68 frontend tests.

GitHub Actions runs the same backend suite plus frontend tests, lint, and production build for every pull request and every push to `main`. Runs use read-only repository permissions, locked npm dependencies, bounded execution times, and cancellation of superseded work.

## Health and maintenance

- `GET /health` checks the API process.
- `GET /ready` checks database readiness without exposing connection details.
- `scripts/backup-database.ps1` creates PostgreSQL backups in the ignored `backups/` directory.
- `scripts/restore-database.ps1` restores a selected backup with confirmation safeguards.
- `backend.image_maintenance` identifies or removes old unreferenced uploaded images.

## Security notes

Never commit `.env`, database dumps, uploaded images, private keys, or access tokens. The repository ignores these local files. Use `.env.example` only as a template, and rotate `SECRET_KEY` between environments.
