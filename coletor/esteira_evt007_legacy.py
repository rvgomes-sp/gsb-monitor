#!/usr/bin/env python3
"""Esteira EVT-007 — garimpo do ouro. Homologado >= 10MM -> classifica -> drilla
O/C/S EXIGE -> explode por (vencedor x lote) -> lapida (85%, frescor, fonte) -> Supabase.

Só sobe LINHA COMPLETA (com vencedor + dataResultado). Grão = 1 vencedor x 1 lote
= 1 contrato = 1 garantia. Doutrina Rodrigo: PNCP draga, Supabase peneira, monitor recebe ouro.

Uso: python coletor/esteira_evt007.py saidas/raw_20260821.json 2026-08-21
"""
from __future__ import annotations

import json
import re
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ferramentas"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "monitor"))
from pncp import frescor as fr  # noqa: E402
from pncp.cliente import INTEGRACAO, ClientePNCP, ErroPNCP, TransitorioPNCP  # noqa: E402
from classificador_biblioteca import classificar  # noqa: E402
from inferencia import reduzir_objeto  # noqa: E402

PISO = Decimal("10000000")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _c(s):
    return _CTRL.sub(" ", s) if isinstance(s, str) else s


def _dec(v):
    try:
        return Decimal(str(v)) if v not in (None, "") else Decimal(0)
    except Exception:
        return Decimal(0)


def _cpf(ni):
    d = "".join(c for c in (ni or "") if c.isdigit())
    return len(d) == 11


def drill(cli, r, m, safra):
    """Drilla uma contratação homologada e devolve linhas (1 por vencedor x lote)."""
    org = r.get("orgaoEntidade") or {}
    uni = r.get("unidadeOrgao") or {}
    cnpj, ano, seq = org.get("cnpj"), r.get("anoCompra"), r.get("sequencialCompra")
    if not (cnpj and ano and seq):
        return []
    base = f"{INTEGRACAO}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
    try:
        itens = cli.get(f"{base}/itens", endpoint="10.13")
    except (TransitorioPNCP, ErroPNCP):
        return []
    if not isinstance(itens, list):
        itens = itens.get("itens") if isinstance(itens, dict) else []
    est_tot = _dec(r.get("valorTotalEstimado"))
    hom_tot = _dec(r.get("valorTotalHomologado"))
    pct = float(hom_tot / est_tot * 100) if est_tot else None
    reforcada = bool(m["grupo"] == "O" and pct is not None and pct < 85)
    objeto = re.sub(r"\s+", " ", (r.get("objetoCompra") or "")).strip()
    comum = dict(
        safra=safra, numero_controle_pncp=r.get("numeroControlePNCP"),
        id_biblioteca=m["id_biblioteca"], codigo_objeto=m["codigo_objeto"],
        grupo_objeto=m["grupo"], familia=m["familia"],
        garantia_codigo=m["garantia_codigo"], garantia_status=m["garantia_status"],
        orgao=_c(org.get("razaoSocial")), orgao_cnpj=cnpj, uf=uni.get("ufSigla"),
        municipio=uni.get("municipioNome"), codigo_ibge=str(uni.get("codigoIbge") or ""),
        esfera=org.get("esferaId"), poder=org.get("poderId"),
        modalidade_id=r.get("modalidadeId"), modalidade=r.get("modalidadeNome"),
        objeto=_c(objeto), objeto_curto=_c(reduzir_objeto(objeto, 80)),
        valor_estimado_total=float(est_tot), valor_homologado_total=float(hom_tot),
        pct_homologado_estimado=round(pct, 1) if pct is not None else None,
        garantia_reforcada=reforcada,
        fonte_plataforma=_c(r.get("usuarioNome")), link_origem=r.get("linkSistemaOrigem"),
    )
    linhas = []
    for it in itens:
        if not it.get("temResultado"):
            continue
        n = it.get("numeroItem")
        try:
            res = cli.get(f"{base}/itens/{n}/resultados", endpoint="10.17")
        except (TransitorioPNCP, ErroPNCP):
            continue
        if not isinstance(res, list):
            res = res.get("listaResultados") if isinstance(res, dict) else []
        for rr in (res or []):
            ni = rr.get("niFornecedor")
            if _cpf(ni):
                continue
            f = fr.avaliar(rr.get("dataResultado"), rr.get("dataInclusao"))
            linha = dict(comum)
            linha.update(
                numero_item=n, vencedor=_c(rr.get("nomeRazaoSocialFornecedor")),
                vencedor_cnpj=ni, porte=rr.get("porteFornecedorNome"),
                natureza_juridica=rr.get("naturezaJuridicaNome"),
                valor_homologado_item=float(_dec(rr.get("valorTotalHomologado") or rr.get("valorUnitarioHomologado"))),
                quantidade_homologada=float(_dec(rr.get("quantidadeHomologada"))),
                data_resultado=f.data_resultado.isoformat() if f.data_resultado else None,
                data_inclusao=f.data_inclusao.isoformat() if f.data_inclusao else None,
                delta_calendar_days=f.delta_calendar_days, delta_business_days=f.delta_business_days,
                frescor=f.classe,
                completo=bool(ni and f.data_resultado),
            )
            linhas.append(linha)
    return linhas


def main() -> int:
    arq, safra = sys.argv[1], sys.argv[2]
    d = json.loads(Path(arq).read_text(encoding="utf-8"))
    alvo = [r for r in d["linhas"] if _dec(r.get("valorTotalHomologado")) >= PISO]
    drill_set = []
    for r in alvo:
        m = classificar(r.get("objetoCompra") or "")
        if m["grupo"] in ("O", "C", "S") and m["garantia_status"] == "EXIGE":
            drill_set.append((r, m))
    print(f"homologado>=10MM={len(alvo)} | drill O/C/S-EXIGE={len(drill_set)}", file=sys.stderr, flush=True)

    linhas = []
    with ClientePNCP() as cli:
        for i, (r, m) in enumerate(drill_set, 1):
            ls = drill(cli, r, m, safra)
            linhas.extend(ls)
            print(f"  [{i}/{len(drill_set)}] {r.get('numeroControlePNCP')} -> {len(ls)} linha(s)",
                  file=sys.stderr, flush=True)

    Path("saidas").mkdir(exist_ok=True)
    Path(f"saidas/ouro_{safra.replace('-','')}.json").write_text(
        json.dumps(linhas, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    # carga no Supabase
    cols = list(linhas[0].keys()) if linhas else []
    if linhas:
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
                cur.execute("delete from gsb.oportunidades_evt007 where safra=%s", (safra,))
                cur.executemany("insert into gsb.oportunidades_evt007 (" + ",".join(cols) + ") values " + ph,
                                [[x.get(c) for c in cols] for x in linhas])
                con.commit()
                cur.execute("""select count(*), count(*) filter (where completo),
                               count(*) filter (where frescor in ('FRESH','FRESH_CALENDAR_EXCEPTION')),
                               count(*) filter (where garantia_reforcada)
                               from gsb.oportunidades_evt007 where safra=%s""", (safra,))
                print("gravadas/completas/frescas/reforcadas:", cur.fetchone(), file=sys.stderr)
    print(f"[ouro: {len(linhas)} linhas | saidas/ouro_{safra.replace('-','')}.json]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
