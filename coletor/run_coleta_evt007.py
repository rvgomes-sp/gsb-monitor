#!/usr/bin/env python3
"""CLI do Motor de Coleta EVT-007 (produção) — obra fresca >= R$ 10 MM.

Uso:
  python coletor/run_coleta_evt007.py --date 2026-08-24
  python coletor/run_coleta_evt007.py --date 2026-08-24 --out saidas/oportunidades.json

Imprime o FUNIL de aceite (descobertas -> não-obra -> candidatas -> drill ->
homologadas>=10MM -> backfills -> oportunidades frescas) e detalha cada oportunidade.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pncp.cliente import ClientePNCP
from pncp.motor import MODALIDADES_PADRAO, Motor

BRT = timezone(timedelta(hours=-3))


def main() -> int:
    p = argparse.ArgumentParser(description="Coleta EVT-007 — obra fresca >= R$ 10 MM")
    p.add_argument("--date", help="AAAA-MM-DD; padrão D-1 (BRT)")
    p.add_argument("--modalities", default="", help="ex: 4,5,6,7 (padrão)")
    p.add_argument("--piso", type=float, default=10_000_000)
    p.add_argument("--max-pages", type=int, default=0, help="teto de páginas/modalidade (0=todas)")
    p.add_argument("--out", help="grava as oportunidades em JSON")
    a = p.parse_args()

    alvo = date.fromisoformat(a.date) if a.date else (datetime.now(BRT).date() - timedelta(days=1))
    mods = [int(x) for x in a.modalities.split(",") if x.strip()] if a.modalities else MODALIDADES_PADRAO

    with ClientePNCP() as cli:
        motor = Motor(cli=cli, piso=Decimal(str(a.piso)), max_pages=a.max_pages)
        print(f"Coletando EVT-007 obra | D={alvo.isoformat()} | mod={mods} | piso={a.piso:,.0f}",
              file=sys.stderr, flush=True)
        fun, ops = motor.rodar(alvo, mods)

    print("\n" + "=" * 56)
    print(f"FUNIL EVT-007 — D={fun.data_alvo}  (status {fun.status})")
    print("=" * 56)
    print(f"  Contratações MOD 4-7 (homologado >= piso):  {fun.descobertas:>5}")
    print(f"  Não-obras eliminadas após /itens:           {fun.nao_obra_eliminadas:>5}")
    print(f"  Candidatas a obra (FORTE/REVISAR):          {fun.candidatas_obra:>5}   {fun.por_classe_obra}")
    print(f"  Drill de resultados executado:              {fun.drill_executado:>5}")
    print(f"  Obras c/ evento homologado hoje:            {fun.obras_homologadas_piso:>5}")
    print(f"  Backfills eliminados (só delta grande):     {fun.backfills_eliminados:>5}")
    print(f"  OPORTUNIDADES FRESCAS entregues:            {fun.oportunidades_frescas:>5}")
    if fun.paginas_puladas:
        print(f"  (páginas instáveis puladas: {fun.paginas_puladas})")

    print("\n--- oportunidades ---")
    for o in ops:
        print(f"\n• {o['orgao']} ({o['uf']}) | {o['modalidade']} | R$ {float(Decimal(o['valor_homologado_consolidado']))/1e6:,.1f} MM")
        print(f"  {o['numero_controle_pncp']} | classe={o['classe_obra']} itens_obra={o['itens_obra']}")
        print(f"  objeto: {(o['objeto'] or '')[:90]}")
        venc = o['vencedores'][0] if o['vencedores'] else {}
        print(f"  vencedor: {venc.get('nome_fornecedor')} ({venc.get('ni_fornecedor')}) porte={venc.get('porte_nome')}")
        print(f"  FRESCOR: dataResultado={o['data_resultado']} dataInclusao={o['data_inclusao']} "
              f"Δcal={o['delta_calendar_days']} Δutil={o['delta_business_days']} [{o['freshness_class']}]")
        print(f"  origem: {o['source_sender_raw']} | {o['source_host']}")

    # rejeitados de FRONTEIRA (para caçar falso negativo — sem drill)
    fronteira = [r for r in fun.rejeitados if r.get("fronteira")]
    print(f"\n--- rejeitados de fronteira ({len(fronteira)} de {len(fun.rejeitados)} NAO_OBRA; materiais/compras óbvios omitidos) ---")
    for r in fronteira:
        print(f"  [{r['classe_objeto']}] {r['numero_controle_pncp']}")
        print(f"     objeto: {(r['objeto'] or '')[:100]}")
        print(f"     MS={r['materialOuServico']} unid={r['unidadeMedida']} | motivo: {r['motivo_exclusao']}")
    if fun.descartes_frescor:
        print(f"\n--- candidatas descartadas por frescor ({len(fun.descartes_frescor)}) ---")
        for d in fun.descartes_frescor:
            print(f"  {d['numero_controle_pncp']} | {d['motivo']} | {(d['objeto'] or '')[:70]}")

    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({"funil": fun.__dict__, "oportunidades": ops},
                                          ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(f"\n[gravado em {a.out}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
