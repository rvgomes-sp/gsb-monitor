"""Cliente HTTP do PNCP — httpx + tenacity, com evidência e resiliência.

Duas bases (ver docs/pncp_v2.5/REVISAO_ENDPOINTS_EVT007.md):
  CONSULTA   = descoberta (/contratacoes/atualizacao) + 10.5 (case detail GET)
  INTEGRACAO = itens (10.13), resultados (10.17), documentos (10.8/9), histórico (10.19)

Regras: retry curto/backoff nos transitórios (408/425/429/5xx); página instável do
PNCP é PULADA (não aborta a coleta) e contabilizada; toda resposta pode virar
evidência (sha256 dos bytes crus).
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential_jitter)

CONSULTA = "https://pncp.gov.br/api/consulta"
INTEGRACAO = "https://pncp.gov.br/api/pncp"
TRANSITORIOS = {408, 425, 429, 500, 502, 503, 504}


class ErroPNCP(RuntimeError):
    """Erro não-recuperável (4xx que não seja transitório)."""


class TransitorioPNCP(RuntimeError):
    """Erro recuperável — vale retry; se persistir, pula a página."""


@dataclass
class Evidencia:
    endpoint: str
    url: str
    http_status: int
    source_hash: str
    latencia_ms: int
    payload: Any


@dataclass
class ClientePNCP:
    timeout: float = 60.0
    tentativas: int = 12
    _cli: httpx.Client = field(default=None, repr=False)
    evidencias: list[Evidencia] = field(default_factory=list, repr=False)
    guardar_evidencia: bool = False

    def __post_init__(self):
        self._cli = httpx.Client(
            timeout=self.timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": "GSB-EVT007/3.0",
                # ⚠️ CDN do PNCP trava com gzip/br do httpx (ReadTimeout). identity é obrigatório.
                "Accept-Encoding": "identity",
            },
            follow_redirects=False,  # 10.5 na Integração dá 301 sem Location: é sinal, não seguir
        )

    def fechar(self):
        if self._cli:
            self._cli.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.fechar()

    def get(self, url: str, *, endpoint: str = "") -> Any:
        """GET com retry curto. Levanta TransitorioPNCP (página instável) ou ErroPNCP."""

        @retry(
            retry=retry_if_exception_type(TransitorioPNCP),
            stop=stop_after_attempt(self.tentativas),
            wait=wait_exponential_jitter(initial=1, max=60),
            reraise=True,
        )
        def _bater() -> Any:
            t0 = time.monotonic()
            try:
                r = self._cli.get(url)
            except (httpx.TransportError, httpx.TimeoutException) as e:
                raise TransitorioPNCP(f"transporte: {e}") from e
            lat = int((time.monotonic() - t0) * 1000)
            if r.status_code in TRANSITORIOS:
                ra = r.headers.get("Retry-After")
                if ra and ra.isdigit():
                    time.sleep(min(60, int(ra)))
                raise TransitorioPNCP(f"HTTP {r.status_code}")
            if r.status_code >= 400:
                raise ErroPNCP(f"HTTP {r.status_code} em {url}")
            raw = r.content
            try:
                payload = r.json()
            except ValueError as e:
                raise TransitorioPNCP(f"JSON inválido: {e}") from e
            if self.guardar_evidencia:
                self.evidencias.append(Evidencia(
                    endpoint=endpoint, url=url, http_status=r.status_code,
                    source_hash=hashlib.sha256(raw).hexdigest(),
                    latencia_ms=lat, payload=payload,
                ))
            return payload

        return _bater()
