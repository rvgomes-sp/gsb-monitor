#!/usr/bin/env python3
"""Sobe as obras coletadas (saída do run_coleta_evt007) para o monitor.

Lê um ou mais JSON de saída do coletor (--in), mapeia as oportunidades para o
shape do monitor e faz POST em /api/import/snapshot (substituição total).

Uso:
  python monitor/subir_obras.py --in saidas/val_20260820_mod4.json saidas/val_20260820_mod567.json \
      --url https://gsb-monitor.vercel.app --token "$IMPORT_TOKEN"
  (ou --dry para só gerar o feed em monitor/data/monitor_feed_real.json)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inferencia import rotulo_linha  # noqa: E402

PCT_GARANTIA = 5.0

# ordem da fila: frescor primeiro (o mais novo no topo), depois valor desc.
_FRESCOR_RANK = {"FRESH": 0, "FRESH_CALENDAR_EXCEPTION": 1, "BACKFILL": 2}
_FRESCOR_CURTO = {"FRESH": "fresco", "FRESH_CALENDAR_EXCEPTION": "fresco (sex→seg)", "BACKFILL": "backfill"}
BRAND = {"title": "VIP | GSB Monitor",
         "subtitle": "Inteligência de Contratações Públicas & Seguro Garantia",
         "signature": "Ana Fonseca", "message": "Obras homologadas frescas — a prospecção começa agora."}
OPERATOR = {"name": "Rodrigo Vazquez", "role": "Sócio-fundador · V&F", "initials": "RV"}
EVENTS = [["EVT-001", "PCA", "Planejamento"], ["EVT-002", "Edital", "Publicação"],
          ["EVT-003", "Disputa", "Julgamento/recurso"], ["EVT-007", "Homologação", "ATUAL — obra fresca"],
          ["EVT-008", "Convocação", "Relógio 30 dias"]]


def _brl(v: float) -> str:
    return f"R$ {v/1_000_000:,.1f} MM".replace(",", "@").replace(".", ",").replace("@", ".")


def oportunidade(o: dict) -> dict:
    val = float(o.get("valor_homologado_consolidado") or 0)
    venc = (o.get("vencedores") or [{}])[0]
    garantia = round(val * PCT_GARANTIA / 100, 2)
    porte = venc.get("porte_nome") or ""
    frescor = o.get("freshness_class") or ""
    delta = o.get("delta_calendar_days")
    # objeto reduzido + inferência do trabalho (determinístico, do classificador)
    reduzido, inferencia = rotulo_linha(o.get("objeto") or "", o.get("classe_obra"))
    n_lotes = len(o.get("lotes") or [])  # dedup pode agregar contratações-irmãs
    return {
        "process_id": o.get("numero_controle_pncp"),
        "processo": o.get("numero_controle_pncp"),
        "orgao": o.get("orgao") or "—",
        "uf": o.get("uf") or "", "municipio": o.get("municipio") or "",
        "fornecedor": venc.get("nome_fornecedor") or "—",
        "fornecedor_cnpj": venc.get("ni_fornecedor") or "",
        "porte": porte, "natureza_juridica": venc.get("natureza_juridica_nome") or "",
        # a linha do monitor mostra o trabalho claro; objeto completo fica para busca/consulta
        "objeto": f"{inferencia} — {reduzido}" + (f" · {n_lotes} lotes" if n_lotes > 1 else ""),
        "objeto_reduzido": reduzido, "inferencia_trabalho": inferencia,
        "objeto_completo": (o.get("objeto") or "")[:600],
        "modalidade": o.get("modalidade") or "",
        "classe_obra": o.get("classe_obra"),
        "data_homologacao": o.get("data_resultado"),
        "data_inclusao": o.get("data_inclusao"),
        "delta_dias": delta, "frescor": frescor,
        "origem": o.get("source_sender_raw"),
        # a coluna "Homologação" ganha o carimbo de frescor
        "evento": f"EVT-007 · {_FRESCOR_CURTO.get(frescor, frescor)}"
                  + (f" · Δ{delta}d" if delta is not None else ""),
        "status": "NOVA", "documentos": "A confirmar edital",
        "valor": val, "valor_numero": val,
        "rota": "Vazquez & Fonseca" if val > 10_000_000 else "Vieira Mendonça",
        "atualizado": date.today().isoformat(),
        "percentual_garantia_execucao": PCT_GARANTIA,
        "garantia_execucao": garantia, "seguro_garantia_execucao": garantia,
    }


def _rank(op: dict) -> tuple:
    """Ordem da fila: frescor (novo primeiro) e, dentro do mesmo frescor, maior valor."""
    return (_FRESCOR_RANK.get(op.get("frescor") or "", 9),
            -float(op.get("valor_numero") or 0))


def deduplicar(ops: list[dict]) -> list[dict]:
    """1) por numero_controle_pncp; 2) colapsa contratações-irmãs (mesmo órgão+vencedor+
    valor+objeto reduzido) num único alvo comercial, contando lotes. Conservador."""
    por_controle, ordem = {}, []
    for o in ops:
        k = o.get("numero_controle_pncp")
        if k not in por_controle:
            por_controle[k] = o
            ordem.append(k)
    unicas = [por_controle[k] for k in ordem]

    agrupado, saida = {}, []
    for o in unicas:
        venc = (o.get("vencedores") or [{}])[0]
        red, _ = rotulo_linha(o.get("objeto") or "", o.get("classe_obra"))
        chave = (o.get("cnpj_orgao"), venc.get("ni_fornecedor"),
                 str(o.get("valor_homologado_consolidado")), red)
        if chave in agrupado:
            base = agrupado[chave]
            base.setdefault("lotes", [base.get("numero_controle_pncp")])
            base["lotes"].append(o.get("numero_controle_pncp"))
        else:
            agrupado[chave] = o
            saida.append(o)
    return saida


def montar_feed(ops: list[dict]) -> dict:
    o2 = [oportunidade(o) for o in ops]
    o2.sort(key=_rank)   # fila ordenada: frescor -> valor (o melhor alvo no topo)
    total = sum(x["valor"] for x in o2)
    maior = max((x["valor"] for x in o2), default=0)
    vf = sum(1 for x in o2 if x["rota"] == "Vazquez & Fonseca")
    ufs = sorted({x["uf"] for x in o2 if x["uf"]})
    orgaos = len({x["orgao"] for x in o2 if x["orgao"] not in ("", "—")})
    kpis = [
        {"icon": "◇", "label": "Obras frescas homologadas", "value": str(len(o2)), "trend": "coleta EVT-007 · PNCP"},
        {"icon": "◈", "label": "Valor homologado", "value": _brl(total), "trend": "consolidado das obras"},
        {"icon": "◆", "label": "Maior obra", "value": _brl(maior), "trend": "—"},
    ]
    queues = [
        {"subtitle": "Emissão · acima de R$ 10 MM", "event_id": "VF", "label": "Vazquez & Fonseca", "count": vf, "priority": "high"},
        {"subtitle": "Estruturação · R$ 1 a 10 MM", "event_id": "VM", "label": "Vieira Mendonça", "count": len(o2) - vf, "priority": "medium"},
    ]
    summary = {"organs": str(orgaos) if orgaos else "—", "states": str(len(ufs)) if ufs else "—", "opportunities": len(o2)}
    insights = {"escopo": "obras frescas EVT-007 (D0/D1)", "oportunidades_na_base": len(o2),
                "valor_total_na_base": total, "maior_homologacao": maior,
                "orgaos_na_base": orgaos or "—", "ufs_na_base": ", ".join(ufs) or "—"}
    return {"brand": BRAND, "operator": OPERATOR, "kpis": kpis, "events": EVENTS,
            "queues": queues, "opportunities": o2, "summary": summary, "insights": insights}


def main() -> int:
    raise RuntimeError("LEGACY_EVT007_DISABLED_GATE_B: use python -m evt007; operational promotion is blocked")
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", nargs="+", required=True, help="JSON(s) de saída do coletor")
    ap.add_argument("--url", default="https://gsb-monitor.vercel.app")
    ap.add_argument("--token", help="IMPORT_TOKEN (se ausente, só grava o feed local)")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    ops = []
    for f in a.inp:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        ops.extend(d.get("oportunidades") or [])
    unicas = deduplicar(ops)
    print(f"dedup: {len(ops)} -> {len(unicas)} alvos ({len(ops) - len(unicas)} lotes/duplicatas agregados)")
    feed = montar_feed(unicas)
    dest = Path(__file__).resolve().parent / "data" / "monitor_feed_real.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"feed montado: {len(unicas)} obras | {dest}")

    if a.dry or not a.token:
        print("(dry / sem token — não subiu ao monitor)")
        return 0
    body = json.dumps({"feed": feed, "operations": {}}).encode()
    req = urllib.request.Request(f"{a.url}/api/import/snapshot", data=body,
                                 headers={"content-type": "application/json", "x-import-token": a.token})
    try:
        r = urllib.request.urlopen(req, timeout=90)
        print("SNAPSHOT:", r.status, r.read().decode()[:200])
    except urllib.error.HTTPError as e:
        print("ERRO", e.code, e.read().decode()[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
