#!/usr/bin/env python3
"""003-S/02-R/Etapa3 canonical factual dry-run. Explicit frozen date, no Monitor."""
import argparse,csv,json,sys,time
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pncp.cliente import ClientePNCP
from pncp.motor import Motor,MODALIDADES_PADRAO
from pncp.ponte_oficial import Catser,map_fact,run_bridge
from evt007_catalog_bridge import metrics,write_json,item_key

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--date",required=True,choices=["2026-09-10"])
    p.add_argument("--modalities",default="4,5,6,7",choices=["4,5,6,7"])
    p.add_argument("--max-pages",type=int,default=0,choices=[0])
    p.add_argument("--catser",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();report={"date":a.date,"modalidades":MODALIDADES_PADRAO,"persisted":False}
    try:
        with ClientePNCP(guardar_evidencia=True,evidence_directory=str(a.out/"http"),verboso=True) as cli:
            fun,events=Motor(cli=cli,max_pages=0).rodar(date.fromisoformat(a.date),MODALIDADES_PADRAO)
            report["discovery"]=fun.__dict__
            write_json(a.out/"events.json",events)
            facts=[];seen={}
            for e in events:
                f=map_fact(e)
                if f["result_key"] in seen:
                    if seen[f["result_key"]]!=f: raise ValueError("conflicting repeated factual result")
                    continue
                seen[f["result_key"]]=f;facts.append(f)
            write_json(a.out/"facts.json",facts)
            if fun.status!="COMPLETE":
                report["status"]="DRY_RUN_INCOMPLETO";return 2
            if fun.contratacoes_atualizadas_lidas==0:
                report["status"]="RESULTADO_ANOMALO_DA_CONSULTA_DE_DESCOBERTA";return 2
            catser=Catser(a.catser)
            ids=run_bridge(events,cli,catser)
            report["catser_sha256"]=catser.observed_hash
            report["metrics"]=metrics(facts,facts,ids,sum(e.endpoint=="identidade" for e in cli.evidencias))
            write_json(a.out/"identities.json",ids)
            index={i["item_key"]:i for i in ids}
            audit=[dict(**f,identity=index[item_key(f["case_id"],f["item_number"])]) for f in facts]
            write_json(a.out/"audit.json",audit)
            report["status"]="DRY_RUN_VALIDO" if events else ("SEM_CONTRATACAO_ACIMA_PISO" if fun.contratacoes_acima_piso==0 else "SEM_EVENTO_INCLUIDO_NO_DIA")
            report["persistence_gate_passed"]=bool(events) and not catser.error
            return 0
    except Exception as exc:
        report.update(status="ERRO_TECNICO",error=str(exc));return 2
    finally:
        report["elapsed_seconds"]=time.monotonic()-start
        write_json(a.out/"execution.json",report)
        print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__": raise SystemExit(main())
