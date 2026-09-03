"""One canonical discovery endpoint; bounded retry and provable page coverage."""
from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from .contracts import RESULTS_URL, SOURCE, calendar_day, decode, digest, integer


@dataclass
class Response:
    status: int
    body: bytes
    headers: dict = field(default_factory=dict)


class TransportFailure(RuntimeError):
    def __init__(self, reason, attempts):
        super().__init__(reason)
        self.attempts = attempts


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_get(url: str) -> Response:
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme, parsed.netloc, parsed.path) != ("https", "dadosabertos.compras.gov.br", urllib.parse.urlsplit(RESULTS_URL).path):
        raise ValueError("noncanonical discovery endpoint")
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "GSB-EVT007-GateB/1"}, method="GET")
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
            return Response(response.status, response.read(), dict(response.headers))
    except urllib.error.HTTPError as error:
        return Response(error.code, error.read(), dict(error.headers))


def fetch(url, get=public_get, *, sleep=time.sleep, now=lambda: datetime.now(timezone.utc), tries=4, max_wait=60):
    if tries < 1 or not 0 <= max_wait <= 60:
        raise ValueError("invalid retry bounds")
    attempts = []
    for attempt in range(tries):
        try:
            response = get(url)
            record = {"attempt": attempt + 1, "status": response.status, "body_sha256": digest(response.body),
                      "response_body": response.body.decode("utf-8", errors="replace"), "headers": response.headers}
        except TransportFailure as error:
            # A bounded transport can stop between retries. Keep the earlier
            # HTTP evidence rather than losing it when its budget is exhausted.
            raise TransportFailure(str(error), attempts + error.attempts) from error
        except (TimeoutError, ConnectionError, urllib.error.URLError) as error:
            response = None
            record = {"attempt": attempt + 1, "status": None, "error": type(error).__name__}
        attempts.append(record)
        if response is not None and response.status == 200:
            return response, attempts
        if response is not None and response.status not in (429, 500, 502, 503, 504):
            raise TransportFailure("NON_RETRYABLE_HTTP", attempts)
        if attempt + 1 == tries:
            raise TransportFailure("RETRIES_EXHAUSTED", attempts)
        wait = min(2 ** attempt, max_wait)
        if response is not None:
            header = next((str(v) for k, v in response.headers.items() if k.lower() == "retry-after"), None)
            if header:
                try:
                    requested = float(header) if header.isdigit() else (parsedate_to_datetime(header) - now()).total_seconds()
                except (ValueError, TypeError, OverflowError):
                    raise TransportFailure("INVALID_RETRY_AFTER", attempts)
                wait = max(wait, requested)
        if wait > max_wait:
            record["retry_after_seconds"] = wait
            raise TransportFailure("RETRY_DEFERRED_NOT_EVADED", attempts)
        record["wait_seconds"] = wait
        sleep(wait)
    raise AssertionError("unreachable")


@dataclass
class Collection:
    window: str
    status: str = "FAILED"
    pages: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    attempts: list = field(default_factory=list)
    reasons: list = field(default_factory=list)
    official_total: int | None = None
    official_pages: int | None = None
    duplicate_rows: int = 0

    def summary(self):
        return {"source": SOURCE, "window": self.window, "status": self.status,
                "official_total": self.official_total, "official_pages": self.official_pages,
                "pages_received": len(self.pages), "rows_received": len(self.rows),
                "duplicate_rows": self.duplicate_rows, "reasons": self.reasons}


def collect(window: str, *, get=public_get, max_pages: int, page_size=500, sleep=time.sleep) -> Collection:
    if calendar_day(window) != window or max_pages < 1 or not 1 <= page_size <= 500:
        raise ValueError("explicit date and bounded page limit required")
    result = Collection(window)
    seen_pages, seen_rows = set(), set()
    for page in range(1, max_pages + 1):
        params = {"dataResultadoPncpInicial": window, "dataResultadoPncpFinal": window,
                  "pagina": page, "tamanhoPagina": page_size}
        url = RESULTS_URL + "?" + urllib.parse.urlencode(params)
        try:
            response, attempts = fetch(url, get, sleep=sleep)
            result.attempts.extend({"page": page, **a} for a in attempts)
        except TransportFailure as error:
            result.attempts.extend({"page": page, **a} for a in error.attempts)
            result.reasons.append(str(error))
            break
        page_record = {"page": page, "url": url, "body": response.body,
                       "body_sha256": digest(response.body), "headers": response.headers}
        result.pages.append(page_record)  # even a malformed HTTP200 is evidence
        try:
            payload = decode(response.body)
            rows = payload["resultado"]
            if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
                raise ValueError("invalid rows")
            total, pages, remaining = (integer(payload[k], minimum=0) for k in ("totalRegistros", "totalPaginas", "paginasRestantes"))
            page_record["metadata"] = {k: payload[k] for k in ("totalRegistros", "totalPaginas", "paginasRestantes")}
            if result.official_total is None:
                result.official_total, result.official_pages = total, pages
            if (total, pages) != (result.official_total, result.official_pages):
                raise ValueError("TOTALS_CHANGED_DURING_PAGINATION")
            if total == 0:
                if rows or pages not in (0, 1) or remaining != 0 or page != 1:
                    raise ValueError("INVALID_EMPTY_COVERAGE")
                result.status = "COMPLETE"
                return result
            if pages != (total + page_size - 1) // page_size or remaining != pages - page:
                raise ValueError("PAGINATION_METADATA_INCONSISTENT")
            if len(rows) != min(page_size, total - (page - 1) * page_size):
                raise ValueError("PAGE_LENGTH_MISMATCH")
            content_hash = digest(rows)
            if content_hash in seen_pages:
                raise ValueError("REPEATED_PAGE")
            seen_pages.add(content_hash)
            for row in rows:
                row_hash = digest(row)
                if row_hash in seen_rows:
                    result.duplicate_rows += 1
                    if "DUPLICATED_ROW_COVERAGE_UNCERTAIN" not in result.reasons:
                        result.reasons.append("DUPLICATED_ROW_COVERAGE_UNCERTAIN")
                seen_rows.add(row_hash)
            result.rows.extend(rows)
            if page == pages:
                if len(result.rows) == total and not result.reasons:
                    result.status = "COMPLETE"
                else:
                    result.status = "PARTIAL"
                return result
        except (ValueError, KeyError, TypeError) as error:
            result.reasons.append(str(error))
            break
    else:
        result.reasons.append("MAX_PAGES_REACHED")
    result.status = "PARTIAL" if result.rows else "FAILED"
    return result
