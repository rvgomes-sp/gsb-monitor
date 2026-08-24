#!/usr/bin/env python3
"""Gera monitor/data/monitor_feed_real.json a partir do banco vivo de licitações.

Modos:
  --zerar                 feed vazio (zera o monitor, preserva marca/eventos)
  --casos casos.json      feed a partir da saída do coletor (run_coleta_evt007 --out)
  (--db)                  [futuro] direto do Supabase licitacoes via DATABASE_URL

Mantém a forma que o monitor_vip.html espera:
  brand, operator, kpis, events, queues, opportunities, summary, insights
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DESTINO = RAIZ / "data" / "monitor_feed_real.json"
PCT_GARANTIA = 5.0  # % garantia de execução (padrão)

BRAND = {
    "title": "VIP | GSB Monitor",
    "subtitle": "Inteligência de Contratações Públicas & Seguro Garantia",
    "signature": "Ana Fonseca",
    "message": "O investimento virou máquina. A prospecção começa agora.",
}
OPERATOR = {"name": "Rodrigo Vazquez", "role": "Sócio-fundador · V&F", "initials": "RV"}
EVENTS = [
    ["EVT-001", "PCA", "Planejamento"],
    ["EVT-002", "Edital", "Publicação"],
    ["EVT-003", "Disputa", "Julgamento/recurso"],
    ["EVT-007", "Homologação", "ATUAL — chegamos primeiro"],
    ["EVT-008", "Convocação", "Relógio 30 dias"],
]


def _brl(v: float) -> str:
    return f"R$ {v/1_000_000:,.0f} MM".replace(",", ".") if v >= 1_000_000 else f"R$ {v:,.0f}"


def feed_base(kpis, queues, opportunities, summary, insights) -> dict:
    return {"brand": BRAND, "operator": OPERATOR, "kpis": kpis, "events": EVENTS,
            "queues": queues, "opportunities": opportunities, "summary": summary,
            "insights": insights}


def feed_zerado() -> dict:
    kpis = [
        {"icon": "◇", "label": "Oportunidades qualificadas", "value": "0", "trend": "aguardando coleta · PNCP"},
        {"icon": "◈", "label": "Contratos mapeados", "value": "R$ 0", "trend": "valor total em jogo"},
        {"icon": "◆", "label": "Maior homologação", "value": "R$ 0", "trend": "—"},
    ]
    queues = [
        {"subtitle": "Emissão · acima de R$ 10 MM", "event_id": "VF", "label": "Vazquez & Fonseca", "count": 0, "priority": "high"},
        {"subtitle": "Estruturação · R$ 1 a 10 MM", "event_id": "VM", "label": "Vieira Mendonça", "count": 0, "priority": "medium"},
    ]
    summary = {"organs": "—", "states": "—", "opportunities": 0}
    insights = {"escopo": "monitor zerado — aguardando primeira coleta", "oportunidades_na_base": 0,
                "valor_total_na_base": 0, "maior_homologacao": 0, "orgaos_na_base": "—", "ufs_na_base": "—"}
    return feed_base(kpis, queues, [], summary, insights)


def _oportunidade(caso: dict) -> dict:
    val = float(caso.get("valor_total_homologado") or 0)
    # vencedor principal = 1º resultado do item de maior valor
    itens = caso.get("itens") or []
    venc = {}
    for it in itens:
        for r in (it.get("resultados") or []):
            if (r.get("papel") == "VENCEDOR"):
                venc = r
                break
        if venc:
            break
    garantia = round(val * PCT_GARANTIA / 100, 2)
    dr = next((r.get("data_resultado") for it in itens for r in (it.get("resultados") or []) if r.get("data_resultado")), None)
    return {
        "process_id": caso.get("numero_controle_pncp"),
        "orgao": caso.get("orgao_razao_social") or "—",
        "processo": caso.get("numero_compra") or caso.get("numero_controle_pncp"),
        "fornecedor": venc.get("nome_fornecedor") or "—",
        "fornecedor_cnpj": venc.get("ni_fornecedor") or "",
        "objeto": (caso.get("objeto_compra") or "")[:280],
        "modalidade": caso.get("modalidade_nome") or "",
        "uf": caso.get("uf") or "",
        "municipio": caso.get("municipio") or "",
        "data_homologacao": dr,
        "evento": "EVT-007 Homologação",
        "status": "NOVA",
        "documentos": "A confirmar edital",
        "valor": val,
        "valor_numero": val,
        "rota": "Vazquez & Fonseca" if caso.get("rota") == "VAZQUEZ_FONSECA" else "Vieira Mendonça",
        "atualizado": date.today().isoformat(),
        "porte": venc.get("porte_nome") or "",
        "natureza_juridica": venc.get("natureza_juridica_nome") or "",
        "percentual_garantia_execucao": PCT_GARANTIA,
        "garantia_execucao": garantia,
        "seguro_garantia_execucao": garantia,
    }


def feed_de_casos(casos: list[dict]) -> dict:
    ops = [_oportunidade(c) for c in casos]
    total = sum(o["valor"] for o in ops)
    maior = max((o["valor"] for o in ops), default=0)
    vf = sum(1 for o in ops if o["rota"] == "Vazquez & Fonseca")
    vm = len(ops) - vf
    ufs = sorted({o["uf"] for o in ops if o["uf"]})
    orgaos = len({o["orgao"] for o in ops if o["orgao"] and o["orgao"] != "—"})
    kpis = [
        {"icon": "◇", "label": "Oportunidades qualificadas", "value": str(len(ops)), "trend": "coleta PNCP EVT-007"},
        {"icon": "◈", "label": "Contratos mapeados", "value": _brl(total), "trend": "valor homologado em jogo"},
        {"icon": "◆", "label": "Maior homologação", "value": _brl(maior), "trend": "—"},
    ]
    queues = [
        {"subtitle": "Emissão · acima de R$ 10 MM", "event_id": "VF", "label": "Vazquez & Fonseca", "count": vf, "priority": "high"},
        {"subtitle": "Estruturação · R$ 1 a 10 MM", "event_id": "VM", "label": "Vieira Mendonça", "count": vm, "priority": "medium"},
    ]
    summary = {"organs": str(orgaos) if orgaos else "—", "states": str(len(ufs)) if ufs else "—", "opportunities": len(ops)}
    insights = {"escopo": f"coleta EVT-007", "oportunidades_na_base": len(ops),
                "valor_total_na_base": total, "maior_homologacao": maior,
                "orgaos_na_base": orgaos or "—", "ufs_na_base": ", ".join(ufs) or "—"}
    return feed_base(kpis, queues, ops, summary, insights)


def main() -> int:
    p = argparse.ArgumentParser(description="Gera o feed do GSB Monitor")
    p.add_argument("--zerar", action="store_true", help="feed vazio (zera o monitor)")
    p.add_argument("--casos", help="JSON de casos (saída do coletor) para gerar o feed")
    p.add_argument("--out", default=str(DESTINO))
    a = p.parse_args()

    if a.zerar:
        feed = feed_zerado()
    elif a.casos:
        casos = json.loads(Path(a.casos).read_text(encoding="utf-8"))
        feed = feed_de_casos(casos)
    else:
        p.error("informe --zerar ou --casos")

    Path(a.out).write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"feed gravado: {a.out} | oportunidades={len(feed['opportunities'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
