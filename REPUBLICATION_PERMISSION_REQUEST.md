# Listing republication permission request

This package is a business outreach and technical requirements template, not legal advice.
Have final contract language reviewed by Dominican counsel before production publication.

## Initial request

Subject: Dominican Republic property listing feed partnership

Hello [organization/contact name],

My name is [sender name], and I represent [marketplace legal/business name]. We are building
a Dominican Republic property-discovery marketplace where visitors can browse available sale
and rental properties without creating an account.

We would like to discuss an authorized listing-feed partnership with [organization]. Our goal
is to display only inventory that you and your participating brokers, developers, or owners are
authorized to distribute. We will not scrape or republish your listings without written permission.

Could you connect us with the person responsible for API/MLS licensing, listing syndication,
or data-distribution partnerships? We would like to review:

- consumer and commercial display rights for listing data and photographs;
- covered brokers, developers, owners, territories, and listing statuses;
- API, XML, JSON, CSV, webhook, and sandbox availability;
- required attribution and canonical links;
- refresh frequency, availability verification, withdrawals, and urgent takedowns;
- permitted caching, normalization, translation, and audit retention;
- buyer-lead routing and permitted storage of inquiries; and
- pricing, contract term, termination, and post-termination deletion requirements.

Our ingestion design keeps provider attribution and stable source identities, prevents duplicate
publication, keeps new sources private until approved, and automatically withdraws records that
leave an authorized full feed.

Please let us know the appropriate next step for reviewing a sandbox and a written republication
agreement.

Sincerely,

[sender name]
[role]
[marketplace legal/business name]
[website]
[business email]
[telephone]

## Written approval must cover

The signed agreement or addendum should identify the parties and explicitly address:

1. The provider's authority to license each supplied listing, description, photograph, logo,
   brokerage/developer identity, and contact route.
2. Permission for public consumer display and commercial marketplace use.
3. The countries, territories, brands, offices, and listings included.
4. Required attribution, disclaimers, canonical links, and brand guidelines.
5. Whether content may be cached, normalized, indexed, translated, resized, or excerpted.
6. Update frequency, availability accuracy, missing-record semantics, expiry, and takedown SLA.
7. Buyer inquiry routing, consent, privacy responsibilities, and data-retention limits.
8. Security requirements for API keys, feeds, personal information, and incident notification.
9. Fees, usage limits, audit rights, warranties, liability allocation, term, and termination.
10. Required deletion or retention after a listing withdrawal or agreement termination.

## Activation evidence

Before enabling a provider in production, retain:

- the signed agreement and effective/expiry dates;
- the authorized signer and provider support/takedown contacts;
- a permission summary approved by counsel;
- API credentials in a secrets manager, never source control or browser code;
- the approved attribution text and source-link format;
- a representative sandbox validation report; and
- a successful withdrawal/takedown test.
