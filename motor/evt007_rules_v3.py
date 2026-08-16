#!/usr/bin/env python3
"""Motor de regras EVT-007 v3 — TRÊS CAMINHOS DE GARANTIA.

Fecha as decisões do Vazquez (11-13/08/2026):
  - classificação por CÓDIGO de catálogo (classe), não por palavra
  - material nunca CERTA automática (requalifica por valor, passa pelo humano)
  - TRÊS caminhos de garantia, basta um acender:
      (1) OBJETO   — classe do catálogo = CERTA/INFERIR/MONITORAR/...
      (2) GATILHO 85% — homologado/estimado < 0,85 -> garantia adicional
                        (independe de objeto; vale mesmo se edital diz "sem garantia")
      (3) EDITAL   — Fase 2: motor de edital lê o TR (esboço aqui)
  - "não haverá garantia" NUNCA descarta
  - funil reordenado: valor ANTES do drill (resolve volume)

Lê gsb.evt007_results; grava gsb.evt007_rule_decisions e gsb.evt007_opportunities.
Config: gsb_config.json + familias_catalogo_classe.json (editáveis).

Uso:
  python evt007_rules_v3.py --date 2026-07-22
  python evt007_rules_v3.py --all --dry-run
"""
from __future__ import annotations
import argparse, json, os, unicodedata
from collections import defaultdict, Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any


# Degrau de reserva (Vazquez): quando catalogoCodigoItem vem VAZIO,
# classifica pela DESCRIÇÃO do objeto. Marcado como "por texto" (auditável).
TERMOS_OBRA = ["obra","constru","reforma","pavimenta","edifica","engenharia",
    "infraestrutura","manutenc","saneamento","esgoto","drenagem","rodovia",
    "recapea","asfalt","terraplan","urbaniza","eficiencia energetica"]
TERMOS_SERVICO_CONTINUO = ["limpeza","vigilancia","seguranca","conservac",
    "copeiragem","recepc","portaria","brigada","jardinagem","manutencao predial",
    "transporte de passageiro","transporte escolar"]

RULE_VERSION = "EVT007-RULES-V3-2026-08-13"

def _fold(v): 
    s="".join(c for c in unicodedata.normalize("NFD",str(v or "")) if unicodedata.category(c)!="Mn")
    return s.casefold().strip()
def _digits(v): return "".join(c for c in str(v or "") if c.isdigit())
import re as _re
def _cnpj_key(v):
    """Chave de fornecedor: preserva CNPJ ALFANUMERICO (Receita 2026)."""
    s=str(v or "").strip().upper()
    return s if _re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", s) else _digits(s)
def _dec(v):
    if v in (None,""): return None
    try: return Decimal(str(v))
    except InvalidOperation: return None


class Config:
    def __init__(self, cfg_path, fam_path):
        self.cfg=json.loads(Path(cfg_path).read_text(encoding="utf-8"))
        fam=json.loads(Path(fam_path).read_text(encoding="utf-8"))
        self.mat={k:v["status"] for k,v in fam["material_classe"].items()}
        self.srv={k:v["status"] for k,v in fam["servico_classe"].items()}
        f=self.cfg["funil"]
        self.piso=Decimal(str(f["piso_valor_coleta"]))
        self.fronteira=Decimal(str(f["fronteira_rota"]))
        self.max_itens=int(f["max_itens_soma"])
        self.limiar85=Decimal(str(self.cfg["garantia"]["caminho_2_gatilho_85"]["limiar"]))
        pn=self.cfg["porte_natureza"]
        self.size_ok=set(pn["size_id_aceito"]); self.size_nome=[_fold(x) for x in pn["size_nome_aceito"]]
        self.nat_ids=set(pn["nature_ids_aceitos"]); self.nat_nomes=[_fold(x) for x in pn["nature_nomes_aceitos"]]
        self.prio_mod=set(self.cfg["modalidades_prioritarias"])

    def status_objeto(self, material_ou_servico, codigo_classe, descricao=""):
        cod=_digits(codigo_classe)
        if cod:
            tab = self.mat if _fold(material_ou_servico) in ("m","material") else self.srv
            return tab.get(cod, "MONITORAR")
        # DEGRAU DE RESERVA: catálogo vazio -> classifica por descrição (marcado)
        d=_fold(descricao)
        if d:
            if any(t in d for t in TERMOS_OBRA):
                return "CERTA_POR_TEXTO"
            if any(t in d for t in TERMOS_SERVICO_CONTINUO):
                return "CERTA_POR_TEXTO"
        return "SEM_CATALOGO"


# ---------- CAMINHO 2: gatilho 85% (matemática pura) ---------- #
def gatilho_85(valor_estimado, valor_homologado, limiar):
    ve=_dec(valor_estimado); vh=_dec(valor_homologado)
    if not ve or ve==0 or not vh: return (False, None)
    ratio = vh/ve
    return (ratio < limiar, ratio)


# ---------- CAMINHO 3: edital (esboço Fase 2) ---------- #
def analisar_edital(cnpj, ano, seq, cfg):
    """Esboço: baixa /arquivos, lê TR, procura termos. Ativado na Fase 2.
    Retorna dict com achados; None se não executado."""
    return None  # Fase 2 — implementado quando ligarmos o motor de edital


def _mercado(rec, cfg):
    # MODO CARDUME (Vazquez): no gatilho-85 inclui ME/EPP -> nao filtra porte/natureza.
    # O deságio (>15%) e o filtro; porte/natureza viram informacao, nao corte.
    if _fold(rec.get("channel"))=="cardume_85":
        return "ACCEPTED",("CARDUME_85_SEM_CORTE_PORTE",)
    sid=_digits(rec.get("supplier_size_id")); snm=_fold(rec.get("supplier_size_name"))
    if not sid and not snm: return "PENDING",("PORTE_NAO_INFORMADO",)
    if sid not in cfg.size_ok and not any(t in snm for t in cfg.size_nome):
        return "REJECTED",("PORTE_FORA_DO_CORTE",)
    nid=_digits(rec.get("legal_nature_id")); nnm=_fold(rec.get("legal_nature_name"))
    if not nid and not nnm: return "PENDING",("NATUREZA_NAO_INFORMADA",)
    # Decisao Vazquez: SO as 3 naturezas (por codigo estrito; nome como reforco exato).
    ok = (nid in cfg.nat_ids) if nid else any(t==nnm for t in cfg.nat_nomes)
    return ("ACCEPTED",()) if ok else ("REJECTED",("NATUREZA_FORA_DO_CORTE",))


def _rota(v, cfg): return "VAZQUEZ_FONSECA" if v>cfg.fronteira else "VIEIRA_MENDONCA"

def _tese(v, garantia_status, temas, cfg):
    if temas and v<=cfg.fronteira: return 3,"VM_CONSULTORIA"
    if v>cfg.fronteira: return 1,"VF_EMISSAO"
    if v>=cfg.piso: return 2,"VM_HIBRIDO"
    return 4,"ASSINATURA"

def _plano(v):
    if v>=Decimal("5000000"): return "PREMIUM"
    if v>=Decimal("1000000"): return "INTERMEDIARIO"
    return "GRATIS"

def _score(v, prio, garantia_status, gatilho85, mercado):
    s=min(int(v/Decimal("100000")),300)
    s+=120 if prio else 0
    s+={"CERTA":150,"CERTA_POR_TEXTO":110,"INFERIR":80,"MONITORAR":40,"STANDBY":15,"DESCARTAR":0,"SEM_CATALOGO":30}.get(garantia_status,30)
    s+=100 if gatilho85 else 0   # gatilho 85% pesa alto: oportunidade invisível
    s+=60 if mercado=="ACCEPTED" else 0
    return s


def avaliar_caso(case_id, rows, cfg):
    live=[r for r in rows if not r.get("cancellation_at")]
    if not live:
        return [{"case_id":case_id,"business_state":"REJECTED","reasons":["TODOS_CANCELADOS"]}]
    by_sup=defaultdict(list)
    for r in live:
        ni=_cnpj_key(r.get("supplier_identifier"))
        if ni: by_sup[ni].append(r)
    cands=[]
    for ni,recs in by_sup.items():
        valued=[(_dec(r.get("homologated_total_value")) or Decimal(0), r) for r in recs]
        total=sum(v for v,_ in valued); items={r.get("item_number") for _,r in valued}
        indiv=[(v,r) for v,r in valued if v>=cfg.piso]
        if indiv: qv=max(v for v,_ in indiv); basis="ITEM"
        elif len(items)<=cfg.max_itens and total>cfg.fronteira: qv=total; basis=f"SOMA_{len(items)}"
        else: continue

        ref=recs[0]
        payload=ref.get("source_payload") or "{}"
        if isinstance(payload,str):
            try: payload=json.loads(payload)
            except Exception: payload={}

        # CAMINHO 1: objeto por catálogo
        mos=payload.get("material_or_service") or payload.get("materialOuServico") or payload.get("material_ou_servico")
        classe=(payload.get("catalog_code") or payload.get("catalog_category")
                or payload.get("codigoClasse") or payload.get("catalogoCodigoItem")
                or payload.get("categoriaItemCatalogo"))
        descricao=(payload.get("item_description") or payload.get("purchase_object")
                   or payload.get("descricao") or payload.get("objetoCompra") or "")
        status_obj=cfg.status_objeto(mos, classe, descricao)

        # CAMINHO 2: gatilho 85% (lê das colunas reais do banco)
        ve=(payload.get("item_estimated_total") or payload.get("estimated_total_value")
            or payload.get("estimated_unit_value")
            or payload.get("valorTotal") or payload.get("valorTotalEstimado"))
        g85,ratio=gatilho_85(ve, ref.get("homologated_total_value"), cfg.limiar85)

        mercado,mr=_mercado(ref,cfg)
        mod=_digits(payload.get("modalidadeId") or payload.get("codigoModalidadeContratacao"))
        prio = mod in cfg.prio_mod if mod else False
        temas=[]  # massa temática pode ser derivada depois
        rota=_rota(qv,cfg); tese_n,tese=_tese(qv,status_obj,temas,cfg)
        score=_score(qv,prio,status_obj,g85,mercado)

        # decisão de garantia: 3 caminhos, basta um acender
        acende = (status_obj in ("CERTA","INFERIR","CERTA_POR_TEXTO")) or g85
        garantia_final = "PROVAVEL" if acende else "A_CONFIRMAR_EDITAL"
        if g85: garantia_final="ADICIONAL_85_PROVAVEL"
        if status_obj=="CERTA": garantia_final="ALTA_CERTEZA"
        if status_obj=="CERTA_POR_TEXTO": garantia_final="PROVAVEL_POR_TEXTO_CONFIRMAR_EDITAL"

        reasons=[f"VALOR:{basis}", f"OBJETO_CATALOGO:{status_obj}",
                 f"GATILHO_85:{'SIM' if g85 else 'nao'}"+(f"({ratio:.0%})" if ratio else ""),
                 f"MODALIDADE:{'PRIORITARIA' if prio else 'outra'}",
                 f"PORTE_NATUREZA:{mercado}", f"GARANTIA:{garantia_final}"]

        bstate = "REJECTED" if mercado=="REJECTED" else ("PENDING_ENRICHMENT" if mercado=="PENDING" else "QUALIFIED")
        cand={"case_id":case_id,"supplier_identifier":ni,
              "supplier_name":ref.get("supplier_name") or "",
              "result_date":ref.get("result_date"),
              "market_state":mercado,"business_state":bstate,"route":rota,
              "considered_items":len(items),"qualifying_value":qv,
              "reasons":reasons,"tese":tese_n,"tese_nome":tese,
              "plano_assinatura":_plano(qv),"garantia":garantia_final,
              "objeto_status":status_obj,"gatilho_85":g85,
              "ratio_85":(f"{ratio:.4f}" if ratio else None),
              "priority_mod":prio,"score":score}
        cands.append(cand)
    if not cands: return None
    # AJUSTE 1 (Vazquez): caso multi-fornecedor gera uma oportunidade POR fornecedor
    # que passa o piso, nao so o de maior valor. Retorna lista.
    return sorted(cands, key=lambda x: x.get("score",0), reverse=True)


def _dk(c,ni): return sha256(f"{c}|{ni}|{RULE_VERSION}".encode()).hexdigest()
def _ok(c,ni,rd): return sha256(f"{c}|{ni}|{rd}".encode()).hexdigest()

def run(target, process_all, dry_run, cfg_path, fam_path):
    cfg=Config(cfg_path, fam_path)
    import psycopg
    url=os.environ.get("DATABASE_URL","")
    if not url: raise SystemExit("DATABASE_URL nao definida")
    with psycopg.connect(url) as conn:
        if process_all:
            cur=conn.execute("SELECT * FROM gsb.evt007_results ORDER BY case_id")
        else:
            cur=conn.execute("SELECT * FROM gsb.evt007_results WHERE result_date=%s ORDER BY case_id",(target,))
        cols=[d.name for d in cur.description]; rows=cur.fetchall()
    records=[dict(zip(cols,r)) for r in rows]
    by_case=defaultdict(list)
    for r in records: by_case[r["case_id"]].append(r)

    decisions=[]; opps=[]; tese_c=Counter(); g85_c=0; gar_c=Counter()
    for cid,crows in by_case.items():
        ds=avaliar_caso(cid,crows,cfg)
        if not ds: continue
        if isinstance(ds,dict): ds=[ds]   # compat
        for d in ds:
            decisions.append(d)
            if d.get("business_state")=="QUALIFIED":
                opps.append(d); tese_c[d["tese_nome"]]+=1; gar_c[d["garantia"]]+=1
                if d.get("gatilho_85"): g85_c+=1

    if not dry_run:
        with psycopg.connect(url) as conn, conn.transaction():
            for d in decisions:
                conn.execute("""INSERT INTO gsb.evt007_rule_decisions(
                    decision_key,scope_key,case_id,supplier_identifier,rule_version,
                    market_state,business_state,route,considered_items,qualifying_value,reasons)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT(decision_key) DO UPDATE SET
                      market_state=excluded.market_state,business_state=excluded.business_state,
                      route=excluded.route,qualifying_value=excluded.qualifying_value,
                      reasons=excluded.reasons,decided_at=now()""",
                    (_dk(d["case_id"],d["supplier_identifier"]),RULE_VERSION,d["case_id"],
                     d["supplier_identifier"],RULE_VERSION,d.get("market_state","-"),
                     d["business_state"],d.get("route"),d.get("considered_items",0),
                     d.get("qualifying_value"),json.dumps(d.get("reasons",[]))))
            for d in opps:
                pl={k:(str(v) if isinstance(v,(Decimal,date)) else v) for k,v in d.items()}
                conn.execute("""INSERT INTO gsb.evt007_opportunities(
                    opportunity_id,scope_key,case_id,supplier_identifier,supplier_name,
                    route,qualifying_value,result_date,status,payload)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'NOVA',%s::jsonb)
                    ON CONFLICT(opportunity_id) DO UPDATE SET
                      route=excluded.route,qualifying_value=excluded.qualifying_value,
                      payload=excluded.payload,updated_at=now()""",
                    (_ok(d["case_id"],d["supplier_identifier"],d["result_date"]),RULE_VERSION,
                     d["case_id"],d["supplier_identifier"],d["supplier_name"],d["route"],
                     d["qualifying_value"],d["result_date"],json.dumps(pl,ensure_ascii=False)))

    return {"rule_version":RULE_VERSION,"casos":len(by_case),"decisoes":len(decisions),
            "oportunidades":len(opps),"por_tese":dict(tese_c),
            "por_garantia":dict(gar_c),"acionou_gatilho_85":g85_c,"dry_run":dry_run,
            "top5":sorted([{k:(str(v) if isinstance(v,(Decimal,date)) else v)
                for k,v in o.items() if k in ("case_id","supplier_name","qualifying_value",
                "route","tese_nome","garantia","objeto_status","gatilho_85","ratio_85","score")}
                for o in opps], key=lambda x:x.get("score",0),reverse=True)[:5]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--date"); p.add_argument("--all",action="store_true")
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--config",default="gsb_config.json")
    p.add_argument("--familias",default="familias_catalogo_classe.json")
    a=p.parse_args()
    target=date.fromisoformat(a.date) if a.date else None
    if not target and not a.all: raise SystemExit("Informe --date ou --all")
    print(json.dumps(run(target,a.all,a.dry_run,a.config,a.familias),ensure_ascii=False,indent=2,default=str))
    return 0
if __name__=="__main__": raise SystemExit(main())
