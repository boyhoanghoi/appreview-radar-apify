# Your first feedback shortlist

Use this walkthrough to inspect a small Android + iOS sample before setting up a larger research workflow.

## 1. Open the Actor

Open [AppReview Radar](https://apify.com/reliable_quatrain/google-play-app-store-review-radar), click **Try for free**, then choose **JSON** input. Confirm the current rate in **Pricing** and set a run maximum total charge, for example **$0.02** for this small check. A charge limit may produce fewer rows.

## 2. Paste the starter input

```json
{
  "appPreset": "chatgpt",
  "country": "gb",
  "language": "en",
  "maxReviews": 20,
  "maxReviewsPerApp": 10,
  "maxPagesPerApp": 1,
  "maxRating": 3
}
```

The independent demo targets ChatGPT's public Android package `com.openai.chatgpt` and iOS ID `6448311069`. It saves only matching 1–3-star reviews, with a global ceiling of 20 and per-app ceiling of 10.

**These are ceilings, not promised counts.** With one source page per app, there may be fewer matching reviews or none. Different stores expose different windows and can fail independently. A source error appears in diagnostics.

## 3. Start and inspect the evidence

Click **Start**. Open the saved dataset, then inspect:

1. The review text, rating, store/app ID, and supplied date/version.
2. The matched topics and the literal matching evidence.
3. `SUMMARY` and `DIAGNOSTICS` for filtering, missing fields, failures, and page caps.
4. The **Output tab** for links to the CSV and Markdown report. The separate `OUTPUT` record contains the complete JSON report.

Download `results.csv` to compare the rows in a spreadsheet. Read `feedback-report.md` for counts and source excerpts. The rating histogram and topic totals describe **saved rows only**, not the app's overall reception. A review can match multiple topics.

## 4. Research your own question

For two Android competitors, disable the demo and supply their package IDs:

```json
{
  "appPreset": "none",
  "googlePlayApps": ["com.spotify.music", "com.soundcloud.android"],
  "country": "us",
  "language": "en",
  "maxReviews": 30,
  "maxReviewsPerApp": 15,
  "maxPagesPerApp": 2,
  "maxRating": 2
}
```

This is a recipe, not a claim that a fixed number of reviews is available. To focus further, add `topicFilters: ["billing"]` or `includeKeywords: ["subscription", "refund"]`. Filters combine; adding them can reduce the results to zero. Increase source pages, not just output caps, when you need a larger review window.

For iOS, use `appStoreApps` with numeric IDs or standard `apps.apple.com` listing URLs. A store URL identifies the app; the configured `country` is the requested storefront context.

## 5. Skip reviews on the next run

Open the completed run's `KNOWN_REVIEW_IDS` record. Pass its array into `knownReviewIds` in the next input. Each key is `{store}:{appId}:{reviewId}`.

- Existing keys are skipped before saving and charging.
- Only saved rows are added to the rolling list; filtered/failed reviews are not.
- The history holds at most 10,000 keys. Older keys may eventually be eligible again.
- Same-key edits are skipped. This is not review change detection.

**Scheduling does not carry state automatically.** Your API/n8n/Make/custom workflow must read the previous record and pass it into the next input. This project includes the state contract; it does not claim to ship an automatically configured third-party workflow.

The local CLI can read the prior file directly:

```powershell
reviewradar --input examples/first-run.json --output output
reviewradar --input examples/first-run.json --previous-ids output/known_review_ids.json --output output-next
```

A repeat is not guaranteed to return zero: fresh reviews may appear and a later run can inspect a different source window.

## Cost and limits

At the configured launch rate of $0.50/1,000 saved reviews, the starter's maximum 20 rows generate $0.01 in review events. Check the Actor's live Pricing tab; platform usage follows the applicable plan/model. Failed sources, filtered rows, duplicates, and supplied known keys do not generate review events.

Topic detection uses transparent English/Vietnamese phrases, not an LLM. It can match negations or miss paraphrases. “Feature request” is a rule match for human review, not verified intent or guaranteed product demand.

Read [SOURCES.md](SOURCES.md) before relying on date semantics, store coverage, requested locales, missing replies, or source access behavior. These sources are public web/feed endpoints, not the authenticated store-management APIs. Neither full history nor representative sampling is guaranteed.
