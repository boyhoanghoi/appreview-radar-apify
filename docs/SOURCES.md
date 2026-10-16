# Sources and access behavior

Verified locally on 2026-10-16. This project retrieves public written reviews;
it is independent of Google, Apple and the example app publishers.

## Google Play

- Fixed HTTPS POST endpoint: `https://play.google.com/_/PlayStoreUi/data/batchexecute?hl=en&gl=us`.
- Public reviews RPC: `oCPfdb`, newest-first, 100 requested records per page.
- Continuation depends on the upstream response. There is no complete-history,
  total-count, language accuracy or geographic residency guarantee.
- App IDs only generate the request payload; they cannot change the host/path.
- RPC/index mapping is adapted from the MIT-licensed
  [JoMingyu/google-play-scraper](https://github.com/JoMingyu/google-play-scraper).
  The original license is included in `licenses/GOOGLE_PLAY_SCRAPER_MIT.txt`.
  The dependency is not imported: its transport disables TLS verification and
  lacks the response/time limits required here.

## Apple App Store

- Fixed HTTPS GET endpoint pattern:
  `https://itunes.apple.com/{country}/rss/customerreviews/page={1..10}/id={appId}/sortby=mostrecent/json`.
- The accessible RSS window is limited; the observed ChatGPT US page contained
  50 written reviews. This does not guarantee 50 per page or 500 available reviews.
- An empty accessible feed is not proof the app does not exist.
- Apple's next link is checked against the same country, app and next page.
  A fresh JSON URL is generated; arbitrary links/query parameters are not followed.
- Developer replies are unavailable in this feed; no replies are invented.
- `helpfulVotes` is null for Apple: its vote-count fields are not represented as
  verified helpful-upvote counts.
- No language filter is promised for Apple. `languageRequested` is null there.

The 16 October 2026 Apify Cloud probe returned an empty valid US ChatGPT feed,
while the GB ChatGPT feed returned reviews. The same US feed returned reviews
locally. The reason for this difference is unverified. Starter examples use
`country: "gb"`, which was verified on cloud; this does not guarantee future
availability. No alternate URL, proxy or source-access bypass was added.

## Robots, transport and privacy

The generic rules in [Google robots.txt](https://play.google.com/robots.txt)
currently exclude `/_`, and [Apple robots.txt](https://itunes.apple.com/robots.txt)
currently excludes `/*/rss/*`. **This Actor does not claim robots compliance and
does not automatically enforce these exclusions for the documented review feeds.**
Endpoint accessibility is not a guarantee of permission or future availability.
Customers should evaluate their intended use and the source's applicable terms.

There is no login, proxy, browser fingerprint imitation, CAPTCHA handling or
access-control bypass. HTTPS certificates and public DNS addresses are verified.
Redirects are refused. HTTP 403 and 429 stop the request without retry. At most
one transient network/server retry is allowed, within a 60-attempt run budget.
Requests are paced and have a configurable total timeout; each decompressed
response is capped at 2 MiB. HTTP/parser failures are not reported as empty success.

Reviewer names, avatars, profiles and contact data are not exported. Review IDs
are used for stable repeat-run deduplication. Review text and developer reply text
are capped at 8,000 characters; `reviewTextTruncated` identifies clipped review
text. Dates are normalized to UTC when available. Storefront/language parameters
describe the request, not a reviewer's residence or verified language.
