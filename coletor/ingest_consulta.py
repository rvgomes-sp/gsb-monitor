#!/usr/bin/env python3
"""Camada 1 — INGESTÃO BARATA (só Consulta, superfície saudável).

Varre mod 4-7 em /contratacoes/atualizacao para um dia e guarda TODAS as linhas
cruas (sem filtrar). Não toca a Integração. A análise/classificação acontece
depois, na NOSSA base (SQL) — não dentro da API.

Uso:
  python coletor/ingest_consulta.py 20260821 --out saidas/raw_20260821.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pncp.cliente import ClientePNCP, CONSULTA  # noqa: E402

MODS = [4, 5, 6, 7]


def puxar(data: str, mods: list[int]) -> list[dict]:
    linhas: list[dict] = []
    with ClientePNCP(pausa_base=1.2, jitter=0.8, timeout=30) as c:
        for mod in mods:
            pagina, total = 1, None
            while total is None or pagina <= total:
                q = urlencode({"dataInicial": data, "dataFinal": data,
                               "codigoModalidadeContratacao": mod,
                               "pagina": pagina, "tamanhoPagina": 50})
                try:
                    p = c.get(f"{CONSULTA}/v1/contratacoes/atualizacao?{q}", endpoint="ingest")
                except Exception as e:
                    print(f"  [mod {mod}] pág {pagina} FALHOU {e}", file=sys.stderr, flush=True)
                    pagina += 1
                    continue
                if total is None:
                    total = int(p.get("totalPaginas") or 0)
                    print(f"  [mod {mod}] {total} páginas", file=sys.stderr, flush=True)
                for r in (p.get("data") or []):
                    r["_modalidade_consulta"] = mod
                    linhas.append(r)
                if not total:
                    break
                if pagina % 10 == 0:
                    print(f"  [mod {mod}] {pagina}/{total} | acumulado={len(linhas)}",
                          file=sys.stderr, flush=True)
                pagina += 1
    return linhas


def main() -> int:
    raise RuntimeError("LEGACY_EVT007_DISABLED_GATE_B: use python -m evt007; operational promotion is blocked")
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="AAAAMMDD")
    ap.add_argument("--modalities", default="")
    ap.add_argument("--out")
    a = ap.parse_args()
    mods = [int(x) for x in a.modalities.split(",") if x.strip()] if a.modalities else MODS
    linhas = puxar(a.data, mods)
    out = Path(a.out or f"saidas/raw_{a.data}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"data": a.data, "total": len(linhas), "linhas": linhas},
                              ensure_ascii=False), encoding="utf-8")
    print(f"INGEST OK | {a.data} | {len(linhas)} contratações | {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
