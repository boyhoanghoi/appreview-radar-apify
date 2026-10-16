"""Validate identifiers and filters before generating fixed public feed URLs."""

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit


@dataclass(frozen=True)
class App:
    store: str
    app_id: str

    @property
    def key(self) -> str:
        return f"{self.store}:{self.app_id}"


PRESETS = {
    "none": (),
    "chatgpt": (App("google-play", "com.openai.chatgpt"), App("app-store", "6448311069")),
}
LABELS = {"google-play:com.openai.chatgpt": "ChatGPT (Android)", "app-store:6448311069": "ChatGPT (iOS)"}


def parse_app(value: Any, store: str) -> App:
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise ValueError("Apps must be non-empty package IDs, numeric Apple IDs, or supported HTTPS store URLs.")
    value = value.strip()
    if "://" in value:
        try:
            parsed = urlsplit(value)
            if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
                raise ValueError()
            if store == "google-play" and parsed.hostname == "play.google.com" and parsed.path.rstrip("/") == "/store/apps/details":
                ids = parse_qs(parsed.query).get("id", [])
                if len(ids) != 1:
                    raise ValueError()
                value = ids[0]
            elif store == "app-store" and parsed.hostname in {"apps.apple.com", "itunes.apple.com"}:
                match = re.search(r"/id(\d+)(?:/|$)", parsed.path)
                if not match:
                    raise ValueError()
                value = match[1]
            else:
                raise ValueError()
        except ValueError:
            raise ValueError("Use a public Google Play app-details URL or Apple App Store app URL for the matching input.") from None
    pattern = r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+" if store == "google-play" else r"[0-9]{5,15}"
    if not re.fullmatch(pattern, value) or len(value) > 250:
        raise ValueError("Use an Android package such as com.openai.chatgpt or a numeric Apple app ID such as 6448311069.")
    return App(store, value)


def iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) > 100:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def integer(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}.")
    return value


def words(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 30 or any(not isinstance(v, str) or not v.strip() or len(v) > 100 for v in value):
        raise ValueError(f"{name} must be up to 30 non-empty strings of at most 100 characters.")
    return tuple(dict.fromkeys(v.strip().casefold() for v in value))


@dataclass(frozen=True)
class RunConfig:
    apps: tuple[App, ...]
    country: str = "us"
    language: str = "en"
    max_reviews: int = 100
    max_reviews_per_app: int = 100
    max_pages_per_app: int = 3
    min_rating: int = 1
    max_rating: int = 5
    include_keywords: tuple[str, ...] = ()
    exclude_keywords: tuple[str, ...] = ()
    topic_filters: tuple[str, ...] = ()
    feature_requests_only: bool = False
    reviewed_after: datetime | None = None
    known_review_ids: tuple[str, ...] = ()
    timeout_seconds: int = 20
    min_delay_seconds: float = 0.5

    @classmethod
    def from_dict(cls, data: Any) -> "RunConfig":
        if not isinstance(data, dict):
            raise ValueError("Input must be a JSON object.")
        allowed = {"googlePlayApps", "appStoreApps", "appPreset", "country", "language", "maxReviews", "maxReviewsPerApp", "maxPagesPerApp", "minRating", "maxRating", "includeKeywords", "excludeKeywords", "topicFilters", "featureRequestsOnly", "reviewedAfter", "knownReviewIds", "timeoutSeconds", "minDelaySeconds"}
        unknown = [str(k) for k in data if k not in allowed and not str(k).startswith("__")]
        if unknown:
            raise ValueError("Unknown input field(s): " + ", ".join(sorted(unknown)))
        preset = data.get("appPreset", "none")
        if not isinstance(preset, str) or preset not in PRESETS:
            raise ValueError("appPreset must be none or chatgpt.")
        apps = []
        for name, store in (("googlePlayApps", "google-play"), ("appStoreApps", "app-store")):
            values = data.get(name, [])
            if not isinstance(values, list) or len(values) > 10:
                raise ValueError(f"{name} must be a list of at most 10 app identifiers or store URLs.")
            apps.extend(parse_app(value, store) for value in values)
        apps = tuple(dict.fromkeys([*apps, *PRESETS[preset]]))
        if not 1 <= len(apps) <= 10:
            raise ValueError("Choose an appPreset or supply app IDs; the combined list must contain 1 to 10 unique apps.")
        country, language = data.get("country", "us"), data.get("language", "en")
        if not isinstance(country, str) or not re.fullmatch(r"[a-zA-Z]{2}", country):
            raise ValueError("country must be a two-letter storefront code such as us or vn.")
        if not isinstance(language, str) or not re.fullmatch(r"[a-zA-Z]{2,3}(?:-[a-zA-Z]{2})?", language):
            raise ValueError("language must be a language code such as en or vi; it is a Google Play request hint only.")
        lower, upper = integer(data.get("minRating", 1), "minRating", 1, 5), integer(data.get("maxRating", 5), "maxRating", 1, 5)
        if lower > upper:
            raise ValueError("minRating cannot exceed maxRating.")
        feature = data.get("featureRequestsOnly", False)
        if not isinstance(feature, bool):
            raise ValueError("featureRequestsOnly must be true or false.")
        topics = words(data.get("topicFilters", []), "topicFilters")
        if any(t not in {"stability", "performance", "billing", "login", "ads", "privacy", "feature-request"} for t in topics):
            raise ValueError("Unknown topicFilters value; use stability, performance, billing, login, ads, privacy or feature-request.")
        after_raw = data.get("reviewedAfter")
        after = iso_datetime(after_raw) if after_raw not in (None, "") else None
        if after_raw not in (None, "") and after is None:
            raise ValueError("reviewedAfter must be an ISO date or timestamp.")
        prior = data.get("knownReviewIds", [])
        if not isinstance(prior, list) or len(prior) > 10000 or any(not isinstance(v, str) or not v.strip() or len(v) > 600 for v in prior):
            raise ValueError("knownReviewIds must be at most 10,000 non-empty reviewKey strings, at most 600 characters each.")
        delay = data.get("minDelaySeconds", 0.5)
        if isinstance(delay, bool) or not isinstance(delay, (int, float)) or not math.isfinite(delay) or not 0.25 <= delay <= 10:
            raise ValueError("minDelaySeconds must be from 0.25 to 10.")
        return cls(apps=apps, country=country.lower(), language=language.lower(),
            max_reviews=integer(data.get("maxReviews", 100), "maxReviews", 1, 2000),
            max_reviews_per_app=integer(data.get("maxReviewsPerApp", 100), "maxReviewsPerApp", 1, 1000),
            max_pages_per_app=integer(data.get("maxPagesPerApp", 3), "maxPagesPerApp", 1, 10),
            min_rating=lower, max_rating=upper, include_keywords=words(data.get("includeKeywords", []), "includeKeywords"),
            exclude_keywords=words(data.get("excludeKeywords", []), "excludeKeywords"), topic_filters=topics,
            feature_requests_only=feature, reviewed_after=after, known_review_ids=tuple(dict.fromkeys(v.strip() for v in prior)),
            timeout_seconds=integer(data.get("timeoutSeconds", 20), "timeoutSeconds", 5, 45), min_delay_seconds=float(delay))
