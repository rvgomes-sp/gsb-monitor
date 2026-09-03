"""Bounded PNCP context for results ALREADY discovered in Compras.gov.

No search, national drill, catalogue traversal, edital or OSINT endpoint exists.
Only the known purchase and exact known item are accessible. Gate C opt-in only.
"""
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from .collection import NoRedirect, Response, TransportFailure, fetch
from .contracts import decode, digest
from .factual import normalize_result


def pncp_context_get(url):
    parsed=urlsplit(url)
    if (parsed.scheme,parsed.netloc)!=("https","pncp.gov.br") or not re.fullmatch(
            r"/api/pncp/v1/orgaos/[0-9]{14}/compras/[0-9]{4}/[0-9]+(?:/itens/[0-9]+)?",parsed.path):
        raise ValueError("Only exact PNCP purchase/item context allowed")
    if parsed.query or parsed.fragment:
        raise ValueError("PNCP discovery query forbidden")
    request=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'GSB-EVT007-GateB/1'},method='GET')
    try:
        with urllib.request.build_opener(NoRedirect).open(request,timeout=30) as r:
            return Response(r.status,r.read(),dict(r.headers))
    except urllib.error.HTTPError as error:
        return Response(error.code,error.read(),dict(error.headers))


def enrich_known_results(collection, *, request_budget: int, get=pncp_context_get, sleep=__import__('time').sleep):
    if request_budget < 1:
        raise ValueError('Positive explicit request budget required')
    calls=0; cache={}; envelopes=[]; seen=set(); stopped=False

    def bounded(url):
        nonlocal calls
        if calls>=request_budget:
            raise TransportFailure('ENRICHMENT_BUDGET_EXHAUSTED',[])
        calls+=1
        return get(url)

    def obtain(url):
        nonlocal stopped
        if url in cache: return cache[url]
        try:
            response,attempts=fetch(url,get=bounded,sleep=sleep)
            collection.attempts.extend({'stage':'PNCP_ENRICHMENT','url':url,**a} for a in attempts)
            value=decode(response.body)
            if not isinstance(value,dict): raise ValueError('PNCP response is not an object')
            cache[url]=(value,digest(response.body))
            return cache[url]
        except TransportFailure as error:
            collection.attempts.extend({'stage':'PNCP_ENRICHMENT','url':url,**a} for a in error.attempts)
            # Permissions/rate-limit deferral stop the whole enrichment batch.
            stopped=True
            raise

    for raw in collection.rows:
        fact=normalize_result(raw,collection.window)
        if not fact.identity or set(fact.reasons)-{'MODALIDADE_AUSENTE_OU_CONTRADITORIA'}:
            continue
        identity=fact.identity
        key=(identity['process_id'],identity['numero_item'])
        if key in seen: continue
        seen.add(key)
        cnpj,rest=identity['process_id'].split('-1-'); seq,year=rest.split('/')
        base=f'https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{year}/{int(seq)}'
        try:
            purchase,purchase_hash=obtain(base)
            item,item_hash=obtain(base+f"/itens/{identity['numero_item']}")
            envelopes.append({'process_id':identity['process_id'],'numeroItem':identity['numero_item'],
                              'source':'PNCP_ITENS','source_url':base+f"/itens/{identity['numero_item']}",
                              'purchase_source_url':base,'item':item,'purchase':purchase,
                              'item_response_sha256':item_hash,'purchase_response_sha256':purchase_hash})
        except (TransportFailure,ValueError) as error:
            collection.status='PARTIAL' if collection.rows else 'FAILED'
            collection.reasons.append('ENRICHMENT_INCOMPLETE:'+str(error))
            if stopped: break
    return envelopes
