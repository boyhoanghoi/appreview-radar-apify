# AppReview Radar launch verification

Verified **16 October 2026 (Asia/Saigon)**.

- [Public Actor](https://apify.com/reliable_quatrain/google-play-app-store-review-radar).
- [GitHub source](https://github.com/boyhoanghoi/appreview-radar-apify).
- Actor ID `NsFUW9rONTkafXY5T`; latest build **0.2.1**, ID `EPkad7qI6DSNhl4jF`, succeeded. Package version: **0.2.0**.
- Runtime source commit: `ce73be247949be40bb376037b19bfaf619b209e3`.
- **51 Python tests passed**: inputs, source parsing, pagination, TLS/host/response bounds, filters, keyword evidence, safe exports, prior-ID handoff, scoped/bounded snapshots, same-ID edits, timestamp-only stability, atomic checkpoints and saved-row billing/state.
- Official Apify CLI validated input, dataset and output schemas.
- A standalone Python wheel was built and inspected for runtime modules and both MIT license notices.
- Single active pay-per-event price: **USD 0.0005 per `review-saved` ($0.50/1,000)**. No start or separate report/topic event was configured.

## Cloud checks on the published build

Both used the ChatGPT Android+iOS preset, GB storefront, English Google Play
hint, one page per app, rating range 1-3, `changedOnly: true`, empty known IDs
and a 60-review cap. Each run had a USD 0.04 maximum Actor charge. The repeat
received the first run's complete `SNAPSHOT` as `previousSnapshot`.

| Check | Run | Dataset / event result |
| --- | --- | --- |
| First run | `ZENdNSPL7kb4xu0wr` | Succeeded; 6 NEW Google Play rows, 6 events, snapshot has 6 keys, no failed sources |
| Snapshot repeat | `78dk2cScEctkI0Uso` | Succeeded; 5 unchanged reviews skipped, 3 NEW rows and 3 events, snapshot has 9 keys, no failed sources |

Final run metadata was fetched after completion, allowing for eventual event
count updates, and compared with dataset and SUMMARY counts. CSV keys/change
labels match saved dataset rows, Markdown reports contain the correct saved
counts, and `OUTPUT.snapshot` matches `SNAPSHOT`. Existing baseline entries,
including a review missing from the repeat's source window, were preserved.
No UNCHANGED review was saved or charged. Live source windows changed between
runs, so the repeat legitimately saved three additional new-to-baseline reviews.
Same-ID edited review and refusal-to-save behavior are covered by controlled
tests; no actual customer review edit was asserted in this cloud sample.

Platform usage observed for these two small owner tests was
approximately USD 0.00073 and USD 0.00060. The latest build used
USD 0.00349. These are measured sample infrastructure costs, not
customer revenue, forecasts or guarantees for large/filtered workloads.

## Source windows and public presentation

An earlier release verified GB Apple data on cloud. Both cloud checks in this
release instead received a valid empty GB Apple feed, with zero Apple rows and
zero Apple events. Apple parsing is covered by fixture tests; the current cloud
sample verifies the empty-source path, not populated Apple output. Earlier US
cloud/local differences were also observed. The reason is unknown.
Empty windows are never labeled as proof of an app having no reviews. See
[SOURCES.md](SOURCES.md), including actual access behavior and endpoint limits.

Public Actor metadata, Store content and current pricing are recorded in
`launch.json`. The updated Store README explains snapshot monitoring and its
source-window limits.

- [English first run](FIRST_RUN.md), [Vietnamese first run](FIRST_RUN_VI.md).
- [Launch drafts](LAUNCH_POSTS.md), [customer validation plan](ACQUISITION_PLAN_VI.md).
- Product image: `assets/launch/review-radar-preview.png` is visible in the Store README.
- Icon asset: `assets/brand/icon-512.png` is ready for upload under
  [Publishing / Display information](https://console.apify.com/actors/NsFUW9rONTkafXY5T/publication).
  This release did not upload the separate top-level Actor icon.

No promotional post, email or message was sent. Owner trials are not customer
traction; no customer revenue or payout is claimed. Topic tags are keyword
mentions, not verified complaints or intent. Same-ID edit detection now uses
caller-supplied snapshots; scheduled runs still require explicit state transfer.
Known IDs retain their legacy skip priority, so leave them empty for edit tracking.
