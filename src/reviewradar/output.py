"""Portable exports built only from reviews that were actually saved."""

import csv
import io
import json
from pathlib import Path
import re
from urllib.parse import quote, urlsplit

from .analysis import saved_analysis, topic_report
from .snapshot import write_snapshot


def spreadsheet_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value


def reviews_csv(rows: list[dict]) -> str:
    fields = ["reviewKey", "reviewChange", "contentHash", "previousContentHash", "store", "appId", "appLabel", "appLabelSource", "rating", "reviewTitle", "reviewText", "reviewTextTruncated",
              "reviewDate", "appVersion", "helpfulVotes", "developerReply", "developerReplyStatus", "topicTags", "topicMatches", "hasFeatureRequestPhrase",
              "analysisMethod", "countryRequested", "languageRequested", "reviewId", "appUrl", "sourceUrl", "observedAt"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: spreadsheet_cell(row.get(field)) for field in fields})
    return stream.getvalue()


def md_text(value) -> str:
    return re.sub(r"([\\`*_{}\[\]()<>#!|])", r"\\\1", " ".join(str(value).split()))


def md_link(title: str, url: str) -> str:
    try:
        parsed = urlsplit(url)
        safe = parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        safe = False
    return f"[{md_text(title)}]({quote(url, safe=':/?=&%+@,;~.-_')})" if safe else md_text(title)


def feedback_markdown(rows: list[dict], summary: dict) -> str:
    analysis = saved_analysis(rows)
    lines = ["# App feedback shortlist", "", f"{len(rows)} saved reviews from selected public app-store feeds.", "",
        "This is a filtered sample. Counts and average ratings below describe saved rows only, not the app's overall rating or issue prevalence.", "",
        "Topic tags are literal English/Vietnamese keyword mentions. Praise and negations can match; read the quoted evidence before deciding what to change.", ""]
    if summary.get("observedAt"):
        lines.extend([f"Observed: {md_text(summary['observedAt'])}", ""])
    if summary.get("failedApps") or summary.get("skippedApps"):
        lines.extend([f"Source failures: {summary.get('failedApps', 0)}. Skipped apps: {summary.get('skippedApps', 0)}. See DIAGNOSTICS before comparing apps.", ""])
    if summary.get("savedReviewChanges"):
        changes = summary["savedReviewChanges"]
        lines.extend([f"Compared with supplied snapshot: {changes.get('NEW', 0)} new to this baseline, {changes.get('UPDATED', 0)} updated, {changes.get('UNCHANGED', 0)} unchanged saved reviews.", "",
                      "New to a snapshot does not mean newly posted. Missing reviews never imply deletion.", ""])
    lines.extend(["## Saved reviews by app", "", "| App | Store | Saved reviews | Sample average stars |", "| --- | --- | ---: | ---: |"])
    grouped = {}
    for row in rows:
        grouped.setdefault((row["store"], row["appId"]), []).append(row)
    for (store, _), sample in grouped.items():
        first = sample[0]
        label = md_link(first["appLabel"], first["appUrl"])
        average = sum(row["rating"] for row in sample) / len(sample)
        lines.append(f"| {label} | {md_text(store)} | {len(sample)} | {average:.2f} |")
    if not rows:
        lines.append("| No saved reviews | — | 0 | — |")
    lines.append("")
    lines.extend(["## Saved sample", "", "| Rating | Saved reviews |", "| --- | ---: |"])
    lines.extend(f"| {rating} | {count} |" for rating, count in analysis["ratingHistogram"].items())
    lines.extend(["", "## Topic mentions", "", "| Keyword topic | Saved reviews mentioning it |", "| --- | ---: |"])
    lines.extend(f"| {md_text(topic)} | {count} |" for topic, count in analysis["topicMentionCounts"].items())
    if not analysis["topicMentionCounts"]:
        lines.append("| No configured keyword match | 0 |")
    lines.extend(["", "## Review excerpts", ""])
    for row in rows[:100]:
        heading = f"{row['appLabel']} - {row['rating']}/5 - {row.get('reviewDate') or 'date unknown'}"
        excerpt = row["reviewText"][:500]
        lines.extend([f"### {md_link(heading, row['appUrl'])}", "", f"Key: {md_text(row['reviewKey'])}", "",
            "> " + md_text(excerpt) + (" … [excerpt]" if len(row["reviewText"]) > 500 else ""), "",
            "Keyword topics: " + md_text(", ".join(row["topicTags"]) or "none"), ""])
    if len(rows) > 100:
        lines.extend(["Report excerpt list is limited to the first 100 saved reviews; CSV/JSON contain every saved row.", ""])
    if not rows:
        lines.extend(["No matching reviews were saved. Check source diagnostics, filters and the supplied known-ID list.", ""])
    lines.extend(["## Source coverage", "", "Public feed history is limited. Empty or missing pages do not prove that an app has no reviews. Country/language fields describe requested source context, not reviewer residence. See DIAGNOSTICS for each app.", ""])
    return "\n".join(lines)


def rolling_known_ids(previous, rows: list[dict]) -> tuple[list[str], bool]:
    union = list(dict.fromkeys([*previous, *(row["reviewKey"] for row in rows)]))
    return union[-10000:], len(union) > 10000


def export_results(report: dict, directory: str | Path) -> None:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("results", "summary", "diagnostics"):
        (directory / f"{name}.json").write_text(json.dumps(report[name], indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (directory / "topics.json").write_text(json.dumps(topic_report(report["results"]), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (directory / "results.csv").write_text("\ufeff" + reviews_csv(report["results"]), encoding="utf-8", newline="")
    (directory / "feedback-report.md").write_text(feedback_markdown(report["results"], report["summary"]), encoding="utf-8")
    if "knownReviewIds" in report:
        (directory / "known_review_ids.json").write_text(json.dumps(report["knownReviewIds"], indent=2) + "\n", encoding="utf-8")
    if "snapshot" in report:
        write_snapshot(report["snapshot"], directory / "snapshot.json")
