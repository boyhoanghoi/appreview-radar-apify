# AppReview Radar launch verification

Verified **16 October 2026 (Asia/Saigon)**.

- [Public Actor](https://apify.com/reliable_quatrain/google-play-app-store-review-radar).
- [GitHub source](https://github.com/boyhoanghoi/appreview-radar-apify).
- Actor ID `NsFUW9rONTkafXY5T`; latest build **0.1.2**, ID `VdArZDLue3c6M4734`, succeeded.
- **40 Python tests passed**: inputs, source parsing, pagination, TLS/host/response bounds, filters, keyword evidence, safe exports, prior-ID handoff and saved-row billing/state.
- Official Apify CLI validated input, dataset and output schemas.
- A standalone Python wheel was built and inspected for runtime modules and both MIT license notices.
- Single active pay-per-event price: **USD 0.0005 per `review-saved` ($0.50/1,000)**. No start or separate report/topic event was configured.

## Cloud checks on the published build

Both used the ChatGPT Android+iOS preset, GB storefront, English Google Play
hint, one page per app, rating range 1-3, a six-review global cap and three per
app. Each run had a USD 0.01 maximum Actor charge.

| Check | Run | Dataset / event result |
| --- | --- | --- |
| First run | `iJvJ75b2qSjlNHnzN` | Succeeded; 6 rows and 6 `review-saved` events, 3 per store, no failed sources |
| Known-ID repeat | `3qL49QZDN4fXO8jy1` | Succeeded; 6 known keys skipped, 4 different rows and 4 events, both stores, no failed sources |

Final run metadata was fetched after completion, allowing for eventual event
count updates, and compared with dataset and SUMMARY counts. The two saved-key
sets have no overlap. All saved ratings satisfy the filter. `TOPICS` uses only
saved rows; the Markdown report includes the per-app table and correct row count.
Author names/images are absent from the exported schema/rows.

Platform usage observed for these two small owner tests was
USD 0.0005935847055531211 and USD 0.0005936175838841333. The latest build used
USD 0.004502444444444444. These are measured sample infrastructure costs, not
customer revenue, forecasts or guarantees for large/filtered workloads.

## Source windows and public presentation

An earlier US cloud probe received an empty valid Apple feed; the same US app
had reviews locally. GB Apple data was then verified on cloud, and the starter
examples/prefill now use GB. The reason for the different US response is unknown.
Empty windows are never labeled as proof of an app having no reviews. See
[SOURCES.md](SOURCES.md), including actual access behavior and endpoint limits.

Anonymous public Actor metadata confirmed `isPublic=true`, latest build and
active event pricing. Store returned HTTP 200; its HTML includes the product
preview and GB starter. The raw GitHub PNG also returned HTTP 200.

- [English first run](FIRST_RUN.md), [Vietnamese first run](FIRST_RUN_VI.md).
- [Launch drafts](LAUNCH_POSTS.md), [customer validation plan](ACQUISITION_PLAN_VI.md).
- Product image: `assets/launch/review-radar-preview.png` is visible in the Store README.
- Icon asset: `assets/brand/icon-512.png` is ready for upload under
  [Publishing / Display information](https://console.apify.com/actors/NsFUW9rONTkafXY5T/publication).
  This release did not upload the separate top-level Actor icon.

No promotional post, email or message was sent. Owner trials are not customer
traction; no customer revenue or payout is claimed. Topic tags are keyword
mentions, not verified complaints or intent. Scheduled-state transfer and
edited-review change detection are not implemented; callers pass known IDs.
