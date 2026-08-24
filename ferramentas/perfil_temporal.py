#!/usr/bin/env python3
"""Perfil Temporal de Integração EVT-007 por ORIGEM (estudo experimental).

Pergunta: para cada ORIGEM, quando um EVT-007 aparece no PNCP, qual a distribuição
empírica de idade da homologação (delta = dataInclusao - dataResultado)?

Correções metodológicas (Rodrigo, 2026-08-25):
  - usuarioNome NÃO é sempre "plataforma" (às vezes é sistema do órgão) -> guardamos
    como `source_sender_raw` (+ source_host do linkSistemaOrigem + source_type heurístico).
  - delta é DERIVADO -> preservamos SEMPRE as duas datas brutas.
  - Régua de confiança por n E presença em >1 dia (não chamar n=1 de padrão).

Radar prospectivo D-contra-D: para cada dia, coleta contratações atualizadas nele,
abre itens/resultados SEM filtrar dataResultado, e considera resultados que ENTRARAM
no PNCP naquele dia (dataInclusao.date == dia). Acumula vários dias numa base.

Saída:
  .scratch/latency_observations.jsonl — 1 observação por linha (evidência, carga p/ sidecar)
  .scratch/perfil_temporal.json       — matrizes cruzadas + régua de confiança
  stdout — resumo
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "coletor"))
from pncp.cliente import CONSULTA, INTEGRACAO, ClientePNCP  # noqa: E402

SCR = Path(__file__).resolve().parents[1] / ".scratch"
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]

# heurística de origem (transparente, ajustável) — integradores privados conhecidos
PLATAFORMAS_PRIVADAS = ["licitanet", "bbmnet", "bnc", "bll", "portaldecompraspublicas",
                        "comprasbr", "licitardigital", "publinexo", "bionexo", "compras public",
                        "peintegrado", "e-nortesolucoes", "compraspublicas", "licitar digital",
                        "portal de compras", "bolsa", "cidadecompras", "compramais", "abase",
                        "srp", "novo bbmnet", "startgov", "sigcompras", "efácil"]


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v)) if v not in (None, "") else Decimal(0)
    except Exception:
        return Decimal(0)


def _d(s):
    try:
        return date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


def _dt(s):
    try:
        return datetime.fromisoformat(str(s)[:19]) if s else None
    except ValueError:
        return None


def bucket_delta(delta: int) -> str:
    if delta < 0:
        return "ANOMALIA"
    return {0: "D0", 1: "D1", 2: "D2"}.get(delta, "D3_PLUS")


def source_host(link: str | None) -> str:
    if not link:
        return ""
    try:
        return (urlparse(link).hostname or "").lower()
    except Exception:
        return ""


def source_type(sender: str, host: str) -> str:
    s = (sender or "").lower()
    if any(p in s for p in PLATAFORMAS_PRIVADAS) or (host and not host.endswith(".gov.br")):
        return "PRIVATE_PLATFORM"
    if host.endswith(".gov.br") or "compras.gov" in s or "gov.br" in s:
        return "ORG_SYSTEM"
    return "UNKNOWN"


def confianca(n: int) -> str:
    if n < 10:
        return "INDICIO"
    if n < 50:
        return "PRELIMINAR"
    if n < 200:
        return "PADRAO_PROVAVEL"
    return "PADRAO_FORTE"


def rodar(alvos: list[str], por_modalidade: int, modalidades: list[int], piso: Decimal, run_id: str):
    SCR.mkdir(exist_ok=True)
    fh = (SCR / "latency_observations.jsonl").open("w", encoding="utf-8")
    obs = []  # observações (para matrizes)

    with ClientePNCP() as cli:
        for alvo_str in alvos:
            alvo = _d(alvo_str)
            for mod in modalidades:
                achei, pg, tp = 0, 1, None
                while (tp is None or pg <= tp) and achei < por_modalidade:
                    q = urllib.parse.urlencode({"dataInicial": alvo_str, "dataFinal": alvo_str,
                                                "codigoModalidadeContratacao": mod,
                                                "pagina": pg, "tamanhoPagina": 50})
                    try:
                        p = cli.get(f"{CONSULTA}/v1/contratacoes/atualizacao?{q}", endpoint="descoberta")
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
                        sender = (r.get("usuarioNome") or "?").strip()
                        host = source_host(r.get("linkSistemaOrigem"))
                        stype = source_type(sender, host)
                        uni = r.get("unidadeOrgao") or {}
                        base = f"{INTEGRACAO}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
                        try:
                            itens = cli.get(f"{base}/itens", endpoint="10.13")
                        except Exception:
                            continue
                        if not isinstance(itens, list):
                            itens = itens.get("itens") if isinstance(itens, dict) else []
                        achei += 1
                        for it in (itens or []):
                            if not it.get("temResultado"):
                                continue
                            n = it.get("numeroItem")
                            try:
                                res = cli.get(f"{base}/itens/{n}/resultados", endpoint="10.17")
                            except Exception:
                                continue
                            if not isinstance(res, list):
                                res = res.get("listaResultados") if isinstance(res, dict) else []
                            for rr in (res or []):
                                di, dr = _dt(rr.get("dataInclusao")), _d(rr.get("dataResultado"))
                                if not di or not dr or di.date() != alvo:
                                    continue
                                delta = (di.date() - dr).days
                                o = {
                                    "result_key": f"{r.get('numeroControlePNCP')}|{n}|{rr.get('sequencialResultado')}",
                                    "dia_coleta": alvo.isoformat(),
                                    "source_sender_raw": sender, "source_host": host, "source_type": stype,
                                    "org_cnpj": cnpj, "org_name": org.get("razaoSocial"),
                                    "uf": uni.get("ufSigla"), "modalidade_id": mod,
                                    "modalidade": r.get("modalidadeNome"),
                                    "data_resultado": rr.get("dataResultado"),
                                    "data_inclusao": rr.get("dataInclusao"),
                                    "delta_days": delta, "delta_bucket": bucket_delta(delta),
                                    "inclusion_hour": di.hour, "run_id": run_id,
                                }
                                obs.append(o)
                                fh.write(json.dumps(o, ensure_ascii=False) + "\n")
                    if not tp:
                        break
                    pg += 1
    fh.close()
    return obs


def relatorio(obs: list[dict]):
    por_src = defaultdict(Counter)
    dias_por_src = defaultdict(set)
    hora_por_src = defaultdict(Counter)
    stype_por_src = {}
    src_x_dia = defaultdict(lambda: Counter())
    src_x_org = defaultdict(lambda: Counter())
    src_x_mod = defaultdict(lambda: Counter())
    for o in obs:
        s = o["source_sender_raw"]
        por_src[s][o["delta_bucket"]] += 1
        por_src[s]["n"] += 1
        dias_por_src[s].add(o["dia_coleta"])
        hora_por_src[s][o["inclusion_hour"]] += 1
        stype_por_src[s] = o["source_type"]
        src_x_dia[s][o["dia_coleta"]] += 1
        src_x_org[s][o["org_name"]] += 1
        src_x_mod[s][o["modalidade"]] += 1

    saida = {"n_observacoes": len(obs), "por_origem": {}}
    for s in sorted(por_src, key=lambda k: -por_src[k]["n"]):
        c = por_src[s]
        n = c["n"]
        saida["por_origem"][s] = {
            "source_type": stype_por_src[s], "n": n, "dias_distintos": len(dias_por_src[s]),
            "confianca": confianca(n), "multi_dia": len(dias_por_src[s]) > 1,
            "D0": c["D0"], "D1": c["D1"], "D2": c["D2"], "D3_PLUS": c["D3_PLUS"], "ANOMALIA": c["ANOMALIA"],
            "pct_D0": round(100 * c["D0"] / n, 1) if n else 0,
            "hora_top": hora_por_src[s].most_common(4),
            "por_dia": dict(src_x_dia[s]), "por_modalidade": dict(src_x_mod[s]),
            "top_orgaos": src_x_org[s].most_common(3),
        }
    (SCR / "perfil_temporal.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== PERFIL TEMPORAL — {len(obs)} observações ===")
    print(f"{'source_sender_raw':30} {'tipo':16} {'n':>4} {'dias':>4} {'%D0':>6} {'D1':>4} {'D2':>4} {'D3+':>4} {'conf':>16}")
    for s, i in saida["por_origem"].items():
        print(f"{s[:30]:30} {i['source_type']:16} {i['n']:>4} {i['dias_distintos']:>4} "
              f"{i['pct_D0']:>5}% {i['D1']:>4} {i['D2']:>4} {i['D3_PLUS']:>4} {i['confianca']:>16}"
              + ("" if i["multi_dia"] else "  [1dia]"))
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", default="2026-08-17,2026-08-18,2026-08-19,2026-08-20,2026-08-21")
    ap.add_argument("--por-modalidade", type=int, default=12)
    ap.add_argument("--modalidades", default="4,5,6,7")
    ap.add_argument("--piso", type=float, default=10_000_000)
    ap.add_argument("--run-id", default="run_local")
    a = ap.parse_args()
    alvos = [d.strip().replace("-", "") for d in a.dates.split(",") if d.strip()]
    obs = rodar(alvos, a.por_modalidade,
                [int(x) for x in a.modalidades.split(",") if x.strip()], Decimal(str(a.piso)), a.run_id)
    relatorio(obs)


if __name__ == "__main__":
    main()
