#!/usr/bin/env python3
"""Coletor de AMOSTRA — Compras.gov Dados Abertos (fonte de teste enquanto PNCP está fora).

Puxa resultados de itens homologados por dataResultado e grava em gsb.evt007_results,
no MESMO formato do coletor PNCP (mesma tabela, mesmo motor v3 roda em cima).
Fonte marcada como COMPRASGOV_DADOS_ABERTOS para não confundir com a coleta PNCP.

Uso (amostra controlada):
  python evt007_collect_comprasgov.py --date 2026-07-23 --max-pages 3
  python evt007_collect_comprasgov.py --date 2026-07-23 --max-pages 3 --dry-run
"""
from __future__ import annotations
import argparse, json, os, re, time, urllib.request
from datetime import date
from hashlib import sha256

BASE=("https://dadosabertos.compras.gov.br/modulo-contratacoes/"
      "3_consultarResultadoItensContratacoes_PNCP_14133")
SOURCE="COMPRASGOV_DADOS_ABERTOS"

def is_cnpj_aln(s):
    s=(s or "").strip().upper()
    return bool(re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", s))
def is_cpf(s):
    d="".join(c for c in (s or "") if c.isdigit())
    return len(d)==11 and not is_cnpj_aln((s or "").strip().upper())

def _get(url, tries=6, to=60):
    last=None
    for a in range(1,tries+1):
        try:
            req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"GSB/1.0"})
            with urllib.request.urlopen(req,timeout=to) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as e:
            last=e; time.sleep(min(30,3*a))
    raise RuntimeError(f"falha: {last}")

def _rkey(*p): return sha256("|".join(str(x) for x in p).encode()).hexdigest()

def classify_ni(ni):
    """Classifica o identificador do fornecedor."""
    s=(ni or "").strip().upper()
    d="".join(c for c in s if c.isdigit())
    if is_cnpj_aln(s): return "CNPJ"
    if len(d)==11: return "CPF"           # pessoa física
    if len(d)==14 and not is_cnpj_aln(s): return "CNPJ_INVALIDO"
    return "ESTRANGEIRO_OU_INVALIDO"       # ex.: entidade estrangeira sem CNPJ BR

def map_row(r):
    ni=r.get("niFornecedor")
    tipo=classify_ni(ni)
    if tipo!="CNPJ":   # só CNPJ (numérico ou alfanumérico) interessa (decisão Vazquez)
        return None
    case_id=r.get("numeroControlePNCPCompra") or r.get("idContratacaoPNCP")
    item=r.get("numeroItemPncp")
    seqr=r.get("sequencialResultado")
    return {
        "result_key": _rkey(case_id,item,seqr,r.get("niFornecedor")),
        "case_id": case_id,
        "item_number": int(item) if str(item).isdigit() else None,
        "result_sequence": int(seqr) if str(seqr).isdigit() else None,
        "supplier_identifier": (ni or "").strip().upper(),
        "supplier_name": r.get("nomeRazaoSocialFornecedor"),
        "supplier_size_id": r.get("porteFornecedorId"),
        "supplier_size_name": r.get("porteFornecedorNome"),
        "legal_nature_id": r.get("naturezaJuridicaId"),
        "legal_nature_name": r.get("naturezaJuridicaNome"),
        "result_date": (r.get("dataResultadoPncp") or "")[:10] or None,
        "inclusion_at": r.get("dataInclusaoPncp"),
        "update_at": r.get("dataAtualizacaoPncp"),
        "cancellation_at": r.get("dataCancelamentoPncp") if r.get("dataCancelamentoPncp")!="None" else None,
        "homologated_quantity": r.get("quantidadeHomologada"),
        "homologated_unit_value": r.get("valorUnitarioHomologado"),
        "homologated_total_value": r.get("valorTotalHomologado"),
        "platform": "Compras.gov.br",
        "platform_delta_status": "VERIFICADO",
        "source_name": SOURCE,
        "source_payload": json.dumps(r, ensure_ascii=False, sort_keys=True),
    }

def run(target, max_pages, dry_run):
    d=target.isoformat()
    collected=[]; page=1; total=None
    while True:
        url=f"{BASE}?dataResultadoPncpInicial={d}&dataResultadoPncpFinal={d}&pagina={page}&tamanhoPagina=500"
        payload=_get(url)
        rows=payload.get("resultado") or []
        total=payload.get("totalRegistros")
        for r in rows:
            m=map_row(r)
            if m: collected.append(m)
        if page>=int(payload.get("totalPaginas") or 1) or (max_pages and page>=max_pages):
            break
        page+=1
    report={"status":"COMPLETE","source":SOURCE,"date":d,
            "total_disponivel":total,"paginas_lidas":page,
            "linhas_coletadas":len(collected),"dry_run":dry_run,
            "amostra":collected[:2]}
    if not dry_run:
        import psycopg
        url=os.environ.get("DATABASE_URL","")
        if not url: raise SystemExit("DATABASE_URL nao definida")
        cols=["result_key","case_id","item_number","result_sequence","supplier_identifier",
              "supplier_name","supplier_size_id","supplier_size_name","legal_nature_id",
              "legal_nature_name","result_date","inclusion_at","update_at","cancellation_at",
              "homologated_quantity","homologated_unit_value","homologated_total_value",
              "platform","platform_delta_status","source_name","source_payload"]
        ph=",".join(f"%({c})s" for c in cols)
        with psycopg.connect(url) as conn, conn.transaction():
            for m in collected:
                conn.execute(f"""INSERT INTO gsb.evt007_results({','.join(cols)})
                    VALUES({ph}) ON CONFLICT(result_key) DO UPDATE SET
                    update_at=excluded.update_at, source_payload=excluded.source_payload,
                    platform=excluded.platform, platform_delta_status=excluded.platform_delta_status
                """, {**m, "source_payload": m["source_payload"]})
        report["gravado_no_banco"]=len(collected)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    p.add_argument("--max-pages", type=int, default=3)
    p.add_argument("--dry-run", action="store_true")
    a=p.parse_args()
    rep=run(date.fromisoformat(a.date), a.max_pages, a.dry_run)
    print(json.dumps(rep, ensure_ascii=False, indent=2, default=str))
    return 0
if __name__=="__main__": raise SystemExit(main())
