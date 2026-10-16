from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reviewradar.analysis import filter_reason, tag_review
from reviewradar.cli import main
from reviewradar.config import RunConfig
from reviewradar.output import export_results
from reviewradar.runner import run_pipeline
from reviewradar.snapshot import SnapshotTracker, classify_review, review_fingerprint, validate_snapshot, write_snapshot
from reviewradar.sources import ReviewPage
from reviewradar.sources import _normal
from reviewradar.config import App
from reviewradar.transport import FeedError
from test_core import FakeClient, review


class SnapshotTests(unittest.TestCase):
    def test_unpaired_source_surrogates_are_rejected_before_billing_or_hashing(self):
        config = RunConfig.from_dict({"appPreset": "chatgpt"})
        row = _normal(App("google-play", "com.openai.chatgpt"), config,
            review_id="source-id", text="bad\ud800text", rating=1, source_url="https://play.google.com")
        self.assertIsNone(row)

    def test_hash_tracks_content_edits_and_replies_but_not_votes_dates_or_observation(self):
        original = review()
        digest = review_fingerprint(original)
        self.assertEqual(digest, review_fingerprint({**original, "helpfulVotes": 999, "reviewDate": "2026-10-16T00:00:00Z", "observedAt": "later"}))
        for changes in ({"rating": 1}, {"reviewText": "Edited"}, {"appVersion": "2.0"}, {"developerReply": {"text": "Resolved", "repliedAt": None}}):
            self.assertNotEqual(digest, review_fingerprint({**original, **changes}))
        one = {**original, "developerReply": {"text": "Resolved", "repliedAt": None}}
        two = {**original, "developerReply": {"repliedAt": None, "text": "Resolved"}}
        self.assertEqual(review_fingerprint(one), review_fingerprint(two))
        timestamp_only = {**one, "developerReply": {"text": "Resolved", "repliedAt": "2026-10-16T00:00:00Z"}}
        self.assertEqual(review_fingerprint(one), review_fingerprint(timestamp_only))
        first = classify_review(original, validate_snapshot({}, "us", "en"))
        self.assertEqual(first["reviewChange"], "NEW")
        snapshot = {"version": 1, "country": "us", "language": "en", "reviews": {original["reviewKey"]: digest}}
        self.assertEqual(classify_review(original, snapshot)["reviewChange"], "UNCHANGED")
        self.assertEqual(classify_review({**original, "rating": 1}, snapshot)["reviewChange"], "UPDATED")

    def test_scope_malformed_input_and_export_roundtrip(self):
        base = validate_snapshot({}, "gb", "en")
        for bad in (None, [], {**base, "version": True}, {**base, "reviews": {"key": "nohash"}}, {**base, "extra": 1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_snapshot(bad, "gb", "en")
        with self.assertRaisesRegex(ValueError, "country/language"):
            validate_snapshot(base, "us", "en")
        tracker = SnapshotTracker(base)
        tracker.remember(classify_review(review(), base))
        self.assertEqual(validate_snapshot(tracker.snapshot, "gb", "en"), tracker.snapshot)

    def test_unicode_byte_bound_and_oldest_eviction_stay_reusable(self):
        with patch("reviewradar.snapshot.MAX_SNAPSHOT_BYTES", 1200), patch("reviewradar.snapshot.MAX_SNAPSHOT_REVIEWS", 3):
            base = validate_snapshot({}, "us", "en")
            tracker = SnapshotTracker(base)
            for i in range(8):
                item = {**review(str(i)), "reviewKey": "google-play:com.example.app:" + str(i) + "ệ" * 100}
                tracker.remember(classify_review(item, base))
                encoded = json.dumps(tracker.snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self.assertLessEqual(len(encoded), 1200)
                self.assertLessEqual(len(tracker.snapshot["reviews"]), 3)
                self.assertEqual(len(encoded), tracker.byte_size)
                validate_snapshot(tracker.snapshot, "us", "en")
            self.assertTrue(tracker.truncated)
            self.assertTrue(any("7ệ" in key for key in tracker.snapshot["reviews"]))
            too_big = {**base, "reviews": {str(i) + "ệ" * 150: "a" * 64 for i in range(3)}}
            with self.assertRaises(ValueError):
                validate_snapshot(too_big, "us", "en")

    def test_atomic_checkpoint_survives_replace_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            original = validate_snapshot({}, "us", "en")
            write_snapshot(original, path)
            changed = {**original, "reviews": {"key": "a" * 64}}
            with patch("reviewradar.snapshot.os.replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    write_snapshot(changed, path)
            self.assertEqual(json.loads(path.read_text()), original)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_reply_filters_do_not_treat_unavailable_apple_reply_as_absent(self):
        config = RunConfig.from_dict({"appPreset": "chatgpt", "replyFilter": "without-visible-reply"})
        base = tag_review(review(developerReplyStatus="not-shown"))
        self.assertIsNone(filter_reason(base, config))
        self.assertEqual(filter_reason({**base, "developerReplyStatus": "unavailable"}, config), "reply_status_unavailable")
        self.assertEqual(filter_reason({**base, "developerReplyStatus": "present"}, config), "has_visible_reply")
        self.assertIsNone(filter_reason({**base, "developerReplyStatus": "present"}, replace(config, reply_filter="with-reply")))
        self.assertEqual(filter_reason({**base, "appVersion": None}, replace(config, app_version_keywords=("2.0",))), "app_version_not_matched")


class SnapshotPipelineTests(unittest.IsolatedAsyncioTestCase):
    def config(self, **changes):
        return RunConfig.from_dict({"googlePlayApps": ["com.example.app"], "changedOnly": True, **changes})

    async def test_same_id_edit_saved_unchanged_free_and_missing_baseline_preserved(self):
        initial = [review("1"), review("2"), review("outside-window")]
        base = validate_snapshot({}, "us", "en")
        tracker = SnapshotTracker(base)
        for row in initial:
            tracker.remember(classify_review(row, base))
        saved = []
        async def fetch(client, app, config, token):
            return ReviewPage([review("1"), review("2", text="Edited: login is broken")], None, 2)
        async def save(row):
            saved.append(row)
            return True
        report = await run_pipeline(self.config(previousSnapshot=tracker.snapshot), save, client_factory=FakeClient, page_fetcher=fetch)
        self.assertEqual([row["reviewId"] for row in saved], ["2"])
        self.assertEqual(saved[0]["reviewChange"], "UPDATED")
        self.assertEqual(report["summary"]["unchangedReviewsSkipped"], 1)
        self.assertEqual(report["summary"]["savedReviewChanges"], {"NEW": 0, "UPDATED": 1, "UNCHANGED": 0})
        self.assertIn(initial[2]["reviewKey"], report["snapshot"]["reviews"])
        self.assertEqual(report["snapshot"]["reviews"][initial[1]["reviewKey"]], saved[0]["contentHash"])

    async def test_failed_filtered_known_and_unpaid_reviews_never_advance_fingerprints(self):
        base = validate_snapshot({}, "us", "en")
        original = review("1")
        base["reviews"][original["reviewKey"]] = review_fingerprint(original)
        async def fetch(client, app, config, token):
            return ReviewPage([review("1", text="Edited")], None, 1)
        async def refuse(row):
            return False
        for changes, callback in (({}, refuse), ({"maxRating": 1}, None), ({"knownReviewIds": [original["reviewKey"]]}, None)):
            report = await run_pipeline(self.config(previousSnapshot=base, **changes), callback, client_factory=FakeClient, page_fetcher=fetch)
            self.assertEqual(report["results"], [])
            self.assertEqual(report["snapshot"], base)
        async def error(client, app, config, token):
            raise FeedError("rate-limited", "Denied", 429)
        failed = await run_pipeline(self.config(previousSnapshot=base), client_factory=FakeClient, page_fetcher=error)
        self.assertEqual(failed["snapshot"], base)
        self.assertEqual(failed["summary"]["failedApps"], 1)

    async def test_all_invalid_source_records_are_a_failure_and_keep_snapshot(self):
        base = validate_snapshot({}, "us", "en")
        base["reviews"]["prior-key"] = "a" * 64
        async def invalid(client, app, config, token):
            return ReviewPage([], None, 3, 3)
        report = await run_pipeline(self.config(previousSnapshot=base), client_factory=FakeClient, page_fetcher=invalid)
        self.assertEqual(report["summary"]["failedApps"], 1)
        self.assertEqual(report["snapshot"], base)
        self.assertEqual(report["diagnostics"][0]["errorCode"], "all_records_invalid")


class SnapshotCliTests(unittest.TestCase):
    def test_previous_snapshot_file_loaded_and_exported_without_known_id_suppression(self):
        snapshot = validate_snapshot({}, "gb", "en")
        snapshot["reviews"]["old-key"] = "a" * 64
        seen = []
        async def pipeline(config):
            seen.append(config.previous_snapshot)
            self.assertEqual(config.known_review_ids, ())
            return {"results": [], "snapshot": config.previous_snapshot, "diagnostics": [], "summary": {"failedApps": 0}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "input.json").write_text(json.dumps({"appPreset": "chatgpt", "country": "gb", "changedOnly": True}))
            write_snapshot(snapshot, root / "prior.json")
            args = ["reviewradar", "--input", str(root / "input.json"), "--previous-snapshot", str(root / "prior.json"), "--output", str(root / "out")]
            with patch("sys.argv", args), patch("reviewradar.cli.run_pipeline", new=pipeline), patch("builtins.print"):
                self.assertEqual(main(), 0)
            self.assertEqual(seen, [snapshot])
            self.assertEqual(json.loads((root / "out/snapshot.json").read_text()), snapshot)
