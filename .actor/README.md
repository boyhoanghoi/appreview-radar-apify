# Google Play & App Store Reviews | AppReview Radar

**Turn public app reviews into a feedback shortlist for your next product decision.** Read Android and iOS reviews in one run, filter by stars and words, and export CSV plus a Markdown report with source evidence.

Built for indie app founders, product teams, ASO specialists, and agencies comparing competitor feedback. No store login, LLM key, paid upstream API, or proxy setup is required.

![Illustrative workflow: public reviews, transparent filters, and an exportable feedback shortlist.](https://raw.githubusercontent.com/boyhoanghoi/appreview-radar-apify/main/assets/launch/review-radar-preview.png)

## Try a small run

Choose the **ChatGPT demo preset**, or paste this into JSON input:

```json
{
  "appPreset": "chatgpt",
  "country": "us",
  "language": "en",
  "maxReviews": 20,
  "maxReviewsPerApp": 10,
  "maxPagesPerApp": 1,
  "maxRating": 3
}
```

Click **Start**, then open the dataset and the **Output tab**. It links `results.csv` and `feedback-report.md`. The run requests up to 20 saved reviews across Android and iOS; it may return fewer or zero because filters apply to a bounded source window. Check **DIAGNOSTICS** for source failures or page limits. The separate `OUTPUT` record is the complete JSON report.

[Step-by-step guide](https://github.com/boyhoanghoi/appreview-radar-apify/blob/main/docs/FIRST_RUN.md) · [Hướng dẫn tiếng Việt](https://github.com/boyhoanghoi/appreview-radar-apify/blob/main/docs/FIRST_RUN_VI.md)

## What you get

- **One schema for two stores:** review ID, store, app ID, requested locale, rating, review text, date/version when supplied, public reply where exposed, source URL, and matched topic evidence.
- **Filters before billing:** rating band, ISO date cutoff, included words, excluded words, topic matches, and an explicit feature-request phrase option.
- **Transparent topic tags:** stability, performance, billing, login, ads, privacy, and feature-request mentions using English/Vietnamese literal rules.
- **Ready-to-use exports:** dataset/CSV, Markdown feedback report, and `TOPICS` with per-topic counts and evidence.
- **Repeat-review deduplication:** pass `KNOWN_REVIEW_IDS` into your next input to skip saved reviews before output and charging.

Topic matches are rules, not AI analysis or a verified bug diagnosis. Read the original evidence: a request phrase does not prove intent or demand. The report uses saved reviews only; it is not representative polling or the app's overall rating.

## Useful recipes

**Compare complaints about two apps:** set your Android package IDs or iOS numeric IDs, `maxRating: 2`, and the same country/page settings. Group exported rows by app; compare the original text and available versions rather than treating different sample sizes as market share.

**Inspect login problems:** choose `topicFilters: ["login"]`, optionally add `reviewedAfter`, and download the report. Topic keywords match literal text and can miss paraphrases or match a negated phrase.

**Find feature-request mentions:** set `featureRequestsOnly: true`. Results must contain a supported request phrase; they are candidates for human review, not verified feature requests.

**Monitor reviews already exported:** copy the previous `KNOWN_REVIEW_IDS` array into `knownReviewIds`. Your workflow must pass that state explicitly; attaching a schedule does not do it automatically. Same-key edits are skipped, so this is not review change detection.

## Main inputs

| Input | Purpose |
| --- | --- |
| `appPreset` | `none` or Android + iOS `chatgpt` demo |
| `googlePlayApps`, `appStoreApps` | App IDs or standard store URLs; combined maximum 10 apps |
| `country`, `language` | Requested store country and Google Play language hint; not reviewer residence/language verification |
| `maxReviews` | Global saved cap; default 100, maximum 2,000 |
| `maxReviewsPerApp` | Saved cap per app; default 100, maximum 1,000 |
| `maxPagesPerApp` | Source-page cap per app; default 3, maximum 10 |
| `minRating`, `maxRating` | Inclusive 1–5-star range |
| `includeKeywords`, `excludeKeywords` | Case-insensitive substring lists; any excluded match removes the review |
| `topicFilters` | Any selected topic must match, in addition to other filters |
| `featureRequestsOnly` | Require an explicit supported request phrase |
| `reviewedAfter` | ISO cutoff; unknown review dates are excluded |
| `knownReviewIds` | Saved keys to skip, up to 10,000 |

Preset apps and supplied apps are combined and deduplicated. App names are not searched automatically; use an ID or a store listing URL.

## Pricing

Launch rate: **$0.50 per 1,000 saved matching reviews**, one `review-saved` event per saved row. Confirm the live rate in **Pricing**. No Actor start fee and no extra review events for report/topic evidence.

At that rate, 20 saved reviews generate **$0.01** in review events. Source failures, filtered reviews, duplicates, and supplied known IDs do not generate review events. Platform usage follows Apify's applicable plan and pricing model. Set a **maximum total charge** for the run.

## Important limits

- Public web/feed data only. This is not the official authenticated Google Play Developer or App Store Connect API.
- Source windows are incomplete. The reader scans at most 10 pages per app, and available pages may contain fewer reviews or be empty. Google Play is bounded by your page cap and what the source returns. No full-history guarantee.
- Apple RSS does not expose developer replies. Missing source values stay `null`; labels are not verified app metadata.
- The requested country is not verified reviewer residence. Language is a Google Play hint, not a guaranteed review-language filter.
- Failures are explained in `DIAGNOSTICS`; they are not silently treated as an app having no reviews.
- Known-key history rolls at 10,000 saved keys and must be passed explicitly. Same-key edited reviews are skipped.
- No login, private data access, CAPTCHA bypass, proxy rotation, or automated review posting.

[Source policy and field caveats](https://github.com/boyhoanghoi/appreview-radar-apify/blob/main/docs/SOURCES.md) · [Open-source repository](https://github.com/boyhoanghoi/appreview-radar-apify)

This independent tool is not affiliated with OpenAI, Google, or Apple. The ChatGPT preset is a public-app example, not an endorsement.
