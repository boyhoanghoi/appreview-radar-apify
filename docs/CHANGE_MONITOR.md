# Monitor edited reviews and visible replies

The fingerprint workflow compares review fields with a snapshot supplied by
your workflow. It can catch a changed rating, title/text, app version or exposed
developer reply **while the review remains in the fetched source window**.

1. Run [examples/change-monitor.json](../examples/change-monitor.json) with
   `changedOnly: true`, an empty `previousSnapshot`, and no `knownReviewIds`.
2. Save the returned **SNAPSHOT** object.
3. Pass it as `previousSnapshot` with the same country/language next time.
4. `NEW` is absent from that supplied baseline; `UPDATED` has different exposed
   content; `UNCHANGED` is skipped before saving and review-saved billing.

This is source-window monitoring, not full-history reconciliation. A capped or
filtered first run leaves other existing reviews untracked; they may appear as
`NEW` in later runs. Dates, votes and observation time alone do not count as
content edits. Text after the 8,000-character export bound cannot be compared.
Missing reviews are never marked deleted, and changes between two observations
cannot be recovered. Apple RSS does not expose developer replies.

Only accepted saved rows advance fingerprints. Failed, filtered, unchanged-skip,
known-ID-skip or unaffordable rows retain their previous baseline. The returned
snapshot has a version, country, language and review-key-to-SHA256 map. It holds
at most 10,000 entries and 2 MiB in compact UTF-8 JSON. Oldest saved entries are
evicted when necessary and `SUMMARY.snapshotTruncated` becomes true; evicted keys
may be `NEW` again. This is bounded state, not unlimited review history.

The default `changedOnly: false` still saves and bills matching unchanged rows.
The legacy known-ID list has priority: a `knownReviewIds` key is skipped even if
its content changed. For edit monitoring, use the snapshot and leave that list
empty. Schedules do not load previous state automatically; the caller must pass
the most recent SNAPSHOT explicitly.

## Local two-run workflow

```powershell
reviewradar --input examples/change-monitor.json --output output/monitor-first
reviewradar --input examples/change-monitor.json --previous-snapshot output/monitor-first/snapshot.json --output output/monitor-next
```

The `--previous-snapshot` file replaces any input `previousSnapshot` and must
match the configured country/language. `snapshot.json` is written atomically
after other exports finish. A repeat may contain additional reviews from the
bounded window; it need not return zero.

## Version and reply filters

- `appVersionKeywords`: case-insensitive substring OR matching on the version
  exposed by a review. Unknown versions are excluded when set.
- `replyFilter: "with-reply"`: keep Google Play reviews with an exposed reply.
- `replyFilter: "without-visible-reply"`: keep Google Play reviews with no reply
  shown in this public source. It is not proof about other interfaces.
- Both reply-specific filters exclude Apple RSS reviews because their reply
  status is unavailable; `replyFilter: "all"` keeps the existing behavior.

These filters combine with rating, keywords, topics and date filters before
persistence/billing. `developerReplyStatus` is `present`, `not-shown` or
`unavailable`, so downstream support queues can retain the distinction.
