import json,unittest
from hashlib import sha256
from mic.catalog import CatalogSnapshot
from mic.contracts import FactualResult,TransportEvidence,MicStatus,ReasonCode
from mic.engine import MicEngine

class Transport:
    def __init__(self,status=200): self.status=status;self.calls=0
    def fetch_item(self,case,item):
        self.calls+=1
        payload={"resultado":[{"case_id":case,"item_number":item,"materialOuServico":"S","codItemCatalogo":7}]}
        raw=json.dumps(payload,separators=(",",":")).encode()
        return TransportEvidence("fixture://item",self.status,raw,sha256(raw).hexdigest(),payload,"start","finish")

def cat(namespace="CATSER"):
    raw=b"synthetic snapshot"
    return CatalogSnapshot(namespace,raw,sha256(raw).hexdigest(),[{"code":"7","name":"fixture"}])

def fact(): return FactualResult("r1","CASE",1,"FIXTURE",{})

class AdversarialTests(unittest.TestCase):
    def test_http_404_fails_closed_with_zero_lookup(self):
        t,c=Transport(404),cat();o=MicEngine(t,{"CATSER":c},{"M":"CATMAT","S":"CATSER"},"v").run([fact()])[0]
        self.assertEqual((o.mic_status,o.mic_reason_code,c.lookups),(MicStatus.ERRO_TECNICO,ReasonCode.ERRO_TRANSPORTE,0))
        self.assertEqual((o.identity_http_status,o.identity_payload_raw),(404,o.identity_payload_raw))
    def test_http_500_fails_closed_with_zero_lookup(self):
        t,c=Transport(500),cat();o=MicEngine(t,{"CATSER":c},{"M":"CATMAT","S":"CATSER"},"v").run([fact()])[0]
        self.assertEqual((o.mic_status,o.mic_reason_code,c.lookups),(MicStatus.ERRO_TECNICO,ReasonCode.ERRO_TRANSPORTE,0))
    def test_http_200_control_allows_lookup(self):
        t,c=Transport(200),cat();o=MicEngine(t,{"CATSER":c},{"M":"CATMAT","S":"CATSER"},"v").run([fact()])[0]
        self.assertEqual((o.mic_status,c.lookups),(MicStatus.MATCH_EXATO_CATSER,1))
    def test_only_exact_namespace_configuration_is_accepted(self):
        MicEngine(Transport(),{}, {"M":"CATMAT","S":"CATSER"},"v")
        invalid=[{"Servico":"CATSER","M":"CATMAT","S":"CATSER"},{"M":"CATMAT","s":"CATSER"},
                 {"M":"CATMAT"," S":"CATSER"},{"M":"CATMAT","S ":"CATSER"},
                 {"M":"catmat","S":"CATSER"},{"M":"CATMAT","S":"CATSER","X":"CATMAT"},
                 {"M":"CATMAT"},{"M":"CATSER","S":"CATMAT"}]
        for rule in invalid:
            t,c=Transport(),cat()
            with self.subTest(rule=rule),self.assertRaises(ValueError): MicEngine(t,{"CATSER":c},rule,"v")
            self.assertEqual((t.calls,c.lookups),(0,0))
    def test_catser_selection_rejects_catmat_snapshot(self):
        t,c=Transport(),cat("CATMAT");o=MicEngine(t,{"CATSER":c},{"M":"CATMAT","S":"CATSER"},"v").run([fact()])[0]
        self.assertEqual((o.mic_status,o.mic_reason_code,c.lookups),(MicStatus.ERRO_TECNICO,ReasonCode.SNAPSHOT_NAMESPACE_DIVERGENTE,0))
    def test_catmat_selection_rejects_catser_snapshot(self):
        class MTransport(Transport):
            def fetch_item(self,case,item):
                e=super().fetch_item(case,item);e.payload["resultado"][0]["materialOuServico"]="M"
                raw=json.dumps(e.payload,separators=(",",":")).encode()
                return TransportEvidence(e.url,200,raw,sha256(raw).hexdigest(),e.payload,e.started_at,e.finished_at)
        t,c=MTransport(),cat("CATSER");o=MicEngine(t,{"CATMAT":c},{"M":"CATMAT","S":"CATSER"},"v").run([fact()])[0]
        self.assertEqual((o.mic_status,o.mic_reason_code,c.lookups),(MicStatus.ERRO_TECNICO,ReasonCode.SNAPSHOT_NAMESPACE_DIVERGENTE,0))
