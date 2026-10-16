import argparse
import asyncio
import json
from pathlib import Path

from .config import RunConfig
from .output import export_results, rolling_known_ids
from .runner import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="AppReview Radar: public app reviews with keyword evidence and repeat-key deduplication.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", default=Path("output"), type=Path)
    parser.add_argument("--previous-ids", type=Path, help="Load known_review_ids.json exported by an earlier run.")
    parser.add_argument("--previous-snapshot", type=Path, help="Load snapshot.json to detect same-ID edits; use changedOnly to suppress unchanged reviews.")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if args.previous_snapshot:
            if not isinstance(data, dict):
                raise ValueError("Input must be a JSON object.")
            data = {**data, "previousSnapshot": json.loads(args.previous_snapshot.read_text(encoding="utf-8-sig"))}
        config = RunConfig.from_dict(data)
        if args.previous_ids:
            prior = json.loads(args.previous_ids.read_text(encoding="utf-8-sig"))
            previous = RunConfig.from_dict({**data, "knownReviewIds": prior})
            config = RunConfig.from_dict({**data, "knownReviewIds": list(dict.fromkeys([*config.known_review_ids, *previous.known_review_ids]))})
        report = asyncio.run(run_pipeline(config))
        report["knownReviewIds"], report["summary"]["knownReviewIdsTruncated"] = rolling_known_ids(config.known_review_ids, report["results"])
        export_results(report, args.output)
    except (OSError, ValueError, RecursionError) as exc:
        parser.exit(2, f"AppReview Radar: {exc}\n")
    except KeyboardInterrupt:
        parser.exit(130, "AppReview Radar: interrupted.\n")
    print(f"Saved {len(report['results'])} reviews to {args.output.resolve()}; {report['summary']['failedApps']} failed sources.")
    return 1 if report["summary"]["failedApps"] and not report["results"] else 0
