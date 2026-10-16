import asyncio
import csv
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reviewradar.analysis import filter_reason, saved_analysis, tag_review, topic_report
from reviewradar.cli import main
from reviewradar.config import App, RunConfig, parse_app
from reviewradar.output import export_results, feedback_markdown, reviews_csv, rolling_known_ids
from reviewradar.runner import run_pipeline
from reviewradar.sources import ReviewPage
from reviewradar.transport import FeedError


def review(identity="a", text="The app crashes. Please add offline mode.", rating=2, **extra):
    return {"reviewId": identity, "reviewKey": f"google-play:com.example.app:{identity}", "store": "google-play", "appId": "com.example.app",
        "appLabel": "com.example.app", "appLabelSource": "app-id", "rating": rating, "reviewTitle": "",
        "reviewText": text, "reviewTextTruncated": False, "reviewDate": "2026-10-15T00:00:00Z", "appVersion": "1.0",
        "helpfulVotes": 0, "developerReply": None, "countryRequested": "us", "languageRequested": "en",
        "appUrl": "https://play.google.com/store/apps/details?id=com.example.app", "sourceUrl": "https://play.google.com/_/PlayStoreUi/data/batchexecute?hl=en&gl=us", **extra}


class ConfigTests(unittest.TestCase):
    def test_supported_urls_presets_order_and_dedup(self):
        self.assertEqual(parse_app("https://play.google.com/store/apps/details?id=com.openai.chatgpt&hl=en", "google-play"), App("google-play", "com.openai.chatgpt"))
        self.assertEqual(parse_app("https://apps.apple.com/us/app/chatgpt/id6448311069", "app-store"), App("app-store", "6448311069"))
        config = RunConfig.from_dict({"appPreset": "chatgpt", "googlePlayApps": ["com.openai.chatgpt", "com.example.other"], "country": "VN", "language": "VI"})
        self.assertEqual([app.key for app in config.apps], ["google-play:com.openai.chatgpt", "google-play:com.example.other", "app-store:6448311069"])
        self.assertEqual(config.country, "vn")
        self.assertEqual(config.language, "vi")

    def test_unsafe_urls_invalid_filters_unknown_fields_and_combined_cap(self):
        for value in ("http://play.google.com/store/apps/details?id=com.x.app", "https://play.google.com.evil.test/store/apps/details?id=com.x.app", "https://u:p@play.google.com/store/apps/details?id=com.x.app", "https://127.0.0.1/", "com.app/../../private", "https://play.google.com/store/apps/details?id=com.x.app&id=com.y.app"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_app(value, "google-play")
        base = {"appPreset": "chatgpt"}
        for changes in ({"maxReviews": True}, {"minDelaySeconds": float("nan")}, {"minRating": 5, "maxRating": 3},
                        {"topicFilters": ["sentiment"]}, {"featureRequestsOnly": "yes"}, {"country": "../../"}, {"language": "en&x=1"},
                        {"changedOnly": "yes"}, {"replyFilter": "none"}, {"appVersionKeywords": "1.0"}, {"previousSnapshot": {"version": 1}},
                        {"reviewedAfter": "bad-date"}, {"knownReviewIds": [""]}, {"unknown": 1},
                        {"googlePlayApps": [f"com.x.app{i}" for i in range(10)]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                RunConfig.from_dict({**base, **changes})
        with self.assertRaises(ValueError):
            RunConfig.from_dict({})

    def test_extreme_dates_fail_validation_and_long_exported_keys_can_be_reused(self):
        with self.assertRaises(ValueError):
            RunConfig.from_dict({"appPreset": "chatgpt", "reviewedAfter": "0001-01-01T00:00:00+01:00"})
        app_id = "a." + "b" * 248
        key = f"google-play:{app_id}:" + "x" * 300
        keys, _ = rolling_known_ids([], [{"reviewKey": key}])
        config = RunConfig.from_dict({"googlePlayApps": [app_id], "knownReviewIds": keys})
        self.assertEqual(config.known_review_ids, (key,))


class AnalysisTests(unittest.TestCase):
    def test_topic_evidence_and_word_boundaries_without_sentiment_claim(self):
        row = tag_review(review(text="No ads, great performance. Please add offline mode."))
        self.assertEqual(set(row["topicTags"]), {"ads", "feature-request"})
        self.assertTrue(row["hasFeatureRequestPhrase"])
        self.assertIn("No ads", row["topicMatches"][0]["evidenceExcerpt"])
        self.assertNotIn("sentiment", row)
        self.assertEqual(tag_review(review(text="Downloads are complete."))["topicTags"], [])
        vietnamese = tag_review(review(text="Ứng dụng chậm, bị trừ tiền. Vui lòng thêm chế độ ngoại tuyến."))
        self.assertEqual(set(vietnamese["topicTags"]), {"performance", "billing", "feature-request"})
        for match in vietnamese["topicMatches"]:
            self.assertLessEqual(len(match["evidenceExcerpt"]), 240)
            original = vietnamese["reviewTitle"] + "\n" + vietnamese["reviewText"]
            self.assertEqual(match["evidenceExcerpt"], original[match["excerptStart"]:match["excerptStart"] + 240])

    def test_filters_and_unknown_dates_apply_independently(self):
        config = RunConfig.from_dict({"googlePlayApps": ["com.example.app"], "maxRating": 3, "includeKeywords": ["offline"], "topicFilters": ["feature-request"], "featureRequestsOnly": True, "reviewedAfter": "2026-10-01"})
        row = tag_review(review())
        self.assertIsNone(filter_reason(row, config))
        self.assertEqual(filter_reason({**row, "rating": 5}, config), "rating_outside_range")
        self.assertEqual(filter_reason({**row, "reviewDate": None}, config), "review_date_unknown")
        self.assertEqual(filter_reason({**row, "reviewDate": "2026-09-01T00:00:00Z"}, config), "reviewed_before_cutoff")
        self.assertEqual(filter_reason(row, replace(config, exclude_keywords=("offline",))), "keyword_excluded")
        self.assertEqual(filter_reason(row, replace(config, topic_filters=("privacy",))), "topic_not_matched")

    def test_analysis_uses_saved_rows_only_and_topics_overlap(self):
        rows = [tag_review(review())]
        analysis = saved_analysis(rows)
        self.assertEqual(analysis["savedReviews"], 1)
        self.assertEqual(analysis["sampleAverageRating"], 2)
        self.assertEqual(analysis["ratingHistogram"]["2"], 1)
        self.assertEqual(analysis["topicMentionCounts"], {"stability": 1, "feature-request": 1})
        self.assertEqual(topic_report(rows)["scope"], "saved-results-only")
        self.assertIsNone(saved_analysis([])["sampleAverageRating"])


class FakeClient:
    def __init__(self, config):
        self.requests = 0
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    def config(self, **changes):
        return RunConfig.from_dict({"googlePlayApps": ["com.example.app"], **changes})

    async def test_known_duplicates_and_filters_precede_saved_callback(self):
        async def fetch(client, app, config, token):
            client.requests += 1
            return ReviewPage([review("old"), review("high", rating=5), review("new"), review("new")], None, 4)
        accepted = []
        async def save(row):
            accepted.append(row)
            return True
        report = await run_pipeline(self.config(maxRating=3, knownReviewIds=[review("old")["reviewKey"]]), save, client_factory=FakeClient, page_fetcher=fetch)
        self.assertEqual([r["reviewId"] for r in accepted], ["new"])
        self.assertEqual(report["summary"]["knownReviewsSkipped"], 1)
        self.assertEqual(report["summary"]["filteredReviews"], 1)
        self.assertEqual(report["summary"]["duplicateReviews"], 1)
        self.assertEqual(report["summary"]["analysis"]["savedReviews"], 1)
        self.assertFalse(report["summary"]["fullHistoryCoverage"])

    async def test_caps_and_callback_refusal_do_not_include_unsaved_rows(self):
        async def fetch(client, app, config, token):
            client.requests += 1
            return ReviewPage([review("1"), review("2")], "next", 2)
        async def refuse(row):
            return False
        report = await run_pipeline(self.config(), refuse, client_factory=FakeClient, page_fetcher=fetch)
        self.assertEqual(report["results"], [])
        self.assertEqual(report["summary"]["analysis"]["savedReviews"], 0)
        capped = await run_pipeline(self.config(maxReviews=1, appStoreApps=["6448311069"]), client_factory=FakeClient, page_fetcher=fetch)
        self.assertEqual(len(capped["results"]), 1)
        self.assertEqual(capped["diagnostics"][1]["status"], "skipped")
        self.assertFalse(capped["diagnostics"][0]["accessibleWindowEnded"])

    async def test_error_empty_window_and_repeated_cursor_are_explicit(self):
        async def error(client, app, config, token):
            raise FeedError("rate-limited", "Denied", 429)
        failed = await run_pipeline(self.config(), client_factory=FakeClient, page_fetcher=error)
        self.assertEqual(failed["summary"]["failedApps"], 1)
        self.assertEqual(failed["diagnostics"][0]["httpStatus"], 429)
        async def empty(client, app, config, token):
            return ReviewPage([], None, 0)
        report = await run_pipeline(self.config(), client_factory=FakeClient, page_fetcher=empty)
        self.assertEqual(report["diagnostics"][0]["stopReason"], "empty_page_or_unavailable")
        self.assertFalse(report["summary"]["fullHistoryCoverage"])
        async def repeat(client, app, config, token):
            return ReviewPage([review()], "same", 1)
        report = await run_pipeline(self.config(), client_factory=FakeClient, page_fetcher=repeat)
        self.assertEqual(report["diagnostics"][0]["stopReason"], "repeated_pagination_token")

    async def test_global_deadline_stops_sources_and_preserves_existing_rows(self):
        async def slow(client, app, config, token):
            await asyncio.sleep(0.05)
        with patch("reviewradar.runner.MAX_RUN_SECONDS", 0.001):
            report = await run_pipeline(self.config(appStoreApps=["6448311069"]), client_factory=FakeClient, page_fetcher=slow)
        self.assertEqual(report["diagnostics"][0]["errorCode"], "run_deadline")
        self.assertEqual(report["diagnostics"][1]["status"], "skipped")


class ExportTests(unittest.TestCase):
    def test_csv_and_markdown_escape_review_content_without_mutation(self):
        row = tag_review(review(text="=SUM(A1) <script>alert(1)</script> [attack](javascript:bad)", appLabel="<b>Fake</b>"))
        exported = list(csv.DictReader(io.StringIO(reviews_csv([row]))))[0]
        self.assertTrue(exported["reviewText"].startswith("'=SUM"))
        self.assertTrue(row["reviewText"].startswith("=SUM"))
        report = feedback_markdown([row], {})
        self.assertNotIn("<script>", report)
        self.assertNotIn("<b>", report)
        self.assertNotIn("](javascript:", report)
        self.assertIn("## Saved reviews by app", report)
        self.assertIn("| 1 | 2.00 |", report)

    def test_empty_exports_and_rolling_seen_list_only_saved(self):
        row = tag_review(review())
        keys, truncated = rolling_known_ids(["old"], [row])
        self.assertEqual(keys, ["old", row["reviewKey"]])
        self.assertFalse(truncated)
        keys, truncated = rolling_known_ids([str(n) for n in range(10000)], [row])
        self.assertEqual(len(keys), 10000)
        self.assertTrue(truncated)
        with tempfile.TemporaryDirectory() as directory:
            export_results({"results": [], "summary": {}, "diagnostics": [], "knownReviewIds": ["old"]}, directory)
            text = (Path(directory) / "feedback-report.md").read_text(encoding="utf-8")
            self.assertIn("No matching reviews were saved", text)
            self.assertEqual(json.loads((Path(directory) / "known_review_ids.json").read_text()), ["old"])


class CliTests(unittest.TestCase):
    def test_prior_keys_merge_before_pipeline(self):
        seen = []
        async def pipeline(config):
            seen.extend(config.known_review_ids)
            return {"results": [], "summary": {"failedApps": 0}, "diagnostics": []}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "input.json").write_text(json.dumps({"appPreset": "chatgpt", "knownReviewIds": ["first"]}))
            (root / "prior.json").write_text(json.dumps(["prior", "first"]))
            args = ["reviewradar", "--input", str(root / "input.json"), "--previous-ids", str(root / "prior.json"), "--output", str(root / "out")]
            with patch("sys.argv", args), patch("reviewradar.cli.run_pipeline", new=pipeline), patch("builtins.print"):
                self.assertEqual(main(), 0)
            self.assertEqual(seen, ["first", "prior"])
            self.assertEqual(json.loads((root / "out/known_review_ids.json").read_text()), seen)
