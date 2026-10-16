"""Persist and charge only filtered reviews; exports and state use saved rows."""

import asyncio
from dataclasses import replace

from .analysis import saved_analysis, topic_report
from .config import RunConfig
from .output import feedback_markdown, reviews_csv, rolling_known_ids
from .runner import run_pipeline


BILLABLE_EVENT = "review-saved"


async def run_actor():
    from apify import Actor

    async with Actor:
        try:
            config = RunConfig.from_dict(await Actor.get_input() or {})
        except ValueError as exc:
            message = f"Invalid input: {exc}"
            Actor.log.error(message)
            await Actor.set_value("OUTPUT", {"error": message, "results": []})
            Actor.exit_code, Actor.status_message = 1, message
            return
        manager = Actor.get_charging_manager()
        pricing = manager.get_pricing_info()
        ppe = pricing.is_pay_per_event
        if ppe and Actor.configuration.is_at_home and BILLABLE_EVENT not in pricing.per_event_prices:
            message = f"Missing pay-per-event configuration for {BILLABLE_EVENT}."
            Actor.log.error(message)
            await Actor.set_value("OUTPUT", {"error": message, "results": []})
            Actor.exit_code, Actor.status_message = 1, message
            return
        budget_reached = False
        saved = []
        if ppe:
            available = manager.compute_push_data_limit(config.max_reviews, BILLABLE_EVENT, is_default_dataset=True)
            budget_reached = available == 0
            if available:
                config = replace(config, max_reviews=min(config.max_reviews, available))

        async def save(row):
            nonlocal budget_reached
            if ppe:
                if manager.compute_push_data_limit(1, BILLABLE_EVENT, is_default_dataset=True) < 1:
                    budget_reached = True
                    return False
                charge = await Actor.push_data(row, charged_event_name=BILLABLE_EVENT)
                if charge.charged_count:
                    saved.append(row)
                budget_reached = charge.event_charge_limit_reached or charge.charged_count == 0
                return charge.charged_count > 0
            await Actor.push_data(row)
            saved.append(row)
            return True

        if budget_reached:
            report = {"results": [], "diagnostics": [{"app": app.key, "status": "skipped", "stopReason": "spending_limit"} for app in config.apps],
                      "summary": {"inputApps": len(config.apps), "failedApps": 0, "requests": 0, "fullHistoryCoverage": False}}
        else:
            report = await run_pipeline(config, save)
        report["results"] = saved
        report.setdefault("snapshot", config.previous_snapshot)
        known, truncated = rolling_known_ids(config.known_review_ids, saved)
        report["knownReviewIds"] = known
        report["summary"].update({"savedReviews": len(saved), "analysis": saved_analysis(saved), "countsScope": "saved-results-only",
            "budgetLimitReached": budget_reached, "knownReviewIdsTruncated": truncated,
            "billingEvent": BILLABLE_EVENT if ppe else None,
            "chargedReviews": manager.get_charged_event_count(BILLABLE_EVENT) if ppe else 0})
        await Actor.set_value("RESULTS", saved)
        await Actor.set_value("SUMMARY", report["summary"])
        await Actor.set_value("DIAGNOSTICS", report["diagnostics"])
        await Actor.set_value("KNOWN_REVIEW_IDS", known)
        await Actor.set_value("SNAPSHOT", report["snapshot"])
        await Actor.set_value("TOPICS", topic_report(saved))
        await Actor.set_value("results.csv", reviews_csv(saved), content_type="text/csv; charset=utf-8")
        await Actor.set_value("feedback-report.md", feedback_markdown(saved, report["summary"]), content_type="text/markdown; charset=utf-8")
        await Actor.set_value("OUTPUT", report)
        failed = report["summary"].get("failedApps", 0)
        if failed and not saved:
            Actor.exit_code = 1
        Actor.status_message = f"Saved {len(saved)} matching reviews; {failed} failed sources. See diagnostics for source windows."


def main():
    asyncio.run(run_actor())


if __name__ == "__main__":
    main()
