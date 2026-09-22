#!/usr/bin/env python3
"""Read-only, rate-limited RIS OGD v2.6 search for the Austrian valuation monitor.

This script identifies CANDIDATE documents, not legally relevant decisions.
It makes no completeness claim beyond successfully paginated keyword queries.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_ROOT = "https://data.bka.gv.at/ris/api/v2.6"
APPLICATIONS = ("Justiz", "Vwgh", "Vfgh")
TERMS = (
    "Verkehrswert", "Liegenschaftsbewertung", "Nutzwert",
    "Wohnungseigentum", "Enteignung", "Liegenschaftszinssatz",
    "Sachverständigengutachten",
)
PAGE_SIZE = 50
PAGE_ENUM = "Fifty"
MIN_INTERVAL_SECONDS = 2.2
SOURCE = "https://www.ris.bka.gv.at/UI/Ogd.aspx"
DOCS = ("https://www.data.gv.at/katalog/dataset/"
        "0fb9ae1a-92cb-4ab8-a589-470c16d4fe21")


class RISResponseError(RuntimeError):
    """API, transport or response-schema error."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise RISResponseError("Unerwartete Weiterleitung: Anfragestopp")


class RISClient:
    """The only outbound network access is the fixed official RIS API host."""

    def __init__(self, user_agent: str, interval: float = MIN_INTERVAL_SECONDS):
        self.user_agent = user_agent
        self.interval = max(MIN_INTERVAL_SECONDS, interval)
        self.last_request = 0.0
        self.opener = build_opener(NoRedirects())

    def get(self, endpoint: str, params: dict[str, str]) -> dict:
        if endpoint not in ("Judikatur", "History"):
            raise ValueError("Nicht freigegebener Endpunkt")
        url = API_ROOT + "/" + endpoint + "?" + urlencode(params)
        if urlsplit(url).hostname != "data.bka.gv.at":
            raise ValueError("Nicht freigegebener Server")
        delay = self.interval - (time.monotonic() - self.last_request)
        if delay > 0:
            time.sleep(delay)
        self.last_request = time.monotonic()
        request = Request(url, headers={
            "Accept": "application/json", "User-Agent": self.user_agent,
        }, method="GET")
        try:
            with self.opener.open(request, timeout=35) as response:
                if response.status != 200:
                    raise RISResponseError("Unerwarteter HTTP-Status")
                if not response.headers.get("Content-Type", "").lower().startswith(
                    "application/json"
                ):
                    raise RISResponseError("Keine JSON-Antwort")
                raw = response.read(10_000_001)
                if len(raw) > 10_000_000:
                    raise RISResponseError("Antwort zu groß")
            result = json.loads(raw.decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise RISResponseError(f"RIS-Anfrage fehlgeschlagen: {type(exc).__name__}") from exc
        if not isinstance(result, dict):
            raise RISResponseError("Unerwartetes JSON-Format")
        return result


def parse_page(response: dict) -> tuple[int, list[dict]]:
    """Fail closed when official RIS response envelope or pagination is missing."""
    root = response.get("OgdSearchResult")
    if not isinstance(root, dict) or str(root.get("@status", "ok")).lower() == "error":
        raise RISResponseError("RIS-Antwort ohne gültiges OgdSearchResult")
    results = root.get("OgdDocumentResults")
    if not isinstance(results, dict):
        raise RISResponseError("RIS-Antwort ohne OgdDocumentResults")
    hits = results.get("Hits")
    try:
        total = int(hits.get("#text", 0) if isinstance(hits, dict) else hits)
    except (TypeError, ValueError) as exc:
        raise RISResponseError("RIS-Gesamttrefferzahl fehlt") from exc
    if total < 0:
        raise RISResponseError("Ungültige RIS-Trefferzahl")
    documents = results.get("OgdDocumentReference", [])
    if isinstance(documents, dict):
        documents = [documents]
    if documents is None:
        documents = []
    if not isinstance(documents, list) or any(not isinstance(d, dict) for d in documents):
        raise RISResponseError("Unerwartete Dokumentliste")
    if total and not documents:
        raise RISResponseError("Treffer ohne Dokumentliste")
    return total, documents


def find_first(node: object, field: str) -> object | None:
    """Find a named metadata field in the nested RIS response."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key.lower() == field.lower() and value is not None:
                return value
        for value in node.values():
            found = find_first(value, field)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = find_first(item, field)
            if found is not None:
                return found
    return None


def scalar(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in ("#text", "Value"):
            if key in value:
                return scalar(value[key])
    if isinstance(value, list):
        return scalar(value[0]) if value else None
    return None


def record_from_reference(ref: dict, application: str) -> dict:
    data = ref.get("Data", ref)
    metadata = data.get("Metadaten", data) if isinstance(data, dict) else data
    document_id = scalar(find_first(metadata, "ID"))
    raw_url = scalar(find_first(metadata, "DokumentUrl"))
    source_url = None
    if raw_url:
        parts = urlsplit(raw_url)
        if parts.scheme == "https" and parts.hostname in (
            "ris.bka.gv.at", "www.ris.bka.gv.at"
        ):
            source_url = raw_url
    if not document_id:
        raise RISResponseError("RIS-Dokument ohne ID")
    return {
        "id": document_id,
        "application": application,
        "case_number": scalar(find_first(metadata, "Geschaeftszahl")),
        "court": scalar(find_first(metadata, "Gericht")),
        "decision_date": scalar(find_first(metadata, "Entscheidungsdatum")),
        "published_in_ris": scalar(find_first(metadata, "Veroeffentlicht")),
        "modified_in_ris": scalar(find_first(metadata, "Geaendert")),
        "summary": scalar(find_first(metadata, "Kurzinformation")),
        "source_url": source_url,
        "search_terms": [],
    }


def collect_pages(
    client: RISClient, endpoint: str, params: dict[str, str], max_pages: int
) -> tuple[list[dict], int, bool]:
    found: list[dict] = []
    total = 0
    complete = True
    for page in range(1, max_pages + 1):
        query = {**params, "DokumenteProSeite": PAGE_ENUM, "Seitennummer": str(page)}
        result = client.get(endpoint, query)
        count, docs = parse_page(result)
        if page == 1:
            total = count
        elif count != total:
            complete = False  # RIS changed during pagination
        found.extend(docs)
        if len(found) >= total:
            break
        if not docs:
            complete = False
            break
    if len(found) < total:
        complete = False
    return found, total, complete


def run(
    client: RISClient, today: date, *, max_pages: int = 2,
    applications: tuple[str, ...] = APPLICATIONS,
    terms: tuple[str, ...] = TERMS,
) -> dict:
    if max_pages < 1 or max_pages > 5:
        raise ValueError("max_pages muss zwischen 1 und 5 liegen")
    if not applications or any(app not in APPLICATIONS for app in applications):
        raise ValueError("Nicht freigegebene RIS-Applikation")
    if not terms or any(term not in TERMS for term in terms):
        raise ValueError("Nicht freigegebener Suchbegriff")
    started = datetime.now(timezone.utc).isoformat()
    # The overlapping 14-day window tolerates a delayed weekly GitHub run.
    date_from = (today - timedelta(days=14)).isoformat()
    date_until = today.isoformat()
    index: dict[str, dict] = {}
    searches = []
    errors = []
    for app in applications:
        for term in terms:
            params = {
                "Applikation": app, "Suchworte": term,
                "Dokumenttyp.SucheInRechtssaetzen": "true",
                "Dokumenttyp.SucheInEntscheidungstexten": "true",
                "ImRisSeit": "ZweiWochen",
            }
            try:
                refs, hits, fully_paged = collect_pages(
                    client, "Judikatur", params, max_pages
                )
                for ref in refs:
                    doc = record_from_reference(ref, app)
                    key = app + ":" + doc["id"]
                    if key not in index:
                        index[key] = doc
                    if term not in index[key]["search_terms"]:
                        index[key]["search_terms"].append(term)
                searches.append({
                    "application": app, "term": term, "hits": hits,
                    "returned": len(refs), "pagination_complete": fully_paged,
                })
            except RISResponseError as exc:
                errors.append({"application": app, "term": term, "reason": str(exc)})
                searches.append({
                    "application": app, "term": term,
                    "pagination_complete": False,
                })
    # History is checked independently. It is NOT assumed to carry document text:
    # even an exhaustive history page list is not a full relevance check.
    history = []
    for app in applications:
        params = {
            "Anwendung": app,
            "AenderungenVon": date_from,
            "AenderungenBis": date_until,
        }
        try:
            refs, hits, fully_paged = collect_pages(
                client, "History", params, max_pages
            )
            history.append({
                "application": app, "total_changes": hits,
                "returned": len(refs),
                "pagination_complete": fully_paged,
            })
        except RISResponseError as exc:
            errors.append({"application": app, "history": True, "reason": str(exc)})
            history.append({
                "application": app, "pagination_complete": False
            })
    queries_complete = (
        not errors
        and all(s["pagination_complete"] for s in searches)
        and all(h["pagination_complete"] for h in history)
    )
    return {
        "generated_at_utc": started,
        "search_window": {
            "ris_since": "ZweiWochen",
            "history_from": date_from,
            "history_to": date_until,
        },
        "status": "technical_queries_complete" if queries_complete else "incomplete",
        "legal_completeness_claim": False,
        "notice": (
            "Nur Stichwort-Kandidaten und RIS-Änderungszahlen; keine fachliche "
            "Beurteilung oder vollständige Durchsicht sämtlicher RIS-Dokumente. "
            "Fehlende Treffer beweisen nicht, dass keine relevante Judikatur vorliegt."
        ),
        "sources": {"ris_ogd": SOURCE, "documentation": DOCS},
        "queries": searches,
        "history": history,
        "errors": errors,
        "candidates": sorted(
            index.values(),
            key=lambda x: (x["decision_date"] or "", x["application"], x["id"]),
            reverse=True,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/latest.json")
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args(argv)
    agent = os.environ.get("RIS_USER_AGENT", "RIS-OGD-Reader/0.1 (GitHub Actions)")
    client = RISClient(user_agent=agent)
    report = run(client, args.date, max_pages=args.max_pages)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"RIS-Abfrage: {report['status']}; {len(report['candidates'])} "
        f"Kandidaten; {len(report['errors'])} Fehler."
    )
    return 0 if report["status"] == "technical_queries_complete" else 2


if __name__ == "__main__":
    sys.exit(main())
