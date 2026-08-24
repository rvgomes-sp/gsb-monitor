#!/usr/bin/env python3
"""Perfil Temporal de Integração EVT-007 por Plataforma (estudo, não operação).

Pergunta (Rodrigo, 2026-08-25): tudo que o PNCP entrega como novo HOJE (D)
corresponde a homologações de hoje? Se não, qual plataforma entrega atrasado e
quanto? Radar PROSPECTIVO: coleta o que entrou no PNCP em D e mede a idade.

Método (D contra D):
  1. Descobre contratações atualizadas em D (Consulta /atualizacao).
  2. Abre itens (10.13) e resultados (10.17) SEM filtrar dataResultado==D.
  3. Considera resultados que ENTRARAM no PNCP em D (dataInclusao.date == D)
     — proxy de "novo hoje".
  4. delta_dias = dataInclusao.date - dataResultado.date  (idade da oportunidade)
  5. Agrupa por plataforma (usuarioNome) → D0/D1/D2/D3+ + hora de inclusão.

NÃO julga a plataforma; MEDE. Classificação operacional:
  DELTA_0=IMEDIATO  DELTA_1=ATRASO_1D  DELTA_2_PLUS=ATRASADO  DELTA_NEG=ANOMALIA

Saída:
  .scratch/perfil_temporal.jsonl  — 1 resultado por linha (evidência para auditoria)
  .scratch/perfil_temporal.json   — matriz por plataforma + histograma de hora
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "coletor"))
from pncp.cliente import CONSULTA, INTEGRACAO, ClientePNCP  # noqa: E402

SCR = Path(__file__).resolve().parents[1] / ".scratch"
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v)) if v not in (None, "") else Decimal(0)
    except Exception:
        return Decimal(0)


def _d(s) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s)[:19])
    except ValueError:
        return None


def classe_delta(delta: int) -> str:
    if delta < 0:
        return "ANOMALIA"
    if delta == 0:
        return "IMEDIATO"
    if delta == 1:
        return "ATRASO_1D"
    return "ATRASADO"


def rodar(alvo_str: str, por_modalidade: int, modalidades: list[int], piso: Decimal):
    SCR.mkdir(exist_ok=True)
    alvo = date.fromisoformat(f"{alvo_str[:4]}-{alvo_str[4:6]}-{alvo_str[6:]}")
    fh = (SCR / "perfil_temporal.jsonl").open("w", encoding="utf-8")

    plat = defaultdict(lambda: Counter())        # plataforma -> {D0,D1,D2,D3+,ANOM}
    plat_total = Counter()
    plat_hora = defaultdict(Counter)             # plataforma -> hora de inclusao
    n_result = n_casos = 0

    with ClientePNCP() as cli:
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
                    plataforma = (r.get("usuarioNome") or "?").strip()
                    uni = r.get("unidadeOrgao") or {}
                    base = f"{INTEGRACAO}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
                    try:
                        itens = cli.get(f"{base}/itens", endpoint="10.13")
                    except Exception:
                        continue
                    if not isinstance(itens, list):
                        itens = itens.get("itens") if isinstance(itens, dict) else []
                    achei += 1
                    n_casos += 1
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
                            di = _dt(rr.get("dataInclusao"))
                            dr = _d(rr.get("dataResultado"))
                            # SÓ o que entrou HOJE no PNCP (novo hoje)
                            if not di or di.date() != alvo:
                                continue
                            if not dr:
                                continue
                            delta = (di.date() - dr).days
                            cls = classe_delta(delta)
                            n_result += 1
                            plat[plataforma][cls] += 1
                            plat_total[plataforma] += 1
                            plat_hora[plataforma][di.hour] += 1
                            fh.write(json.dumps({
                                "plataforma": plataforma, "orgao": org.get("razaoSocial"),
                                "uf": uni.get("ufSigla"), "modalidadeId": mod,
                                "modalidade": r.get("modalidadeNome"),
                                "numero_controle_pncp": r.get("numeroControlePNCP"),
                                "numero_item": n, "seq_resultado": rr.get("sequencialResultado"),
                                "data_resultado": rr.get("dataResultado"),
                                "data_inclusao": rr.get("dataInclusao"),
                                "delta_dias": delta, "classe": cls,
                                "dia_semana_resultado": DIAS[dr.weekday()],
                                "dia_semana_inclusao": DIAS[di.weekday()],
                                "hora_inclusao": di.hour,
                                "link_sistema_origem": r.get("linkSistemaOrigem"),
                            }, ensure_ascii=False) + "\n")
                if not tp:
                    break
                pg += 1
    fh.close()

    saida = {"data": alvo.isoformat(), "n_casos": n_casos, "n_resultados_novos_hoje": n_result,
             "por_plataforma": {}}
    for pl in sorted(plat_total, key=lambda k: -plat_total[k]):
        n = plat_total[pl]
        c = plat[pl]
        saida["por_plataforma"][pl] = {
            "n": n,
            "IMEDIATO_D0": c["IMEDIATO"], "ATRASO_1D": c["ATRASO_1D"],
            "ATRASADO_D2+": c["ATRASADO"], "ANOMALIA": c["ANOMALIA"],
            "pct_D0": round(100 * c["IMEDIATO"] / n, 1) if n else 0,
            "hora_inclusao_top": plat_hora[pl].most_common(4),
        }
    (SCR / "perfil_temporal.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== PERFIL TEMPORAL — D={alvo.isoformat()} | casos={n_casos} | resultados novos hoje={n_result} ===")
    print(f"(raw: perfil_temporal.jsonl)\n")
    print(f"{'plataforma':32} {'n':>5} {'D0':>6} {'D1':>5} {'D2+':>5} {'ANOM':>5} {'%D0':>6}  hora_incl_top")
    for pl, info in saida["por_plataforma"].items():
        print(f"{pl[:32]:32} {info['n']:>5} {info['IMEDIATO_D0']:>6} {info['ATRASO_1D']:>5} "
              f"{info['ATRASADO_D2+']:>5} {info['ANOMALIA']:>5} {info['pct_D0']:>5}%  {info['hora_inclusao_top']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-08-22")
    ap.add_argument("--por-modalidade", type=int, default=12)
    ap.add_argument("--modalidades", default="4,5,6,7")
    ap.add_argument("--piso", type=float, default=10_000_000)
    a = ap.parse_args()
    rodar(a.date.replace("-", ""), a.por_modalidade,
          [int(x) for x in a.modalidades.split(",") if x.strip()], Decimal(str(a.piso)))


if __name__ == "__main__":
    main()
