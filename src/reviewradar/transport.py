"""Small verified-TLS client for two fixed public review endpoints.

No proxy, identity rotation, browser emulation or challenge handling is used.
The current generic robots exclusions are documented in docs/SOURCES.md.
"""

import asyncio
import ipaddress
import re
import ssl
import time
from urllib.parse import parse_qs, urlsplit

import aiohttp


MAX_REQUESTS = 60
MAX_BODY_BYTES = 2 * 1024 * 1024
USER_AGENT = "AppReviewRadar/0.1 (+public-review-export)"


class FeedError(Exception):
    def __init__(self, status: str, message: str, http_status: int | None = None):
        super().__init__(message)
        self.status = status
        self.http_status = http_status


def validate_endpoint(url: str, method: str) -> None:
    """Prevent app IDs, pagination or input URLs from changing the destination."""
    try:
        p = urlsplit(url)
        if p.scheme != "https" or p.username or p.password or p.port not in (None, 443) or p.fragment:
            raise ValueError()
        if p.hostname == "play.google.com" and p.path == "/_/PlayStoreUi/data/batchexecute" and method == "POST":
            q = parse_qs(p.query, keep_blank_values=True, strict_parsing=True)
            if set(q) != {"hl", "gl"} or any(len(v) != 1 for v in q.values()):
                raise ValueError()
            if not re.fullmatch(r"[a-z]{2,3}(?:-[a-z]{2})?", q["hl"][0]) or not re.fullmatch(r"[a-z]{2}", q["gl"][0]):
                raise ValueError()
            return
        if p.hostname == "itunes.apple.com" and method == "GET" and not p.query:
            if re.fullmatch(r"/[a-z]{2}/rss/customerreviews/page=(?:[1-9]|10)/id=[0-9]{5,15}/sortby=mostrecent/json", p.path):
                return
    except (ValueError, TypeError, AttributeError):
        pass
    raise FeedError("invalid-source", "Only the fixed Google Play reviews RPC and Apple customer-review feed are supported.")


class PublicResolver(aiohttp.resolver.DefaultResolver):
    async def resolve(self, host, port=0, family=0):
        records = await super().resolve(host, port, family)
        if not records or any(not ipaddress.ip_address(r["host"]).is_global for r in records):
            raise FeedError("invalid-source", "Review host resolved to a non-public network address.")
        return records


class ReviewClient:
    def __init__(self, config):
        self.config = config
        self.requests = 0
        self._session = None
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(ssl=ssl.create_default_context(), resolver=PublicResolver(), use_dns_cache=False, limit=4)
        self._session = aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/plain;q=0.9"}, trust_env=False)
        return self

    async def __aexit__(self, *exc):
        if self._session:
            await self._session.close()

    async def _pace(self):
        async with self._lock:
            if self.requests >= MAX_REQUESTS:
                raise FeedError("request_limit", "The 60-attempt HTTP budget was reached.")
            delay = self.config.min_delay_seconds - (time.monotonic() - self._last_request)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request = time.monotonic()
            self.requests += 1

    async def fetch_text(self, url: str, *, method="GET", data=None, headers=None) -> str:
        method = method.upper()
        validate_endpoint(url, method)
        if self._session is None:
            raise RuntimeError("Use ReviewClient as an async context manager.")
        for attempt in range(2):
            await self._pace()
            try:
                async with self._session.request(method, url, data=data, headers=headers, allow_redirects=False) as response:
                    status = response.status
                    if status in (403, 429):
                        raise FeedError("access-denied" if status == 403 else "rate-limited", "The source refused this request; no retry or bypass was attempted.", status)
                    if 300 <= status < 400:
                        raise FeedError("redirect-refused", "The review endpoint redirected; redirects are not followed.", status)
                    if 500 <= status < 600 and attempt == 0:
                        continue
                    if status != 200:
                        raise FeedError("http-error", f"The review endpoint returned HTTP {status}.", status)
                    if response.content_length is not None and response.content_length > MAX_BODY_BYTES:
                        raise FeedError("response-too-large", "The source response exceeded 2 MiB.")
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        body.extend(chunk)
                        if len(body) > MAX_BODY_BYTES:
                            raise FeedError("response-too-large", "The source response exceeded 2 MiB.")
                    try:
                        return bytes(body).decode("utf-8-sig")
                    except UnicodeDecodeError:
                        raise FeedError("invalid-response", "The review response was not valid UTF-8.") from None
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                if attempt == 1:
                    raise FeedError("transport-error", f"Could not retrieve the review feed ({type(error).__name__}).") from None
        raise FeedError("transport-error", "Could not retrieve the review feed.")
