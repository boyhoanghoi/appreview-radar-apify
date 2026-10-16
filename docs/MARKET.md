# Why AppReview Radar

Research snapshot: **16 October 2026**, Asia/Saigon. This is a product hypothesis supported by public category usage; it is not evidence of future revenue or of paying customers for this Actor.

## Current first-party evidence

Counts below came from the public Apify Actor API `GET /v2/acts/{username}~{actor}` and Store pages. Monthly activity is `stats.totalUsers30Days`, not lifetime users divided by time, paid accounts, or number of reviews. Store search metadata differed by a couple of users from individual Actor responses, so exact counts can change with caching.

| Direct category / comparison | Total users | 30-day users | Pricing observed |
| --- | ---: | ---: | --- |
| [neatrat/google-play-store-reviews-scraper](https://apify.com/neatrat/google-play-store-reviews-scraper) | 3,044 | 364 | From $0.10/1,000; FREE tier $0.15/1,000 in active event pricing |
| [thewolves/google-play-reviews-scraper](https://apify.com/thewolves/google-play-reviews-scraper) | 1,868 | 356 | $0.10/1,000 reviews |
| [thewolves/appstore-reviews-scraper](https://apify.com/thewolves/appstore-reviews-scraper) | 2,662 | 499 | $0.10/1,000 reviews |
| [data_xplorer/google-news-scraper-fast](https://apify.com/data_xplorer/google-news-scraper-fast) | 2,321 | 630 | Store advertises from $1/1,000 results |
| [autofacts/shopify](https://apify.com/autofacts/shopify) | 2,352 | 85 | Current primary event $1–$1.20/1,000 products by tier; optional extra events |

API source examples: [Google Play](https://api.apify.com/v2/acts/neatrat~google-play-store-reviews-scraper), [App Store](https://api.apify.com/v2/acts/thewolves~appstore-reviews-scraper), [Google News](https://api.apify.com/v2/acts/data_xplorer~google-news-scraper-fast), [Shopify](https://api.apify.com/v2/acts/autofacts~shopify).

The direct review category shows recurring use on both mobile stores. News also has credible demand; review research was chosen for a concrete audience and a bounded cross-store workflow. None of these figures proves that a new entrant will acquire users.

## Who this product is for

1. An indie app founder who wants the original evidence behind complaints about their app and competitors.
2. A product/ASO analyst who needs a filtered CSV and short report rather than reconciling two store schemas.
3. An agency that regularly checks specific client/competitor apps and needs to skip previously exported review IDs.

The specific job is **“give me a manageable, evidenced feedback shortlist”**. It is not finding personal contact details, automatically posting reviews, or predicting a commercially successful app idea.

## Differentiation and pricing hypothesis

Raw review scraping is a low-price category. Mature direct competitors advertise $0.10/1,000 reviews, so charging more for a generic wrapper would be difficult to justify.

AppReview Radar adds a normalized Android+iOS schema, literal English/Vietnamese topic evidence, filters before billing, Markdown and CSV exports, bounded coverage diagnostics, and an explicit saved-ID contract. These features reduce the manual steps between a source review and a research shortlist. Whether users value them enough to pay is **unverified**.

Configured launch rate: **$0.50/1,000 saved filtered reviews**, one `review-saved` event and no start event. The live Store Pricing tab determines the active rate. Small owner-run cloud costs are recorded in [LAUNCH_STATUS.md](LAUNCH_STATUS.md); pricing still needs validation with actual customer feedback and workloads. It is not a revenue forecast.

## Technical feasibility and source distinctions

Google's official review management API requires authorization for the developer's apps. Apple's App Store Connect API similarly exposes reviews for apps under authorized access. Competitor review research therefore uses public web/feed data rather than those management APIs. [Google](https://developers.google.com/android-publisher/reply-to-reviews), [Apple](https://developer.apple.com/documentation/appstoreconnectapi/customer-reviews).

The Node [google-play-scraper project](https://github.com/facundoolano/google-play-scraper) documents pagination, star filters, source replies, and the distinction between written reviews and star-only ratings. Its GitHub API showed a 4 October 2026 push, but its README explicitly warns that the author does not actively maintain it beyond reviewing community contributions. A recent push is not a reliability guarantee. The Python JoMingyu package last repository push was August 2024; no dependency should be assumed current without live source verification.

Apple's public review feed exposes limited per-storefront windows. Missing values, feed holes, unavailable pages, and source format changes must remain visible. See [SOURCES.md](SOURCES.md) for this implementation's actual access and parsing policy. Do not advertise all review history, exact reviewer geography, guaranteed review language, or private developer replies from an RSS source.

## Validate demand before widening scope

Prepare one clear public example, then ask a small number of relevant app developers or product/ASO analysts to evaluate the output. Outreach requires a separate explicit instruction; no message or promotional post has been sent by this project.

Record where users arrive, whether a first run succeeds, which fields/filters they use, whether they run it again, and any verified paying usage. Do not count owner tests as customer traction. A useful early signal is a user returning to answer a real product question, followed by a genuine paid run; neither is promised by publication.

Only add more stores, automatic integrations, AI summarization, or pricing complexity after observing a repeated unmet need. Automatic scheduled-state handoff is not implemented. The upgraded Actor supports [bounded caller-supplied snapshot tracking](CHANGE_MONITOR.md) for exposed same-ID edits; it does not reconcile complete history or infer deletions. The legacy known-ID mode still skips edited keys by design.
