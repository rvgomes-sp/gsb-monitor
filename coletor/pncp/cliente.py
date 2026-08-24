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
import random
import sys
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
    """Cliente educado com o PNCP (régua de produção — governanca/INCIDENTE_TRANSPORTE_PNCP.md).

    - Conexão NOVA por chamada (sem keep-alive): o stall de TLS observado ocorreu em conexão
      reusada; requests avulsos (curl) sempre passaram.
    - delay base + jitter entre chamadas; honra Retry-After no 429.
    - máx 3 tentativas, timeout curto, log por chamada (nunca silêncio).
    - circuit breaker: após N timeouts CONSECUTIVOS, cooldown longo.
    """
    timeout: float = 25.0
    tentativas: int = 3
    pausa_base: float = 0.4          # delay base entre chamadas (s)
    jitter: float = 0.4              # + aleatório [0, jitter]
    breaker_limite: int = 5          # timeouts consecutivos p/ acionar breaker
    breaker_cooldown: float = 120.0  # cooldown do breaker (s)
    verboso: bool = False
    _cli: httpx.Client = field(default=None, repr=False)
    evidencias: list[Evidencia] = field(default_factory=list, repr=False)
    guardar_evidencia: bool = False
    _falhas_seguidas: int = field(default=0, repr=False)

    def __post_init__(self):
        self._cli = httpx.Client(
            timeout=httpx.Timeout(self.timeout, connect=10.0, read=self.timeout, pool=10.0),
            headers={
                "Accept": "application/json",
                "User-Agent": "GSB-EVT007/3.0",
                # CDN do PNCP trava com gzip/br do httpx -> identity obrigatório.
                "Accept-Encoding": "identity",
                # conexão nova por chamada: evita o stall de renegociação em conexão reusada.
                "Connection": "close",
            },
            follow_redirects=False,  # 10.5 na Integração dá 301 sem Location: é sinal, não seguir
            limits=httpx.Limits(max_keepalive_connections=0, max_connections=2),
        )

    def fechar(self):
        if self._cli:
            self._cli.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.fechar()

    def get(self, url: str, *, endpoint: str = "") -> Any:
        """GET educado: log por tentativa, honra Retry-After, delay+jitter, circuit breaker.
        Levanta TransitorioPNCP (página instável, após N tentativas) ou ErroPNCP (4xx não-429)."""

        @retry(
            retry=retry_if_exception_type(TransitorioPNCP),
            stop=stop_after_attempt(self.tentativas),
            wait=wait_exponential_jitter(initial=1, max=8),
            reraise=True,
        )
        def _bater(attempt=[0]) -> Any:
            attempt[0] += 1
            t0 = time.monotonic()
            try:
                r = self._cli.get(url)
            except (httpx.TransportError, httpx.TimeoutException) as e:
                self._registrar_falha()
                self._log(f"    [{endpoint}] tentativa {attempt[0]} FALHOU {type(e).__name__} "
                          f"{int((time.monotonic()-t0)*1000)}ms")
                raise TransitorioPNCP(f"transporte: {e}") from e
            lat = int((time.monotonic() - t0) * 1000)
            if r.status_code in TRANSITORIOS:
                ra = r.headers.get("Retry-After")
                espera = min(30, int(ra)) if (ra and ra.isdigit()) else min(15, 2 ** attempt[0])
                self._registrar_falha()
                self._log(f"    [{endpoint}] tentativa {attempt[0]} HTTP {r.status_code} "
                          f"-> espera {espera}s (Retry-After={ra})")
                time.sleep(espera)
                raise TransitorioPNCP(f"HTTP {r.status_code}")
            if r.status_code >= 400:
                raise ErroPNCP(f"HTTP {r.status_code} em {url}")
            raw = r.content
            try:
                payload = r.json()
            except ValueError as e:
                raise TransitorioPNCP(f"JSON inválido: {e}") from e
            self._falhas_seguidas = 0     # sucesso reseta o breaker
            if self.verboso:
                self._log(f"    [{endpoint}] OK {r.status_code} {lat}ms")
            if self.guardar_evidencia:
                self.evidencias.append(Evidencia(
                    endpoint=endpoint, url=url, http_status=r.status_code,
                    source_hash=hashlib.sha256(raw).hexdigest(),
                    latencia_ms=lat, payload=payload,
                ))
            # pacing educado: delay base + jitter entre chamadas
            time.sleep(self.pausa_base + random.random() * self.jitter)
            return payload

        return _bater()

    def _registrar_falha(self):
        self._falhas_seguidas += 1
        if self._falhas_seguidas >= self.breaker_limite:
            self._log(f"  ⚡ circuit breaker: {self._falhas_seguidas} falhas seguidas "
                      f"-> cooldown {self.breaker_cooldown:.0f}s")
            time.sleep(self.breaker_cooldown)
            self._falhas_seguidas = 0

    def _log(self, msg: str):
        print(msg, file=sys.stderr, flush=True)
