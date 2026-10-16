"""Bounded review windows, filters before billing, and saved-only analysis."""

from datetime import datetime, timezone
import asyncio
import time
from typing import Awaitable, Callable

from .analysis import filter_reason, saved_analysis, tag_review
from .config import RunConfig
from .sources import fetch_page
from .transport import FeedError, ReviewClient
from .snapshot import SnapshotTracker, classify_review, validate_snapshot

MAX_RUN_SECONDS = 180


async def run_pipeline(config: RunConfig, on_result: Callable[[dict], Awaitable[bool]] | None = None,
                       *, client_factory=ReviewClient, page_fetcher=fetch_page) -> dict:
    started = time.monotonic()
    observed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows, diagnostics, seen = [], [], set()
    known = set(config.known_review_ids)
    previous = validate_snapshot(config.previous_snapshot, config.country, config.language)
    tracker = SnapshotTracker(previous)
    stopped = False
    async with client_factory(config) as client:
        for app in config.apps:
            state = {"app": app.key, "status": "skipped" if stopped else "success", "pagesRead": 0, "requests": 0,
                "fetchedReviews": 0, "invalidReviews": 0, "filteredReviews": 0, "knownReviewsSkipped": 0,
                "unchangedReviewsSkipped": 0,
                "duplicateReviews": 0, "savedReviews": 0, "filterReasons": {}, "accessibleWindowEnded": False,
                "fullHistoryCoverage": False, "stopReason": "global_or_spending_limit" if stopped else None}
            diagnostics.append(state)
            if stopped:
                continue
            before = client.requests
            token, seen_tokens = None, set()
            try:
                for _ in range(config.max_pages_per_app):
                    remaining = MAX_RUN_SECONDS - (time.monotonic() - started)
                    if remaining <= 0:
                        raise FeedError("run_deadline", "Run reached its 180-second source-processing deadline.")
                    try:
                        async with asyncio.timeout(remaining):
                            page = await page_fetcher(client, app, config, token)
                    except TimeoutError:
                        raise FeedError("run_deadline", "Run reached its 180-second source-processing deadline.") from None
                    state["pagesRead"] += 1
                    state["fetchedReviews"] += page.raw_count
                    state["invalidReviews"] += page.invalid_count
                    if page.invalid_count and not page.rows:
                        raise FeedError("all_records_invalid", "No returned review could be normalized; the source schema or text encoding may have changed.")
                    next_token = page.next_token
                    stop_app = False
                    for index, raw in enumerate(page.rows):
                        key = raw["reviewKey"]
                        if key in known:
                            state["knownReviewsSkipped"] += 1
                            continue
                        if key in seen:
                            state["duplicateReviews"] += 1
                            continue
                        seen.add(key)
                        reply_status = "unavailable" if raw["store"] == "app-store" else "present" if raw.get("developerReply") else "not-shown"
                        row = tag_review(classify_review({**raw, "observedAt": observed, "developerReplyStatus": reply_status}, previous))
                        reason = filter_reason(row, config)
                        if reason:
                            state["filteredReviews"] += 1
                            state["filterReasons"][reason] = state["filterReasons"].get(reason, 0) + 1
                            continue
                        if config.changed_only and row["reviewChange"] == "UNCHANGED":
                            state["unchangedReviewsSkipped"] += 1
                            continue
                        if on_result is not None and not await on_result(row):
                            stopped = stop_app = True
                            state["stopReason"] = "spending_or_callback_limit"
                            break
                        rows.append(row)
                        tracker.remember(row)
                        state["savedReviews"] += 1
                        more = index < len(page.rows) - 1 or next_token is not None
                        if len(rows) >= config.max_reviews:
                            stopped = stop_app = True
                            state["stopReason"] = "global_review_limit"
                            state["accessibleWindowEnded"] = not more
                            break
                        if state["savedReviews"] >= config.max_reviews_per_app:
                            stop_app = True
                            state["stopReason"] = "per_app_review_limit"
                            state["accessibleWindowEnded"] = not more
                            break
                    if stop_app:
                        break
                    if next_token is None:
                        state["accessibleWindowEnded"] = True
                        state["stopReason"] = "empty_page_or_unavailable" if page.raw_count == 0 else "source_window_ended"
                        break
                    if next_token in seen_tokens:
                        state["stopReason"] = "repeated_pagination_token"
                        break
                    seen_tokens.add(next_token)
                    token = next_token
                else:
                    state["stopReason"] = "page_limit"
            except FeedError as exc:
                state.update({"status": "failed", "errorCode": exc.status, "httpStatus": exc.http_status,
                              "error": str(exc), "stopReason": "source_error"})
                if exc.status in {"request_limit", "run_deadline"}:
                    stopped = True
            state["requests"] = client.requests - before
        requests = client.requests
    return {"results": rows, "diagnostics": diagnostics, "snapshot": tracker.snapshot, "summary": {
        "inputApps": len(config.apps), "successfulApps": sum(s["status"] == "success" for s in diagnostics),
        "failedApps": sum(s["status"] == "failed" for s in diagnostics), "skippedApps": sum(s["status"] == "skipped" for s in diagnostics),
        "savedReviews": len(rows), "fetchedReviews": sum(s["fetchedReviews"] for s in diagnostics),
        "invalidReviews": sum(s["invalidReviews"] for s in diagnostics), "filteredReviews": sum(s["filteredReviews"] for s in diagnostics),
        "knownReviewsSkipped": sum(s["knownReviewsSkipped"] for s in diagnostics),
        "unchangedReviewsSkipped": sum(s["unchangedReviewsSkipped"] for s in diagnostics),
        "snapshotTruncated": tracker.truncated,
        "savedReviewChanges": {kind: sum(row["reviewChange"] == kind for row in rows) for kind in ("NEW", "UPDATED", "UNCHANGED")},
        "duplicateReviews": sum(s["duplicateReviews"] for s in diagnostics), "requests": requests,
        "fullHistoryCoverage": False, "countsScope": "saved-results-only", "analysis": saved_analysis(rows),
        "countryRequested": config.country, "languageRequested": config.language,
        "resolvedApps": [app.key for app in config.apps], "observedAt": observed,
        "durationSeconds": round(time.monotonic() - started, 3),
        "note": "Public source windows are incomplete and storefront-scoped; absence is not evidence of deletion or no reviews. Saved samples are not representative app ratings."}}
