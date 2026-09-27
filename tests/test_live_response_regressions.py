"""Regression tests replay a captured official RIS response, not invented cases."""
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from ris_reader import RISClient, RISResponseError, parse_page, record_from_reference


RAW_RESPONSE = (Path(__file__).parent / "fixtures" /
                "vwgh_keyword_2026-09-27.json").read_bytes()


def captured_response():
    response = Mock()
    response.status = 200
    response.headers = {"Content-Type": "application/json; charset=utf-8"}
    response.read.return_value = RAW_RESPONSE
    manager = Mock()
    manager.__enter__ = Mock(return_value=response)
    manager.__exit__ = Mock(return_value=False)
    return manager


class LiveResponseRegressionTests(unittest.TestCase):
    def test_official_ogd_links_survive_parsing(self):
        hits, refs = parse_page(json.loads(RAW_RESPONSE))
        self.assertEqual(hits, 1)
        record = record_from_reference(refs[0], "Vwgh")
        self.assertEqual(record["id"], "JWT_2026180280_20260812L00")
        self.assertEqual(record["case_number"], "Ra 2026/18/0280")
        self.assertEqual(
            record["source_url"],
            refs[0]["Data"]["Metadaten"]["Allgemein"]["DokumentUrl"],
        )
        self.assertEqual(
            record["content_html_url"],
            "https://ogd.ris.bka.gv.at/Dokumente/Vwgh/"
            "JWT_2026180280_20260812L00/JWT_2026180280_20260812L00.html",
        )

    @patch("ris_reader.time.sleep")
    def test_timeout_retries_then_returns_real_response(self, sleep):
        client = RISClient("RIS-OGD-Reader regression test")
        client.opener = Mock()
        client.opener.open.side_effect = [
            TimeoutError("timed out"), TimeoutError("timed out"), captured_response(),
        ]
        result = client.get("History", {"Anwendung": "Vwgh"})
        self.assertEqual(result, json.loads(RAW_RESPONSE))
        self.assertEqual(client.opener.open.call_count, 3)
        sleep.assert_any_call(5)
        sleep.assert_any_call(15)
        self.assertTrue(all(
            call.kwargs["timeout"] == 60
            for call in client.opener.open.call_args_list
        ))

    @patch("ris_reader.time.sleep")
    def test_persistent_timeout_still_fails(self, sleep):
        client = RISClient("RIS-OGD-Reader regression test")
        client.opener = Mock()
        client.opener.open.side_effect = TimeoutError("timed out")
        with self.assertRaisesRegex(RISResponseError, "nach 3 Versuch"):
            client.get("History", {"Anwendung": "Vwgh"})
        self.assertEqual(client.opener.open.call_count, 3)

    def test_non_transient_http_error_is_not_retried(self):
        client = RISClient("RIS-OGD-Reader regression test")
        client.opener = Mock()
        client.opener.open.side_effect = HTTPError(
            "https://data.bka.gv.at/ris/api/v2.6/History", 403, "Forbidden", {}, None,
        )
        with self.assertRaisesRegex(RISResponseError, "HTTP 403 nach 1 Versuch"):
            client.get("History", {"Anwendung": "Vwgh"})
        self.assertEqual(client.opener.open.call_count, 1)
