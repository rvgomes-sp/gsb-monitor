"""Motor de coleta EVT-007 — produção. Funil comercial: obra fresca >= R$ 10 MM.

Fluxo (Rodrigo, 2026-08-25):
  DIA D → descoberta mod 4-7 (homologado consolidado >= piso)
        → GET /itens (1×/contratação) → CLASSIFICADOR BARATO de obra
            NAO_OBRA → para  |  OBRA_FORTE/REVISAR → drill
        → GET /resultados só nos candidatos → resultados vigentes
        → valor homologado CONSOLIDADO (nível contratação) >= R$ 10 MM
        → FRESCOR (dataResultado × dataInclusao): FRESH/EXCEPTION = radar; BACKFILL = auditoria
        → OPORTUNIDADE

O frescor pertence ao EVENTO novo; os R$ 10 MM à CONTRATAÇÃO consolidada
(não exigir tudo homologado hoje). Perfil temporal é subproduto (grava delta/plataforma).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode, urlparse

from . import classificador as clf
from . import frescor as fr
from .cliente import CONSULTA, INTEGRACAO, ClientePNCP, ErroPNCP, TransitorioPNCP

MODALIDADES_PADRAO = [4, 5, 6, 7]
PISO_PADRAO = Decimal("10000000")


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v)) if v not in (None, "") else Decimal(0)
    except Exception:
        return Decimal(0)


def _cpf(ni: str | None) -> bool:
    d = "".join(c for c in (ni or "") if c.isdigit())
    return len(d) == 11 and len((ni or "").strip()) == 11


def _host(link) -> str:
    try:
        return (urlparse(link).hostname or "").lower() if link else ""
    except Exception:
        return ""


@dataclass
class Funil:
    data_alvo: str
    piso: str
    status: str = "COMPLETE"
    paginas_lidas: int = 0
    paginas_puladas: int = 0
    descobertas: int = 0                 # contratações mod 4-7 com homologado >= piso
    nao_obra_eliminadas: int = 0         # descartadas após /itens
    candidatas_obra: int = 0             # OBRA_FORTE + REVISAR
    drill_executado: int = 0
    obras_homologadas_piso: int = 0      # obra + consolidado >= piso + tem resultado hoje
    backfills_eliminados: int = 0        # tinham evento hoje, mas só BACKFILL
    oportunidades_frescas: int = 0
    por_classe_obra: dict = field(default_factory=dict)


@dataclass
class Motor:
    cli: ClientePNCP
    piso: Decimal = PISO_PADRAO
    pausa: float = 0.15

    # ---- descoberta (homologado consolidado >= piso) ----
    def descobrir(self, alvo: date, modalidade: int, fun: Funil):
        ds = alvo.strftime("%Y%m%d")
        pagina, total_paginas = 1, None
        while total_paginas is None or pagina <= total_paginas:
            q = urlencode({"dataInicial": ds, "dataFinal": ds,
                           "codigoModalidadeContratacao": modalidade,
                           "pagina": pagina, "tamanhoPagina": 50})
            try:
                payload = self.cli.get(f"{CONSULTA}/v1/contratacoes/atualizacao?{q}", endpoint="descoberta")
            except TransitorioPNCP:
                fun.paginas_puladas += 1
                fun.status = "PARTIAL"
                pagina += 1
                total_paginas = total_paginas or (pagina + 1)
                continue
            fun.paginas_lidas += 1
            if total_paginas is None:
                total_paginas = int(payload.get("totalPaginas") or 0)
            for r in (payload.get("data") or []):
                if _dec(r.get("valorTotalHomologado")) >= self.piso:
                    yield r
            if not total_paginas:
                break
            pagina += 1
            time.sleep(self.pausa)

    # ---- processa uma contratação candidata ----
    def processar(self, row: dict, alvo: date, fun: Funil) -> dict | None:
        org = row.get("orgaoEntidade") or {}
        cnpj, ano, seq = org.get("cnpj"), row.get("anoCompra"), row.get("sequencialCompra")
        if not (cnpj and ano and seq):
            return None
        base = f"{INTEGRACAO}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"

        # 1) /itens (1×) + classificador BARATO
        try:
            itens = self.cli.get(f"{base}/itens", endpoint="10.13")
        except (TransitorioPNCP, ErroPNCP):
            return None
        if not isinstance(itens, list):
            itens = itens.get("itens") if isinstance(itens, dict) else []
        cl = clf.classificar_contratacao(itens or [], row.get("objetoCompra") or "")
        fun.por_classe_obra[cl.classe] = fun.por_classe_obra.get(cl.classe, 0) + 1
        if cl.classe == clf.NAO_OBRA:
            fun.nao_obra_eliminadas += 1
            return None
        fun.candidatas_obra += 1

        # 2) drill /resultados só nos itens candidatos (com resultado)
        fun.drill_executado += 1
        alvo_itens = set(cl.itens_obra) or {it.get("numeroItem") for it in itens}
        eventos_hoje = []      # frescor de cada resultado incluído HOJE
        vencedores = []
        for it in itens:
            n = it.get("numeroItem")
            if n not in alvo_itens or not it.get("temResultado"):
                continue
            try:
                res = self.cli.get(f"{base}/itens/{n}/resultados", endpoint="10.17")
            except (TransitorioPNCP, ErroPNCP):
                continue
            if not isinstance(res, list):
                res = res.get("listaResultados") if isinstance(res, dict) else []
            for rr in (res or []):
                ni = rr.get("niFornecedor")
                if _cpf(ni):
                    continue
                f = fr.avaliar(rr.get("dataResultado"), rr.get("dataInclusao"))
                if f.data_inclusao and f.data_inclusao.date() == alvo:
                    eventos_hoje.append((n, rr, f))
                    vencedores.append({
                        "numero_item": n, "ni_fornecedor": ni,
                        "nome_fornecedor": rr.get("nomeRazaoSocialFornecedor"),
                        "porte_nome": rr.get("porteFornecedorNome"),
                        "natureza_juridica_nome": rr.get("naturezaJuridicaNome"),
                        "quantidade_homologada": str(_dec(rr.get("quantidadeHomologada"))),
                        "valor_unitario_homologado": str(_dec(rr.get("valorUnitarioHomologado"))),
                    })
            time.sleep(self.pausa)

        # sem evento NOVO hoje -> não é EVT-007 fresco de hoje
        if not eventos_hoje:
            return None
        fun.obras_homologadas_piso += 1

        # 3) frescor = evento mais fresco entre os que chegaram hoje
        mais_fresco = min(eventos_hoje, key=lambda e: (e[2].delta_business_days if e[2].delta_business_days is not None else 9999))
        f = mais_fresco[2]
        if not f.no_radar:
            fun.backfills_eliminados += 1
            return None  # só BACKFILL hoje -> fica na auditoria, fora do radar
        fun.oportunidades_frescas += 1

        homologado = _dec(row.get("valorTotalHomologado"))
        uni = row.get("unidadeOrgao") or {}
        return {
            "numero_controle_pncp": row.get("numeroControlePNCP"),
            "cnpj_orgao": cnpj, "ano": ano, "sequencial": seq,
            "orgao": org.get("razaoSocial"), "uf": uni.get("ufSigla"),
            "municipio": uni.get("municipioNome"),
            "modalidade": row.get("modalidadeNome"), "modalidade_id": row.get("modalidadeId"),
            "objeto": row.get("objetoCompra"),
            "classe_obra": cl.classe, "itens_obra": cl.itens_obra, "motivo_obra": cl.motivo,
            "valor_homologado_consolidado": str(homologado),
            "vencedores": vencedores,
            # frescor / perfil temporal (subproduto)
            "source_sender_raw": row.get("usuarioNome"),
            "source_host": _host(row.get("linkSistemaOrigem")),
            "link_sistema_origem": row.get("linkSistemaOrigem"),
            "data_resultado": f.data_resultado.isoformat() if f.data_resultado else None,
            "data_inclusao": f.data_inclusao.isoformat() if f.data_inclusao else None,
            "delta_calendar_days": f.delta_calendar_days,
            "delta_business_days": f.delta_business_days,
            "freshness_class": f.classe,
        }

    # ---- execução ----
    def rodar(self, alvo: date, modalidades: list[int]) -> tuple[Funil, list[dict]]:
        fun = Funil(alvo.isoformat(), str(self.piso))
        vistos: set = set()
        ops: list[dict] = []
        for mod in modalidades:
            for row in self.descobrir(alvo, mod, fun):
                chave = row.get("numeroControlePNCP") or f"{row.get('anoCompra')}/{row.get('sequencialCompra')}"
                if chave in vistos:
                    continue
                vistos.add(chave)
                fun.descobertas += 1
                try:
                    op = self.processar(row, alvo, fun)
                except Exception:
                    continue
                if op:
                    ops.append(op)
        return fun, ops
