import asyncio
from dataclasses import replace
import ssl
import unittest
from unittest.mock import AsyncMock, patch

import aiohttp

from reviewradar.config import RunConfig
from reviewradar.transport import FeedError, MAX_BODY_BYTES, PublicResolver, ReviewClient, validate_endpoint


URL = "https://itunes.apple.com/us/rss/customerreviews/page=1/id=6448311069/sortby=mostrecent/json"


class FakeContent:
    def __init__(self, chunks):
        self.chunks = chunks

    async def iter_chunked(self, size):
        for chunk in self.chunks:
            yield chunk


class FakeResponse:
    def __init__(self, status=200, chunks=(b'{"feed":{}}',), content_length=None):
        self.status = status
        self.content = FakeContent(chunks)
        self.content_length = content_length

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class TransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = replace(RunConfig.from_dict({"appPreset": "chatgpt"}), min_delay_seconds=0)
        self.client = ReviewClient(self.config)

    async def test_fixed_endpoint_allowlist_rejects_ssrf_redirect_targets_and_methods(self):
        validate_endpoint(URL, "GET")
        validate_endpoint("https://play.google.com/_/PlayStoreUi/data/batchexecute?hl=en&gl=us", "POST")
        for value, method in ((URL, "POST"), (URL.replace("https:", "http:"), "GET"),
            (URL.replace("itunes.apple.com", "127.0.0.1"), "GET"), (URL + "?url=https://example.com", "GET"),
            (URL + "#fragment", "GET"), (URL.replace("itunes.apple.com", "user@itunes.apple.com"), "GET"),
            ("https://play.google.com/store/apps/details?id=app", "POST"),
            ("https://play.google.com/_/PlayStoreUi/data/batchexecute?hl=en&gl=us&gl=gb", "POST")):
            with self.subTest(value=value), self.assertRaises(FeedError):
                validate_endpoint(value, method)

    async def test_denied_rate_limited_and_redirect_responses_are_never_retried(self):
        for code in (403, 429, 302):
            client = ReviewClient(self.config)
            client._session = FakeSession([FakeResponse(code)])
            with self.assertRaises(FeedError) as error:
                await client.fetch_text(URL)
            self.assertEqual(error.exception.http_status, code)
            self.assertEqual(client.requests, 1)
            self.assertFalse(client._session.calls[0][2]["allow_redirects"])

    async def test_single_retry_for_server_or_network_failures(self):
        for first in (FakeResponse(503), aiohttp.ClientConnectionError("unreachable"), asyncio.TimeoutError()):
            client = ReviewClient(self.config)
            client._session = FakeSession([first, FakeResponse()])
            self.assertEqual(await client.fetch_text(URL), '{"feed":{}}')
            self.assertEqual(client.requests, 2)

    async def test_repeated_failures_stop_after_second_attempt(self):
        self.client._session = FakeSession([FakeResponse(503), FakeResponse(503)])
        with self.assertRaises(FeedError) as error:
            await self.client.fetch_text(URL)
        self.assertEqual(error.exception.http_status, 503)
        self.assertEqual(self.client.requests, 2)

    async def test_cap_checks_content_length_and_streamed_decompressed_bytes(self):
        cases = [FakeResponse(content_length=MAX_BODY_BYTES + 1),
            FakeResponse(chunks=(b"x" * MAX_BODY_BYTES, b"x"))]
        for response in cases:
            client = ReviewClient(self.config)
            client._session = FakeSession([response])
            with self.assertRaises(FeedError) as error:
                await client.fetch_text(URL)
            self.assertEqual(error.exception.status, "response-too-large")
            self.assertEqual(client.requests, 1)

    async def test_request_budget_includes_retries(self):
        self.client.requests = 59
        self.client._session = FakeSession([FakeResponse(503)])
        with self.assertRaises(FeedError) as error:
            await self.client.fetch_text(URL)
        self.assertEqual(error.exception.status, "request_limit")
        self.assertEqual(self.client.requests, 60)
        self.assertEqual(len(self.client._session.calls), 1)

    async def test_bad_utf8_is_an_explicit_unretried_failure(self):
        self.client._session = FakeSession([FakeResponse(chunks=(b"\xff",))])
        with self.assertRaises(FeedError) as error:
            await self.client.fetch_text(URL)
        self.assertEqual(error.exception.status, "invalid-response")

    async def test_context_uses_verified_tls_and_disables_environment_proxies(self):
        async with ReviewClient(self.config) as client:
            context = client._session.connector._ssl
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertFalse(client._session.trust_env)
            self.assertEqual(client._session.timeout.total, self.config.timeout_seconds)

    async def test_non_public_dns_results_are_rejected(self):
        with patch.object(aiohttp.resolver.DefaultResolver, "resolve", new=AsyncMock(return_value=[{"host": "127.0.0.1"}])):
            resolver = PublicResolver()
            try:
                with self.assertRaises(FeedError):
                    await resolver.resolve("itunes.apple.com", 443)
            finally:
                await resolver.close()


if __name__ == "__main__":
    unittest.main()
