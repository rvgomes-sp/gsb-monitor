"""Versioned contracts. Source values never double as commercial decisions."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

SOURCE = "COMPRASGOV_DADOS_ABERTOS"
RESULTS_URL = "https://dadosabertos.compras.gov.br/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133"
MODALITIES = frozenset({4, 5, 6, 7})
FLOOR = Decimal("10000000")
CATALOG_STATES = frozenset({"NAO_FORNECIDO", "NAO_VALIDADO", "MATCH_EXATO", "SEM_MATCH", "CONTRADITORIO", "ERRO_LOOKUP"})


def canonical(value) -> str:
    # Preserve Decimal as a JSON number, never float-rounded or changed into a
    # string in factual payloads. Full original HTTP bytes are kept separately.
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("nonfinite decimal")
        return str(value)
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise TypeError("JSON object keys must be strings")
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + canonical(value[k]) for k in sorted(value)) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonical(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    data = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def decode(body: bytes):
    return json.loads(body.decode("utf-8-sig"), parse_float=Decimal,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def integer(value, *, minimum=1):
    if isinstance(value, bool) or value is None:
        raise ValueError("missing/invalid integer")
    text = str(value).strip()
    if not text.isascii() or not text.isdigit():
        raise ValueError("integer must contain digits only")
    number = int(text)
    if number < minimum:
        raise ValueError("integer out of range")
    return number


def money(value) -> Decimal:
    if value is None or isinstance(value, (bool, float)):
        raise ValueError("money requires lossless JSON Decimal, integer or decimal string")
    try:
        result = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError("invalid amount") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("invalid amount")
    return result


def calendar_day(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing date")
    text = value.strip()
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00")) if "T" in text else date.fromisoformat(text)
    # Official calendar date, not converted into UTC to shift a business day.
    return parsed.date().isoformat() if isinstance(parsed, datetime) else parsed.isoformat()
