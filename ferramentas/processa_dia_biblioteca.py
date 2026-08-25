#!/usr/bin/env python3
"""Processa um dia cru -> biblioteca codificada (máquina). Ingestão barata, sem drill.

Uso: python ferramentas/processa_dia_biblioteca.py saidas/raw_20260824.json 2026-08-24
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "monitor"))
from classificador_biblioteca import classificar  # noqa: E402
from inferencia import reduzir_objeto  # noqa: E402

PISO = 10_000_000
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _c(s):
    return _CTRL.sub(" ", s) if isinstance(s, str) else s


def main() -> int:
    arq, data_ref = sys.argv[1], sys.argv[2]
    d = json.loads(Path(arq).read_text(encoding="utf-8"))
    linhas = [r for r in d["linhas"] if float(r.get("valorTotalEstimado") or 0) >= PISO]

    cols = ["data_referencia", "controle_pncp", "uf", "orgao", "modalidade_id",
            "valor_estimado", "situacao", "objeto", "descricao_curta",
            "familia_inferida", "garantia_hipotese", "motivo_hipotese",
            "garantia_label_raw", "garantia_grau", "nota", "fonte",
            "codigo_objeto", "grupo_objeto", "garantia_grau_fino", "garantia_codigo",
            "garantia_status", "garantia_prioridade", "id_biblioteca", "rotulado_por"]
    data = []
    for r in linhas:
        obj = re.sub(r"\s+", " ", (r.get("objetoCompra") or "")).strip()
        m = classificar(obj)
        data.append([
            data_ref, r.get("numeroControlePNCP"), (r.get("unidadeOrgao") or {}).get("ufSigla"),
            _c((r.get("orgaoEntidade") or {}).get("razaoSocial")), r.get("modalidadeId"),
            float(r.get("valorTotalEstimado") or 0), r.get("situacaoCompraNome"),
            _c(obj), _c(reduzir_objeto(obj, 80)),
            m["familia"], m["garantia_grau"], "auto (regras Rodrigo)",
            None, m["garantia_grau"], None, f"ingest_{data_ref.replace('-','')}",
            m["codigo_objeto"], m["grupo"], m["garantia_grau"], m["garantia_codigo"],
            m["garantia_status"], m["garantia_prioridade"], m["id_biblioteca"], "maquina",
        ])

    # carga
    url = None
    for l in open("monitor-vip/.env.local", encoding="utf-8"):
        if l.strip().startswith("DATABASE_URL"):
            url = l.split("=", 1)[1].strip().strip('"').strip("'"); break
    if "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    import psycopg
    ph = "(" + ",".join(["%s"] * len(cols)) + ")"
    with psycopg.connect(url, connect_timeout=20) as con:
        with con.cursor() as cur:
            cur.execute("delete from gsb.biblioteca_objetos where data_referencia=%s and rotulado_por='maquina'", (data_ref,))
            cur.executemany("insert into gsb.biblioteca_objetos (" + ",".join(cols) + ") values " + ph, data)
            con.commit()
            cur.execute("""select grupo_objeto, count(*), to_char(sum(valor_estimado)/1e6,'FM999G990D0')||' MM'
                           from gsb.biblioteca_objetos where data_referencia=%s and rotulado_por='maquina'
                           group by 1 order by 2 desc""", (data_ref,))
            print(f"gravados {len(data)} objetos (maquina) | data={data_ref}")
            for row in cur.fetchall():
                print("  ", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
