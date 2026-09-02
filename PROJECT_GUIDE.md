# Property Marketplace Study Guide

This guide explains how the project fits together. You do not need to understand
every file at once. Follow the study order near the bottom and run the examples as
you go.

## The Big Picture

The application has three main parts:

1. **React frontend** — displays pages, reads form input, and sends HTTP requests.
2. **FastAPI backend** — receives requests, checks input and authentication, and
   chooses the correct service.
3. **PostgreSQL database** — permanently stores users, properties, favorites, and
   inquiries.

A normal request follows this path:

```text
React page
  -> FastAPI route
  -> service (business rules)
  -> repository (database query)
  -> SQLAlchemy model
  -> PostgreSQL
```

The response travels back through the same layers in reverse.

All authenticated accounts can both buy and sell. The legacy database `role`
column is retained for compatibility, but it is not part of the public account
API and does not control permissions. Authentication and property ownership are
the authorization rules.

## Backend Folders

### `backend/routes/`

Routes define the HTTP API. They answer questions such as:

- Is this a `GET`, `POST`, `PUT`, `PATCH`, or `DELETE` request?
- What URL should the frontend call?
- Does the request require authentication?
- What input and output model should be used?

Example: `POST /properties/` is defined in `backend/routes/properties.py`.

`POST /uploads/property-images` is defined in `backend/routes/uploads.py`. It
requires a Bearer token, validates the encoded image and its real file signature,
and saves accepted property pictures under `backend/uploads/property-images/`.
FastAPI serves those files from `/uploads/property-images/<filename>`.
Pillow fully decodes each upload, verifies its declared format and dimensions,
and rejects corrupt files and decompression-bomb-sized images. Validated bytes
are written to a temporary file and atomically moved into place so a crash cannot
leave a partially written final image.

### `backend/services/`

Services contain business rules. They answer questions such as:

- Does this property exist?
- Does the current user own it?
- Has the user already favorited it?
- Is the seller allowed to reply to this inquiry?

Services raise an `HTTPException` when a rule is broken.

### `backend/repositories/`

Repositories communicate with the database through SQLAlchemy. They contain the
queries for creating, reading, updating, and deleting records.

Keeping queries here prevents database details from spreading throughout routes
and services.

All write repositories use one shared transaction helper that explicitly rolls
back failed property, favorite, inquiry, and account commits. This resets the
SQLAlchemy session for later work and ensures post-commit cleanup never runs when
the database change did not succeed.

### `backend/db_models/`

These classes describe the database tables and relationships:

- `UserDB` -> `users`
- `PropertyDB` -> `properties`
- `FavoriteDB` -> `favorites`
- `InquiryDB` -> `inquiries`
- `ListingReportDB` -> `listing_reports`

Relationship cleanup is also configured here. For example, deleting a property
removes its favorites and inquiries.

At backend startup, `backend/db.py` applies small idempotent compatibility
updates, including the property-description column and favorite uniqueness
index, when an older database does not have them. Startup stops with a clear
error if legacy duplicate favorites must be reviewed instead of deleting data
automatically.
Startup also ensures indexes for newest and price-ordered property browsing,
owner dashboards, buyer/seller inquiry timelines, and property-related favorite
lookups. The index migration is idempotent, so both new and upgraded databases
receive the same query support without manual repair.

### `backend/models.py`

These Pydantic models validate API input and control API output. Database models
describe storage; Pydantic models describe data crossing the API boundary.

### `backend/auth/`

Authentication has three responsibilities:

- Hash and verify passwords.
- Create and verify access tokens.
- Confirm protected requests belong to an existing user.

Password hashes use bcrypt directly and remain compatible with existing bcrypt
hashes. Registration and password changes enforce bcrypt's 72-byte UTF-8 limit;
verification rejects oversized input safely instead of truncating it or raising
an application error.
Changing an account's sign-in email requires the current password. Name-only
profile edits remain convenient, while a failed or missing password leaves the
original email unchanged even when a valid authenticated session is present.
New profiles collect first name, optional middle name, last name, date of birth,
and an optional 1,000-character biography. The structured name is combined into
the existing public display name so listing, inquiry, and moderation snapshots
remain backward compatible. Birth dates and biographies are returned only by
the authenticated account endpoints; they are not added to public listings.
My Account also shows a private summary of the saved full name, formatted birth
date, and biography beneath the editable profile form.
Account creation requires the password to be entered twice; mismatched values
are rejected in the browser before any registration request is sent.

The browser sends a token in this header:

```text
Authorization: Bearer <access-token>
```

Optional Google, Facebook, and Yahoo sign-in uses the server-side OAuth
authorization-code flow. Provider credentials stay in environment variables.
The callback resolves a stable provider identity, requires an email supplied as
verified by the provider, and links it to the matching marketplace account or
creates an account on first use. The browser receives a short-lived, single-use
marketplace code and exchanges it for the normal access token, keeping provider
tokens and marketplace tokens out of redirect URLs.

## Frontend Folders

### `frontend/src/pages/`

Each file is a screen, such as login, registration, property details, favorites,
or inquiries. Pages usually hold state and call the backend with `fetch()`.
The My Properties seller dashboard loads both the owner's listings and aggregate
statistics for listing availability, favorites, and inquiries.

### `frontend/src/components/`

Components are reusable interface pieces. `PropertyCard`, `Navbar`, and
`ProtectedRoute` are used by multiple pages.
The responsive `Navbar` highlights the active page and loads the authenticated
seller's pending-inquiry total for an attention badge. A failed badge request is
non-blocking, and successful inquiry status changes refresh the count without a
page reload.

### `frontend/src/utils/`

Small shared helpers live here. `apiError.js` converts FastAPI string and
validation-array errors into readable messages for forms. When the backend
returns a request ID, the helper appends it as a support ID so a user-visible
failure can be matched to the corresponding server log entry.
`apiResponse.js` safely reads response bodies. Empty or malformed responses—for
example during a development server reload—become clear retry messages instead
of exposing raw browser errors such as `Unexpected end of JSON input`.
`apiFetch.js` gives every API request a 20-second timeout while preserving page
navigation cancellation. A stalled connection becomes a clear timeout message
instead of leaving a page loading forever.
It also avoids sending requests when the browser reports that the device is
offline. Final read failures explain that the marketplace could not be reached;
write failures instead warn that server confirmation was not received and ask
the user to check the latest information before repeating the action.

### Learning note: How listing maps work

The marketplace currently stores the seller's location description, not GPS
coordinates or a verified street address. `propertyMap.js` trims that text,
encodes it as a Google Maps search query, and opens the result in a separate
browser tab. For example, listing `PM-000007` stores `cotui`, so its link searches
Maps for that phrase. Google will likely find Cotuí in the Dominican Republic,
but a one-word location is less reliable than a description such as
`Sector La Altagracia, Cotuí, Sánchez Ramírez, Dominican Republic`.

This design protects a seller from publishing an exact home address and avoids
requiring a paid map API key. Its tradeoff is that the map is approximate and
depends on the seller's wording. The forms therefore ask for sector,
city/province, and country when possible, while the buyer page explicitly says
to confirm the exact location with the seller. Create and edit forms also let
the seller preview the exact map search before saving and warn—without blocking
publication—when the description contains only one location part. A future precise-pin feature
should store structured country, province, latitude, and longitude fields and
let the seller choose whether the exact pin or only an approximate area is
public.
Protected pages and buyer actions preserve a safe same-site return path when
login or registration is required. After authentication, the user returns to
the listing or dashboard they intended to use. External and protocol-relative
destinations are rejected so this convenience cannot become an open redirect.
The shared request helper also expires stale sessions consistently whenever an
authenticated request returns `401`. It checks that the rejected request used
the current token, preventing a delayed request from an older session from
logging out a newly signed-in user. Login and logout state stays synchronized
between browser tabs, while network failures and `503` outages preserve login.
Access tokens carry an account token generation. Password changes increment that
generation, immediately revoking tokens issued on other devices and returning a
replacement token so the active browser remains signed in. Generation-less
tokens issued before this migration are treated as generation 1 until the first
password change.

### `frontend/src/context/AuthContext.jsx`

The authentication context remembers whether a token exists and provides login
and logout functions to the rest of React.

### `frontend/src/App.jsx`

This is the frontend route map. It decides which page appears for each browser
URL and which pages require login. Its final wildcard route displays a helpful
React 404 page for unknown browser addresses.

### `frontend/vite.config.js`

During development, Vite forwards API paths such as `/users`, `/properties`, and
`/uploads` to FastAPI on port `8000`.

Some browser pages share prefixes with API endpoints: `/inquiries`,
`/favorites`, and `/properties/:id`. Vite serves React for direct HTML
navigation to those page routes while continuing to proxy programmatic API
requests to FastAPI.
Buyer search filters, sorting, and the current result page are stored in the URL.
Searches therefore survive refreshes and browser Back/Forward navigation and can
be bookmarked or shared. Unsupported or malformed URL values safely fall back
to defaults instead of being forwarded to the API.
The main navigation labels this destination “Search Properties.” Filter labels
stay concise without repeating “optional”; empty fields and “Any” selections
continue to mean that a filter is not applied.
The results screen requests only the nine properties shown on the current page.
Property list and search endpoints support optional bounded `limit` and `offset`
parameters and return the full matching count in `X-Total-Count`; callers that
omit pagination retain the original complete-list behavior. CORS explicitly
exposes total-count and request-ID headers to production browser frontends.
The home page also shows up to six recently viewed listings so buyers can resume
browsing without an account. Only validated public listing-card fields are kept
in browser storage, repeated visits move a listing to the front, corrupt or
blocked storage never breaks navigation, and the buyer can clear the history.
The home page opens with a confidence-focused hero, an original motivational
message, a direct jump to the search filters, and factual marketplace benefits
without making unsupported safety or inventory claims.
Every property detail page can share a canonical listing URL. Supported devices
open their native share sheet; other browsers copy the link to the clipboard or
show a selectable manual-copy link. Search parameters and fragments are omitted
so recipients always receive a stable property address.
The Create Property form automatically saves validated text, numeric, selection,
amenity, and external-image URL fields in a seller-specific browser draft. It
restores after refresh or accidental navigation and can be explicitly discarded.
Local picture files are never persisted and must be reselected; a successful
listing creation removes the draft, while failed submissions preserve it.
Each draft also retains a random creation identity sent as an `Idempotency-Key`.
If a response is lost after the database commit, retrying returns that seller's
original property rather than creating a duplicate. The same key remains usable
independently by another seller. When a replay uploaded replacement temporary
files, the browser removes only files absent from the returned original listing.
Property responses include an internal edit version. The seller UI returns that
version on save; PostgreSQL locks the listing row, rejects a stale tab with `409`,
and increments the version after a successful edit. This prevents an older form
from silently overwriting a newer seller change. API clients that omit the
version header remain backward compatible.
Buyer inquiry submissions also carry a buyer-scoped creation identity. A retry
after an ambiguous timeout returns the original inquiry conversation, even if
the browser payload was edited before retrying. A genuinely new inquiry with a
different identity still respects the one-pending-inquiry-per-property rule.
Authenticated non-owners can report a listing using a bounded reason and optional
details. Each buyer can create only one report per listing, and a buyer-scoped
idempotency key makes retrying after an uncertain response return the original
record. Reports store the listing ID, title, owner ID, and owner name as review
evidence; deleting the listing clears its live foreign-key link but retains those
snapshots. Reports are recorded for operator review and do not automatically hide
or remove a listing. Administrators explicitly allowlisted by immutable account
ID receive a private
moderation queue with status filters, reporter and listing snapshots, bounded
review notes, and pagination. Review updates lock the report row and require its
current version; exact retries return the saved decision while stale tabs receive
`409`. Resolved and dismissed reports cannot be reopened or switched to the other
terminal state.
Administrators can also place a live reported listing on a reversible safety hold.
The hold is separate from the seller's availability choice: it removes the listing
from public browsing, search, reference lookup, and public counts, and it rejects
new inquiries. Direct links and the seller dashboard remain available with a clear
warning so the owner can correct details or delete the listing. While held, an
owner may save corrections only with the listing marked unavailable. Releasing the
hold does not silently publish it; the owner chooses when to mark it available.
Safety updates use a dedicated version, row lock, reviewer/report audit fields, and
exact-retry handling so two moderator tabs cannot silently overwrite each other.
Each authenticated buyer also has a private paginated report history. It shows
only that buyer's submitted reason, details, public review status, timestamps,
and retained listing reference. Internal moderator notes, reviewer identity, and
other buyers' reports are excluded by the API response model. The history remains
useful after listing deletion and is linked from both the successful report
confirmation and the Account page.

## Example: Creating a Property

1. The user submits the form in `CreateProperty.jsx`.
2. The user may attach a JPG, PNG, or WebP picture up to 5 MB, preview it, or
   paste an external HTTP/HTTPS image URL instead. Up to eight attached pictures
   are supported, and the first picture becomes the listing cover.
   The owner also chooses whether the listing is for sale or for rent; rental
   prices are treated and displayed as monthly rent.
   Optional validated amenities can be selected and later used as a buyer search
   filter. Existing listings safely default to an empty amenities list.
3. For an attached file, React converts the image bytes to base64 and sends
   `POST /uploads/property-images` with JSON and a Bearer token.
4. `backend/routes/uploads.py` checks the declared content type, file signature,
   and size, saves the file with a random name, and returns its `/uploads/...`
   path. Uploaded files are ignored by Git.
5. React sends `POST /properties/` with the returned image path (or the external
   URL) and the rest of the property JSON.
6. `backend/routes/properties.py` validates the token and request body.
7. `backend/services/property_services.py` applies the business rules.
8. `backend/repositories/property_repository.py` creates a `PropertyDB` row.
9. PostgreSQL stores the property record; the image itself remains on disk.
10. FastAPI returns validated property JSON and React navigates to its details.

Property owners can use the same attachment workflow while editing a listing on
the property details page. Selecting a new local picture shows a preview; saving
uploads it first and then updates the property with the returned image path. The
existing external URL option remains available.
Edit mode also lists every gallery picture. Owners can remove individual images,
choose a different cover, and add several new files while keeping the eight-image
limit. Rejected updates roll back newly uploaded files without removing the
existing gallery.
Canceling edit mode restores every field from the last saved property, including
gallery order and amenities. Local image preview object URLs are released when
selections change or pages unmount so repeated image editing does not accumulate
browser memory.

Uploaded files are cleaned up when their property is deleted, when an owner
replaces an uploaded picture, or when deleting an account removes its listings.
External HTTP/HTTPS images are never deleted by the application.

New upload filenames include the authenticated owner's user ID and a random
identifier. If property creation or editing is rejected after a new picture was
uploaded, the frontend calls the owner-protected upload deletion endpoint to
remove that unused file. It deliberately leaves the file in place after an
ambiguous network failure so a successfully saved listing never loses its image.
Before deleting, the endpoint checks the property records and returns `409` if
the image is already attached to any listing. Lifecycle cleanup performs the
same reference check so a still-used image is never removed prematurely.
Cleanup happens after the database commit. A disk permission or filesystem error
is logged and does not turn an already-successful property update, deletion, or
account deletion into a misleading API failure; the maintenance command can
recover the leftover file later.

## Automated Tests

The tests use temporary in-memory SQLite databases. They do not modify the real
PostgreSQL database.

`backend/tests/test_core_flows.py` tests services and business rules directly.

`backend/tests/test_api_flows.py` sends simulated HTTP requests through FastAPI
and verifies the complete route-to-database flow.

Run all backend tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

Check the frontend:

```powershell
cd frontend
npm test
npm run lint
npm run build
```

## Starting the Application

Run `run.bat` from the project root. It opens two server windows:

- FastAPI backend at `http://127.0.0.1:8000`
- Vite frontend at `http://127.0.0.1:5173`

`GET /health` is a lightweight check that confirms the FastAPI process is
responding. `GET /ready` additionally runs `SELECT 1` and returns `503` when the
database is unavailable. SQLAlchemy uses `pool_pre_ping` so stale pooled
connections are detected and replaced before a normal request uses them.
Unexpected SQLAlchemy failures become a consistent retryable `503` response.
The response never exposes SQL text, parameters, credentials, or database host
details, and SQLAlchemy is configured to hide bound parameters in engine errors.
Unexpected non-database application failures become a sanitized `500` response
with the same request ID while the full exception is retained only in server
logs. Internal paths, configuration values, and stack details are not returned
to buyers or sellers.
Every response includes a unique `X-Request-ID`. Completion logs include that ID,
the method, path, status, and duration. Database-error JSON includes the same ID,
allowing a browser report to be matched to the exact server-side request without
exposing internal details.

Keep both server windows open while using the application. The frontend uses
Vite's development proxy to reach FastAPI, so closing the frontend server causes
the browser to report `Failed to fetch` even when the backend is still healthy.

The saved login token normally survives page refreshes. A `Failed to fetch`
message means a server connection failed; an invalid or expired token instead
returns an HTTP `401` response from FastAPI.

Restart `run.bat` after changing backend routes. To manually verify picture
attachments, log in, open Create Property, choose an accepted image smaller than
5 MB, confirm its preview, submit the listing, and check that the image appears
on the property details page.

## Configuration Safety

`.env` contains local secrets and must not be committed. `.env.example` documents
the required settings without containing real credentials.

The important settings are:

- `DATABASE_URL` — PostgreSQL connection information.
- `SECRET_KEY` — signs and verifies access tokens.
- `CORS_ORIGINS` — frontend addresses allowed to call FastAPI.
- `ADMIN_USER_IDS` — optional comma-separated positive Account IDs allowed to use the moderation queue.

Startup rejects missing, placeholder, and very weak signing secrets. Secrets
shorter than the recommended 32 characters produce a rotation warning without
breaking an existing development setup. Generate a cryptographically random
replacement with:

```powershell
.\scripts\generate-secret-key.ps1
```

Copy the generated value into `.env` as `SECRET_KEY`. Rotation invalidates all
existing login tokens, so users must log in again. `CORS_ORIGINS` accepts only a
comma-separated list of valid HTTP/HTTPS origins without paths; wildcard origins
are rejected because credentialed requests are enabled.

To generate and atomically update `.env` without printing the new secret, use:

```powershell
.\scripts\generate-secret-key.ps1 -UpdateEnv
```

## Upload Storage Maintenance

Uploads left after a crash or ambiguous network failure are intentionally not
deleted immediately because the property request may have succeeded. A safe
maintenance command can find old files that no property references.

Preview candidates without changing anything:

```powershell
.\.venv\Scripts\python.exe -m backend.image_maintenance
```

Delete candidates older than the default 24-hour safety window:

```powershell
.\.venv\Scripts\python.exe -m backend.image_maintenance --delete
```

The command protects every database-referenced image, ignores recent files and
unrelated file types, and also detects old `.upload-*.tmp` files from interrupted
atomic writes. Use `--older-than-hours` to select a longer safety window; values
below one hour are rejected. Run the dry mode first before every manual cleanup.

## Database Backup and Recovery

Database health checks detect an outage but do not replace backups. The project
includes PowerShell wrappers around PostgreSQL's official `pg_dump` and
`pg_restore` tools. They read `DATABASE_URL` without printing it or placing it
directly in the PostgreSQL command arguments. Backup files are stored under the
Git-ignored `backups/database/` folder by default.

Create a timestamped custom-format backup:

```powershell
.\scripts\backup-database.ps1
```

Restore is intentionally blocked unless the destructive operation is explicitly
confirmed:

```powershell
.\scripts\restore-database.ps1 `
  -BackupFile .\backups\database\property-marketplace-YYYYMMDD-HHMMSS.dump `
  -ConfirmRestore
```

Both scripts stop when PostgreSQL command-line tools are missing or a command
returns an error. The backup script verifies that a non-empty file was produced.
Always copy important backups to a separate drive or managed backup service; a
backup stored only on the application drive does not protect against drive loss.
Do not test restoration against the only copy of a production database—use a
separate recovery database first.

## Suggested Study Order

Study one request from beginning to end instead of reading folders in isolation:

1. Open `frontend/src/pages/CreateProperty.jsx`.
2. Find `POST /properties/` in `backend/routes/properties.py`.
3. Follow it into `backend/services/property_services.py`.
4. Follow that into `backend/repositories/property_repository.py`.
5. Read `PropertyDB` in `backend/db_models/property.py`.
6. Read the matching test in `backend/tests/test_api_flows.py`.

After that flow makes sense, repeat the process for login, favorites, and
inquiries. Understanding one complete path is more useful than memorizing every
file.

## Current Reliability Baseline

The project currently has automated coverage for:

- Registration and login
- Email, profile, and password-change validation
- Password confirmation for sign-in email changes without blocking name-only edits
- Authenticated listing reports with owner protection, bounded categories/details, duplicate prevention, retry safety, and retained review snapshots
- Explicit immutable-account-ID moderation with private queue filters, review notes, terminal decisions, exact-retry handling, and stale-tab conflict protection
- Reversible, audited listing safety holds with public-discovery exclusion, inquiry blocking, seller correction access, and independent stale-update protection
- Ownership-isolated buyer report history with public status updates, deleted-listing snapshots, pagination, and strict exclusion of internal moderation fields
- Database rollback after duplicate-email conflicts
- Password hashing and token validation
- Expired, malformed, and deleted-user tokens
- Login preservation during temporary frontend/backend connection failures
- Safe post-login return to interrupted buyer and seller workflows
- Consistent token-matched session expiry and cross-tab authentication updates
- Password-change revocation of older sessions with active-session replacement
- Automatic logout when a protected request returns `401`
- Property creation, ownership, updates, and deletion
- Property input validation for text, price, type, bedrooms, bathrooms, size, and status
- Property owner names in listing responses and details
- Property descriptions in create, edit, and details flows
- Required property images in cards, create, edit, and details flows
- Authenticated property-picture attachments in create and edit flows, with type,
  signature, and size checks
- Uploaded-picture cleanup after replacement, property deletion, and account deletion
- Owner-protected rollback cleanup after a rejected create or edit request
- Database reference checks that protect pictures already used by a listing
- Full image decoding, dimension limits, and atomic upload writes
- Dry-run-first maintenance for old orphaned uploads and stale temporary files
- Non-fatal, logged image-cleanup failures after successful database commits
- Shared transaction rollback for property, favorite, inquiry, and account writes
- Separate process-health and database-readiness checks with stale-connection detection
- Timestamped PostgreSQL backup tooling and confirmation-gated restore tooling
- Startup validation for signing secrets and credentialed CORS origins
- Safe retryable database-error responses without SQL parameter leakage
- Sanitized, request-correlated responses for unexpected application failures
- Unique request IDs and timing/status logs for API troubleshooting
- Private, authenticated, and error API responses use `Cache-Control: no-store`; all API responses include browser-safe content-type and referrer headers
- Login attempts are throttled per client-and-email pair after five failures in fifteen minutes, with a `Retry-After` response and automatic reset after successful authentication
- Safe frontend reads retry temporary network, timeout-status, rate-limit, and gateway failures up to two times; write requests are never automatically replayed
- An app-wide connection notice warns when the browser reports that the device is offline, keeps loaded information usable, and briefly confirms when connectivity returns
- Offline requests stop before transmission, while exhausted reads and interrupted writes use distinct guidance so users do not blindly repeat an unconfirmed change
- A visible inquiry inbox and its navigation unread count refresh immediately after reconnection; editor and form pages deliberately avoid automatic reloads that could disturb typed text or selected local pictures
- Property cards and details distinguish newly listed homes from seller-updated listings using database-backed creation and update timestamps
- Every property must retain at least one validated picture; both creation and editing reject image-less listings in the interface and API
- Missing or unreachable property pictures use an accessible marketplace-wide fallback; cards and thumbnails load lazily while the main detail image is prioritized
- Sellers can choose any selected picture as the listing cover during creation or editing; the chosen picture is persisted as the first image
- Newly selected property pictures can be removed individually without discarding the rest of the upload batch or losing cover ordering
- Multi-picture property details include accessible previous/next gallery controls with circular navigation in addition to thumbnails
- Buyers can save up to six validated, deduplicated property searches on their device, reopen them with one click, and remove them independently
- Signed-in buyers can add or remove favorites directly from search and recently viewed cards; per-property pending states prevent duplicate requests and owner listings omit the control
- Property details never guess a signed-in buyer's saved state: favorite controls wait for authoritative loading, failures keep inquiry access available, and saved-state verification has a focused retry
- Favorite verification uses a buyer-scoped single-property lookup rather than downloading the buyer's complete saved collection; creation uses the same indexed ownership lookup for duplicate prevention
- The public property discovery page can be shared with validated active filters and pagination through native sharing, clipboard copying, or a manual-link fallback; private routes have no page-share control
- Failed property discovery and detail loads provide in-place retry controls; retries preserve active search state and superseded requests are cancelled during navigation or filter changes
- Property details distinguish guest, verifying, verified, and failed identity states; signed-in seller/buyer actions remain hidden until ownership is known, and failed verification is cancellation-safe with in-place retry
- Property-detail retries run through the same abort-controlled lifecycle as initial loading, preventing late retry responses from updating a page after navigation
- Sellers can mark listings available or unavailable directly from the dashboard; updates include the current version, preserve the full listing payload, lock duplicate clicks, and synchronize dashboard counts after server confirmation
- Seller cards show ownership-scoped favorites, total inquiries, and pending inquiries per listing from one grouped engagement query, making properties that need follow-up visible without opening each one
- Seller dashboards can instantly search their loaded inventory by title, location, or stable public reference and filter it by availability or listings with pending inquiries
- Seller dashboard startup failures provide an in-place retry that cancels stale requests and reloads listings, statistics, and engagement together without requiring a browser refresh
- Seller listing cards with inquiries link directly to a URL-filtered conversation view for that stable property reference; sent and received status filters continue to work within the selected listing, and sellers can clear the listing filter without leaving the page
- Inquiry loading is cancellation-safe and provides an in-place retry after temporary failures without dropping the selected listing reference; every conversation card also repeats its stable `PM-…` reference to reduce buyer/seller mix-ups
- Listings support explicit US dollar (`USD` / `US$`) and Dominican peso (`DOP` / `RD$`) pricing across creation, editing, cards, details, favorites, drafts, and recently viewed history; price filters and sorting require a currency and use an indexed currency-price query
- The sticky marketplace header includes active-route styling, a live pending-inquiry badge, and a keyboard-accessible mobile menu that closes after navigation, logout, or Escape
- Every listing displays a stable public reference such as `PM-000123`; buyers can search the exact validated reference, making phone, family, agent, and messaging conversations less ambiguous
- Create, edit, and buyer search location fields offer all 31 Dominican provinces plus the National District as accessible suggestions while remaining free text for sectors, neighborhoods, and future countries
- Property details can open the seller-provided location as a safe external map search without storing precise coordinates, embedding a tracking map, or requiring a map API key

The login throttle keeps at most 10,000 client-and-email entries in each API
process. This is an effective single-instance baseline. A deployment running
multiple API processes or servers should use a shared rate-limit store (such as
Redis or a gateway rate limiter) so attempts cannot be distributed across
instances.
- Consistent frontend API errors with server-correlated support IDs
- Complete edit cancellation and browser-memory cleanup for image previews
- Safe global handling for empty and malformed API response bodies
- Shared API request timeouts with navigation-aware cancellation
- Up to eight listing pictures, a first-picture cover, and details-page gallery
- For-sale and for-rent listings with validation, search filtering, and monthly pricing
- Validated property amenities in create, edit, details, and buyer search
- Authenticated seller dashboard statistics with ownership-isolated counts
- Consistent photo cards in favorites with broken-image fallback
- Favorite loading is cancellation-safe with in-place retry; failed removals keep the buyer's list visible, report the action error separately, and lock duplicate removal clicks
- Bathroom counts in create, edit, cards, and property details
- Minimum-bathroom property search filtering
- Optional square-footage values in create, edit, cards, and property details
- Optional minimum square-footage property search filtering
- Responsive search-form grid that keeps all filters visible
- Search-result sorting by newest, lowest price, or highest price
- Bookmarkable and shareable URL-backed search, sorting, and pagination state
- Backward-compatible server-side property pagination with exact result totals
- Bounded, device-local recently viewed listings with clear-history control
- Recently viewed listings appear after the primary marketplace results and pagination, keeping current inventory and search ahead of browsing history
- Native property sharing with clipboard and manual-copy fallbacks
- Seller-specific automatic listing drafts with safe restore and discard flows
- Seller-scoped idempotent property creation with replay upload cleanup
- Versioned seller edits that reject stale-tab overwrites
- Irreversible listing deletion requires the currently loaded listing version, rejects stale tabs after another edit, and locks duplicate delete clicks while the request is pending
- Buyer-scoped retry-safe inquiry creation without duplicate conversations
- Idempotent database indexes for property browsing and buyer/seller dashboards
- Unavailable listings reject new inquiries and use distinct status styling
- Inquiry creation locks the property row before validating availability, serializing buyer submissions against seller availability changes so stale reads cannot admit a request after a listing becomes unavailable
- Client-side property pagination with result ranges and responsive controls
- Property creation timestamps, timestamp-based newest sorting, and listed dates
- Every account can buy and sell; ownership controls listing changes
- Property search filtering and invalid-range rejection
- Newest-first ordering for properties, favorites, and inquiries
- Favorites and duplicate prevention
- Database-enforced favorite uniqueness and conflict rollback
- Prevention of favoriting your own listing
- Buyer and seller inquiry permissions
- Buyer cancellation of pending inquiries, with cancelled inquiries locked from
  later seller status changes or replies
- Duplicate-pending-inquiry prevention at both the service and database levels
- Inquiry creation and last-activity timestamps with newest-first timeline ordering
- One-way inquiry status transitions, preventing accepted, rejected, or cancelled
  inquiries from being reopened and blocking replies to closed inquiries
- Inquiry status changes, buyer cancellation, and seller replies lock the conversation row until commit, preventing concurrent tabs from overwriting one another after validating stale state
- Separate sent/received inquiry status filters with live per-status counts
- Sent and received inquiry histories use independent server-side status/property filtering and bounded pagination with authoritative ownership-scoped totals; existing unpaginated endpoints remain backward compatible
- Inquiry cards contain a persistent two-way message history, so buyers and sellers can reply directly from the inquiries page without reopening the property; participant checks and row locking prevent outsiders or concurrent updates from corrupting a conversation
- Two-way inquiry messages carry sender-scoped retry identities, preventing duplicate replies when a successful request is retried after a timeout or connection loss
- Buyer and seller read positions are stored independently; the navigation shows ownership-scoped unread message totals, visible conversation cards identify new messages, and snapshot-bounded receipts ensure a message arriving after the delivered page cannot be marked read before it is shown
- Inquiry data refreshes while the tab is visible and immediately after focus returns; temporary background failures preserve the already-loaded conversations, show a non-blocking retry notice, and never replace usable inbox data with an error screen
- Accept, reject, and cancel transitions are retry-safe: repeating the same completed action returns its existing result, conflicting terminal changes remain blocked, and rejection requires explicit browser confirmation because it closes the conversation
- Unsaved inquiry replies are bounded to the API limit and kept in account-scoped session storage, surviving accidental reloads without remaining permanently on a shared device; automatic conversation refresh pauses while a draft or inquiry action is active
- Contact-owner drafts persist the buyer's bounded message together with its property/account-scoped retry identity for the browser session, making reloads and ambiguous connection failures safe; suggested questions append without overwriting existing text, and buyers can explicitly clear a draft
- The property contact-owner composer provides clear labeling, suggested questions, a message limit, and keyboard submission while retaining retry-safe inquiry creation
- Human-readable names and property titles in inquiry responses
- Account deletion cleanup
- Permanent account deletion requires both the current password and an explicit typed `DELETE` confirmation; incorrect passwords leave the account and all related marketplace data intact
- Account loading is navigation-cancellation-safe and provides in-place retry without reloading the browser or restarting the application
- A complete buyer-seller HTTP workflow

Passing tests reduce regressions, but they do not prove that bugs are impossible.
New behavior should be added with a matching test whenever practical.

The repository's GitHub Actions workflow runs backend tests and the complete
frontend test/lint/build gate on pull requests and pushes to `main`. Its jobs use
read-only repository permissions, dependency caches keyed by committed dependency
manifests, explicit timeouts, and concurrency cancellation. On Windows,
`scripts/check.ps1` runs the same local verification sequence with fail-fast exit
handling.
