"""Explicit offline replay or future Gate C shadow; never a production command."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from .collection import Response, collect
from .contracts import SOURCE, canonical, decode, digest
from .pipeline import evaluate
from .store import Store, initialize
from .enrichment import enrich_known_results


def replay_transport(manifest_path):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source") != SOURCE:
        raise ValueError("noncanonical replay source")
    pages = {}
    for entry in manifest["pages"]:
        page = entry["page"]
        if isinstance(page, bool) or not isinstance(page, int) or page < 1 or page in pages:
            raise ValueError("invalid/duplicate page in manifest")
        path = (manifest_path.parent / entry["path"]).resolve()
        body = path.read_bytes()
        if digest(body) != entry["sha256"]:
            raise ValueError("replay custody mismatch: " + str(path))
        pages[page] = body

    def get(url):
        args = parse_qs(urlsplit(url).query)
        if args["dataResultadoPncpInicial"] != [manifest["window"]] or args["dataResultadoPncpFinal"] != [manifest["window"]]:
            raise ValueError("replay date mismatch")
        page = int(args["pagina"][0])
        return Response(200, pages[page]) if page in pages else Response(404, b"missing preserved page")
    return manifest, get


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gate B EVT-007 isolated proof ledger; no Monitor writer")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init-ledger", help="explicit local schema initialization, no Supabase")
    init.add_argument("--ledger", type=Path, required=True)
    replay = commands.add_parser("replay", help="offline replay of hash-verified official pages")
    replay.add_argument("--manifest", type=Path, required=True)
    shadow = commands.add_parser("shadow", help="Gate C ONLY: bounded official GETs, isolated output")
    shadow.add_argument("--date", required=True)
    shadow.add_argument("--acknowledge-gate-c-authorization", action="store_true", required=True)
    shadow.add_argument("--page-size", type=int, default=500)
    shadow.add_argument("--enrich-pncp", action="store_true")
    shadow.add_argument("--enrichment-request-budget", type=int)
    for sub in (replay, shadow):
        sub.add_argument("--ledger", type=Path, required=True)
        sub.add_argument("--max-pages", type=int, required=True)
        sub.add_argument("--enrichments", type=Path)
    args = parser.parse_args(argv)
    if args.command == "init-ledger":
        initialize(args.ledger)
        print(canonical({"status": "INITIALIZED_LOCAL_ONLY"}))
        return 0
    store = Store(args.ledger)  # validate before HTTP; never request-time DDL
    try:
        enrichments = decode(args.enrichments.read_bytes()) if args.enrichments else []
        if not isinstance(enrichments, list):
            raise ValueError("enrichments must be an array of item-scoped envelopes")
        if args.command == "replay":
            manifest, get = replay_transport(args.manifest)
            collected = collect(manifest["window"], get=get, max_pages=args.max_pages,
                                page_size=manifest["page_size"], sleep=lambda _: None)
        else:
            if args.enrich_pncp and (args.enrichments or not args.enrichment_request_budget):
                raise ValueError("PNCP context requires an explicit request budget and no mixed enrichment file")
            collected = collect(args.date, max_pages=args.max_pages, page_size=args.page_size)
            if args.enrich_pncp and collected.status == "COMPLETE":
                enrichments = enrich_known_results(collected, request_budget=args.enrichment_request_budget)
        evaluated = evaluate(collected, enrichments)
        run_id, decisions = store.record(collected, evaluated)
        output = {**collected.summary(), "mode": args.command, "run_id": run_id,
                  "factual_states": dict(Counter(f.status for f, _ in evaluated)),
                  "factual_reasons": dict(Counter(r for f, _ in evaluated for r in f.reasons)),
                  "decisions": dict(Counter((d["classificacao"] or {}).get("resultado", "NAO_CLASSIFICADO") for _, d in evaluated)),
                  "candidate_count": sum(d["candidato"] for d in decisions), "ledger_counts": store.counts(),
                  "operational_writes": 0, "production_connected": False}
        print(canonical(output))
        return 0 if collected.status == "COMPLETE" else 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
