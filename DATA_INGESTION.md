# Property data ingestion

The marketplace has two inventory classes that must remain distinguishable:

1. Owner-managed listings created in the application.
2. Externally managed listings received under an explicit display agreement.

Government geographic and statistical data can enrich either class, but it is
not evidence that a property is currently available.

## Source acceptance gate

Before a feed can be imported, record its provider, country, license or contract,
attribution text, canonical license URL, commercial-display permission, refresh
schedule, takedown method, and support contact. Do not scrape a public website merely
because a listing is visible in a browser.

Every record requires a stable provider ID, canonical source URL, source update time,
status, currency, country, normalized geography, and retrieval time. Imported data
must be staged and validated before publication. A missing record in a later feed is
not immediately deleted: mark it stale, confirm according to the provider contract,
then withdraw it while retaining the audit trail.

## Dominican Republic source plan

- Use Oficina Nacional de Estadística territorial publications for geographic codes
  and names, subject to the license attached to the exact dataset/version.
- Treat Catastro Nacional and DGII information as parcel, valuation, or statistical
  enrichment only where the published dataset and its license permit the intended use.
- Obtain active inventory through signed feeds from brokers, developers, associations,
  or listing platforms. The agreement must explicitly permit commercial consumer display,
  photos, attribution, caching, updates, and takedowns.

## Feed lifecycle

`receive -> validate rights and schema -> stage -> deduplicate -> moderate -> publish`

Published records retain source identity and never overwrite owner-managed listings.
Refreshes are idempotent on `(source_key, external_id)`. Material changes create an
audit event. Expired rights or takedown requests remove the public record promptly.

The initial code contract lives in `backend/feed_models.py`. Persistence, an administrator
approval gate, import audits, stale-feed withdrawal, and buyer search are implemented. The
ReppingDR synchronizer remains inert until both a signed permission-document URL is recorded
by an administrator and `REPPINGDR_API_KEY` is configured on the server. The API key must
never be placed in frontend code.

## Safe activation checklist

1. Receive written permission covering commercial display, photos, caching, attribution,
   lead routing, update frequency, and takedowns.
2. Register the provider as a pending source through the administrator API.
3. Record the signed permission URL, expiration date if any, and stale-feed window through
   the approval endpoint. This action is attributed to the authenticated administrator.
4. Store the API key only as a server environment secret.
5. Run one controlled synchronization and review the audit log and sample records.
6. Schedule refreshes only at the interval allowed by the contract. Run stale withdrawal
   after failed or delayed refreshes; revoked or expired permission unpublishes inventory.

## Provider candidates under review

These are candidates, not approved or licensed sources:

1. **ReppingDR API** — strongest initial technical candidate. Its documentation advertises
   authenticated JSON access to Dominican property listings, zones, and market data. Before
   subscribing, obtain written permission for republication because its public terms prohibit
   reproducing platform content without written permission.
2. **Direct Dominican broker and developer feeds** — strongest rights model. Several regional
   portals document XML onboarding, showing that local agencies already have machine-readable
   catalogs. Approach providers directly for a reciprocal or publisher feed agreement.
3. **Portal/CRM syndication feeds** — technically mature fallback using stable XML IDs and full
   snapshots. Coverage and Dominican rights must be confirmed per provider.

The first outreach should ask for a sandbox key, data dictionary, geographic coverage, consumer
display rights, image rights, attribution language, refresh limits, webhook or deletion behavior,
and production pricing. Never place a provider API key in the browser; retrieval belongs in the
backend ingestion worker.

## Permission-first outreach order

1. **AEI-RD** — request a national display/feed partnership or introduction to its MLS/API team.
   AEI represents a large directory of Dominican real-estate companies, exposes MLS-number search,
   documents EasyBroker API synchronization, and publishes that it is open to collaborations that
   strengthen the industry.
2. **AEI member agencies** — pilot with 3–5 agencies covering different territories. Ask each agency
   to authorize its own listings, photos, contact information, and an XML/JSON refresh feed.
3. **APROCOVICI and ADETI** — request introductions to Cibao housing developers and tourism-property
   developers respectively, with project-level inventory feeds and clear developer attribution.
4. **ReppingDR** — pursue only with a signed republication addendum; its API is technically suitable,
   but its public terms alone do not grant reproduction rights.

Do not collect personal owner details from listings for reuse. The contracting broker, developer,
or authorized owner must opt in and remain the authoritative contact for inquiries and takedowns.
