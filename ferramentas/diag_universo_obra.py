#!/usr/bin/env python3
"""Diagnóstico do UNIVERSO de descoberta (só Consulta — superfície saudável).

Pergunta central (checkpoint 2026-08-24): quantas contratações mod 4-7 são
'tocadas' num dia, e como se distribuem por situação e por valor ESTIMADO vs
HOMOLOGADO? Testa a hipótese de que filtrar por valorTotalHomologado>=piso na
descoberta derruba a maioria das obras (campo derivado, quase sempre nulo).

Não faz drill de Integração. Não classifica obra (isso é subproduto). Só conta.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "coletor"))
from pncp.cliente import ClientePNCP, CONSULTA  # noqa: E402

PISO = 10_000_000
MODS = [4, 5, 6, 7]


def _f(v):
    try:
        return float(v) if v not in (None, "") else None
    except Exception:
        return None


def rodar(data: str):
    tot = Counter()
    sit = Counter()               # situacaoCompraNome (nível contratação)
    est_ge = Counter()            # estimado>=piso por modalidade
    hom_ge = Counter()            # homologado>=piso por modalidade
    hom_nulo = Counter()          # homologado nulo por modalidade
    est_ge_hom_nulo = 0           # estimado>=piso E homologado nulo  <-- vazamento
    est_ge_sit = Counter()        # situação dos estimado>=piso
    amostra_vazamento = []
    with ClientePNCP(pausa_base=1.2, jitter=0.8, timeout=30) as c:
        for mod in MODS:
            pagina, total_paginas = 1, None
            while total_paginas is None or pagina <= total_paginas:
                q = urlencode({"dataInicial": data, "dataFinal": data,
                               "codigoModalidadeContratacao": mod,
                               "pagina": pagina, "tamanhoPagina": 50})
                try:
                    p = c.get(f"{CONSULTA}/v1/contratacoes/atualizacao?{q}", endpoint="diag")
                except Exception as e:
                    print(f"  [mod {mod}] pág {pagina} falhou: {e}", file=sys.stderr)
                    pagina += 1
                    continue
                if total_paginas is None:
                    total_paginas = int(p.get("totalPaginas") or 0)
                    print(f"  [mod {mod}] {total_paginas} páginas", file=sys.stderr)
                for r in (p.get("data") or []):
                    tot[mod] += 1
                    sn = r.get("situacaoCompraNome") or "?"
                    sit[sn] += 1
                    est = _f(r.get("valorTotalEstimado"))
                    hom = _f(r.get("valorTotalHomologado"))
                    if hom is None:
                        hom_nulo[mod] += 1
                    if est is not None and est >= PISO:
                        est_ge[mod] += 1
                        est_ge_sit[sn] += 1
                        if hom is None:
                            est_ge_hom_nulo += 1
                            if len(amostra_vazamento) < 25:
                                amostra_vazamento.append({
                                    "numeroControlePNCP": r.get("numeroControlePNCP"),
                                    "modalidade": mod, "situacao": sn,
                                    "estimado": est, "objeto": (r.get("objetoCompra") or "")[:110],
                                })
                    if hom is not None and hom >= PISO:
                        hom_ge[mod] += 1
                if not total_paginas:
                    break
                pagina += 1
    return {
        "data": data, "total_por_mod": dict(tot), "total_geral": sum(tot.values()),
        "situacao_contratacao": dict(sit.most_common()),
        "estimado_ge_piso_por_mod": dict(est_ge), "estimado_ge_piso_total": sum(est_ge.values()),
        "homologado_ge_piso_por_mod": dict(hom_ge), "homologado_ge_piso_total": sum(hom_ge.values()),
        "homologado_nulo_por_mod": dict(hom_nulo), "homologado_nulo_total": sum(hom_nulo.values()),
        "VAZAMENTO_estimado_ge_piso_mas_homologado_nulo": est_ge_hom_nulo,
        "situacao_dos_estimado_ge_piso": dict(est_ge_sit.most_common()),
        "amostra_vazamento": amostra_vazamento,
    }


if __name__ == "__main__":
    data = sys.argv[1] if len(sys.argv) > 1 else "20260820"
    res = rodar(data)
    out = Path(__file__).resolve().parent.parent / "saidas" / f"diag_universo_{data}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("amostra_vazamento",)},
                     ensure_ascii=False, indent=1))
    print(f"\n[gravado em {out}]", file=sys.stderr)
