#!/usr/bin/env python3
"""Sobe o OURO do Supabase (gsb.oportunidades_evt007) para o monitor.

Doutrina: só frescor, obras e serviços, 1 linha por vencedor x lote.
Ordena por frescor -> valor homologado. Regra dos 85% em destaque na garantia.

Uso: python monitor/subir_ouro.py --url https://gsb-monitor.vercel.app [--dry]
(token e DATABASE_URL lidos de monitor-vip/.env.local)
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

PCT = 5.0
BRAND = {"title": "VIP | GSB Monitor",
         "subtitle": "Observatório de Oportunidades · EVT-007 · Seguro Garantia",
         "signature": "Ana Fonseca", "message": "Ouro homologado fresco — obras e serviços."}
OPERATOR = {"name": "Rodrigo Vazquez", "role": "Sócio-fundador · V&F", "initials": "RV"}
EVENTS = [["EVT-002", "Edital", "Publicação"], ["EVT-003", "Disputa", "Julgamento"],
          ["EVT-007", "Homologação", "ATUAL — ouro fresco"], ["EVT-008", "Convocação", "Relógio 30 dias"]]


def _brl(v):
    return f"R$ {v/1_000_000:,.1f} MM".replace(",", "@").replace(".", ",").replace("@", ".")


def _frescor_label(fr, delta):
    if fr == "FRESH":
        return f"Fresco · D+{delta if delta is not None else '?'}"
    if fr == "FRESH_CALENDAR_EXCEPTION":
        return "Fresco · exceção calendário"
    return "Backfill"


def _env(k):
    for l in open("monitor-vip/.env.local", encoding="utf-8"):
        if l.strip().startswith(k):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def carregar():
    url = _env("DATABASE_URL")
    if "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    import psycopg
    q = """
      select safra, numero_controle_pncp, numero_item, id_biblioteca, codigo_objeto, grupo_objeto,
             orgao, uf, municipio, modalidade, objeto_curto, objeto,
             vencedor, vencedor_cnpj, porte, natureza_juridica,
             valor_estimado_total, valor_homologado_total, valor_homologado_item,
             pct_homologado_estimado, garantia_reforcada,
             data_resultado, data_inclusao, delta_calendar_days, frescor, fonte_plataforma
      from gsb.oportunidades_evt007
      where completo and frescor in ('FRESH','FRESH_CALENDAR_EXCEPTION')
            and grupo_objeto in ('O','S')
      order by (frescor='FRESH') desc, valor_homologado_item desc
    """
    with psycopg.connect(url, connect_timeout=20) as con:
        with con.cursor(row_factory=__import__("psycopg").rows.dict_row) as cur:
            cur.execute(q)
            return cur.fetchall()


def oportunidade(r):
    val = float(r["valor_homologado_item"] or 0)
    proc = f'{r["numero_controle_pncp"]}/L{r["numero_item"]}'
    reforc = r["garantia_reforcada"]
    pct_label = (f"5% + reforço (deságio {100 - float(r['pct_homologado_estimado']):.0f}%)"
                 if reforc and r["pct_homologado_estimado"] is not None else "5%")
    return {
        "process_id": proc, "processo": proc,
        "orgao": r["orgao"] or "—", "uf": r["uf"] or "", "municipio": r["municipio"] or "",
        "fornecedor": r["vencedor"] or "—", "fornecedor_cnpj": r["vencedor_cnpj"] or "",
        "porte": r["porte"] or "", "natureza_juridica": r["natureza_juridica"] or "",
        "objeto": (r["objeto_curto"] or r["objeto"] or "")[:200],
        "modalidade": r["modalidade"] or "",
        "classe_obra": r["id_biblioteca"],
        "data_homologacao": str(r["data_resultado"]) if r["data_resultado"] else "",
        "data_inclusao": str(r["data_inclusao"]) if r["data_inclusao"] else "",
        "delta_dias": r["delta_calendar_days"], "frescor": r["frescor"],
        "frescor_label": _frescor_label(r["frescor"], r["delta_calendar_days"]),
        "safra": str(r["safra"]), "origem": r["fonte_plataforma"],
        "valor_estimado": float(r["valor_estimado_total"] or 0),
        "valor_homologado_consolidado": float(r["valor_homologado_total"] or 0),
        "pct_homologado_estimado": float(r["pct_homologado_estimado"]) if r["pct_homologado_estimado"] is not None else None,
        "garantia_reforcada": bool(reforc),
        "evento": f'EVT-007 · {_frescor_label(r["frescor"], r["delta_calendar_days"])}',
        "status": "REFORÇADA" if reforc else "NOVA",
        "documentos": [],
        "garantia_execucao": "SIM", "percentual_garantia_execucao": pct_label,
        "seguro_garantia_execucao": round(val * PCT / 100, 2),
        "valor": _brl(val), "valor_numero": val,
        "rota": "Corretora Vazquez & Fonseca" if val > 10_000_000 else "Consultoria Vieira Mendonca",
        "atualizado": date.today().isoformat(),
    }


def montar_feed(rows):
    ops = [oportunidade(r) for r in rows]
    total = sum(o["valor_numero"] for o in ops)
    maior = max((o["valor_numero"] for o in ops), default=0)
    vf = sum(1 for o in ops if o["valor_numero"] > 10_000_000)
    reforc = sum(1 for o in ops if o["garantia_reforcada"])
    ufs = sorted({o["uf"] for o in ops if o["uf"]})
    orgaos = len({o["orgao"] for o in ops if o["orgao"] not in ("", "—")})
    obras = sum(1 for o in ops if str(o["classe_obra"]).startswith("O"))
    kpis = [
        {"icon": "◇", "label": "Oportunidades frescas (EVT-007)", "value": str(len(ops)), "trend": "obras + serviços homologados"},
        {"icon": "◈", "label": "Ouro homologado", "value": _brl(total), "trend": f"{obras} obras · {len(ops)-obras} serviços"},
        {"icon": "◆", "label": "Maior contrato", "value": _brl(maior), "trend": f"{reforc} c/ garantia reforçada (85%)"},
    ]
    queues = [
        {"subtitle": "Corretora · acima de R$ 10 MM", "event_id": "VF", "label": "Vazquez & Fonseca", "count": vf, "priority": "high"},
        {"subtitle": "Consultoria · até R$ 10 MM", "event_id": "VM", "label": "Vieira Mendonça", "count": len(ops) - vf, "priority": "medium"},
    ]
    summary = {"organs": str(orgaos), "states": str(len(ufs)), "opportunities": len(ops)}
    # top órgão e top UF por valor
    from collections import defaultdict
    porg = defaultdict(float); puf = defaultdict(float)
    for o in ops:
        porg[o["orgao"]] += o["valor_numero"]; puf[o["uf"]] += o["valor_numero"]
    top_org = max(porg.items(), key=lambda x: x[1]) if porg else ("—", 0)
    top_uf = max(puf.items(), key=lambda x: x[1]) if puf else ("—", 0)
    insights = [
        {"name": f"{len(ops)} oportunidades frescas",
         "desc": f"EVT-007 homologado · {obras} obras e {len(ops)-obras} serviços · safras 21 e 24/08"},
        {"name": f"{reforc} com garantia reforçada",
         "desc": "lotes de obra com deságio > 15% (regra dos 85%) — garantia de execução ampliada"},
        {"name": f"Maior praça: {top_uf[0]}",
         "desc": f"{_brl(top_uf[1])} homologados · órgão líder: {(top_org[0] or '—')[:40]} ({_brl(top_org[1])})"},
        {"name": f"Fila: {vf} Corretora · {len(ops)-vf} Consultoria",
         "desc": f"{_brl(total)} de ouro homologado · maior contrato {_brl(maior)} · {orgaos} órgãos, {len(ufs)} UFs"},
    ]
    return {"brand": BRAND, "operator": OPERATOR, "kpis": kpis, "events": EVENTS,
            "queues": queues, "opportunities": ops, "summary": summary, "insights": insights}


def main():
    raise RuntimeError("LEGACY_EVT007_DISABLED_GATE_B: use python -m evt007; operational promotion is blocked")
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://gsb-monitor.vercel.app")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    rows = carregar()
    feed = montar_feed(rows)
    dest = Path(__file__).resolve().parent / "data" / "monitor_feed_ouro.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"feed montado: {len(rows)} linhas de ouro | {dest}")

    if a.dry:
        print("(dry — não subiu)")
        return 0
    token = _env("IMPORT_TOKEN")
    body = json.dumps({"feed": feed, "operations": {}}).encode()
    req = urllib.request.Request(f"{a.url}/api/import/snapshot", data=body,
                                 headers={"content-type": "application/json", "x-import-token": token})
    try:
        r = urllib.request.urlopen(req, timeout=90)
        print("SNAPSHOT:", r.status, r.read().decode()[:200])
    except urllib.error.HTTPError as e:
        print("ERRO", e.code, e.read().decode()[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
