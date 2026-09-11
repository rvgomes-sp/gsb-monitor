"""EVT-007 factual. Existing PNCP discovery/drill/freshness, without inference gates."""
from __future__ import annotations
import json,sys,time
from dataclasses import dataclass,field
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode
from . import frescor as fr
from .cliente import CONSULTA,INTEGRACAO,ClientePNCP,ErroPNCP,TransitorioPNCP
MODALIDADES_PADRAO=[4,5,6,7]
PISO_PADRAO=Decimal("10000000")
def _dec(v):
    try: return Decimal(str(v)) if v not in (None,"") else Decimal(0)
    except Exception: return Decimal(0)
def _log(msg): print(msg,file=sys.stderr,flush=True)

@dataclass
class Funil:
    data_alvo:str
    piso:str
    status:str="COMPLETE"
    paginas_lidas:int=0
    paginas_puladas:int=0
    contratacoes_atualizadas_lidas:int=0
    contratacoes_acima_piso:int=0
    descobertas:int=0
    total_itens_lidos:int=0
    total_itens_com_resultado:int=0
    total_resultados_lidos:int=0
    total_eventos_incluidos_no_dia:int=0
    n_fresh:int=0
    n_exception:int=0
    n_backfill:int=0
    por_modalidade:dict=field(default_factory=dict)
    resultados_por_item:dict=field(default_factory=dict)
    ocorrencias:list=field(default_factory=list)

@dataclass
class Motor:
    cli:ClientePNCP
    piso:Decimal=PISO_PADRAO
    pausa:float=0.0
    max_pages:int=0

    def falha(self,fun,stage,identity,error):
        fun.status="PARTIAL"
        fun.ocorrencias.append(dict(stage=stage,identity=identity,error=str(error)))

    def descobrir(self,alvo,modalidade,fun):
        ds=alvo.strftime("%Y%m%d")
        pagina,total_paginas=1,None
        stats=fun.por_modalidade.setdefault(str(modalidade),dict(
            PAGINAS_LIDAS=0,PAGINAS_PULADAS=0,CONTRATACOES_ATUALIZADAS_LIDAS=0,CONTRATACOES_ACIMA_PISO=0))
        while total_paginas is None or pagina<=total_paginas:
            if self.max_pages and pagina>self.max_pages:
                self.falha(fun,"descoberta",modalidade,"max_pages limited discovery")
                break
            q=urlencode(dict(dataInicial=ds,dataFinal=ds,codigoModalidadeContratacao=modalidade,pagina=pagina,tamanhoPagina=50))
            try:
                payload=self.cli.get(f"{CONSULTA}/v1/contratacoes/atualizacao?{q}",endpoint="descoberta")
            except TransitorioPNCP as exc:
                fun.paginas_puladas+=1;stats["PAGINAS_PULADAS"]+=1
                self.falha(fun,"descoberta",dict(modalidade=modalidade,pagina=pagina),exc)
                pagina+=1;total_paginas=total_paginas or (pagina+1)
                continue
            except ErroPNCP as exc:
                self.falha(fun,"descoberta",dict(modalidade=modalidade,pagina=pagina),exc)
                break
            fun.paginas_lidas+=1;stats["PAGINAS_LIDAS"]+=1
            if not isinstance(payload,dict) or not isinstance(payload.get("data"),list) or type(payload.get("totalPaginas")) is not int:
                self.falha(fun,"descoberta",modalidade,"invalid discovery schema")
                break
            current=payload["totalPaginas"]
            if current<0 or (payload["data"] and current==0):
                self.falha(fun,"descoberta",modalidade,"inconsistent pagination")
                break
            if total_paginas is None: total_paginas=current
            elif current!=total_paginas:
                self.falha(fun,"descoberta",modalidade,"page count changed")
                break
            _log(f"[mod {modalidade}] página {pagina}/{total_paginas}; linhas={len(payload['data'])}")
            for r in payload["data"]:
                fun.contratacoes_atualizadas_lidas+=1;stats["CONTRATACOES_ATUALIZADAS_LIDAS"]+=1
                if not isinstance(r,dict):
                    self.falha(fun,"descoberta",modalidade,"invalid procurement row");continue
                if _dec(r.get("valorTotalHomologado"))>=self.piso:
                    fun.contratacoes_acima_piso+=1;stats["CONTRATACOES_ACIMA_PISO"]+=1
                    yield r
            if not total_paginas: break
            pagina+=1;time.sleep(self.pausa)

    def processar(self,row,alvo,fun):
        org=row.get("orgaoEntidade") or {}
        cnpj,ano,seq=org.get("cnpj"),row.get("anoCompra"),row.get("sequencialCompra")
        case=row.get("numeroControlePNCP")
        if not(cnpj and ano and seq and case):
            self.falha(fun,"contratacao",case,"missing official identifiers");return []
        base=f"{INTEGRACAO}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
        try: itens=self.cli.get(f"{base}/itens",endpoint="10.13")
        except (TransitorioPNCP,ErroPNCP) as exc:
            self.falha(fun,"itens",case,exc);return []
        if isinstance(itens,dict): itens=itens.get("itens")
        if not isinstance(itens,list):
            self.falha(fun,"itens",case,"invalid items schema");return []
        fun.total_itens_lidos+=len(itens)
        eventos=[]
        for it in itens:
            if not isinstance(it,dict):
                self.falha(fun,"itens",case,"invalid item");continue
            if it.get("temResultado") is not True: continue
            fun.total_itens_com_resultado+=1
            n=it.get("numeroItem")
            if type(n) is not int or n<1:
                self.falha(fun,"item",case,"invalid item number");continue
            endpoint=f"{base}/itens/{n}/resultados"
            try: res=self.cli.get(endpoint,endpoint="10.17")
            except (TransitorioPNCP,ErroPNCP) as exc:
                self.falha(fun,"resultados",[case,n],exc);continue
            if isinstance(res,dict): res=res.get("listaResultados")
            if not isinstance(res,list):
                self.falha(fun,"resultados",[case,n],"invalid results schema");continue
            fun.total_resultados_lidos+=len(res)
            fun.resultados_por_item[json.dumps([case,n],separators=(",",":"))]=len(res)
            for rr in res:
                if not isinstance(rr,dict):
                    self.falha(fun,"resultado",[case,n],"invalid result");continue
                f=fr.avaliar(rr.get("dataResultado"),rr.get("dataInclusao"))
                if not f.data_inclusao or not f.data_resultado:
                    self.falha(fun,"frescor",[case,n],"missing or invalid factual dates");continue
                if f.data_inclusao.date()!=alvo: continue
                fun.total_eventos_incluidos_no_dia+=1
                if f.classe==fr.FRESH: fun.n_fresh+=1
                elif f.classe==fr.FRESH_CALENDAR_EXCEPTION: fun.n_exception+=1
                elif f.classe==fr.BACKFILL: fun.n_backfill+=1
                eventos.append(dict(case_id=case,item_number=n,procurement=row,item=it,result=rr,
                    result_endpoint=endpoint,item_endpoint=f"{base}/itens",
                    delta_calendar_days=f.delta_calendar_days,delta_business_days=f.delta_business_days,
                    freshness_class=f.classe))
            time.sleep(self.pausa)
        return eventos

    def rodar(self,alvo,modalidades):
        fun=Funil(alvo.isoformat(),str(self.piso));vistos={};eventos=[]
        for mod in modalidades:
            for row in self.descobrir(alvo,mod,fun):
                key=row.get("numeroControlePNCP")
                if not key:
                    self.falha(fun,"descoberta",mod,"missing numeroControlePNCP");continue
                if key in vistos:
                    if vistos[key]!=row: self.falha(fun,"descoberta",key,"conflicting repeated procurement")
                    continue
                vistos[key]=row;fun.descobertas+=1
                try: eventos.extend(self.processar(row,alvo,fun))
                except Exception as exc: self.falha(fun,"processamento",key,exc)
        return fun,eventos
