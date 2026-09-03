#!/usr/bin/env python3
"""Coletor operacional EVT-007 — PNCP puro (Consulta + Integracao + BrasilAPI).

Caminho provado ao vivo em 12/08/2026:
  1) Consulta /contratacoes/atualizacao?data=D  -> descobre contratacoes
  2) Integracao /itens                          -> lista itens
  3) Integracao /itens/{n}/resultados           -> dataResultado, dataInclusao, fornecedor, valor
  4) BrasilAPI /cnpj/v1/{ni}                    -> porte, natureza juridica

Grava em gsb.evt007_results (migracao 001_evt007.sql).
Retomavel por (modalidade, pagina). Sem arquivo local.

Uso:
  python evt007_collect_pncp.py --date 2026-07-23
  python evt007_collect_pncp.py --date 2026-07-23 --dry-run --max-pages 2
  python evt007_collect_pncp.py   # D-1 America/Sao_Paulo
"""

from __future__ import annotations
import argparse, hashlib, json, os, re, time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

BRT = timezone(timedelta(hours=-3))
CONSULTA = "https://pncp.gov.br/api/consulta"
INTEGRACAO = "https://pncp.gov.br/api/pncp"
BRASILAPI = "https://brasilapi.com.br/api/cnpj/v1"
RETRYABLE = (408, 425, 429, 500, 502, 503, 504)
SOURCE = "PNCP_API_V2_5"
# Modalidades que cobrem o universo GSB (pregao, concorrencia, dispensa, etc.)
# Se quiser todas: range(1,20)
DEFAULT_MODALITIES = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]




import unicodedata as _ud
def _fold(v):
    s="".join(c for c in _ud.normalize("NFD",str(v or "")) if _ud.category(c)!="Mn")
    return s.casefold().strip()

def is_cnpj_aln(s):
    """CNPJ alfanumérico (Receita 2026): 12 alfanum + 2 dígitos DV."""
    s=(s or "").strip().upper()
    return bool(re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", s))
def is_cpf(s):
    d="".join(c for c in (s or "") if c.isdigit())
    return len(d)==11 and not is_cnpj_aln((s or "").strip().upper())

class Err(RuntimeError): pass
class Transient(RuntimeError): pass


def _bool(v):
    if isinstance(v,bool): return v
    if isinstance(v,(dict,list)): return None
    if v in (None,""): return None
    s=str(v).strip().lower()
    if s in ("true","t","1","sim","s"): return True
    if s in ("false","f","0","nao","n","não"): return False
    return None
def _text(v): s=str(v).strip() if v is not None else ""; return None if s in ("","None","null") else s
def _int(v):
    t=_text(v)
    if t is None: return None
    try: return int(float(t))
    except: return None
def _dec(v):
    t=_text(v)
    if t is None: return None
    try: return Decimal(t)
    except: return None
def _ts(v): return _text(v)

def _get(url, tries=12, to=120, pause_429=30):
    parsed=urlparse(url)
    if parsed.scheme!="https": raise Err(f"Nao-HTTPS: {url}")
    last=None
    for a in range(1,tries+1):
        req=Request(url,headers={"Accept":"application/json","User-Agent":"GSB-EVT007/2.0"})
        try:
            with urlopen(req,timeout=to) as r:
                raw=r.read()
            return json.loads(raw.decode("utf-8-sig")), raw
        except HTTPError as e:
            last=e
            if e.code not in RETRYABLE or a==tries:
                if e.code in RETRYABLE: raise Transient(f"HTTP {e.code} apos {tries}x") from e
                raise Err(f"HTTP {e.code}") from e
            ra=e.headers.get("Retry-After") if e.headers else None
            time.sleep(float(ra) if ra and ra.isdigit() else (pause_429 if e.code==429 else min(60,2**a)))
        except (URLError,TimeoutError,OSError,json.JSONDecodeError) as e:
            last=e
            if a==tries: raise Transient(str(e)) from e
            time.sleep(min(120, 8*a))
    raise Transient(str(last))


def _result_key(case_id, item_num, seq_result, ni):
    b=f"{case_id}|{item_num}|{seq_result}|{ni}"
    return hashlib.sha256(b.encode()).hexdigest()


def _enrich_cnpj(ni, cache):
    s=(ni or "").strip().upper()
    if not is_cnpj_aln(s): return None, None   # so enriquece CNPJ valido (inclui alfanumerico)
    k=s
    if k in cache: return cache[k]
    try:
        emp,_=_get(f"{BRASILAPI}/{k}",tries=2,to=20)
        if isinstance(emp,dict):
            cache[k]=(emp.get("porte"), emp.get("natureza_juridica"))
            return cache[k]
    except: pass
    cache[k]=(None,None)
    return None, None


def discover_high_value(target: date, modalities: list[int], page_size: int,
                        min_value: float, top_n: int):
    """Descobre contratacoes do dia, filtra por valorTotalEstimado>=min_value,
    ordena por valor desc, retorna as top_n (alto valor, para analise)."""
    ds=target.strftime("%Y%m%d")
    candidatas=[]
    for mod in modalities:
        page=1; total_pages=None
        while total_pages is None or page<=total_pages:
            q=urlencode({"dataInicial":ds,"dataFinal":ds,"codigoModalidadeContratacao":mod,
                         "pagina":page,"tamanhoPagina":page_size})
            payload,_=_get(f"{CONSULTA}/v1/contratacoes/atualizacao?{q}")
            tp=int(payload.get("totalPaginas") or 0)
            if total_pages is None: total_pages=tp
            for r in (payload.get("data") or []):
                ve=_dec(r.get("valorTotalEstimado")) or Decimal(0)
                if ve>=Decimal(str(min_value)):
                    candidatas.append((ve, r))
            if tp==0: break
            page+=1
            time.sleep(0.2)
    # ordena por valor desc, pega top_n
    candidatas.sort(key=lambda x: x[0], reverse=True)
    if top_n: candidatas=candidatas[:top_n]
    print(f"  descoberta: {len(candidatas)} contratacoes >= R$ {min_value:,.0f} (top {top_n or 'todas'})", flush=True)
    for ve, r in candidatas:
        org=r.get("orgaoEntidade") or {}
        yield r, org.get("cnpj"), r.get("anoCompra"), r.get("sequencialCompra"), ve

def discover_day(target: date, modalities: list[int], page_size: int, max_pages: int):
    """Yield (case_row, cnpj, ano, seq) para cada contratacao atualizada no dia."""
    ds=target.strftime("%Y%m%d")
    for mod in modalities:
        page=1; total_pages=None
        while total_pages is None or page<=total_pages:
            if max_pages and page>max_pages: break
            q=urlencode({"dataInicial":ds,"dataFinal":ds,"codigoModalidadeContratacao":mod,
                         "pagina":page,"tamanhoPagina":page_size})
            payload,_=_get(f"{CONSULTA}/v1/contratacoes/atualizacao?{q}")
            tp=int(payload.get("totalPaginas") or 0)
            if total_pages is None: total_pages=tp
            rows=payload.get("data") or []
            for r in rows:
                org=r.get("orgaoEntidade") or {}
                yield r, org.get("cnpj"), r.get("anoCompra"), r.get("sequencialCompra")
            if tp==0: break
            page+=1
            time.sleep(0.3)


def drill_results(cnpj, ano, seq, target: date, cnpj_cache: dict, platform: str | None):
    """Retorna lista de dicts mapeados para gsb.evt007_results."""
    itens,_=_get(f"{INTEGRACAO}/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens")
    if not isinstance(itens,list): return []
    mapped=[]
    for it in itens:
        if not it.get("temResultado"): continue
        n=it["numeroItem"]
        try:
            res,_=_get(f"{INTEGRACAO}/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{n}/resultados")
        except: continue
        if not isinstance(res,list): continue
        for r in res:
            rd=_text(r.get("dataResultado"))
            if rd is None: continue
            try: rd_date=date.fromisoformat(rd[:10])
            except: continue
            if rd_date!=target: continue
            ni=_text(r.get("niFornecedor"))
            # Decisao (Vazquez): pessoa fisica (CPF) nao interessa -> descartar.
            # CNPJ agora e ALFANUMERICO (Receita 2026): nao filtrar so por digitos.
            if is_cpf(ni):
                continue
            porte_api, nat_api = _enrich_cnpj(ni, cnpj_cache)
            case_id=f"{cnpj}-1-{int(seq):06d}/{ano}"
            mapped.append({
                "result_key": _result_key(case_id, n, r.get("sequencialResultado",1), ni or ""),
                "case_id": case_id,
                "item_id": None,
                "procurement_id": None,
                "pncp_procurement_id": None,
                "item_number": n,
                "result_sequence": _int(r.get("sequencialResultado")) or 1,
                "supplier_identifier": ni,
                "supplier_name": _text(r.get("nomeRazaoSocialFornecedor")),
                "supplier_size_id": _int(r.get("porteFornecedorId")),
                "supplier_size_name": porte_api or _text(r.get("porteFornecedorNome")),
                "legal_nature_id": nat_api or _text(r.get("naturezaJuridicaId")),
                "legal_nature_name": nat_api,
                "result_date": rd_date,
                "inclusion_at": _ts(r.get("dataInclusao")),
                "update_at": _ts(r.get("dataAtualizacao")),
                "cancellation_at": _ts(r.get("dataCancelamento")),
                "cancellation_reason": _text(r.get("motivoCancelamento")),
                "homologated_quantity": _dec(r.get("quantidadeHomologada")),
                "homologated_unit_value": _dec(r.get("valorUnitarioHomologado")),
                "homologated_total_value": _dec(r.get("valorTotalHomologado")),
                "platform": platform,
                "platform_delta_status": ("VERIFICADO" if (platform or "").strip().lower()=="compras.gov.br" else "A_CARACTERIZAR"),
                "source_name": SOURCE,
                # ===== BLOCO RESULTADO (colunas completas) =====
                "discount_percent": _dec(r.get("percentualDesconto")),
                "srp_classification_order": _int(r.get("ordemClassificacaoSrp")),
                "subcontracting_indicator": _bool(r.get("indicadorSubcontratacao")),
                "meepp_benefit": _text(r.get("aplicacaoBeneficioMeEpp")),
                "supplier_locality": _text(r.get("localidadeFornecedor")),
                "country_code": _text(r.get("codigoPais")),
                "person_type": _text(r.get("tipoPessoa")),
                "item_result_status_id": _text(r.get("situacaoCompraItemResultadoId")),
                "item_result_status_name": _text(r.get("situacaoCompraItemResultadoNome")),
                "remaining_reserve": (r.get("reservaRemanescente") or {}).get("nome") if isinstance(r.get("reservaRemanescente"),dict) else _text(r.get("reservaRemanescente")),
                # ===== BLOCO ITEM (o objeto) =====
                "material_or_service": _text(it.get("materialOuServico")),
                "material_or_service_name": _text(it.get("materialOuServicoNome")),
                "item_description": _text(it.get("descricao")),
                "complementary_info": _text(it.get("informacaoComplementar")),
                "catalog_code": _text(it.get("catalogoCodigoItem")),
                "catalog_category": _text(it.get("categoriaItemCatalogo")),
                "item_category_id": _text(it.get("itemCategoriaId")),
                "item_category_name": _text(it.get("itemCategoriaNome")),
                "ncm_code": _text(it.get("ncmNbsCodigo")),
                "judgment_criterion": _text(it.get("criterioJulgamentoNome")),
                "estimated_unit_value": _dec(it.get("valorUnitarioEstimado")),
                "item_estimated_total": _dec(it.get("valorTotal")),
                "measure_unit": _text(it.get("unidadeMedida")),
                "secret_budget": _bool(it.get("orcamentoSigiloso")),
                "benefit_type": _text(it.get("tipoBeneficioNome")),
                "item_situation": _text(it.get("situacaoCompraItemNome")),
                # ===== BLOCO CONTRATAÇÃO (preenchido no run via row) =====
                "purchase_object": None, "modality_name": None, "modality_id": None,
                "is_srp": None, "org_uf": None, "org_municipality": None, "instrument_type": None,
                # payload cru integral (backup de tudo)
                "source_payload": json.dumps({"resultado":r,"item":it}, ensure_ascii=False, sort_keys=True),
            })
        time.sleep(0.2)
    return mapped


class PgStore:
    def __init__(self, url):
        if not url: raise Err("DATABASE_URL nao definida")
        import psycopg; self._pg=psycopg; self._url=url
    def connect(self): return self._pg.connect(self._url)
    def _ensure_types(self):
        # remaining_reserve vem como objeto {codigo,nome}: garante que a coluna e text
        try:
            with self.connect() as c:
                with c.transaction():
                    c.execute("""
                        DO $$ BEGIN
                          IF EXISTS (SELECT 1 FROM information_schema.columns
                                     WHERE table_schema='gsb' AND table_name='evt007_results'
                                     AND column_name='remaining_reserve' AND data_type='boolean') THEN
                            ALTER TABLE gsb.evt007_results ALTER COLUMN remaining_reserve TYPE text
                              USING remaining_reserve::text;
                          END IF;
                        END $$;""")
        except Exception as e:
            print(json.dumps({"warn":"ensure_types","err":str(e)[:80]}), flush=True)

    def upsert(self, records):
        # colunas que existem na tabela (descobertas 1x)
        with self.connect() as c:
            cols_tab=[row[0] for row in c.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='gsb' AND table_name='evt007_results'").fetchall()]
        with self.connect() as c:
            with c.transaction():
                for rec in records:
                    # só insere colunas que existem na tabela E estão no registro
                    cols=[k for k in rec.keys() if k in cols_tab]
                    ph=",".join(f"%({k})s" + ("::jsonb" if k=="source_payload" else "") for k in cols)
                    collist=",".join(cols)
                    # UPDATE de todas as colunas menos as chaves
                    upd=",".join(f"{k}=excluded.{k}" for k in cols
                                 if k not in ("result_key","case_id"))
                    c.execute(
                        f"INSERT INTO gsb.evt007_results({collist}) VALUES({ph}) "
                        f"ON CONFLICT(result_key) DO UPDATE SET {upd}, last_seen_at=now()",
                        rec)


def run(target, page_size, dry_run, max_pages, modalities, min_value=0, top_n=0,
        band="all", max_items=10, exclude_status="", big_only_if_multi=False,
        gatilho_85_mode=False, limiar_85=0.85, value_min=0, value_max=0, so_obras=False):
    EXCLUIR={s.strip().lower() for s in (exclude_status or "").split(",") if s.strip()}
    FAIXA_VM=(Decimal("1000000"),Decimal("10000000"))  # 1-10MM
    FAIXA_VF=Decimal("10000000")                        # >10MM
    skipped_status=skipped_band=skipped_multi=0
    skipped_obra=0
    TERMOS_OBRA=["obra","constru","reforma","pavimenta","edifica","engenharia","infraestrutura",
                 "saneamento","esgoto","drenagem","rodovia","recapea","asfalt","terraplan","urbaniza","ponte","viaduto"]
    store = None if dry_run else PgStore(os.environ.get("DATABASE_URL",""))
    if store: store._ensure_types()
    cnpj_cache={}
    seen_cases=set()
    total_results=0; total_cases=0; sample=[]
    import collections as _c; by_platform=_c.Counter()
    print(f"Coletando EVT-007 para {target.isoformat()} | {len(modalities)} modalidades | dry_run={dry_run}", flush=True)
    # piso efetivo da descoberta: cardume respeita value_min (ou 500k), senao faixa custom/min_value
    eff_min = (value_min or min_value or 500000) if gatilho_85_mode else (value_min or min_value)
    discoverer = (discover_high_value(target, modalities, page_size, eff_min, top_n)
                  if eff_min or top_n else
                  ((r,c,a,s,None) for r,c,a,s in discover_day(target, modalities, page_size, max_pages)))
    for row, cnpj, ano, seq, ve_est in discoverer:
        if not cnpj or not ano or not seq: continue
        platform = row.get("usuarioNome")
        case_key=f"{cnpj}|{ano}|{seq}"
        if case_key in seen_cases: continue
        seen_cases.add(case_key)

        # FILTRO 1 (Vazquez): excluir canceladas/suspensas/desertas/etc
        sit=_fold(row.get("situacaoCompraNome") or row.get("situacaoNome") or "")
        if any(x in sit for x in EXCLUIR):
            skipped_status+=1; continue

        # FILTRO SÓ-OBRAS (Vazquez): objeto tem que ser obra/construção
        if so_obras:
            obj=_fold(row.get("objetoCompra") or "")
            if not any(t in obj for t in TERMOS_OBRA):
                skipped_obra+=1; continue

        # FILTRO 2 (Vazquez): faixa de valor + canal
        vest=_dec(row.get("valorTotalEstimado")) or Decimal(0)
        if gatilho_85_mode:
            # MODO CARDUME: faixa custom (ex 1-5MM), sem corte de porte;
            # o filtro real e o RATIO por item (abaixo)
            lo=Decimal(str(value_min)) if value_min else Decimal(str(min_value or 500000))
            hi=Decimal(str(value_max)) if value_max else Decimal("999999999999")
            if not (lo<=vest<=hi): skipped_band+=1; continue
            canal = "CARDUME_85"
        elif value_min or value_max:
            # faixa CUSTOM (Vazquez): ex 1MM a 5MM
            lo=Decimal(str(value_min)) if value_min else Decimal(0)
            hi=Decimal(str(value_max)) if value_max else Decimal("999999999999")
            if not (lo<=vest<=hi): skipped_band+=1; continue
            canal = "VAZQUEZ_FONSECA" if vest>FAIXA_VF else "VIEIRA_MENDONCA"
        else:
            if band=="vm" and not (FAIXA_VM[0]<=vest<=FAIXA_VM[1]): skipped_band+=1; continue
            if band=="vf" and not (vest>FAIXA_VF): skipped_band+=1; continue
            if band=="all" and vest<FAIXA_VM[0]: skipped_band+=1; continue
            canal = "VAZQUEZ_FONSECA" if vest>FAIXA_VF else "VIEIRA_MENDONCA"

        total_cases+=1
        try:
            mapped=drill_results(cnpj, ano, seq, target, cnpj_cache, platform)
        except Exception as e:
            print(json.dumps({"warn":"drill_fail","case":case_key,"err":str(e)[:80]}), flush=True)
            continue
        if not mapped: continue

        # FILTRO GATILHO-85 (Vazquez): so itens com homologado/estimado < limiar
        if gatilho_85_mode:
            filtrados=[]
            for m in mapped:
                ve_item=_dec(m.get("item_estimated_total")) or _dec(m.get("estimated_unit_value"))
                vh_item=_dec(m.get("homologated_total_value"))
                if ve_item and vh_item and ve_item>0:
                    ratio=float(vh_item)/float(ve_item)
                    if ratio < limiar_85:
                        m["_ratio_85"]=round(ratio,4)
                        filtrados.append(m)
            if not filtrados:
                skipped_multi+=1; continue   # nenhum item acende a regua -> descarta caso
            mapped=filtrados

        # FILTRO 3 (Vazquez): limite de itens; casos com muitos itens so se > 10MM
        n_itens=len({m.get("item_number") for m in mapped})
        if n_itens>max_items:
            if big_only_if_multi and vest<=FAIXA_VF:
                skipped_multi+=1; continue   # muitos itens e nao e grande -> fora
            # limita aos max_items de MAIOR valor homologado
            mapped=sorted(mapped, key=lambda m:_dec(m.get("homologated_total_value")) or Decimal(0), reverse=True)[:max_items]

        # carimba canal + valor estimado + campos da contratacao no payload de cada linha
        for m in mapped:
            m["channel"]=canal
            m["estimated_total_value"]=str(vest)
            m["purchase_object"]=row.get("objetoCompra")
            m["modality_name"]=row.get("modalidadeNome")
            m["modality_id"]=str(row.get("modalidadeId") or "")
            m["is_srp"]=row.get("srp")
            m["org_uf"]=(row.get("unidadeOrgao") or {}).get("ufSigla") if isinstance(row.get("unidadeOrgao"),dict) else row.get("unidadeOrgaoUfSigla")
            m["org_municipality"]=(row.get("unidadeOrgao") or {}).get("municipioNome") if isinstance(row.get("unidadeOrgao"),dict) else None
            m["instrument_type"]=row.get("tipoInstrumentoConvocatorioNome")

        # sanitizar: nenhuma COLUNA pode receber dict/list (só source_payload é jsonb)
        for m in mapped:
            for k,v in list(m.items()):
                if k=="source_payload": continue
                if isinstance(v,(dict,list)):
                    m[k]=None if not v else json.dumps(v, ensure_ascii=False)
        total_results+=len(mapped)
        if mapped: by_platform[str(platform)]+=len(mapped)
        if store: store.upsert(mapped)
        elif len(sample)<5:
            sample.extend({k:(str(v) if isinstance(v,(Decimal,date)) else v) for k,v in m.items() if k!="source_payload"} for m in mapped[:5-len(sample)])
        if total_cases%50==0:
            print(json.dumps({"cases":total_cases,"results":total_results,"cnpj_cache":len(cnpj_cache)}), flush=True)
    report={"status":"COMPLETE","date":target.isoformat(),"source":SOURCE,
            "cases_checked":total_cases,"results_collected":total_results,
            "cnpj_enriched":len(cnpj_cache),"dry_run":dry_run,
            "excluidos_status":skipped_status,"excluidos_faixa":skipped_band,
            "excluidos_multi_itens":skipped_multi,"excluidos_nao_obra":skipped_obra,
            "por_plataforma":dict(by_platform.most_common(15))}
    if dry_run: report["sample"]=sample
    return report


def main():
    raise RuntimeError("LEGACY_EVT007_DISABLED_GATE_B: use python -m evt007; operational promotion is blocked")
    p=argparse.ArgumentParser(description="Coletor EVT-007 PNCP puro")
    p.add_argument("--date",help="AAAA-MM-DD; padrao D-1 BRT")
    p.add_argument("--page-size",type=int,default=50)
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--max-pages",type=int,default=0)
    p.add_argument("--modalities",help="ex: 6,8,13",default="")
    p.add_argument("--min-value",type=float,default=0,help="piso valorTotalEstimado (ex: 10000000)")
    p.add_argument("--top",type=int,default=0,help="pega as N maiores contratacoes")
    p.add_argument("--band",choices=["all","vm","vf"],default="all",
                   help="faixa/canal: vm=1-10MM, vf=>10MM, all=ambas")
    p.add_argument("--max-items",type=int,default=10,help="limite de itens por caso (default 10)")
    p.add_argument("--exclude-status",default="revogada,anulada,suspensa,deserta,fracassada,cancelada",
                   help="situacoes a excluir (nome, minusculo, separado por virgula)")
    p.add_argument("--big-only-if-multi",action="store_true",
                   help="casos com muitos itens (>max-items) so entram se > 10MM")
    p.add_argument("--gatilho-85",action="store_true",
                   help="MODO CARDUME: pesca so itens com homologado/estimado < 0.85 (desagio>15%)")
    p.add_argument("--limiar-85",type=float,default=0.85,help="regua do gatilho (default 0.85)")
    p.add_argument("--no-porte-filter",action="store_true",
                   help="NAO filtra por porte (inclui ME/EPP) - para o cardume do 85%")
    p.add_argument("--value-min",type=float,default=0,help="piso custom da faixa (ex: 1000000)")
    p.add_argument("--value-max",type=float,default=0,help="teto custom da faixa (ex: 5000000)")
    p.add_argument("--so-obras",action="store_true",help="filtra so contratacoes cujo objeto e obra/construcao")
    a=p.parse_args()
    target=date.fromisoformat(a.date) if a.date else (datetime.now(BRT).date()-timedelta(days=1))
    mods=[int(x) for x in a.modalities.split(",") if x.strip()] if a.modalities else DEFAULT_MODALITIES
    try:
        report=run(target, a.page_size, a.dry_run, a.max_pages, mods, a.min_value, a.top, a.band, a.max_items, a.exclude_status, a.big_only_if_multi, a.gatilho_85, a.limiar_85, a.value_min, a.value_max, a.so_obras)
    except Err as e:
        print(json.dumps({"status":"ERROR","error":str(e)})); return 2
    except (Transient,HTTPError,URLError,TimeoutError) as e:
        print(json.dumps({"status":"TRANSIENT","error":str(e)})); return 75
    print(json.dumps(report,ensure_ascii=False,indent=2,default=str),flush=True)
    return 0

if __name__=="__main__": raise SystemExit(main())
