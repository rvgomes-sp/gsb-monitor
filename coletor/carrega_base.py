#!/usr/bin/env python3
"""Gera SQL de carga para licitacoes.contratacoes_raw a partir do JSON cru.

Emite arquivos .sql em lotes (multi-row INSERT ... ON CONFLICT DO UPDATE) que
serão executados na base via conector Supabase. Não conecta direto (o DSN não
está neste ambiente); separa a geração (Python) da execução (conector).

Uso:
  python coletor/carrega_base.py saidas/raw_20260821.json --piso 10000000 --lote 60
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


COMPACTO = False   # setado no main(): base compacta (sem raw/links/objeto longo) p/ carga via conector
OBJ_LIMITE = 400


def _f(v):
    try:
        return float(v) if v not in (None, "") else None
    except Exception:
        return None


def _s(v) -> str:
    """literal de texto seguro (aspas simples dobradas); NULL se vazio."""
    if v is None or v == "":
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def _num(v) -> str:
    f = _f(v)
    return "NULL" if f is None else repr(f)


def _int(v) -> str:
    try:
        return str(int(v)) if v not in (None, "") else "NULL"
    except Exception:
        return "NULL"


def _bool(v) -> str:
    return "true" if v is True else ("false" if v is False else "NULL")


def _ts(v) -> str:
    return _s(v)  # timestamptz aceita ISO string


def linha_values(data_ref: str, r: dict) -> str:
    org = r.get("orgaoEntidade") or {}
    uni = r.get("unidadeOrgao") or {}
    # raw MÍNIMO p/ a base agora (cru integral em disco; backfill do jsonb completo via psycopg).
    # guarda só o que a análise pode querer e não virou coluna própria.
    r_slim = {
        "numeroControlePNCP": r.get("numeroControlePNCP"),
        "modoDisputaNome": r.get("modoDisputaNome"),
        "tipoInstrumentoConvocatorioNome": r.get("tipoInstrumentoConvocatorioNome"),
        "fontesOrcamentarias": [f.get("nome") for f in (r.get("fontesOrcamentarias") or [])],
        "linkProcessoEletronico": r.get("linkProcessoEletronico"),
    }
    if COMPACTO:
        jsonb_lit = "'{}'::jsonb"        # cru vai por psycopg depois; base compacta agora
    else:
        js = json.dumps(r_slim, ensure_ascii=False)
        tag = "$jb$"
        if tag in js:
            js = js.replace("$", "")
        jsonb_lit = f"{tag}{js}{tag}::jsonb"
    cols = [
        _s(data_ref),
        _s(r.get("numeroControlePNCP")),
        _int(r.get("modalidadeId")),
        _s(r.get("modalidadeNome")),
        _s(r.get("situacaoCompraNome")),
        _num(r.get("valorTotalEstimado")),
        _num(r.get("valorTotalHomologado")),
        _s((r.get("objetoCompra") or "")[:OBJ_LIMITE]),  # cru integral em disco; base leva o essencial
        _int(r.get("anoCompra")),
        _int(r.get("sequencialCompra")),
        _s(org.get("cnpj")),
        _s(org.get("razaoSocial")),
        _s(uni.get("ufSigla") or uni.get("ufNome")),
        _s(uni.get("municipioNome") or uni.get("nomeUnidade")),
        _s(r.get("usuarioNome")),
        _bool(r.get("srp")),
        _ts(r.get("dataInclusao")),
        _ts(r.get("dataAtualizacaoGlobal")),
        _ts(r.get("dataAberturaProposta")),
        "NULL" if COMPACTO else _s(r.get("linkSistemaOrigem")),
        jsonb_lit,
    ]
    return "(" + ",".join(cols) + ")"


COLUNAS = ("data_ref,numero_controle_pncp,modalidade_id,modalidade_nome,situacao_nome,"
           "valor_estimado,valor_homologado,objeto,ano_compra,sequencial_compra,"
           "orgao_cnpj,orgao_razao,uf,municipio,usuario_nome,srp,data_inclusao,"
           "data_atualizacao_global,data_abertura_proposta,link_sistema_origem,raw")

CONFLICT = ("""ON CONFLICT (data_ref, numero_controle_pncp) DO UPDATE SET
  situacao_nome=excluded.situacao_nome, valor_estimado=excluded.valor_estimado,
  valor_homologado=excluded.valor_homologado, data_atualizacao_global=excluded.data_atualizacao_global,
  raw=excluded.raw, ingerido_em=now()""")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo")
    ap.add_argument("--piso", type=float, default=0.0, help="filtra valorTotalEstimado>=piso (0=todos)")
    ap.add_argument("--lote", type=int, default=60)
    ap.add_argument("--outdir", default=".scratch/carga")
    ap.add_argument("--compacto", action="store_true", help="sem raw/links, objeto curto (carga via conector)")
    ap.add_argument("--obj-limite", type=int, default=400)
    a = ap.parse_args()
    global COMPACTO, OBJ_LIMITE
    COMPACTO, OBJ_LIMITE = a.compacto, a.obj_limite

    d = json.loads(Path(a.arquivo).read_text(encoding="utf-8"))
    data_ref = f"{d['data'][:4]}-{d['data'][4:6]}-{d['data'][6:]}"
    linhas = d.get("linhas") or []
    if a.piso:
        linhas = [r for r in linhas if (_f(r.get("valorTotalEstimado")) or 0) >= a.piso]

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    n_arq = 0
    for i in range(0, len(linhas), a.lote):
        bloco = linhas[i:i + a.lote]
        vals = ",\n".join(linha_values(data_ref, r) for r in bloco)
        sql = f"INSERT INTO licitacoes.contratacoes_raw ({COLUNAS}) VALUES\n{vals}\n{CONFLICT};"
        (outdir / f"carga_{d['data']}_{n_arq:03d}.sql").write_text(sql, encoding="utf-8")
        n_arq += 1
    print(f"CARGA gerada: {len(linhas)} linhas (piso={a.piso:,.0f}) -> {n_arq} arquivos em {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
