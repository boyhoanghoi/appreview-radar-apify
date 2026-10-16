"""Bounded caller-owned review fingerprints; no inferred removals or shared state."""

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024
MAX_SNAPSHOT_REVIEWS = 10000


def _encoded(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def validate_snapshot(value, country: str, language: str) -> dict:
    empty = {"version": 1, "country": country, "language": language, "reviews": {}}
    if value == {}:
        return empty
    try:
        if not isinstance(value, dict) or set(value) != set(empty) or type(value["version"]) is not int or value["version"] != 1:
            raise ValueError()
        if value["country"] != country or value["language"] != language:
            raise ValueError("previousSnapshot country/language must match this run; start a separate snapshot for a different storefront or language.")
        reviews = value["reviews"]
        if not isinstance(reviews, dict) or len(reviews) > MAX_SNAPSHOT_REVIEWS:
            raise ValueError()
        for key, fingerprint in reviews.items():
            if not isinstance(key, str) or not key.strip() or len(key) > 600 or not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
                raise ValueError()
        if len(_encoded(value)) > MAX_SNAPSHOT_BYTES:
            raise ValueError()
        return {**empty, "reviews": dict(reviews)}
    except (TypeError, RecursionError, UnicodeError, OverflowError):
        raise ValueError("previousSnapshot must be a version-1 review fingerprint snapshot, at most 10,000 entries and 2 MiB UTF-8.") from None
    except ValueError as exc:
        if str(exc).startswith("previousSnapshot country"):
            raise
        raise ValueError("previousSnapshot must be a version-1 review fingerprint snapshot, at most 10,000 entries and 2 MiB UTF-8.") from None


def review_fingerprint(row: dict) -> str:
    # Votes, source dates, observation time and rule tags are not content edits.
    fields = {name: row.get(name) for name in ("reviewTitle", "reviewText", "reviewTextTruncated", "rating", "appVersion", "developerReply")}
    reply = fields["developerReply"]
    fields["developerReply"] = reply.get("text") if isinstance(reply, dict) else None
    canonical = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def classify_review(row: dict, previous: dict) -> dict:
    digest = review_fingerprint(row)
    prior = previous["reviews"].get(row["reviewKey"])
    return {**row, "reviewChange": "NEW" if prior is None else "UNCHANGED" if prior == digest else "UPDATED",
            "contentHash": digest, "previousContentHash": prior}


class SnapshotTracker:
    def __init__(self, previous: dict):
        self.snapshot = {**previous, "reviews": dict(previous["reviews"])}
        self.byte_size = len(_encoded(self.snapshot))
        self.truncated = False

    def remember(self, row: dict) -> None:
        entries = self.snapshot["reviews"]
        key = row["reviewKey"]
        if key in entries:
            # Hashes have fixed size; move a successfully saved update to the end.
            entries.pop(key)
        else:
            self.byte_size += len(_encoded(key)) + 1 + len(_encoded(row["contentHash"])) + (1 if entries else 0)
        entries[key] = row["contentHash"]
        while len(entries) > MAX_SNAPSHOT_REVIEWS or self.byte_size > MAX_SNAPSHOT_BYTES:
            oldest = next(iter(entries))
            digest = entries.pop(oldest)
            self.byte_size -= len(_encoded(oldest)) + 1 + len(_encoded(digest)) + (1 if entries else 0)
            self.truncated = True


def write_snapshot(snapshot: dict, path: str | Path) -> None:
    """Atomic checkpoint: keep the previous file intact if export is interrupted."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            handle.write(_encoded(snapshot) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
