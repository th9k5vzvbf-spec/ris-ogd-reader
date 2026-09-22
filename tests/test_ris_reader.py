"""Deterministic unit tests with synthetic API fixtures; no actual RIS data."""
import io
import json
import unittest
from datetime import date
from email.message import Message

from ris_reader import (
    RISClient,
    RISResponseError,
    collect_pages,
    parse_page,
    record_from_reference,
    run,
)


def sample_ref(document_id="TEST_DOCUMENT_01"):
    """Artificial schema-only test fixture, not an actual court decision."""
    return {
        "Data": {
            "Metadaten": {
                "Technisch": {"ID": document_id, "Organ": "TEST COURT"},
                "Allgemein": {
                    "DokumentUrl": "https://www.ris.bka.gv.at/Dokument.wxe?Abfrage=Justiz"
                },
                "Judikatur": {
                    "Geschaeftszahl": {"item": ["TEST-GZ-01"]},
                    "Entscheidungsdatum": "2026-09-08",
                },
            },
            "Dokumentliste": {
                "ContentReference": {
                    "ContentType": "MainDocument",
                    "Urls": {
                        "ContentUrl": [
                            {"DataType": "Html", "Url": "https://data.bka.gv.at/test"},
                        ]
                    },
                }
            },
        }
    }


def response(total, refs):
    return {
        "OgdSearchResult": {
            "OgdDocumentResults": {
                "Hits": {"#text": str(total), "@pageNumber": "1", "@pageSize": "50"},
                "OgdDocumentReference": refs,
            }
        }
    }


class FakeClient:
    def __init__(self, *, fail_history=False):
        self.calls = []
        self.fail_history = fail_history

    def get(self, endpoint, params):
        self.calls.append((endpoint, dict(params)))
        if endpoint == "History" and self.fail_history:
            raise RISResponseError("Synthetic failure")
        return response(1, sample_ref())


class FakeHTTPResponse:
    def __init__(self, data):
        self.data = data
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.data


class FakeOpener:
    def __init__(self, data):
        self.data = data
        self.urls = []

    def open(self, request, timeout):
        self.urls.append(request.full_url)
        return FakeHTTPResponse(self.data)


class ReaderTests(unittest.TestCase):
    def test_parse_single_reference(self):
        count, refs = parse_page(response(1, sample_ref()))
        self.assertEqual(count, 1)
        self.assertEqual(len(refs), 1)

    def test_parse_zero_results(self):
        count, refs = parse_page(response(0, []))
        self.assertEqual((count, refs), (0, []))

    def test_reject_wrong_envelope(self):
        with self.assertRaises(RISResponseError):
            parse_page({"unrelated": "data"})

    def test_precise_metadata_and_host_validation(self):
        record = record_from_reference(sample_ref(), "Justiz")
        self.assertEqual(record["id"], "TEST_DOCUMENT_01")
        self.assertEqual(record["case_number"], "TEST-GZ-01")
        self.assertEqual(record["court"], "TEST COURT")
        self.assertEqual(record["decision_date"], "2026-09-08")
        self.assertEqual(record["content_html_url"], "https://data.bka.gv.at/test")
        fixture = sample_ref()
        fixture["Data"]["Metadaten"]["Allgemein"]["DokumentUrl"] = (
            "https://malicious.example.com/redirect"
        )
        self.assertIsNone(record_from_reference(fixture, "Justiz")["source_url"])

    def test_reject_document_without_id(self):
        fixture = sample_ref()
        del fixture["Data"]["Metadaten"]["Technisch"]["ID"]
        with self.assertRaises(RISResponseError):
            record_from_reference(fixture, "Justiz")

    def test_history_and_keyword_deduplication(self):
        client = FakeClient()
        report = run(
            client, date(2026, 9, 22),
            applications=("Justiz",), terms=("Verkehrswert",), max_pages=1,
        )
        self.assertEqual(report["status"], "technical_queries_complete")
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(set(report["candidates"][0]["origin"]), {"keyword", "history"})
        self.assertFalse(report["legal_completeness_claim"])
        self.assertEqual(client.calls[0][1]["Dokumenttyp.SucheInRechtssaetzen"], "true")
        self.assertEqual(client.calls[0][1]["Dokumenttyp.SucheInEntscheidungstexten"], "true")
        self.assertEqual(client.calls[1][1]["Anwendung"], "Justiz")

    def test_failed_history_must_mark_incomplete(self):
        report = run(
            FakeClient(fail_history=True), date(2026, 9, 22),
            applications=("Justiz",), terms=("Nutzwert",), max_pages=1,
        )
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(len(report["errors"]), 1)
        self.assertFalse(report["legal_completeness_claim"])

    def test_pagination_limit_must_mark_incomplete(self):
        class PagedClient:
            def get(self, endpoint, params):
                return response(150, [sample_ref()])
        refs, count, complete = collect_pages(
            PagedClient(), "Judikatur",
            {"Applikation": "Justiz", "Suchworte": "Nutzwert"}, max_pages=1,
        )
        self.assertEqual(count, 150)
        self.assertEqual(len(refs), 1)
        self.assertFalse(complete)

    def test_fixed_endpoint_and_api_host(self):
        client = RISClient("ReaderTest/0.1")
        with self.assertRaises(ValueError):
            client.get("https://other.example.invalid/", {})
        fake = FakeOpener(json.dumps(response(0, [])).encode())
        client.opener = fake
        result = client.get("Judikatur", {"Applikation": "Justiz"})
        self.assertEqual(parse_page(result), (0, []))
        self.assertTrue(fake.urls[0].startswith(
            "https://data.bka.gv.at/ris/api/v2.6/Judikatur?"
        ))

    def test_refuse_too_many_pages(self):
        with self.assertRaises(ValueError):
            run(FakeClient(), date(2026, 9, 22), max_pages=40,
                applications=("Justiz",), terms=("Verkehrswert",))


if __name__ == "__main__":
    unittest.main()
