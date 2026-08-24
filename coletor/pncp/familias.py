"""Classificação de família por CÓDIGO de catálogo (CATMAT/CATSER).

NUNCA por palavra-chave (decisão Rodrigo 2026-08-24). Fonte:
config/familias_catalogo.json (classe -> status CERTA/INFERIR/MONITORAR/DESCARTAR).

Entrada = item do 10.13 (materialOuServico + catalogoCodigoItem + categoriaItemCatalogo).
Sem código -> status PENDENTE (só ganha família no enriquecimento por edital).

⚠️ A VALIDAR: o mapeamento código-do-item -> classe assume que a classe (4 díg.)
é prefixo do catalogoCodigoItem. Confirmar em amostra de itens COM código real
antes de confiar na precisão. Sem código, o comportamento (PENDENTE) é definitivo.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_CONFIG = Path(__file__).resolve().parents[2] / "config" / "familias_catalogo.json"

PENDENTE = "PENDENTE"


@dataclass
class Familia:
    codigo: str | None      # classe/grupo/divisão que casou
    nome: str | None
    status: str             # CERTA | INFERIR | MONITORAR | DESCARTAR | STANDBY | PENDENTE
    origem: str             # como casou: 'classe' | 'grupo' | 'divisao' | 'sem_codigo'


class Classificador:
    def __init__(self, caminho: Path = _CONFIG):
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        self.material = dados.get("material_classe", {})
        self.servico = dados.get("servico_classe", {})

    def _tabela(self, material_ou_servico: str | None) -> dict:
        return self.material if (material_ou_servico or "").upper().startswith("M") else self.servico

    def classificar(self, item: dict) -> Familia:
        cod = _somente_digitos(item.get("catalogoCodigoItem"))
        tab = self._tabela(item.get("materialOuServico"))
        if not cod:
            return Familia(None, None, PENDENTE, "sem_codigo")

        # 1) classe exata (4 díg.)
        if cod in tab:
            e = tab[cod]
            return Familia(cod, e.get("nome"), e.get("status", "MONITORAR"), "classe")
        # 2) classe por prefixo de 4 díg. do código do item
        if len(cod) >= 4 and cod[:4] in tab:
            e = tab[cod[:4]]
            return Familia(cod[:4], e.get("nome"), e.get("status", "MONITORAR"), "classe")
        # 3) grupo/divisão: casa pela classe cujo grupo/divisão seja prefixo
        for chave, e in tab.items():
            g = str(e.get("grupo") or "")
            d = str(e.get("divisao") or "")
            if g and cod.startswith(g):
                return Familia(g, e.get("grupo_nome"), e.get("status", "MONITORAR"), "grupo")
            if d and cod.startswith(d):
                return Familia(d, e.get("divisao_nome"), e.get("status", "MONITORAR"), "divisao")
        return Familia(cod, None, "MONITORAR", "sem_match")

    def eh_obra(self, item: dict) -> bool:
        """Obra = famílias de construção (para o gatilho 85%, só obras)."""
        f = self.classificar(item)
        nome = (f.nome or "").upper()
        return "CONSTRU" in nome or "OBRA" in nome or (f.codigo or "").startswith("54")


def _somente_digitos(v) -> str:
    if v is None:
        return ""
    return "".join(c for c in str(v) if c.isdigit())
