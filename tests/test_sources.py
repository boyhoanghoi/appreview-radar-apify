import json
import unittest
from urllib.parse import parse_qs

from reviewradar.config import App, RunConfig
from reviewradar.sources import fetch_page
from reviewradar.transport import FeedError


def rpc(records, token=None):
    payload = [records, [None, token], [None]]
    return ")]}'\n\n" + json.dumps([["wrb.fr", "oCPfdb", json.dumps(payload)]])


def google_record():
    # Synthetic record; deliberately contains discarded author fields.
    return ["review-1", ["Discard Me", [None, None, None, [None, None, "photo"]]],
        2, None, "Please add an offline mode.", [1700000000, 0], 4,
        [None, "We are investigating.", [1700000010, 0]], None, None, "1.2.3"]


def apple_record():
    return {"id": {"label": "1234"}, "author": {"name": {"label": "Discard Me"}},
        "title": {"label": "Offline please"}, "content": {"label": "Please add offline mode."},
        "updated": {"label": "2026-10-15T12:00:00-07:00"}, "im:rating": {"label": "2"},
        "im:version": {"label": "1.2.3"}, "im:voteCount": {"label": "7"}}


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def fetch_text(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class SourceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = RunConfig.from_dict({"appPreset": "chatgpt"})
        self.google = self.config.apps[0]
        self.apple = self.config.apps[1]

    async def test_google_normalizes_utc_and_removes_author_data(self):
        client = FakeClient(rpc([google_record()], "NEXT"))
        page = await fetch_page(client, self.google, self.config)
        self.assertEqual((len(page.rows), page.raw_count, page.invalid_count, page.next_token), (1, 1, 0, "NEXT"))
        row = page.rows[0]
        self.assertEqual(row["reviewDate"], "2023-11-14T22:13:20Z")
        self.assertEqual(row["developerReply"]["repliedAt"], "2023-11-14T22:13:30Z")
        self.assertEqual(row["reviewKey"], "google-play:com.openai.chatgpt:review-1")
        self.assertNotIn("Discard Me", json.dumps(row))
        self.assertNotIn("photo", json.dumps(row))
        self.assertEqual(row["appLabelSource"], "demo-preset")

    async def test_google_payload_is_json_escaped_and_fixed_destination(self):
        client = FakeClient(rpc([], None))
        token = 'token"\\/x'
        await fetch_page(client, self.google, self.config, token)
        url, options = client.calls[0]
        outer = json.loads(parse_qs(options["data"].decode())["f.req"][0])
        inner = json.loads(outer[0][0][1])
        self.assertEqual(inner[1][2], [100, None, token])
        self.assertEqual(inner[2], [self.google.app_id, 7])
        self.assertEqual(options["method"], "POST")
        self.assertTrue(url.startswith("https://play.google.com/_/PlayStoreUi/data/batchexecute?"))

    async def test_length_prefixed_rpc_and_malformed_record_count(self):
        frame = rpc([google_record(), ["bad"]]).split("\n\n", 1)[1]
        page = await fetch_page(FakeClient(")]}'\n\n" + str(len(frame)) + "\n" + frame + "\n"), self.google, self.config)
        self.assertEqual((len(page.rows), page.raw_count, page.invalid_count), (1, 2, 1))

    async def test_google_structural_failure_is_not_empty_success(self):
        for text in ("<html>Denied</html>", "[]", rpc(None), ")]}'\n\n" + json.dumps([["wrb.fr", "unrelated", "[]"]])):
            with self.subTest(text=text[:30]), self.assertRaises(FeedError) as error:
                await fetch_page(FakeClient(text), self.google, self.config)
            self.assertEqual(error.exception.status, "parse-error")

    async def test_bounds_text_and_handles_nullable_bad_dates(self):
        item = google_record()
        item[4] = "x" * 8010
        item[5] = [1e100]
        item[6] = -1
        item[7] = None
        page = await fetch_page(FakeClient(rpc([item])), self.google, self.config)
        row = page.rows[0]
        self.assertEqual(len(row["reviewText"]), 8000)
        self.assertTrue(row["reviewTextTruncated"])
        self.assertIsNone(row["reviewDate"])
        self.assertIsNone(row["helpfulVotes"])
        self.assertIsNone(row["developerReply"])

    async def test_oversized_google_token_is_rejected(self):
        with self.assertRaises(FeedError):
            await fetch_page(FakeClient(rpc([])), self.google, self.config, "a" * 16385)

    async def test_apple_normalizes_and_generates_json_next_from_xml(self):
        next_url = "https://itunes.apple.com/us/rss/customerreviews/page=2/id=6448311069/sortby=mostrecent/xml?urlDesc=ignored"
        feed = {"feed": {"entry": [apple_record()], "link": [{"attributes": {"rel": "next", "href": next_url}}]}}
        client = FakeClient(json.dumps(feed))
        page = await fetch_page(client, self.apple, self.config)
        row = page.rows[0]
        self.assertEqual(page.next_token, "2")
        self.assertEqual(row["reviewDate"], "2026-10-15T19:00:00Z")
        self.assertIsNone(row["helpfulVotes"])
        self.assertIsNone(row["developerReply"])
        self.assertIsNone(row["languageRequested"])
        self.assertNotIn("Discard Me", json.dumps(row))
        self.assertTrue(client.calls[0][0].endswith("/json"))

    async def test_apple_untrusted_next_link_is_not_followed(self):
        for href in ("https://example.com/reviews", "https://itunes.apple.com/us/rss/customerreviews/page=2/id=1234567/sortby=mostrecent/json"):
            feed = {"feed": {"entry": [apple_record()], "link": [{"attributes": {"rel": "next", "href": href}}]}}
            client = FakeClient(json.dumps(feed))
            with self.assertRaises(FeedError):
                await fetch_page(client, self.apple, self.config)
            self.assertEqual(len(client.calls), 1)

    async def test_apple_empty_accessible_window_is_valid_and_stops(self):
        page = await fetch_page(FakeClient('{"feed":{"title":{"label":"Customer reviews"}}}'), self.apple, self.config)
        self.assertEqual((page.rows, page.raw_count, page.next_token), ([], 0, None))

    async def test_apple_invalid_rating_and_app_metadata(self):
        invalid = apple_record()
        invalid["im:rating"]["label"] = "0"
        feed = {"feed": {"entry": [apple_record(), invalid, {"im:name": {"label": "App"}}]}}
        page = await fetch_page(FakeClient(json.dumps(feed)), self.apple, self.config)
        self.assertEqual((len(page.rows), page.raw_count, page.invalid_count), (1, 3, 1))

    async def test_apple_malformed_structure_and_bad_tokens(self):
        for response in ("{}", '{"feed":[]}', '{"feed":{"entry":"bad"}}'):
            with self.assertRaises(FeedError):
                await fetch_page(FakeClient(response), self.apple, self.config)
        for token in ("11", "https://example.com", "1/x", "0"):
            with self.assertRaises(FeedError):
                await fetch_page(FakeClient('{"feed":{}}'), self.apple, self.config, token)

    async def test_apple_malformed_pagination_has_explicit_error(self):
        response = json.dumps({"feed": {"entry": [apple_record()], "link": [{"attributes": []}]}})
        with self.assertRaises(FeedError) as error:
            await fetch_page(FakeClient(response), self.apple, self.config)
        self.assertEqual(error.exception.status, "parse-error")

    async def test_review_identity_does_not_depend_on_country(self):
        other = RunConfig.from_dict({"appPreset": "chatgpt", "country": "gb"})
        one = await fetch_page(FakeClient(rpc([google_record()])), self.google, self.config)
        two = await fetch_page(FakeClient(rpc([google_record()])), self.google, other)
        self.assertEqual(one.rows[0]["reviewKey"], two.rows[0]["reviewKey"])


if __name__ == "__main__":
    unittest.main()
