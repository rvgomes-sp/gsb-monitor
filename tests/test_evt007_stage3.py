"""Synthetic contract tests, never claimed as real PNCP observations."""
import sys,unittest,json
from pathlib import Path
from datetime import date
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"coletor"))
from pncp.motor import Motor,MODALIDADES_PADRAO
from pncp import classificador as clf
from pncp.ponte_oficial import map_fact,run_bridge
from pncp.cliente import Evidencia
from evt007_catalog_bridge import Catser,persist

class Fake:
    def __init__(self):
        self.calls=[];self.evidencias=[]
        self.item={"numeroItem":1,"temResultado":True,"materialOuServico":"M","codItemCatalogo":123,"descricao":"aquisição de papel"}
    def get(self,url,endpoint=""):
        self.calls.append(endpoint)
        if endpoint=="descoberta":
            payload={"data":[{"numeroControlePNCP":"FIXTURE","orgaoEntidade":{"cnpj":"00000000000000"},"anoCompra":2026,"sequencialCompra":1,"valorTotalHomologado":10000000,"objetoCompra":"aquisição de papel"}],"totalPaginas":1}
        elif endpoint=="10.13": payload=[self.item,{"numeroItem":2,"temResultado":False}]
        elif endpoint=="10.17":
            payload=[{"sequencialResultado":1,"niFornecedor":"12345678000199","nomeRazaoSocialFornecedor":"FIXTURE","dataResultado":"2026-09-10","dataInclusao":"2026-09-10T01:00:00","valorTotalHomologado":5},
                     {"sequencialResultado":2,"niFornecedor":"12345678000199","dataResultado":"2026-08-01","dataInclusao":"2026-09-10T02:00:00","valorTotalHomologado":7}]
        else: raise AssertionError(endpoint)
        self.evidencias.append(Evidencia(endpoint,url,200,"a"*64,0,payload));return payload

class Sink:
    def __init__(self): self.inserts=[]
    def execute(self,q,p): self.inserts.append((q,p))

class TestStage3(unittest.TestCase):
    def test_client_has_no_hardcoded_proxy(self):
        source=Path(__file__).parents[1].joinpath("coletor/pncp/cliente.py").read_text()
        self.assertNotIn('proxy="http://127.0.0.1:45401"',source)
        self.assertNotIn("trust_env=False",source)
    def test_nao_obra_traverses_drill_freshness_identity_and_factual_insert(self):
        cli=Fake()
        self.assertEqual(clf.classificar_contratacao([cli.item],"aquisição de papel").classe,clf.NAO_OBRA)
        with patch.object(clf,"classificar_contratacao",side_effect=AssertionError("inference called")):
            fun,events=Motor(cli).rodar(date(2026,9,10),MODALIDADES_PADRAO)
            ids=run_bridge(events,cli,Catser(Path("NOT_USED_FOR_MATERIAL")))
        self.assertEqual(cli.calls.count("10.17"),1)
        self.assertEqual(len(events),2)
        self.assertEqual((fun.n_fresh,fun.n_backfill),(1,1))
        self.assertEqual(len(ids),1)
        self.assertEqual(ids[0]["catalog_match_status"],"MATERIAL_PRESERVADO")
        facts=[map_fact(e) for e in events]
        sink=Sink();persist(sink,facts,[],"fixture")
        self.assertEqual(len(sink.inserts),2)
        self.assertTrue(all("gsb.evt007_results" in q for q,p in sink.inserts))
        self.assertEqual(facts[0]["homologated_total_value"],5)
        self.assertEqual(fun.contratacoes_atualizadas_lidas,4)
        self.assertEqual(fun.contratacoes_acima_piso,4)
    def test_invalid_discovery_is_not_empty_success(self):
        class Bad(Fake):
            def get(self,*a,**k): return {"unexpected":[]}
        fun,events=Motor(Bad()).rodar(date(2026,9,10),MODALIDADES_PADRAO)
        self.assertEqual(fun.status,"PARTIAL");self.assertEqual(events,[])
    def test_other_day_not_an_event(self):
        cli=Fake()
        fun,events=Motor(cli).rodar(date(2026,9,9),MODALIDADES_PADRAO)
        self.assertEqual(events,[])
        self.assertEqual(fun.total_resultados_lidos,2)
if __name__=="__main__": unittest.main()
