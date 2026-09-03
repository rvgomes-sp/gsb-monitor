"""Factual eligibility precedes classification. No operational writer exists."""
from collections import defaultdict
from .catalog import catalog_contract
from .contracts import digest
from .factual import normalize_result, process_reference
from .semantics import decide, parse_obligation


def evaluate(collection, enrichments=()):
    index = defaultdict(list)
    for envelope in enrichments:
        # Conflicting or duplicate envelopes are not silently last-write-wins.
        try:
            key = (process_reference(envelope.get("process_id")), int(envelope["numeroItem"]))
        except (ValueError, TypeError, KeyError):
            raise ValueError("invalid enrichment key")
        if not any(digest(e) == digest(envelope) for e in index[key]):
            index[key].append(envelope)
    facts = []
    versions = defaultdict(set)
    for row in collection.rows:
        initial = normalize_result(row, collection.window)
        env = [] if initial.identity is None else index[(initial.identity["process_id"], initial.identity["numero_item"])]
        fact = normalize_result(row, collection.window, env[0] if len(env) == 1 else None)
        if len(env) > 1:
            fact.status = "QUARENTENA"
            fact.reasons.append("ENRIQUECIMENTOS_DIVERGENTES")
        if fact.event_id:
            versions[fact.event_id].add(fact.raw_hash)
        facts.append(fact)
    # Multiple revisions in the same delivery: preserve all, no positional winner.
    if any(len(v) > 1 for v in versions.values()):
        collection.status = "PARTIAL"
        collection.reasons.append("REVISOES_CONFLITANTES_NA_MESMA_ENTREGA")
    evaluated, seen = [], set()
    for fact in facts:
        key = (fact.event_id, fact.raw_hash)
        if key in seen:
            continue
        seen.add(key)
        if fact.event_id and len(versions[fact.event_id]) > 1:
            fact.status = "QUARENTENA"
            fact.reasons.append("REVISAO_FACTUAL_CONFLITANTE")
        decision = {"estado_factual": fact.status, "motivos_factual": fact.reasons,
                    "candidato": False, "promocao_operacional": "BLOQUEADA_GATE_C",
                    "catalogo": catalog_contract(fact.normalized.get("item_raw", {})),
                    "classificacao": None, "collection_status": collection.status}
        if fact.status == "ELEGIVEL":
            decision["classificacao"] = decide(parse_obligation(fact.normalized.get("descricao_item"), fact.normalized.get("objeto_contexto")))
            decision["candidato"] = collection.status == "COMPLETE" and decision["classificacao"]["resultado"] == "PEDE_GARANTIA"
        evaluated.append((fact, decision))
    return evaluated
