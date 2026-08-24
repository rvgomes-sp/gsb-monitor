"""Classificador de OBRA — barato, roda sobre /itens ANTES do drill de resultados.

Baseado na evidência empírica (governanca/CLASSIFICACAO_ITEM_EVT007.md): catálogo/NCM
têm 0% de conteúdo útil no tier >10 MM, então a classificação usa os campos que a API
realmente preenche — `materialOuServico`, `unidadeMedida`, `descricao` — com `objetoCompra`
como confirmação/fallback. Não usa `catalogoCodigoItem`/`ncm` no caminho crítico.

Sinais por item:
  A (natureza)  materialOuServico == 'S'
  B (unidade)   unidadeMedida em conjunto estrutural de obra (KM, M2, M3, METRO...)
  C (semântica) termos de engenharia/obra na descricao

Classificação da CONTRATAÇÃO (depois de ler todos os itens):
  OBRA_FORTE  algum item com A ∧ B ∧ C
  REVISAR     algum item com A ∧ (B ∨ C), ou objetoCompra com semântica de obra
  NAO_OBRA    nenhum sinal de obra
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# unidades estruturais de obra (comparadas por continência, sem acento/caixa)
UNIDADES_OBRA = ["km", "quilometro", "m2", "metro quadrado", "m3", "metro cubico",
                 "metro linear", "metro", "ml", "hectare", "ha", "global", "empreitada",
                 "verba", "tonelada"]

# termos semânticos de obra/engenharia
TERMOS_OBRA = ["obra", "constru", "restaura", "pavimenta", "recapea", "asfalt",
               "implanta", "recupera", "duplica", "reforma", "rodovia", "ponte",
               "viaduto", "drenagem", "terraplan", "edifica", "saneamento", "esgoto",
               "engenharia", "urbaniza", "revitaliza", "requalifica", "ampliacao",
               "canaliza", "adutora", "barragem", "aterro"]

OBRA_FORTE = "OBRA_FORTE"
REVISAR = "REVISAR"
NAO_OBRA = "NAO_OBRA"


def _fold(v) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(v or "")) if unicodedata.category(c) != "Mn")
    return s.casefold().strip()


def _unidade_obra(u) -> bool:
    f = _fold(u)
    # evita casar "metro" dentro de palavras; usa fronteiras/continência simples
    return any(re.search(rf"\b{re.escape(t)}\b", f) or f == t for t in UNIDADES_OBRA)


def _semantica_obra(txt) -> bool:
    f = _fold(txt)
    return any(t in f for t in TERMOS_OBRA)


@dataclass
class SinalItem:
    numero_item: int | None
    a_servico: bool
    b_unidade: bool
    c_semantica: bool

    @property
    def forte(self) -> bool:
        return self.a_servico and self.b_unidade and self.c_semantica

    @property
    def parcial(self) -> bool:
        return self.a_servico and (self.b_unidade or self.c_semantica)


@dataclass
class Classificacao:
    classe: str                 # OBRA_FORTE | REVISAR | NAO_OBRA
    itens_obra: list[int]       # números dos itens que acenderam sinal de obra
    motivo: str                 # rastro auditável


def sinal_item(it: dict) -> SinalItem:
    return SinalItem(
        numero_item=it.get("numeroItem"),
        a_servico=(it.get("materialOuServico") or "").upper().startswith("S"),
        b_unidade=_unidade_obra(it.get("unidadeMedida")),
        c_semantica=_semantica_obra(it.get("descricao")),
    )


def classificar_contratacao(itens: list[dict], objeto_compra: str = "") -> Classificacao:
    sinais = [sinal_item(it) for it in (itens or [])]
    fortes = [s.numero_item for s in sinais if s.forte]
    parciais = [s.numero_item for s in sinais if s.parcial]
    if fortes:
        return Classificacao(OBRA_FORTE, fortes,
                             f"{len(fortes)} item(ns) com A∧B∧C (serviço+unidade+semântica)")
    if parciais:
        return Classificacao(REVISAR, parciais,
                             f"{len(parciais)} item(ns) com A∧(B∨C) — sinal parcial")
    if _semantica_obra(objeto_compra):
        return Classificacao(REVISAR, [], "objetoCompra com semântica de obra (fallback)")
    return Classificacao(NAO_OBRA, [], "sem sinal de obra nos itens nem no objeto")
