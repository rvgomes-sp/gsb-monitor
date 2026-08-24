#!/usr/bin/env python3
"""CLI do Motor de Coleta EVT-007 (PNCP).

Uso:
  python coletor/run_coleta_evt007.py                      # D-1 (BRT), dry-run, modalidades 4-7
  python coletor/run_coleta_evt007.py --date 2026-08-23
  python coletor/run_coleta_evt007.py --date 2026-08-23 --modalities 6 --out saida.json

Dry-run por padrão (não grava banco): mede volume. A persistência no Supabase
(licitacoes) entra com --gravar (exige DATABASE_URL no ambiente).
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
from pncp.familias import Classificador
from pncp.motor import MODALIDADES_PADRAO, Motor

BRT = timezone(timedelta(hours=-3))


def main() -> int:
    p = argparse.ArgumentParser(description="Coleta EVT-007 do PNCP (banco vivo de licitações)")
    p.add_argument("--date", help="AAAA-MM-DD; padrão D-1 (BRT)")
    p.add_argument("--modalities", default="", help="ex: 6 ou 4,5,6,7 (padrão 4,5,6,7)")
    p.add_argument("--piso", type=float, default=10_000_000, help="piso do homologado (padrão 10 MM)")
    p.add_argument("--max-itens", type=int, default=10)
    p.add_argument("--out", help="grava os casos coletados em JSON neste caminho")
    p.add_argument("--gravar", action="store_true", help="grava no Supabase (exige DATABASE_URL)")
    a = p.parse_args()

    alvo = date.fromisoformat(a.date) if a.date else (datetime.now(BRT).date() - timedelta(days=1))
    mods = [int(x) for x in a.modalities.split(",") if x.strip()] if a.modalities else MODALIDADES_PADRAO

    clf = Classificador()
    with ClientePNCP() as cli:
        motor = Motor(cli=cli, clf=clf, piso=Decimal(str(a.piso)), max_itens=a.max_itens)
        print(f"Coletando EVT-007 | D={alvo.isoformat()} | modalidades={mods} | piso={a.piso:,.0f}",
              file=sys.stderr, flush=True)
        rel, casos = motor.rodar(alvo, mods)

    if a.out:
        Path(a.out).write_text(json.dumps(casos, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(f"[casos gravados em {a.out}]", file=sys.stderr)

    if a.gravar:
        from pncp.banco import gravar
        n = gravar(casos, rel)
        print(f"[gravados {n} casos no Supabase]", file=sys.stderr)

    print(json.dumps(rel.__dict__, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
