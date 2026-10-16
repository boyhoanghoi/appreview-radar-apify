import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from reviewradar.actor import BILLABLE_EVENT, run_actor
from reviewradar.analysis import tag_review
from reviewradar.config import RunConfig
from reviewradar.runner import run_pipeline
from reviewradar.snapshot import review_fingerprint, validate_snapshot
from reviewradar.sources import ReviewPage
from test_core import FakeClient
from test_core import review


class FakeManager:
    def __init__(self, remaining=2, ppe=True):
        self.remaining, self.ppe, self.count = remaining, ppe, 0
    def get_pricing_info(self):
        return SimpleNamespace(is_pay_per_event=self.ppe, per_event_prices={BILLABLE_EVENT: 0.0005})
    def compute_push_data_limit(self, count, event, *, is_default_dataset):
        return min(count, self.remaining)
    def get_charged_event_count(self, event):
        return self.count


class FakeActor:
    def __init__(self, manager):
        self.manager = manager
        self.input = {"appPreset": "chatgpt", "knownReviewIds": ["old"]}
        self.dataset, self.writes, self.events = [], {}, []
        self.configuration = SimpleNamespace(is_at_home=False)
        self.log = SimpleNamespace(error=lambda value: None)
        self.exit_code, self.status_message = 0, ""
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    async def get_input(self):
        return self.input
    def get_charging_manager(self):
        return self.manager
    async def set_value(self, key, value, **kwargs):
        self.writes[key] = value
    async def push_data(self, row, charged_event_name=None):
        if charged_event_name and self.manager.remaining < 1:
            return SimpleNamespace(charged_count=0, event_charge_limit_reached=True)
        self.dataset.append(row)
        self.events.append(charged_event_name)
        if charged_event_name:
            self.manager.count += 1
            self.manager.remaining -= 1
        return SimpleNamespace(charged_count=1 if charged_event_name else 0, event_charge_limit_reached=self.manager.remaining == 0)


async def pipeline(config, callback):
    saved = []
    for i in range(min(3, config.max_reviews)):
        row = tag_review(review(str(i)))
        if not await callback(row):
            break
        saved.append(row)
    return {"results": saved, "diagnostics": [], "summary": {"savedReviews": len(saved), "failedApps": 0}}


class BillingTests(unittest.IsolatedAsyncioTestCase):
    async def run_fake(self, actor, runner=pipeline):
        with patch.dict(sys.modules, {"apify": SimpleNamespace(Actor=actor)}), patch("reviewradar.actor.run_pipeline", new=runner):
            await run_actor()

    async def test_final_affordable_row_saved_and_only_saved_evidence_and_keys_exported(self):
        actor = FakeActor(FakeManager(remaining=1))
        await self.run_fake(actor)
        self.assertEqual(len(actor.dataset), 1)
        self.assertEqual(actor.events, [BILLABLE_EVENT])
        self.assertEqual(actor.writes["SUMMARY"]["chargedReviews"], 1)
        self.assertTrue(actor.writes["SUMMARY"]["budgetLimitReached"])
        self.assertEqual(actor.writes["KNOWN_REVIEW_IDS"], ["old", actor.dataset[0]["reviewKey"]])
        self.assertEqual(actor.writes["SUMMARY"]["analysis"]["savedReviews"], 1)
        self.assertIn("1 saved reviews", actor.writes["feedback-report.md"])
        self.assertEqual(actor.writes["RESULTS"], actor.dataset)
        self.assertEqual(actor.writes["TOPICS"]["topics"][0]["savedReviewCount"], 1)

    async def test_zero_budget_performs_no_source_requests_and_preserves_prior_keys(self):
        actor = FakeActor(FakeManager(remaining=0))
        snapshot = validate_snapshot({}, "us", "en")
        snapshot["reviews"]["old-key"] = "a" * 64
        actor.input["previousSnapshot"] = snapshot
        runner = AsyncMock()
        await self.run_fake(actor, runner)
        runner.assert_not_awaited()
        self.assertEqual(actor.events, [])
        self.assertEqual(actor.writes["KNOWN_REVIEW_IDS"], ["old"])
        self.assertEqual(actor.writes["SUMMARY"]["analysis"]["savedReviews"], 0)
        self.assertEqual(actor.writes["SNAPSHOT"], snapshot)

    async def test_snapshot_advances_only_for_final_affordable_edited_review(self):
        actor = FakeActor(FakeManager(remaining=1))
        prior = validate_snapshot({}, "us", "en")
        original = review("edit")
        prior["reviews"][original["reviewKey"]] = review_fingerprint(original)
        actor.input = {"googlePlayApps": ["com.example.app"], "changedOnly": True, "previousSnapshot": prior}
        async def fetch(client, app, config, token):
            return ReviewPage([review("edit", text="Edited now"), review("unpaid")], None, 2)
        async def actual(config, save):
            return await run_pipeline(config, save, client_factory=FakeClient, page_fetcher=fetch)
        await self.run_fake(actor, actual)
        self.assertEqual(actor.events, [BILLABLE_EVENT])
        self.assertEqual(actor.dataset[0]["reviewChange"], "UPDATED")
        self.assertEqual(actor.writes["SNAPSHOT"]["reviews"], {original["reviewKey"]: actor.dataset[0]["contentHash"]})
        self.assertEqual(actor.writes["SUMMARY"]["savedReviewChanges"], {"NEW": 0, "UPDATED": 1, "UNCHANGED": 0})

    async def test_non_ppe_run_has_no_explicit_event_charge(self):
        actor = FakeActor(FakeManager(ppe=False))
        await self.run_fake(actor)
        self.assertEqual(actor.events, [None, None, None])
        self.assertEqual(actor.writes["SUMMARY"]["chargedReviews"], 0)

    async def test_invalid_input_and_missing_price_fail_without_source_work(self):
        for mode in ("input", "price"):
            actor = FakeActor(FakeManager())
            if mode == "input":
                actor.input = {"googlePlayApps": ["https://127.0.0.1/"]}
            else:
                actor.configuration.is_at_home = True
                actor.manager.get_pricing_info = lambda: SimpleNamespace(is_pay_per_event=True, per_event_prices={})
            runner = AsyncMock()
            await self.run_fake(actor, runner)
            runner.assert_not_awaited()
            self.assertEqual(actor.exit_code, 1)
            self.assertEqual(actor.events, [])

    async def test_all_source_failures_preserve_diagnostics_and_signal_failed_run(self):
        actor = FakeActor(FakeManager())
        async def failed(config, callback):
            return {"results": [], "diagnostics": [{"errorCode": "rate-limited"}], "summary": {"failedApps": 2}}
        await self.run_fake(actor, failed)
        self.assertEqual(actor.exit_code, 1)
        self.assertEqual(actor.writes["DIAGNOSTICS"][0]["errorCode"], "rate-limited")
        self.assertEqual(actor.writes["KNOWN_REVIEW_IDS"], ["old"])
