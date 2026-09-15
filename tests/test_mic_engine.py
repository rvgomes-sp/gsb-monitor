import json,unittest
from hashlib import sha256
from mic.catalog import CatalogSnapshot
from mic.contracts import FactualResult,TransportEvidence,MicStatus,ReasonCode
from mic.engine import MicEngine,item_key,serialize

def snapshot(ns,rows,raw=None,expected=None):
    raw=raw or (ns+json.dumps(rows,sort_keys=True)).encode()
    return CatalogSnapshot(ns,raw,expected or sha256(raw).hexdigest(),rows)

class FakeTransport:
    def __init__(self,items): self.items=items;self.calls=[]
    def fetch_item(self,case,item):
        self.calls.append((case,item));p={"resultado":self.items}
        raw=json.dumps(p,sort_keys=True,separators=(",",":")).encode()
        return TransportEvidence("fixture://item",200,raw,sha256(raw).hexdigest(),json.loads(raw),"2026-01-01T00:00:00Z","2026-01-01T00:00:01Z")

def fact(key="r1",case="CASE",item=1,payload=None): return FactualResult(key,case,item,"FIXTURE",payload or {})
def run(material="S",code=7,catalogs=None,extra=None,records=None):
    row={"case_id":"CASE","item_number":1,"materialOuServico":material,"codItemCatalogo":code}
    row.update(extra or {})
    t=FakeTransport([row])
    cats=catalogs or {"CATSER":snapshot("CATSER",[{"code":"7","name":"serviço"}]),"CATMAT":snapshot("CATMAT",[{"code":"7","name":"material"}])}
    return MicEngine(t,cats,{"M":"CATMAT","S":"CATSER"},"CERT-NS-001").run(records or [fact()])[0],t

class EngineTests(unittest.TestCase):
    def test_t01_exact_catser(self): self.assertEqual(run()[0].mic_status,MicStatus.MATCH_EXATO_CATSER)
    def test_t02_exact_catmat(self): self.assertEqual(run("M")[0].mic_status,MicStatus.MATCH_EXATO_CATMAT)
    def test_t03_namespace_collision(self):
        s,_=run("S");m,_=run("M")
        self.assertEqual((s.catalog_code,m.catalog_code),("7","7"));self.assertNotEqual(s.mic_status,m.mic_status)
    def test_t04_null_code(self): self.assertEqual(run("S",None)[0].mic_status,MicStatus.CODIGO_AUSENTE)
    def test_t05_null_namespace(self): self.assertEqual(run(None,7)[0].mic_status,MicStatus.NAMESPACE_NAO_COMPROVADO)
    def test_t06_aliases_rejected(self):
        for x in ("s"," S","S ","Servico"):
            self.assertEqual(run(x,7)[0].mic_status,MicStatus.NAMESPACE_NAO_COMPROVADO)
    def test_t07_not_found_snapshot_only(self):
        o,_=run("S",999)
        self.assertEqual(o.mic_status,MicStatus.CODIGO_OFICIAL_NAO_LOCALIZADO);self.assertEqual(o.catalog_snapshot_scope,"SNAPSHOT_ONLY")
    def test_t08_description_never_fills_null(self):
        o,_=run("S",None,extra={"descricao":"serviço exatamente igual ao catálogo"})
        self.assertEqual(o.mic_status,MicStatus.CODIGO_AUSENTE)
    def test_t09_snapshot_hash_divergent_zero_lookup(self):
        cat=snapshot("CATSER",[{"code":"7"}],expected="0"*64);o,_=run(catalogs={"CATSER":cat})
        self.assertEqual((o.mic_status,o.mic_reason_code,cat.lookups),(MicStatus.ERRO_TECNICO,ReasonCode.SNAPSHOT_HASH_DIVERGENTE,0))
    def test_t10_duplicate_catalog_key(self):
        cat=snapshot("CATSER",[{"code":"7"},{"code":"7"}]);o,_=run(catalogs={"CATSER":cat})
        self.assertEqual((o.mic_status,o.mic_reason_code),(MicStatus.ERRO_TECNICO,ReasonCode.CHAVE_DUPLICADA_CATALOGO))
    def test_t11_identifier_conflict(self):
        o,_=run(extra={"idCompra":"B"},records=[fact(payload={"idCompra":"A"})])
        self.assertEqual((o.mic_status,o.mic_reason_code),(MicStatus.IDENTIDADE_NAO_RESOLVIDA,ReasonCode.CONFLITO_IDENTIFICADORES))
    def test_t12_item_multiplicity(self):
        t=FakeTransport([{"case_id":"CASE","item_number":1},{"case_id":"CASE","item_number":1}])
        o=MicEngine(t,{}, {"M":"CATMAT","S":"CATSER"},"v").run([fact()])[0]
        self.assertEqual((o.mic_status,o.mic_reason_code),(MicStatus.IDENTIDADE_NAO_RESOLVIDA,ReasonCode.MULTIPLICIDADE_ITEM))
    def test_t13_one_acquisition_per_item(self):
        o,t=run(records=[fact("r1"),fact("r2")]);self.assertEqual(len(t.calls),1);self.assertEqual(o.source_result_keys,["r1","r2"])
    def test_t16_logical_rerun_deterministic(self):
        a,_=run();b,_=run();self.assertEqual(serialize([a]),serialize([b]))
    def test_source_field_name_preserved(self):
        o,_=run(extra={"codItemCatalogo":7});self.assertEqual(o.source_field_name,"codItemCatalogo")
    def test_two_code_fields_fail_closed(self):
        o,_=run(extra={"catalogoCodigoItem":7});self.assertEqual(o.mic_reason_code,ReasonCode.CAMPO_RAW_INVALIDO)
