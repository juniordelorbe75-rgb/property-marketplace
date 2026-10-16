# Habitard Growth Desk

A Python cloud service with a private browser dashboard, public business email discovery, reviewed Gmail invitations and a daily Instagram image queue. Python 3.11+; no third-party runtime packages. This is a first implementation, not a deployed service.

## Included

- Ten researched Dominican Republic contacts imported once, deduplicated by email.
- Inspect a chosen agency contact page for published emails, honoring robots.txt. Daily search-assisted discovery is optional with a Brave Search API key. Search results still need human review for relevance, business identity and outreach eligibility. No guessed addresses or mailbox probing.
- Preview Spanish invitations. Explicit recipient approval and a recorded outreach basis are required. Sending defaults to off; one invitation per minute and ten per UTC day by default. There are no automatic follow-ups.
- Draft and approve Instagram single-image posts with a public image URL and caption. At most one approved due post per UTC day. Only owner-supplied content is published; this version does not generate images, videos or captions automatically.
- Persistent SQLite storage. Failed external operations become uncertain and are never automatically retried. An uncertain Instagram publication pauses the Instagram queue pending manual reconciliation.
- Replies, bounces and opt-outs must be recorded through the dashboard's Suppress button. Automatic Gmail inbox monitoring is not implemented. The initial send-only connection cannot read replies.

## Deploy online using Render

1. This service belongs in `automation/habitard-growth` of `juniordelorbe75-rgb/property-marketplace`. Do not commit real tokens, .env files or the data folder. The seed contains publicly published business addresses and source URLs.
2. Connect the repository in Render and choose a new Blueprint using `automation/habitard-growth/render.yaml`. The Blueprint's rootDir points to the bot folder, so the existing marketplace Dockerfile and root Blueprint are not replaced. Review the current price before creating the service: this configuration uses a paid web service and a persistent disk.
3. Render runs the Docker image with a single instance. The database is stored at `/data/habitard.db`. Do not scale to multiple instances or start a second worker against this database.
4. Open the service's HTTPS URL. Sign in as `admin`, using ADMIN_PASSWORD from the hosting environment. Basic authentication must only be used over HTTPS. The default local bind address is loopback; Docker changes it for cloud hosting.
5. Test contact review and queueing with email and Instagram still disabled. Configure account credentials using Render's secret environment settings, never chat or Git.
6. Connect your accounts, verify the invitation and sender information, test one approved recipient/post, then enable the appropriate channel.

Paid persistent disks are used because the queue must survive deployments. Render cron jobs cannot attach persistent disks: https://render.com/docs/disks and https://render.com/docs/cronjobs

## Gmail connection

Enable Gmail API in a Google Cloud project, configure OAuth consent and obtain offline authorization from the intended sender for `https://www.googleapis.com/auth/gmail.send`. Store GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN in hosting secrets. OAuth apps left in testing can have expiring refresh tokens; configure the project's consent/publishing status appropriately for durable use. No Google password is needed.

Set SENDER_EMAIL, SENDER_NAME and BUSINESS_ADDRESS, preview invitations, and review the recipient's eligibility for the relevant country. EMAIL_ENABLED=true enables processing of approved contacts. EMAIL_DAILY_LIMIT is an application limit, not a guarantee that Google will allow that volume. Pausing the channel prevents future worker ticks; it cannot recall a request already in progress.

Sending follows Google's MIME/base64url message API: https://developers.google.com/workspace/gmail/api/guides/sending
Offline authorization: https://developers.google.com/identity/protocols/oauth2/web-server#offline

This version expects an already obtained refresh token; it does not include an OAuth sign-in screen. Keep monitoring Gmail and promptly suppress replies, bounces and opt-outs. Review requirements for each country before expanding internationally.

## Instagram connection

Create the dedicated Habitard professional account and configure a Meta app for Instagram Login with basic access and content-publishing permissions. Set INSTAGRAM_ACCOUNT_ID, INSTAGRAM_ACCESS_TOKEN and a supported META_API_VERSION. Use the correct token for this Instagram Login flow, not a Facebook Page token. Confirm permissions and current version in your Meta developer dashboard before enabling INSTAGRAM_ENABLED=true.

The adapter creates an image container, checks readiness and publishes it through graph.instagram.com. Public HTTPS JPEG images must meet Meta's current media requirements. The adapter needs live integration testing after the account is connected. Meta documentation could not be retrieved in this build session, so treat the adapter as unverified against a live account. No automatic access-token renewal is implemented; rotate or renew before expiry. TikTok, Reels and carousels are not included.

Reference: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing/

## Discovery

Use the dashboard with a business's exact contact URL. Redirects are deliberately refused, so supply the canonical URL. The crawler limits response sizes, refuses local/private resolved addresses and inspects only one page per request. It is an owner-operated tool, not a public crawling endpoint. Use hosting egress controls if extending it to untrusted users or inputs; DNS validation alone does not eliminate DNS-rebinding risk.

For daily search-assisted discovery set BRAVE_SEARCH_API_KEY and DISCOVERY_ENABLED=true. The default query targets Dominican Republic agencies. Up to ten search results are inspected per day; repeated queries are deduplicated by email. This does not guarantee 200 contacts. Search titles become tentative business names and need correction/verification before outreach. Search API charges may apply. Discovery resumes one minute after startup and its schedule resets on restart.

## Local verification

Run `python -m unittest -v` in this directory. Tests mock all sending/publishing and use a temporary database. To run locally set ADMIN_PASSWORD to a unique value of at least 20 characters, then run `python app.py` and open http://127.0.0.1:8000. Environment variables are configured by the host; `.env.example` is a reference and is not automatically loaded.

## Operations and limits

Back up the persistent database using SQLite's backup facility. Restrict hosting dashboard access and rotate secrets. The private dashboard exposes business contact data to its authenticated owner. Logs never include provider response bodies or tokens. Monitor the Activity section for failures; external alerts are not included. Dashboard data refreshes when an action completes or the page reloads.

All dates and daily caps use UTC. A due queue with a backlog can publish at midnight UTC rather than your preferred local hour; schedule future posts explicitly. Do not edit the invitation template or sender identity without reviewing already approved contacts. Uncertain results need provider-side confirmation before database reconciliation; the UI deliberately has no blind retry button.

Still needed from the owner: GitHub destination and hosting account, account authorizations, verified Habitard registration/listing flow, sender details, new Instagram handle, approved image assets and desired daily publishing time. No repository has been pushed, no hosting purchased, and no real messages or posts have been sent by preparing these files.
