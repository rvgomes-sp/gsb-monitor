"""Offline unit/integration suite. All invented fixtures are explicitly synthetic."""
import ast
import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from evt007.catalog import catalog_contract, retain_legacy_curation, validate_catalog_state
from evt007.collection import Collection, Response, TransportFailure, collect, fetch, public_get
from evt007.contracts import CATALOG_STATES, SOURCE, canonical, decode, digest
from evt007.factual import normalize_result
from evt007.pipeline import evaluate
from evt007.semantics import decide, parse_obligation
from evt007.store import Store, initialize
from evt007.enrichment import enrich_known_results, pncp_context_get

ROOT = Path(__file__).resolve().parents[2]
WINDOW = "2026-07-17"
PROC = "00000000000000-1-000001/2026"  # SYNTHETIC, never sent anywhere


def row(**changes):
    value = {"numeroControlePNCPCompra": PROC, "idContratacaoPNCP": PROC,
             "numeroItemPncp": 1, "sequencialResultado": 1,
             "niFornecedor": "00000000000100", "tipoPessoa": "PJ",
             "nomeRazaoSocialFornecedor": "SYNTHETIC TEST ONLY",
             "dataResultadoPncp": WINDOW + "T00:00:00", "dataInclusaoPncp": "2026-08-01T12:00:00",
             "situacaoCompraItemResultadoId": 1, "situacaoCompraItemResultadoNome": "Informado",
             "dataCancelamentoPncp": None, "motivoCancelamento": None,
             "valorTotalHomologado": "10000000.01"}
    return {**value, **changes}


def envelope(description="Construção de escola com materiais e mão de obra", modality=4, item=1):
    return {"process_id": PROC, "numeroItem": item, "source": "PNCP_ITENS",
            "source_url": f"https://pncp.gov.br/api/pncp/v1/orgaos/00000000000000/compras/2026/1/itens/{item}",
            "purchase_source_url": "https://pncp.gov.br/api/pncp/v1/orgaos/00000000000000/compras/2026/1",
            "item": {"numeroItem": item, "descricao": description, "materialOuServico": "S"},
            "purchase": {"numeroControlePNCP": PROC, "modalidadeId": modality,
                         "objetoCompra": "CONTEXTO SINTETICO NAO DECISOR"}}


def collection(rows=None, status="COMPLETE"):
    return Collection(WINDOW, status=status, rows=rows or [row()])


def page(rows, total=None, pages=1, remaining=0):
    return Response(200, canonical({"resultado": rows, "totalRegistros": len(rows) if total is None else total,
                                    "totalPaginas": pages, "paginasRestantes": remaining}).encode())


class Offline(unittest.TestCase):
    def setUp(self):
        self.block = patch("socket.create_connection", side_effect=AssertionError("LIVE NETWORK FORBIDDEN IN GATE B TESTS"))
        self.block.start()
        self.addCleanup(self.block.stop)


class FactualTests(Offline):
    def test_strict_individual_floor(self):
        for amount, expected in [("9999999.99", "INELEGIVEL"), ("10000000", "INELEGIVEL"), ("10000000.00000001", "ELEGIVEL")]:
            with self.subTest(amount=amount):
                self.assertEqual(normalize_result(row(valorTotalHomologado=amount), WINDOW, envelope()).status, expected)

    def test_no_sum_or_contract_total_substitution(self):
        small = [row(numeroItemPncp=i, valorTotalHomologado="800000", valorTotalHomologadoContratacao="12000000") for i in range(1, 16)]
        evaluated = evaluate(collection(small), [envelope(item=i) for i in range(1, 16)])
        self.assertTrue(all(not d["candidato"] for _, d in evaluated))
        absent = row(valorTotalHomologado=None, valorUnitarioHomologado="11000000")
        self.assertIn("VALOR_INDIVIDUAL_INVALIDO", normalize_result(absent, WINDOW, envelope()).reasons)

    def test_lossless_money_and_invalid_values(self):
        for value in (None, True, "NaN", "Infinity", "R$11MM", "-1", 11000000.5):
            with self.subTest(value=value):
                self.assertIn("VALOR_INDIVIDUAL_INVALIDO", normalize_result(row(valorTotalHomologado=value), WINDOW, envelope()).reasons)
        decoded = decode(b'{"valorTotalHomologado":10000000.00000001}')
        self.assertEqual(normalize_result(row(**decoded), WINDOW, envelope()).status, "ELEGIVEL")
        self.assertEqual(decode(canonical(decoded).encode()),decoded)
        self.assertIn(':10000000.00000001',canonical(decoded))

    def test_modalities_exactly_4567(self):
        for mode in range(1, 20):
            with self.subTest(mode=mode):
                fact = normalize_result(row(), WINDOW, envelope(modality=mode))
                self.assertEqual(fact.status == "ELEGIVEL", mode in {4, 5, 6, 7})

    def test_missing_conflicting_modality_quarantined(self):
        self.assertEqual(normalize_result(row(), WINDOW).status, "QUARENTENA")
        self.assertEqual(normalize_result(row(modalidadeId=7), WINDOW, envelope(modality=4)).status, "QUARENTENA")

    def test_result_status_and_cancellation(self):
        for changes in ({"situacaoCompraItemResultadoId": 2}, {"dataCancelamentoPncp": "2026-07-18"},
                        {"motivoCancelamento": "cancelado"}, {"situacaoCompraItemResultadoId": None},
                        {"situacaoCompraItemResultadoId": 99}, {"situacaoCompraItemResultadoNome": "Cancelado"}):
            with self.subTest(changes=changes):
                self.assertNotEqual(normalize_result(row(**changes), WINDOW, envelope()).status, "ELEGIVEL")

    def test_result_clock_not_inclusion(self):
        fact = normalize_result(row(), WINDOW, envelope())
        self.assertEqual(fact.status, "ELEGIVEL")
        self.assertEqual(fact.normalized["dataResultado"], WINDOW)
        self.assertEqual(fact.normalized["latencia_dias_calendario"], 15)
        for changes in ({"dataResultadoPncp": "2026-07-16"}, {"dataResultadoPncp": None},
                        {"dataResultadoPncp": "2026-02-30"}, {"dataResultado": "2026-07-16"}):
            self.assertNotEqual(normalize_result(row(**changes), WINDOW, envelope()).status, "ELEGIVEL")

    def test_item_scope_and_context_binding(self):
        self.assertEqual(normalize_result(row(), WINDOW, envelope(item=2)).status, "QUARENTENA")
        env = envelope(); env["purchase"]["numeroControlePNCP"] = PROC.replace("000001", "000002")
        self.assertIn("ENRIQUECIMENTO_INCOMPATIVEL", normalize_result(row(), WINDOW, env).reasons)
        for bad in ('https://example.org/itens/1','https://pncp.gov.br/api/pncp/v1/orgaos/00000000000000/compras/2026/2/itens/1'):
            env=envelope(); env['source_url']=bad
            self.assertIn("ENRIQUECIMENTO_INCOMPATIVEL",normalize_result(row(),WINDOW,env).reasons)

    def test_raw_untouched(self):
        raw, env = row(), envelope(); before = copy.deepcopy((raw, env))
        normalize_result(raw, WINDOW, env)
        self.assertEqual((raw, env), before)


class IdentityTests(Offline):
    def test_three_real_sequences_same_item_remain_distinct(self):
        fixture=decode((ROOT/'tests/evt007/fixtures/official_result_sequences.json').read_bytes())
        facts=[normalize_result(r,fixture['window']) for r in fixture['results']]
        self.assertEqual(len({f.event_id for f in facts}),3)
        self.assertEqual(len({f.identity['process_id'] for f in facts}),1)
        self.assertEqual(len({f.identity['numero_item'] for f in facts}),1)
        self.assertTrue(all(f.status=='INELEGIVEL' for f in facts))

    def test_identity_excludes_supplier_dates_and_money(self):
        a = normalize_result(row(), WINDOW)
        for changes in ({"niFornecedor": "11111111000111"}, {"dataResultadoPncp": "2026-07-18"},
                        {"valorTotalHomologado": "12000000"}, {"dataInclusaoPncp": "2026-09-01"}):
            self.assertEqual(a.event_id, normalize_result(row(**changes), WINDOW).event_id)

    def test_different_items_and_sequences_never_collapse(self):
        ids = {normalize_result(row(numeroItemPncp=i, sequencialResultado=s), WINDOW).event_id for i in (1, 2) for s in (1, 2)}
        self.assertEqual(len(ids), 4)

    def test_formatting_normalized_before_identity(self):
        a = normalize_result(row(), WINDOW)
        b = normalize_result(row(numeroItemPncp="01", sequencialResultado="001", numeroControlePNCPCompra=" " + PROC + " "), WINDOW)
        self.assertEqual(a.event_id, b.event_id)

    def test_missing_identity_has_no_synthetic_key(self):
        for changes in ({"numeroItemPncp": None}, {"sequencialResultado": None}, {"numeroItemPncp": True},
                        {"numeroControlePNCPCompra": None, "idContratacaoPNCP": None},
                        {"idContratacaoPNCP": PROC.replace("000001", "000002")}):
            fact = normalize_result(row(**changes), WINDOW)
            self.assertIsNone(fact.event_id)
            self.assertEqual(fact.status, "QUARENTENA")

    def test_simultaneous_revisions_no_arbitrary_winner(self):
        c = collection([row(), row(valorTotalHomologado="12000000")])
        result = evaluate(c, [envelope()])
        self.assertEqual(c.status, "PARTIAL")
        self.assertTrue(all(not d["candidato"] for _, d in result))


class SemanticTests(Offline):
    def test_five_mandatory_contrasts(self):
        examples = [
            ("Fornecimento de materiais de construção para manutenção", "FORNECIMENTO"),
            ("Construção de escola com vigilância do canteiro", "OBRA"),
            ("Limpeza e conservação de hospital", "SERVICO_LIMPEZA_CONSERVACAO"),
            ("Locação de veículos com motorista", "LOCACAO_OPERADA"),
            ("Projeto executivo para construção de ponte, sem execução", "SERVICO_TECNICO_ENGENHARIA"),
        ]
        for text, nature in examples:
            with self.subTest(text=text):
                ir = parse_obligation(text)
                self.assertFalse(ir.ambiguidade, ir.motivos)
                self.assertEqual(ir.natureza_contratual, nature)
                self.assertEqual(decide(ir)["resultado"] == "PEDE_GARANTIA", nature == "OBRA")

    def test_roles_and_exact_support_spans(self):
        text = "Contratação de empresa para construção de escola, com fornecimento de materiais, mão de obra e vigilância do canteiro."
        ir = parse_obligation(text)
        self.assertEqual(ir.natureza_contratual, "OBRA")
        self.assertIn("materiais", ir.insumos)
        self.assertIn("mão de obra", ir.meios_execucao)
        self.assertIn("vigilância do canteiro", ir.obrigacoes_acessorias)
        for span in ir.suporte_spans:
            self.assertEqual(span["texto"], text[span["inicio"]:span["fim"]])

    def test_purpose_does_not_override_head(self):
        ir = parse_obligation("Fornecimento de materiais de construção para manutenção de escola")
        self.assertEqual(ir.natureza_contratual, "FORNECIMENTO")
        self.assertEqual(ir.destinacao, ["para manutenção de escola"])

    def test_limits_and_negation(self):
        ir = parse_obligation("Elaboração de projeto executivo para construção de ponte, sem execução da obra")
        self.assertEqual(ir.natureza_contratual, "SERVICO_TECNICO_ENGENHARIA")
        self.assertIn("sem execução da obra", ir.limitacoes)
        for text in ("Construção de escola sem execução da obra", "Não construir escola", "Construção de escola não incluída"):
            self.assertEqual(decide(parse_obligation(text))["resultado"], "REVISAO")

    def test_equal_principal_obligations_abstain(self):
        ir = parse_obligation("Construção de escola e fornecimento de veículos")
        self.assertTrue(ir.ambiguidade)
        self.assertEqual(decide(ir)["classificacao_origem"], "NAO_CLASSIFICADO")
        self.assertTrue(parse_obligation("Construção de escola ou locação de equipamentos").ambiguidade)

    def test_context_never_replaces_item(self):
        self.assertEqual(parse_obligation("Fornecimento de materiais", "Construção de escola").natureza_contratual, "FORNECIMENTO")
        self.assertIsNone(parse_obligation(None, "Construção de escola").natureza_contratual)
        self.assertIsNone(parse_obligation("Conforme termo de referência", "Construção de escola").natureza_contratual)

    def test_no_false_design_build(self):
        ir = parse_obligation("Contratação de solução integrada de vigilância patrimonial")
        self.assertNotEqual(ir.natureza_contratual, "OBRA")

    def test_semantic_unknowns_and_abstract_construction(self):
        for text in ("Construção de indicadores econômicos", "Construção de modelo de escola", "Recuperação de dados", "Software para construção de ponte", "Hospital", "Equipamentos", "Materiais"):
            with self.subTest(text=text):
                self.assertTrue(parse_obligation(text).ambiguidade)

    def test_domain_rule_does_not_manufacture_documental_fact(self):
        d = decide(parse_obligation("Construção de escola"))
        self.assertEqual(d["classificacao_origem"], "INFERENCIA_GOVERNADA")
        self.assertEqual(d["garantia_documental"], "NAO_INVESTIGADA")
        self.assertNotIn("percentual", d)


class CatalogTests(Offline):
    def test_code_ms_and_id_do_not_certify_catalog(self):
        for kind in ("S", "M", None):
            c = catalog_contract({"catalogo": {"id": 1, "nome": "Catálogo do Compras.gov.br"}, "catalogoCodigoItem": "7820", "materialOuServico": kind})
            self.assertEqual(c["catalogo_validacao_status"], "NAO_VALIDADO")
            self.assertIsNone(c["codigo_oficial"])
            self.assertIsNone(c["gsb_ativo_motor"])

    def test_all_six_states_and_missing(self):
        for state in CATALOG_STATES:
            self.assertEqual(validate_catalog_state(state), state)
        with self.assertRaises(ValueError): validate_catalog_state("OK")
        self.assertEqual(catalog_contract({})["catalogo_validacao_status"], "NAO_FORNECIDO")
        self.assertNotEqual(validate_catalog_state("ERRO_LOOKUP"), "NAO_FORNECIDO")

    def test_historical_false_not_explicit_deactivation(self):
        for v in (False, "False", True, None):
            c = retain_legacy_curation({"gsbStatus": "NAO_CLASSIFICADO", "gsbAtivoMotor": v}, "v1", "historical.csv")
            self.assertEqual(c["gsb_ativo_motor_raw"], v)
            self.assertIsNone(c["gsb_ativo_motor"])


class PaginationTests(Offline):
    def test_complete_and_canonical_request(self):
        urls = []
        def get(url):
            urls.append(url)
            p = int(parse_qs(urlsplit(url).query)["pagina"][0])
            return page([row(numeroItemPncp=p)], total=2, pages=2, remaining=2-p)
        c = collect(WINDOW, get=get, max_pages=2, page_size=1)
        self.assertEqual(c.status, "COMPLETE")
        self.assertEqual(len(c.rows), 2)
        self.assertTrue(all("dadosabertos.compras.gov.br/modulo-contratacoes/3_" in u and "dataResultadoPncpInicial=" + WINDOW in u for u in urls))

    def test_max_pages_is_partial(self):
        c = collect(WINDOW, get=lambda _: page([row()], 2, 2, 1), max_pages=1, page_size=1)
        self.assertEqual(c.status, "PARTIAL")
        self.assertIn("MAX_PAGES_REACHED", c.reasons)

    def test_missing_totals_or_malformed_page_never_complete(self):
        for body in (b'{}', b'{"resultado":[]}', b'not-json', b'{"resultado":null}', b'[]'):
            self.assertEqual(collect(WINDOW, get=lambda _, b=body: Response(200,b), max_pages=1).status, "FAILED")

    def test_repeated_empty_or_changed_page(self):
        for second in (page([row()],2,2,0), page([],2,2,0), page([row(numeroItemPncp=2)],3,3,1)):
            responses = iter([page([row()],2,2,1),second])
            self.assertEqual(collect(WINDOW,get=lambda _: next(responses),max_pages=2,page_size=1).status,"PARTIAL")

    def test_accurate_zero(self):
        for pages in (0,1):
            self.assertEqual(collect(WINDOW,get=lambda _: page([],0,pages,0),max_pages=1).status,"COMPLETE")

    def test_http_failure_no_skip(self):
        calls=[]
        def get(url):
            calls.append(url)
            return page([row()],2,2,1) if len(calls)==1 else Response(403,b'forbidden')
        c=collect(WINDOW,get=get,max_pages=10,page_size=1)
        self.assertEqual(c.status,"PARTIAL"); self.assertEqual(len(calls),2)

    def test_retry_429_respects_retry_after(self):
        responses=iter([Response(429,b'busy',{'Retry-After':'7'}),page([])])
        sleeps=[]
        response,attempts=fetch("test",get=lambda _:next(responses),sleep=sleeps.append)
        self.assertEqual(sleeps,[7]); self.assertEqual(response.status,200); self.assertEqual(len(attempts),2)

    def test_long_retry_after_defers_instead_of_evasion(self):
        with self.assertRaisesRegex(TransportFailure,"RETRY_DEFERRED"):
            fetch("test",get=lambda _:Response(429,b'busy',{'Retry-After':'3600'}),sleep=lambda _:self.fail("must defer"))

    def test_auth_failures_not_retried(self):
        for status in (401,403):
            with self.assertRaises(TransportFailure) as cm:
                fetch("test",get=lambda _:Response(status,b'no'),sleep=lambda _:self.fail("must not retry"))
            self.assertEqual(len(cm.exception.attempts),1)

    def test_date_retry_and_exhaustion(self):
        sleeps=[]; responses=iter([Response(429,b'',{'Retry-After':'Thu, 03 Sep 2026 12:00:10 GMT'}),page([])])
        fetch("test",get=lambda _:next(responses),now=lambda:datetime(2026,9,3,12,tzinfo=timezone.utc),sleep=sleeps.append)
        self.assertEqual(sleeps,[10])
        with self.assertRaises(TransportFailure) as cm:
            fetch("test",get=lambda _:Response(503,b''),tries=3,sleep=lambda _:None)
        self.assertEqual(len(cm.exception.attempts),3)

    def test_discovery_host_cannot_change(self):
        with self.assertRaises(ValueError): public_get("https://pncp.gov.br/api/consulta/v1/contratacoes/atualizacao")


class PersistenceTests(Offline):
    def setUp(self):
        super().setUp(); self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'proof.sqlite'; initialize(self.path)
        self.store=Store(self.path); self.addCleanup(self.store.close)

    def run_fact(self, raw=None, status="COMPLETE"):
        c=collection([raw or row()],status)
        return self.store.record(c,evaluate(c,[envelope()]))[1]

    def test_reexecution_preserves_case_and_deduplicates_facts_decisions(self):
        first=self.run_fact(); second=self.run_fact()
        self.assertEqual(first[0]['case_id'],second[0]['case_id'])
        counts=self.store.counts()
        self.assertEqual(counts['events'],1); self.assertEqual(counts['revisions'],1)
        self.assertEqual(counts['decisions'],1); self.assertEqual(counts['observations'],2)
        self.assertEqual(counts['candidate_cases'],1)

    def test_case_survives_connection_restart(self):
        original=self.run_fact()[0]
        self.store.close()
        self.store=Store(self.path); self.addCleanup(self.store.close)
        replay=self.run_fact()[0]
        self.assertEqual(original['case_id'],replay['case_id'])
        self.assertEqual(self.store.conn.execute('PRAGMA integrity_check').fetchone(),('ok',))

    def test_same_process_distinct_results_reserve_distinct_cases(self):
        c=collection([row(sequencialResultado=1),row(sequencialResultado=2,niFornecedor='11111111000111')])
        decisions=self.store.record(c,evaluate(c,[envelope()]))[1]
        self.assertEqual(len({d['case_id'] for d in decisions}),2)
        self.assertEqual(self.store.counts()['candidate_cases'],2)

    def test_value_revision_and_cancel_preserve_case(self):
        original=self.run_fact()[0]
        revised=self.run_fact(row(valorTotalHomologado='12000000'))[0]
        cancelled=self.run_fact(row(situacaoCompraItemResultadoId=2))[0]
        self.assertEqual(original['case_id'],revised['case_id'])
        self.assertEqual(original['case_id'],cancelled['case_id'])
        self.assertFalse(cancelled['candidato']); self.assertEqual(self.store.counts()['revisions'],3)

    def test_supplier_change_requires_review_not_reassociation(self):
        original=self.run_fact()[0]
        revised=self.run_fact(row(niFornecedor='11111111000111'))[0]
        self.assertEqual(revised['continuidade_case'],'REVISAO_TROCA_FORNECEDOR')
        self.assertIsNone(revised['case_id']); self.assertFalse(revised['candidato'])
        self.assertEqual(self.store.counts()['candidate_cases'],1)

    def test_old_reobservation_does_not_revive_cancelled_candidate(self):
        original=self.run_fact()[0]
        self.run_fact(row(situacaoCompraItemResultadoId=2))
        replay=self.run_fact()[0]
        self.assertEqual(original['case_id'],replay['case_id'])
        self.assertFalse(replay['candidato'])
        self.assertEqual(replay['revisao_status'],'REVISAO_FACTUAL_REQUER_VALIDACAO')

    def test_partial_never_reserves_candidate(self):
        self.assertFalse(self.run_fact(status='PARTIAL')[0]['candidato'])
        self.assertEqual(self.store.counts()['candidate_cases'],0)

    def test_missing_identity_saved_only_in_quarantine(self):
        self.run_fact(row(sequencialResultado=None))
        self.assertEqual(self.store.counts()['events'],0); self.assertEqual(self.store.counts()['quarantine'],1)

    def test_initialize_refuses_overwrite_and_open_never_ddl(self):
        with self.assertRaises(ValueError): initialize(self.path)
        with self.assertRaises(ValueError): Store(Path(self.temp.name)/'absent.sqlite')

    def test_transaction_rolls_back_on_failure(self):
        c=collection(); c.pages=[{'page':1}] # invalid page shape after run insertion
        with self.assertRaises(KeyError): self.store.record(c,[])
        self.assertEqual(self.store.counts()['runs'],0)

    def test_integrity_failure_prevents_any_run_write(self):
        with patch.object(self.store,'check_integrity',side_effect=ValueError('proof ledger integrity failure')):
            with self.assertRaisesRegex(ValueError,'integrity failure'): self.run_fact()
        self.assertEqual(self.store.counts()['runs'],0)


class ArchitectureTests(Offline):
    def test_enrichment_is_only_for_existing_eligible_result_keys(self):
        calls=[]
        def get(url):
            calls.append(url)
            payload=envelope()['item'] if '/itens/' in url else envelope()['purchase']
            return Response(200,canonical(payload).encode())
        c=collection([row(),row(),row(numeroItemPncp=2,valorTotalHomologado='9000000')])
        enriched=enrich_known_results(c,request_budget=2,get=get,sleep=lambda _:None)
        self.assertEqual(len(calls),2); self.assertEqual(len(enriched),1)
        result=evaluate(c,enriched)
        self.assertTrue(result[0][1]['candidato'])
        self.assertFalse(result[1][1]['candidato'])

    def test_enrichment_permission_error_stops_without_bypass(self):
        calls=[]
        def get(url): calls.append(url); return Response(403,b'blocked')
        c=collection([row(),row(numeroItemPncp=2)])
        self.assertEqual(enrich_known_results(c,request_budget=4,get=get,sleep=lambda _:None),[])
        self.assertEqual(len(calls),1); self.assertEqual(c.status,'PARTIAL')

    def test_enrichment_budget_counts_requests_not_items(self):
        calls=[]
        def get(url): calls.append(url); return Response(200,canonical(envelope()['purchase']).encode())
        c=collection()
        self.assertEqual(enrich_known_results(c,request_budget=1,get=get,sleep=lambda _:None),[])
        self.assertEqual(len(calls),1); self.assertEqual(c.status,'PARTIAL')

    def test_budget_exhaustion_preserves_prior_429_evidence(self):
        c=collection()
        enriched=enrich_known_results(c,request_budget=1,get=lambda _:Response(429,b'busy'),sleep=lambda _:None)
        self.assertEqual(enriched,[]); self.assertEqual(c.status,'PARTIAL')
        self.assertEqual(c.attempts[0]['status'],429)
        self.assertEqual(c.attempts[0]['body_sha256'],digest(b'busy'))

    def test_enrichment_cannot_discover_or_traverse_catalog(self):
        for url in ('https://pncp.gov.br/api/consulta/v1/contratacoes/atualizacao','https://pncp.gov.br/api/pncp/v1/catalogos'):
            with self.assertRaises(ValueError): pncp_context_get(url)

    def test_core_does_not_import_legacy_or_operational_clients(self):
        prohibited={'psycopg','supabase','requests','coletor','monitor','motor','ferramentas','subprocess'}
        for path in (ROOT/'evt007').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node,ast.Import):
                    self.assertFalse(prohibited.intersection(x.name.split('.')[0] for x in node.names),path.name)
                elif isinstance(node,ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split('.')[0],prohibited,path.name)

    def test_legacy_clis_fail_closed(self):
        paths=['coletor/run_coleta_evt007.py','coletor/esteira_evt007.py','coletor/ingest_consulta.py',
               'coletor/evt007_collect_comprasgov.py','coletor/evt007_collect_pncp.py',
               'monitor/subir_obras.py','monitor/subir_ouro.py','motor/evt007_rules_v3.py']
        for path in paths:
            module=ast.parse((ROOT/path).read_text())
            main=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='main')
            self.assertIsInstance(main.body[0],ast.Raise,path)

    def test_catalog_prefix_and_false_defaults_removed(self):
        text=(ROOT/'coletor/pncp/familias.py').read_text()
        self.assertNotIn('[:4]',text); self.assertNotIn('startswith',text)
        self.assertNotIn('DEFAULT FALSE',(ROOT/'evt007/store.py').read_text().upper())

    def test_destructive_route_has_no_db_dependency(self):
        text=(ROOT/'monitor-vip/app/api/import/snapshot/route.ts').read_text()
        for word in ('DELETE FROM','ensureDatabase','getSql','request.json','INSERT INTO'):
            self.assertNotIn(word,text)
        self.assertIn('status: 410',text)


if __name__=='__main__': unittest.main()
