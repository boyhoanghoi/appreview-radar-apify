"""Normalize public written reviews, excluding reviewer names and photos.

Google RPC shape/index mapping adapted from google-play-scraper (MIT, PlanB).
See licenses/GOOGLE_PLAY_SCRAPER_MIT.txt. No package transport is imported.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import re
from urllib.parse import urlencode, urlsplit

from .config import LABELS, iso_datetime
from .transport import FeedError


MAX_TOKEN_LENGTH = 16384


@dataclass
class ReviewPage:
    rows: list[dict]
    next_token: str | None
    raw_count: int
    invalid_count: int = 0


def _at(value, *path):
    try:
        for key in path:
            value = value[key]
        return value
    except (TypeError, KeyError, IndexError):
        return None


def _date(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(value):
        try:
            return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")
        except (ValueError, OverflowError, OSError):
            return None
    parsed = iso_datetime(value)
    return parsed.isoformat().replace("+00:00", "Z") if parsed else None


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _label(obj):
    return obj.get("label") if isinstance(obj, dict) else None


def _normal(app, config, *, review_id, text, rating, title="", date=None, version=None, votes=None, reply=None, source_url):
    if not isinstance(review_id, str) or not review_id.strip() or len(review_id) > 300:
        return None
    if not isinstance(text, str) or not text.strip() or isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
        return None
    text = text.strip()
    app_url = (f"https://play.google.com/store/apps/details?id={app.app_id}" if app.store == "google-play"
        else f"https://apps.apple.com/{config.country}/app/id{app.app_id}")
    row = {"reviewId": review_id, "reviewKey": f"{app.key}:{review_id}", "store": app.store, "appId": app.app_id,
        "appLabel": LABELS.get(app.key, app.app_id), "appLabelSource": "demo-preset" if app.key in LABELS else "app-id",
        "countryRequested": config.country, "languageRequested": config.language if app.store == "google-play" else None,
        "reviewTitle": title[:500] if isinstance(title, str) else "", "reviewText": text[:8000], "reviewTextTruncated": len(text) > 8000,
        "rating": rating, "reviewDate": _date(date), "appVersion": version[:200] if isinstance(version, str) and version else None,
        "helpfulVotes": _int(votes), "developerReply": reply, "appUrl": app_url, "sourceUrl": source_url}
    try:
        json.dumps(row, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (UnicodeError, ValueError):
        return None
    return row


def _google_payload(text):
    """Read standard batchexecute frames, including optional length-prefixed frames."""
    if text.startswith(")]}'"):
        text = text[4:].lstrip()
    decoder = json.JSONDecoder()
    cursor = 0
    try:
        for _ in range(12):
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
            endline = text.find("\n", cursor)
            if endline != -1 and text[cursor:endline].strip().isdigit():
                cursor = endline + 1
            if cursor >= len(text):
                break
            frame, cursor = decoder.raw_decode(text, cursor)
            if not isinstance(frame, list):
                continue
            for part in frame:
                if isinstance(part, list) and len(part) > 2 and part[:2] == ["wrb.fr", "oCPfdb"] and isinstance(part[2], str):
                    payload = json.loads(part[2])
                    if not isinstance(payload, list) or (payload and not isinstance(payload[0], list)):
                        raise ValueError()
                    return payload
    except (ValueError, TypeError, RecursionError):
        pass
    raise FeedError("parse-error", "The Google Play review response did not contain a valid reviews RPC payload.")


def _token(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) > MAX_TOKEN_LENGTH:
        raise FeedError("parse-error", "The source returned an invalid or oversized pagination token.")
    return value


async def _google(client, app, config, token):
    token = _token(token)
    url = "https://play.google.com/_/PlayStoreUi/data/batchexecute?" + urlencode({"hl": config.language, "gl": config.country})
    page = [100, None, token] if token else [100]
    request = [None, [2, 2, page, None, [None] * 9], [app.app_id, 7]]
    body = urlencode({"f.req": json.dumps([[["oCPfdb", json.dumps(request, separators=(",", ":")), None, "generic"]]], separators=(",", ":"))}).encode()
    payload = _google_payload(await client.fetch_text(url, method="POST", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}))
    records = payload[0] if payload else []
    if len(records) > 1000:
        raise FeedError("parse-error", "The Google Play response exceeded the bounded review-page size.")
    next_token = _token(_at(payload, -2, -1)) if len(payload) >= 3 else None
    rows, invalid = [], 0
    for item in records:
        reply_text = _at(item, 7, 1)
        reply = {"text": reply_text[:8000], "repliedAt": _date(_at(item, 7, 2, 0))} if isinstance(reply_text, str) and reply_text else None
        row = _normal(app, config, review_id=_at(item, 0), text=_at(item, 4), rating=_at(item, 2),
            date=_at(item, 5, 0), version=_at(item, 10), votes=_at(item, 6), reply=reply, source_url=url)
        if row:
            rows.append(row)
        else:
            invalid += 1
    return ReviewPage(rows, next_token if records else None, len(records), invalid)


async def _apple(client, app, config, token):
    if token is not None and (not isinstance(token, str) or not re.fullmatch(r"[1-9]|10", token)):
        raise FeedError("invalid-source", "Apple pagination must be a generated page number from 1 to 10.")
    page = int(token or "1")
    url = f"https://itunes.apple.com/{config.country}/rss/customerreviews/page={page}/id={app.app_id}/sortby=mostrecent/json"
    try:
        feed = json.loads(await client.fetch_text(url))["feed"]
        if not isinstance(feed, dict):
            raise ValueError()
        records = feed.get("entry", [])
        if isinstance(records, dict):
            records = [records]
        if not isinstance(records, list) or len(records) > 1000:
            raise ValueError()
    except (ValueError, KeyError, TypeError, RecursionError):
        raise FeedError("parse-error", "The Apple response was not a valid customer-review feed.") from None
    rows, invalid = [], 0
    for item in records:
        if isinstance(item, dict) and "im:name" in item and "im:rating" not in item:
            continue  # Some historical feeds also include a non-review app metadata entry.
        raw_rating = _label(item.get("im:rating")) if isinstance(item, dict) else None
        rating = int(raw_rating) if isinstance(raw_rating, str) and re.fullmatch(r"[1-5]", raw_rating) else None
        row = _normal(app, config, review_id=_label(item.get("id")), text=_label(item.get("content")),
            rating=rating, title=_label(item.get("title")), date=_label(item.get("updated")),
            version=_label(item.get("im:version")), source_url=url) if isinstance(item, dict) else None
        if row:
            rows.append(row)
        else:
            invalid += 1
    next_token = None
    for link in feed.get("link", []) if isinstance(feed.get("link", []), list) else []:
        attrs = link.get("attributes", {}) if isinstance(link, dict) else {}
        if not isinstance(attrs, dict):
            raise FeedError("parse-error", "Apple returned malformed feed pagination metadata.")
        if attrs.get("rel") != "next" or page >= 10 or not records:
            continue
        try:
            p = urlsplit(attrs.get("href", ""))
            expected = f"/{config.country}/rss/customerreviews/page={page + 1}/id={app.app_id}/sortby=mostrecent/json"
            # Apple's own next links can carry a harmless urlDesc query; it is never followed.
            valid_paths = {expected, expected[:-4] + "xml"}
            if p.scheme != "https" or p.hostname != "itunes.apple.com" or p.username or p.password or p.port not in (None, 443) or p.fragment or p.path.lower() not in valid_paths:
                raise ValueError()
            next_token = str(page + 1)
        except (ValueError, TypeError):
            raise FeedError("parse-error", "Apple returned a next-page link for an unexpected source.") from None
    return ReviewPage(rows, next_token, len(records), invalid)


async def fetch_page(client, app, config, token=None) -> ReviewPage:
    if app.store == "google-play":
        return await _google(client, app, config, token)
    if app.store == "app-store":
        return await _apple(client, app, config, token)
    raise FeedError("invalid-source", "Unsupported app store.")
