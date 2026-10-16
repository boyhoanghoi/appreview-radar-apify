"""Auditable keyword mentions, not sentiment or inferred customer intent."""

from collections import Counter
import re

from .config import RunConfig, iso_datetime


TOPIC_TERMS = {
    "stability": ("crash", "crashes", "crashing", "bug", "bugs", "freeze", "freezes", "frozen", "lỗi", "văng", "đơ"),
    "performance": ("slow", "lag", "laggy", "loading", "chậm", "giật", "tải lâu"),
    "billing": ("subscription", "refund", "billing", "charged", "payment", "paywall", "đăng ký", "thanh toán", "hoàn tiền", "trừ tiền"),
    "login": ("login", "log in", "sign in", "password", "account", "đăng nhập", "mật khẩu", "tài khoản"),
    "ads": ("ads", "advertisement", "advertisements", "quảng cáo"),
    "privacy": ("privacy", "tracking", "data collection", "personal data", "quyền riêng tư", "theo dõi", "dữ liệu cá nhân"),
    "feature-request": ("please add", "please support", "would be nice", "i wish", "feature request", "mong có", "vui lòng thêm", "hãy thêm", "ước gì", "cần thêm"),
}
PATTERNS = {topic: [(term, re.compile(r"(?<!\w)" + re.escape(term).replace(r"\ ", r"\s+") + r"(?!\w)", re.IGNORECASE)) for term in terms]
            for topic, terms in TOPIC_TERMS.items()}


def tag_review(row: dict) -> dict:
    text = row["reviewTitle"] + "\n" + row["reviewText"]
    matches = []
    for topic, patterns in PATTERNS.items():
        found = [(term, pattern.search(text)) for term, pattern in patterns]
        found = [(term, match) for term, match in found if match]
        if found:
            earliest = min(match.start() for _, match in found)
            start = max(0, earliest - 70)
            excerpt = text[start:start + 240]
            matches.append({"topic": topic, "matchedTerms": [term for term, _ in found],
                "evidenceExcerpt": excerpt, "excerptStart": start})
    return {**row, "topicTags": [match["topic"] for match in matches], "topicMatches": matches,
            "hasFeatureRequestPhrase": any(match["topic"] == "feature-request" for match in matches),
            "analysisMethod": "literal-keyword-mentions-en-vi-v1"}


def filter_reason(row: dict, config: RunConfig) -> str | None:
    if not config.min_rating <= row["rating"] <= config.max_rating:
        return "rating_outside_range"
    if config.app_version_keywords and not any(term in (row.get("appVersion") or "").casefold() for term in config.app_version_keywords):
        return "app_version_not_matched"
    if config.reply_filter != "all":
        if row.get("developerReplyStatus") == "unavailable":
            return "reply_status_unavailable"
        if config.reply_filter == "with-reply" and row.get("developerReplyStatus") != "present":
            return "no_visible_reply"
        if config.reply_filter == "without-visible-reply" and row.get("developerReplyStatus") != "not-shown":
            return "has_visible_reply"
    text = (row["reviewTitle"] + "\n" + row["reviewText"]).casefold()
    if config.include_keywords and not any(word in text for word in config.include_keywords):
        return "keyword_not_included"
    if any(word in text for word in config.exclude_keywords):
        return "keyword_excluded"
    if config.topic_filters and not set(config.topic_filters).intersection(row["topicTags"]):
        return "topic_not_matched"
    if config.feature_requests_only and not row["hasFeatureRequestPhrase"]:
        return "no_feature_request_phrase"
    if config.reviewed_after:
        date = iso_datetime(row.get("reviewDate"))
        if date is None:
            return "review_date_unknown"
        if date < config.reviewed_after:
            return "reviewed_before_cutoff"
    return None


def saved_analysis(rows: list[dict]) -> dict:
    ratings = Counter(row["rating"] for row in rows)
    return {"scope": "saved-results-only", "savedReviews": len(rows),
        "ratingHistogram": {str(score): ratings[score] for score in range(1, 6)},
        "sampleAverageRating": round(sum(row["rating"] for row in rows) / len(rows), 3) if rows else None,
        "reviewsByApp": dict(Counter(f"{row['store']}:{row['appId']}" for row in rows)),
        "reviewsByStore": dict(Counter(row["store"] for row in rows)),
        "topicMentionCounts": dict(Counter(topic for row in rows for topic in row["topicTags"])),
        "featureRequestPhraseReviews": sum(row["hasFeatureRequestPhrase"] for row in rows),
        "note": "Filtered saved sample only; not an app's overall rating, complaint prevalence, sentiment score or proof of customer intent."}


def topic_report(rows: list[dict]) -> dict:
    result = []
    for topic in TOPIC_TERMS:
        matching = [(row, next((match for match in row["topicMatches"] if match["topic"] == topic), None)) for row in rows]
        matching = [(row, match) for row, match in matching if match]
        result.append({"topic": topic, "savedReviewCount": len(matching),
            "examples": [{"reviewKey": row["reviewKey"], "appLabel": row["appLabel"], "rating": row["rating"],
                "matchedTerms": match["matchedTerms"], "evidenceExcerpt": match["evidenceExcerpt"], "appUrl": row["appUrl"]}
                for row, match in matching[:5]]})
    return {"scope": "saved-results-only", "method": "literal-keyword-mentions-en-vi-v1", "topics": result,
            "note": "A keyword mention can be praise, a negation or an unrelated phrase. Read the evidence before labeling an issue or request. Topic counts overlap."}
