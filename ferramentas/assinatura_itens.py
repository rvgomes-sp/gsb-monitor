#!/usr/bin/env python3
"""Assinatura de itens EVT-007 — matriz de presença rigorosa (aprendizado empírico).

Princípio metodológico (Rodrigo, 2026-08-25): DUMP PRIMEIRO, classificar depois.
A heurística de obra é apenas RÓTULO de agrupamento, NUNCA critério de exclusão —
evita a circularidade "acho obra pela palavra obra e concluo que obra tem tal assinatura".

Controles implementados:
  - Denominador explícito por bucket (n_itens_total + contagem por campo).
  - Distingue 4 estados por campo: ABSENT (chave ausente) / NULL / EMPTY / VALUE.
    -> present_key% (chave veio) != non_null% (veio com valor).
  - Separa materialOuServico = M / S / outro, E por modalidadeId.
  - 10.13 e 10.14 guardados SEPARADOS no raw; auditoria de concordância à parte.
  - Evidência por resposta: source_url, http_status, collected_at, sha256(raw).
  - Matriz POR ITEM (uma contratação pode misturar M e S). Sem truncar itens.
  - objetoCompra NÃO é feature primária; entra só como rótulo textual auxiliar.

Saída:
  .scratch/assinatura_1013.jsonl  — 1 item do 10.13 por linha, cru + evidência
  .scratch/assinatura_1014.jsonl  — itens do 10.14 (controle), cru + evidência
  .scratch/assinatura_matriz.json — matriz + frequência de campos + auditoria 10.13x10.14
  stdout — resumo legível
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "coletor"))
from pncp.cliente import CONSULTA, INTEGRACAO, ClientePNCP  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SCR = RAIZ / ".scratch"

# termos SÓ para rótulo de análise (NÃO é regra de produção)
TERMOS_OBRA = ["obra", "constru", "reforma", "pavimenta", "recapea", "asfalt",
               "engenharia", "edifica", "rodovia", "ponte", "viaduto", "drenagem",
               "saneamento", "esgoto", "terraplan", "urbaniza", "km de"]

CAMPOS = ["catalogoCodigoItem", "catalogo", "catalogoId", "categoriaItemCatalogo",
          "ncmNbsCodigo", "ncmNbsDescricao", "informacaoComplementar",
          "unidadeMedida", "criterioJulgamentoNome"]


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v)) if v not in (None, "") else Decimal(0)
    except Exception:
        return Decimal(0)


def estado(item: dict, campo: str) -> str:
    """ABSENT | NULL | EMPTY | VALUE — distingue chave ausente de null/vazio."""
    if campo not in item:
        return "ABSENT"
    v = item[campo]
    if v is None:
        return "NULL"
    if isinstance(v, str) and v.strip() in ("", "None", "null"):
        return "EMPTY"
    if isinstance(v, (dict, list)) and len(v) == 0:
        return "EMPTY"
    return "VALUE"


def _obra_heur(it: dict, objeto: str) -> bool:
    txt = ((it.get("descricao") or "") + " " + (objeto or "")).lower()
    return any(t in txt for t in TERMOS_OBRA)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_ev(cli: ClientePNCP, url: str, endpoint: str):
    """GET + evidência (usa guardar_evidencia do cliente)."""
    t0 = time.monotonic()
    payload = cli.get(url, endpoint=endpoint)
    ev = cli.evidencias[-1] if cli.evidencias else None
    meta = {"source_url": url, "http_status": getattr(ev, "http_status", 200),
            "sha256": getattr(ev, "source_hash", None), "collected_at": now_iso(),
            "latency_ms": int((time.monotonic() - t0) * 1000)}
    return payload, meta


def rodar(alvo: str, por_modalidade: int, modalidades: list[int], piso: Decimal):
    SCR.mkdir(exist_ok=True)
    f13 = (SCR / "assinatura_1013.jsonl").open("w", encoding="utf-8")
    f14 = (SCR / "assinatura_1014.jsonl").open("w", encoding="utf-8")

    # matriz: bucket = (materialOuServico, modalidadeId) -> {campo -> Counter(estado)}
    matriz = defaultdict(lambda: defaultdict(Counter))
    total_bucket = Counter()
    # cross-tab obra-heurística (separado, NÃO filtra)
    obra_x = defaultdict(lambda: defaultdict(Counter))
    obra_total = Counter()
    # frequência global de campos
    freq = defaultdict(Counter)
    unidades = defaultdict(Counter)
    # auditoria 10.13 x 10.14
    audit = {"casos_comparados": 0, "mesmas_chaves": 0, "extras_1014": Counter(),
             "faltantes_1014": Counter(), "divergencia_valor": 0}
    n_itens = n_casos = 0

    with ClientePNCP(guardar_evidencia=True) as cli:
        for mod in modalidades:
            achei, pg, tp = 0, 1, None
            while (tp is None or pg <= tp) and achei < por_modalidade:
                q = urllib.parse.urlencode({"dataInicial": alvo, "dataFinal": alvo,
                                            "codigoModalidadeContratacao": mod,
                                            "pagina": pg, "tamanhoPagina": 50})
                try:
                    p, _ = get_ev(cli, f"{CONSULTA}/v1/contratacoes/atualizacao?{q}", "descoberta")
                except Exception:
                    pg += 1
                    continue
                if tp is None:
                    tp = int(p.get("totalPaginas") or 0)
                for r in (p.get("data") or []):
                    if achei >= por_modalidade:
                        break
                    if _dec(r.get("valorTotalHomologado")) < piso:
                        continue
                    org = r.get("orgaoEntidade") or {}
                    cnpj, ano, seq = org.get("cnpj"), r.get("anoCompra"), r.get("sequencialCompra")
                    if not (cnpj and ano and seq):
                        continue
                    objeto = r.get("objetoCompra") or ""
                    base = f"{INTEGRACAO}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
                    try:
                        itens, ev13 = get_ev(cli, f"{base}/itens", "10.13")
                    except Exception:
                        continue
                    if not isinstance(itens, list):
                        itens = itens.get("itens") if isinstance(itens, dict) else []
                    if not itens:
                        continue
                    achei += 1
                    n_casos += 1
                    for it in itens:
                        n_itens += 1
                        ms = it.get("materialOuServico") or "outro"
                        bucket = (ms, mod)
                        total_bucket[bucket] += 1
                        obra = _obra_heur(it, objeto)
                        obra_total[obra] += 1
                        for c in CAMPOS:
                            st = estado(it, c)
                            matriz[bucket][c][st] += 1
                            obra_x[obra][c][st] += 1
                            freq[c][st] += 1
                        unidades[bucket][(it.get("unidadeMedida") or "?")] += 1
                        f13.write(json.dumps({"modalidadeId": mod, "modalidadeNome": r.get("modalidadeNome"),
                                              "objeto": objeto[:150], "evidencia": ev13,
                                              "chaves": sorted(it.keys()), "item": it},
                                             ensure_ascii=False) + "\n")
                    # controle 10.14: 1º item do caso
                    n = itens[0].get("numeroItem")
                    try:
                        one, ev14 = get_ev(cli, f"{base}/itens/{n}", "10.14")
                        if isinstance(one, dict):
                            f14.write(json.dumps({"evidencia": ev14, "item": one}, ensure_ascii=False) + "\n")
                            audit["casos_comparados"] += 1
                            k13, k14 = set(itens[0].keys()), set(one.keys())
                            if k13 == k14:
                                audit["mesmas_chaves"] += 1
                            for k in (k14 - k13):
                                audit["extras_1014"][k] += 1
                            for k in (k13 - k14):
                                audit["faltantes_1014"][k] += 1
                            if any(one.get(k) != itens[0].get(k) for k in (k13 & k14)):
                                audit["divergencia_valor"] += 1
                    except Exception:
                        pass
                if not tp:
                    break
                pg += 1
    f13.close()
    f14.close()

    saida = {"data": alvo, "n_casos": n_casos, "n_itens": n_itens,
             "matriz_por_ms_modalidade": {}, "por_obra_heuristica": {},
             "frequencia_campos": {}, "auditoria_10_13_x_10_14": {
                 "casos_comparados": audit["casos_comparados"],
                 "mesmas_chaves": audit["mesmas_chaves"],
                 "extras_1014": dict(audit["extras_1014"]),
                 "faltantes_1014": dict(audit["faltantes_1014"]),
                 "divergencia_valor": audit["divergencia_valor"]}}

    def pct(counter, n):
        return {st: {"n": counter[st], "pct": round(100 * counter[st] / n, 1) if n else 0}
                for st in ("VALUE", "NULL", "EMPTY", "ABSENT")}

    for bucket in sorted(total_bucket, key=lambda k: -total_bucket[k]):
        n = total_bucket[bucket]
        saida["matriz_por_ms_modalidade"][f"MS={bucket[0]}|mod={bucket[1]}"] = {
            "n_itens": n, "campos": {c: pct(matriz[bucket][c], n) for c in CAMPOS},
            "unidade_top": unidades[bucket].most_common(5)}
    for obra in (True, False):
        n = obra_total[obra]
        saida["por_obra_heuristica"][f"obra_heur={obra}"] = {
            "n_itens": n, "campos": {c: pct(obra_x[obra][c], n) for c in CAMPOS}}
    for c in CAMPOS:
        tot = sum(freq[c].values())
        saida["frequencia_campos"][c] = {
            "present_key_pct": round(100 * (tot - freq[c]["ABSENT"]) / tot, 1) if tot else 0,
            "non_null_pct": round(100 * freq[c]["VALUE"] / tot, 1) if tot else 0,
            "estados": dict(freq[c])}

    (SCR / "assinatura_matriz.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- stdout resumido ----
    print(f"\n=== ASSINATURA — {alvo} | casos={n_casos} itens={n_itens} ===")
    print(f"(raw: assinatura_1013.jsonl / assinatura_1014.jsonl / matriz: assinatura_matriz.json)\n")
    print("--- % VALUE (non_null) por campo, por bucket (MS,modalidadeId) ---")
    hdr = ["catalogoCodigoItem", "catalogo", "ncmNbsCodigo", "informacaoComplementar"]
    print(f"{'bucket':16} {'n':>4}  " + " ".join(f"{h[:13]:>13}" for h in hdr))
    for bucket in sorted(total_bucket, key=lambda k: -total_bucket[k]):
        n = total_bucket[bucket]
        row = " ".join(f"{round(100*matriz[bucket][h]['VALUE']/n,1) if n else 0:>12}%" for h in hdr)
        print(f"{f'{bucket[0]}|mod{bucket[1]}':16} {n:>4}  {row}")
    print("\n--- por heurística de obra (rótulo, não filtro) ---")
    for obra in (True, False):
        n = obra_total[obra]
        row = " ".join(f"{h.split('C')[0][:6]}={round(100*obra_x[obra][h]['VALUE']/n,1) if n else 0}%" for h in hdr)
        print(f"  obra_heur={obra} (n={n}): {row}")
    print("\n--- frequência de campos (present_key% / non_null%) ---")
    for c in CAMPOS:
        fc = saida["frequencia_campos"][c]
        print(f"  {c:24} present_key={fc['present_key_pct']:>5}%  non_null={fc['non_null_pct']:>5}%")
    print("\n--- auditoria 10.13 x 10.14 ---")
    a = saida["auditoria_10_13_x_10_14"]
    print(f"  casos={a['casos_comparados']} mesmas_chaves={a['mesmas_chaves']} "
          f"extras_1014={a['extras_1014']} divergencia_valor={a['divergencia_valor']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-08-20")
    ap.add_argument("--por-modalidade", type=int, default=8)
    ap.add_argument("--modalidades", default="4,5,6,7")
    ap.add_argument("--piso", type=float, default=10_000_000)
    a = ap.parse_args()
    rodar(a.date.replace("-", ""), a.por_modalidade,
          [int(x) for x in a.modalidades.split(",") if x.strip()], Decimal(str(a.piso)))


if __name__ == "__main__":
    main()
