"""Offline controlled fixtures; these are software checks, never factual observations."""
import copy
import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coletor import evt007_catalog_bridge as b

CASE = "04892707000887-1-000022/2025"


def result(number=1, supplier="12345678000190", value=10000001, text="unclassified"):
    raw = {"idContratacaoPNCP": CASE, "numeroItemPncp": number, "sequencialResultado": 1,
           "idCompra": "39301503903992025", "idCompraItem": "fixture-item-"+str(number),
           "niFornecedor": supplier, "nomeRazaoSocialFornecedor": "TEST FIXTURE",
           "dataResultadoPncp": "2026-09-09T00:00:00", "valorTotalHomologado": value,
           "objetoCompra": text}
    return b.collector.map_row(raw)


def item(material="S", code=5622, number=1):
    return {"idContratacaoPNCP": CASE, "numeroItemPncp": number,
            "idCompra": "39301503903992025", "idCompraItem": "fixture-item-"+str(number),
            "materialOuServico": material, "codItemCatalogo": code}


class HTTP:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0
    def __call__(self, url):
        self.calls += 1
        payload = {"resultado": self.rows, "totalPaginas": 1}
        return payload, {"sha256": hashlib.sha256(json.dumps(payload).encode()).hexdigest()}


class NeverCatser:
    def lookup(self, code):
        raise AssertionError("CATSER must not be consulted")


class SQLiteSink:
    """Actual SQL uniqueness check; only placeholder/cast dialect adapted for SQLite."""
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("ATTACH DATABASE ':memory:' AS gsb")
        for table, cols, key in (("evt007_results", b.RESULT_COLUMNS, "result_key"),
                                 ("evt007_item_identity", b.IDENTITY_COLUMNS, "item_key")):
            self.db.execute(f"CREATE TABLE gsb.{table} (" + ",".join(c+" TEXT" for c in cols) + f", PRIMARY KEY ({key}))")
        self.db.execute("CREATE TABLE gsb.evt007_item_identity_observations (run_id TEXT,item_key TEXT,observation TEXT,PRIMARY KEY(run_id,item_key))")
        self.statements = []
    def execute(self, sql, params):
        self.statements.append(sql)
        assert "monitor." not in sql and "oportunidades" not in sql
        if isinstance(params, dict):
            for name in params:
                sql = sql.replace("%("+name+")s", ":"+name)
        else:
            sql = sql.replace("%s", "?")
        return self.db.execute(sql.replace("::jsonb", ""), params)


class BridgeTests(unittest.TestCase):
    def catser(self):
        return b.Catser(os.environ["CATSER_TEST_PATH"])

    def test_a_entrypoint_has_no_inference_or_legacy_import(self):
        import ast
        tree = ast.parse(Path("coletor/esteira_evt007.py").read_text())
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertEqual(set(imports), {"evt007_catalog_bridge"})
        self.assertFalse(b.MONITOR_WRITE)

    def test_b_cut_is_strict_and_text_independent(self):
        rows = [result(value=10000000), result(value=10000000.01, text="não exige garantia"), result(value=10000001, text="objeto desconhecido")]
        self.assertEqual(len(b.select_results(rows)), 2)
        for row in b.select_results(rows):
            http = HTTP([item()])
            _, ids, _ = b.bridge([row], http, self.catser())
            self.assertEqual(http.calls, 1)
            self.assertEqual(ids[0]["catalog_match_status"], "CATSER_MATCH_EXATO")

    def test_c_service_uses_exact_certified_code(self):
        cat = self.catser()
        _, ids, _ = b.bridge([result()], HTTP([item()]), cat)
        self.assertEqual(ids[0]["catalog_code"], "5622")
        self.assertEqual(ids[0]["catalog_namespace"], "CATSER")
        self.assertEqual(cat.observed_hash, b.CATSER_HASH)
        self.assertEqual(ids[0]["catalog_name"], "OBRAS CIVIS PUBLICAS ( CONSTRUCAO )")

    def test_d_material_is_preserved_without_lookup(self):
        _, ids, _ = b.bridge([result()], HTTP([item("M")]), NeverCatser())
        self.assertEqual(ids[0]["catalog_match_status"], "MATERIAL_PRESERVADO")
        self.assertEqual(ids[0]["catalog_namespace"], "CATMAT")
        self.assertEqual(ids[0]["cod_item_catalogo_raw"], 5622)

    def test_e_no_namespace_normalization_or_null_inference(self):
        for value in (None, "", "s", " S", "S ", "Servico", "serviço"):
            with self.subTest(value=value):
                _, ids, _ = b.bridge([result()], HTTP([item(value)]), NeverCatser())
                self.assertEqual(ids[0]["catalog_match_status"], "NAMESPACE_NAO_RESOLVIDO")
                self.assertEqual(ids[0]["material_ou_servico_raw"], value)

    def test_f_shared_item_gets_one_acquisition_and_two_results(self):
        rows = [result(), result(supplier="98765432000190")]
        original = copy.deepcopy(rows)
        http = HTTP([item()])
        selected, identities, audit = b.bridge(rows, http, self.catser())
        self.assertEqual((len(selected), len(identities), len(audit), http.calls), (2,1,2,1))
        self.assertEqual(rows, original)
        self.assertNotEqual(audit[0]["result_key"], audit[1]["result_key"])

    def test_g_h_sql_rerun_preserves_history_and_never_writes_monitor(self):
        rows = [result(), result(supplier="98765432000190")]
        _, ids, _ = b.bridge(rows, HTTP([item()]), self.catser())
        sink = SQLiteSink()
        b.persist(sink, rows, ids, "fixture-run-1")
        changed = copy.deepcopy(ids)
        changed[0]["catalog_name"] = "later observation"
        for _ in range(2):
            b.persist(sink, rows, changed, "fixture-run-2")
        self.assertEqual(sink.db.execute("select count(*) from gsb.evt007_results").fetchone()[0], 2)
        self.assertEqual(sink.db.execute("select count(*) from gsb.evt007_item_identity").fetchone()[0], 1)
        self.assertEqual(sink.db.execute("select count(*) from gsb.evt007_item_identity_observations").fetchone()[0], 2)
        self.assertEqual(sink.db.execute("select catalog_name from gsb.evt007_item_identity").fetchone()[0], ids[0]["catalog_name"])
        self.assertTrue(all("DO NOTHING" in s for s in sink.statements))

    def test_missing_code_is_not_not_found(self):
        for value in (None, ""):
            _, ids, _ = b.bridge([result()], HTTP([item(code=value)]), NeverCatser())
            self.assertEqual(ids[0]["catalog_match_status"], "CODIGO_CATALOGO_AUSENTE")

    def test_noncanonical_code_is_not_normalized(self):
        for value in ("05622", " 5622", 5622.0, True, "5622.0"):
            _, ids, _ = b.bridge([result()], HTTP([item(code=value)]), NeverCatser())
            self.assertEqual(ids[0]["catalog_match_status"], "AQUISICAO_IDENTIDADE_FALHOU")

    def test_not_found_does_not_fallback(self):
        _, ids, _ = b.bridge([result()], HTTP([item(code=999999999999)]), self.catser())
        self.assertEqual(ids[0]["catalog_match_status"], "CATSER_NAO_LOCALIZADO")

    def test_hash_failure_stops_catser(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"bad.csv"; p.write_text("not the certified snapshot")
            cat = b.Catser(p)
            _, ids, _ = b.bridge([result()], HTTP([item()]), cat)
            self.assertEqual(ids[0]["catalog_match_status"], "ERRO_TECNICO_CATALOGO")
            self.assertEqual(cat.lookups, 0)
            m = b.metrics([result()], [result()], ids, 1)
            self.assertIsNone(m["taxa_match_catser"])
            self.assertEqual(m["denominador_match_sem_falha_tecnica"], 0)

    def test_multirow_preserved_as_failure(self):
        _, ids, _ = b.bridge([result()], HTTP([item(), item()]), NeverCatser())
        self.assertEqual(ids[0]["catalog_match_status"], "AQUISICAO_IDENTIDADE_FALHOU")
        self.assertEqual(len(ids[0]["identity_payload"]["resultado"]), 2)

    def test_official_identifiers_must_converge(self):
        bad = item(); bad["idCompraItem"] = "another-item"
        _, ids, _ = b.bridge([result()], HTTP([bad]), NeverCatser())
        self.assertEqual(ids[0]["catalog_match_status"], "AQUISICAO_IDENTIDADE_FALHOU")

    def test_collection_reads_all_pages_and_preserves_mapping(self):
        from datetime import date
        raw = json.loads(result()["source_payload"])
        other = json.loads(result(number=2)["source_payload"])
        calls = []
        def getter(url):
            calls.append(url)
            return {"resultado":[raw if len(calls)==1 else other], "totalRegistros":2, "totalPaginas":2}
        rows, report = b.collector.collect(date.fromisoformat(b.TARGET), getter=getter)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(rows[0]["source_payload"], b.collector.map_row(raw)["source_payload"])

    def test_incomplete_and_changed_date_fail_closed(self):
        from datetime import date
        raw = json.loads(result()["source_payload"])
        rows, report = b.collector.collect(date.fromisoformat(b.TARGET), max_pages=1,
            getter=lambda _: {"resultado":[raw],"totalRegistros":2,"totalPaginas":2})
        self.assertEqual(report["status"], "INCOMPLETE")
        raw["dataResultadoPncp"] = "2026-09-08"
        with self.assertRaises(ValueError):
            b.collector.collect(date.fromisoformat(b.TARGET), getter=lambda _: {"resultado":[raw],"totalRegistros":1,"totalPaginas":1})

    def test_preflight_missing_factual_relation_stops(self):
        class Connection:
            def execute(self, *a): return self
            def fetchone(self): return (None,)
        with self.assertRaisesRegex(RuntimeError, "gsb.evt007_results"):
            b.preflight(Connection())

    def test_conflicting_source_ids_remain_persistable_failure(self):
        rows = [result(), result(supplier="98765432000190")]
        raw = json.loads(rows[1]["source_payload"])
        raw["idCompra"] = "different-purchase"
        rows[1]["source_payload"] = json.dumps(raw)
        http = HTTP([item()])
        _, ids, _ = b.bridge(rows, http, NeverCatser())
        self.assertEqual(http.calls, 0)
        self.assertEqual(ids[0]["catalog_match_status"], "AQUISICAO_IDENTIDADE_FALHOU")
        sink = SQLiteSink()
        b.persist(sink, rows, ids, "failed-fixture")
        self.assertEqual(sink.db.execute("select count(*) from gsb.evt007_item_identity").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
