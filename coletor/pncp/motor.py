"""Motor de coleta EVT-007 — orquestra descoberta -> drill -> qualificação.

Fluxo (decisões em docs/pncp_v2.5/REVISAO_ENDPOINTS_EVT007.md):
  1. Descoberta (Consulta /contratacoes/atualizacao) por dia D, modalidades 4/5/6/7,
     tamanhoPagina=50, filtrando valorTotalHomologado >= piso (10 MM).
  2. Por caso: drill 10.13 itens + 10.17 resultados (lista crua). Rede de datas =
     resultado INCLUÍDO no dia D (data_inclusao == D); guardamos data_resultado E
     data_inclusao. (10.19 confirma inclusão como auditoria — opcional.)
  3. Qualifica: caso homologado > piso, com resultado, máx 10 itens (maiores),
     família por CÓDIGO de catálogo, gatilho 85% só obras, CPF descartado.
Coleta honesta: página instável é pulada e contada; status COMPLETE/PARTIAL.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

from .cliente import (CONSULTA, INTEGRACAO, ClientePNCP, ErroPNCP,
                      TransitorioPNCP)
from .familias import Classificador

MODALIDADES_PADRAO = [4, 5, 6, 7]
PISO_PADRAO = Decimal("10000000")


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v)) if v not in (None, "") else Decimal(0)
    except Exception:
        return Decimal(0)


def _cpf(ni: str | None) -> bool:
    d = "".join(c for c in (ni or "") if c.isdigit())
    # CNPJ (mesmo alfanumérico) tem 14 chars; CPF tem 11 dígitos
    return len(d) == 11 and len((ni or "").strip()) == 11


@dataclass
class Relatorio:
    data_alvo: str
    modalidades: list[int]
    piso: str
    status: str = "COMPLETE"
    paginas_lidas: int = 0
    paginas_puladas: int = 0
    casos_descobertos: int = 0
    casos_qualificados: int = 0
    itens_qualificados: int = 0
    resultados: int = 0
    por_familia_status: dict = field(default_factory=dict)
    por_uf: dict = field(default_factory=dict)
    por_plataforma: dict = field(default_factory=dict)
    amostra: list = field(default_factory=list)


@dataclass
class Motor:
    cli: ClientePNCP
    clf: Classificador
    piso: Decimal = PISO_PADRAO
    max_itens: int = 10
    pausa: float = 0.2

    # ---- Descoberta ----------------------------------------------------------
    def descobrir(self, alvo: date, modalidade: int, rel: Relatorio):
        ds = alvo.strftime("%Y%m%d")
        pagina, total_paginas = 1, None
        while total_paginas is None or pagina <= total_paginas:
            q = urlencode({"dataInicial": ds, "dataFinal": ds,
                           "codigoModalidadeContratacao": modalidade,
                           "pagina": pagina, "tamanhoPagina": 50})
            url = f"{CONSULTA}/v1/contratacoes/atualizacao?{q}"
            try:
                payload = self.cli.get(url, endpoint="descoberta")
            except TransitorioPNCP:
                rel.paginas_puladas += 1
                rel.status = "PARTIAL"
                pagina += 1
                total_paginas = total_paginas or (pagina + 1)
                continue
            rel.paginas_lidas += 1
            if total_paginas is None:
                total_paginas = int(payload.get("totalPaginas") or 0)
            for r in (payload.get("data") or []):
                if _dec(r.get("valorTotalHomologado")) >= self.piso:
                    yield r
            if not total_paginas:
                break
            pagina += 1
            time.sleep(self.pausa)

    # ---- Drill de um caso ----------------------------------------------------
    def coletar_caso(self, row: dict, alvo: date) -> dict | None:
        org = row.get("orgaoEntidade") or {}
        cnpj, ano, seq = org.get("cnpj"), row.get("anoCompra"), row.get("sequencialCompra")
        if not (cnpj and ano and seq):
            return None
        base = f"{INTEGRACAO}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
        try:
            itens = self.cli.get(f"{base}/itens", endpoint="10.13")
        except (TransitorioPNCP, ErroPNCP):
            return None
        if not isinstance(itens, list):
            itens = itens.get("itens") if isinstance(itens, dict) else []

        itens_qual = []
        for it in itens or []:
            if not it.get("temResultado"):
                continue
            n = it.get("numeroItem")
            try:
                res = self.cli.get(f"{base}/itens/{n}/resultados", endpoint="10.17")
            except (TransitorioPNCP, ErroPNCP):
                continue
            if not isinstance(res, list):
                res = res.get("listaResultados") if isinstance(res, dict) else []
            # rede de datas: resultado INCLUÍDO no dia D
            res_do_dia = [r for r in (res or []) if _data(r.get("dataInclusao")) == alvo]
            if not res_do_dia:
                continue
            fam = self.clf.classificar(it)
            eh_obra = self.clf.eh_obra(it)
            resultados = []
            for r in res_do_dia:
                ni = r.get("niFornecedor")
                if _cpf(ni):  # pessoa física descartada
                    continue
                qtd = _dec(r.get("quantidadeHomologada"))
                unit = _dec(r.get("valorUnitarioHomologado"))
                total_item = qtd * unit
                ratio = None
                if eh_obra:
                    est = _dec(it.get("valorTotal"))
                    if est > 0 and total_item > 0:
                        ratio = round(float(total_item / est), 4)
                resultados.append({
                    "sequencial_resultado": r.get("sequencialResultado"),
                    "ni_fornecedor": ni, "nome_fornecedor": r.get("nomeRazaoSocialFornecedor"),
                    "tipo_pessoa": r.get("tipoPessoa"),
                    "porte_id": r.get("porteFornecedorId"), "porte_nome": r.get("porteFornecedorNome"),
                    "natureza_juridica_id": r.get("naturezaJuridicaId"),
                    "natureza_juridica_nome": r.get("naturezaJuridicaNome"),
                    "codigo_pais": r.get("codigoPais"),
                    "quantidade_homologada": str(qtd), "valor_unitario_homologado": str(unit),
                    "valor_total_homologado_item": str(total_item),
                    "data_resultado": _iso(r.get("dataResultado")),
                    "data_inclusao": r.get("dataInclusao"),
                    "situacao_resultado_id": r.get("situacaoCompraItemResultadoId"),
                    "situacao_resultado_nome": r.get("situacaoCompraItemResultadoNome"),
                    "data_cancelamento": r.get("dataCancelamento"),
                    "indicador_subcontratacao": r.get("indicadorSubcontratacao"),
                    "ordem_classificacao_srp": r.get("ordemClassificacaoSrp"),
                    "reserva_remanescente": (r.get("reservaRemanescente") or {}),
                    "papel": _papel(r.get("reservaRemanescente")),
                    "ratio_85": ratio,
                })
            if not resultados:
                continue
            total_item = sum(_dec(x["valor_total_homologado_item"]) for x in resultados)
            itens_qual.append({
                "numero_item": n, "material_ou_servico": it.get("materialOuServico"),
                "descricao": it.get("descricao"),
                "valor_unitario_estimado": str(_dec(it.get("valorUnitarioEstimado"))),
                "valor_total_estimado": str(_dec(it.get("valorTotal"))),
                "criterio_julgamento_nome": it.get("criterioJulgamentoNome"),
                "catalogo_codigo_item": it.get("catalogoCodigoItem"),
                "categoria_item_catalogo": it.get("categoriaItemCatalogo"),
                "item_categoria_id": it.get("itemCategoriaId"),
                "ncm_nbs_codigo": it.get("ncmNbsCodigo"),
                "familia_codigo": fam.codigo, "familia_nome": fam.nome,
                "familia_status": fam.status, "eh_obra": eh_obra,
                "_total_homologado": total_item,
                "resultados": resultados,
            })
        if not itens_qual:
            return None
        # máx 10 itens (maiores por homologado)
        itens_qual.sort(key=lambda x: x["_total_homologado"], reverse=True)
        if len(itens_qual) > self.max_itens:
            itens_qual = itens_qual[:self.max_itens]

        homologado_caso = _dec(row.get("valorTotalHomologado"))
        uni = row.get("unidadeOrgao") or {}
        return {
            "numero_controle_pncp": row.get("numeroControlePNCP"),
            "cnpj_orgao": cnpj, "ano": ano, "sequencial": seq,
            "numero_compra": row.get("numeroCompra"),
            "modalidade_id": row.get("modalidadeId"), "modalidade_nome": row.get("modalidadeNome"),
            "modo_disputa_id": row.get("modoDisputaId"), "modo_disputa_nome": row.get("modoDisputaNome"),
            "situacao_compra_id": row.get("situacaoCompraId"), "situacao_compra_nome": row.get("situacaoCompraNome"),
            "objeto_compra": row.get("objetoCompra"),
            "informacao_complementar": row.get("informacaoComplementar"),
            "srp": row.get("srp"),
            "valor_total_estimado": str(_dec(row.get("valorTotalEstimado"))),
            "valor_total_homologado": str(homologado_caso),
            "orgao_razao_social": org.get("razaoSocial"),
            "uf": uni.get("ufSigla"), "municipio": uni.get("municipioNome"),
            "usuario_nome": row.get("usuarioNome"),
            "link_sistema_origem": row.get("linkSistemaOrigem"),
            "data_atualizacao_global": row.get("dataAtualizacaoGlobal"),
            "rota": "VAZQUEZ_FONSECA" if homologado_caso > self.piso else "VIEIRA_MENDONCA",
            "itens": itens_qual,
        }

    # ---- Execução ------------------------------------------------------------
    def rodar(self, alvo: date, modalidades: list[int]) -> tuple[Relatorio, list[dict]]:
        rel = Relatorio(alvo.isoformat(), modalidades, str(self.piso))
        vistos: set[str] = set()
        casos: list[dict] = []
        for mod in modalidades:
            for row in self.descobrir(alvo, mod, rel):
                chave = row.get("numeroControlePNCP") or f"{row.get('anoCompra')}/{row.get('sequencialCompra')}"
                if chave in vistos:
                    continue
                vistos.add(chave)
                rel.casos_descobertos += 1
                try:
                    caso = self.coletar_caso(row, alvo)
                except Exception:
                    continue
                if not caso:
                    continue
                casos.append(caso)
                rel.casos_qualificados += 1
                rel.itens_qualificados += len(caso["itens"])
                for it in caso["itens"]:
                    rel.resultados += len(it["resultados"])
                    rel.por_familia_status[it["familia_status"]] = rel.por_familia_status.get(it["familia_status"], 0) + 1
                rel.por_uf[caso.get("uf") or "?"] = rel.por_uf.get(caso.get("uf") or "?", 0) + 1
                p = caso.get("usuario_nome") or "?"
                rel.por_plataforma[p] = rel.por_plataforma.get(p, 0) + 1
                if len(rel.amostra) < 5:
                    rel.amostra.append({k: caso[k] for k in
                                        ("numero_controle_pncp", "orgao_razao_social", "uf",
                                         "valor_total_homologado", "rota") if k in caso})
        return rel, casos


def _data(s) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _iso(s):
    d = _data(s)
    return d.isoformat() if d else None


def _papel(reserva) -> str:
    cod = (reserva or {}).get("codigo") if isinstance(reserva, dict) else None
    return {2: "REMANESCENTE", 3: "RESERVA"}.get(cod, "VENCEDOR")
