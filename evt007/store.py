"""Explicitly initialized local proof ledger. Never opens Supabase or a DSN.

DDL runs ONLY via initialize(), not a request path or Store constructor. This
SQLite schema is not a production migration. Existing operational cases are
not imported, rebound, or mutated. Candidate case IDs are isolated reservations.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4
from .contracts import canonical, digest

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(version TEXT NOT NULL);
INSERT INTO metadata VALUES('gate-b-ledger-1');
CREATE TABLE runs(run_id TEXT PRIMARY KEY, summary_json TEXT NOT NULL, attempts_json TEXT NOT NULL);
CREATE TABLE pages(run_id TEXT REFERENCES runs, page INTEGER, url TEXT NOT NULL, sha256 TEXT NOT NULL, raw BLOB NOT NULL, PRIMARY KEY(run_id,page));
CREATE TABLE events(event_id TEXT PRIMARY KEY, identity_json TEXT NOT NULL UNIQUE);
CREATE TABLE revisions(event_id TEXT REFERENCES events, raw_hash TEXT NOT NULL, raw_json TEXT NOT NULL, PRIMARY KEY(event_id,raw_hash));
CREATE TABLE observations(run_id TEXT REFERENCES runs, event_id TEXT, raw_hash TEXT NOT NULL, PRIMARY KEY(run_id,event_id,raw_hash));
CREATE TABLE quarantine(run_id TEXT REFERENCES runs, raw_hash TEXT, raw_json TEXT, reasons_json TEXT, PRIMARY KEY(run_id,raw_hash));
CREATE TABLE candidate_cases(case_id TEXT PRIMARY KEY, event_id TEXT UNIQUE REFERENCES events, supplier_id TEXT NOT NULL);
CREATE TABLE decisions(decision_id TEXT PRIMARY KEY, event_id TEXT REFERENCES events, raw_hash TEXT, case_id TEXT REFERENCES candidate_cases, payload_json TEXT NOT NULL);
CREATE TABLE evaluations(run_id TEXT REFERENCES runs, decision_id TEXT REFERENCES decisions, PRIMARY KEY(run_id,decision_id));
"""


def initialize(path: Path):
    path = Path(path)
    if path.exists() or path.is_symlink() or str(path) == ":memory:":
        raise ValueError("initialize requires a new local file")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids clobbering a concurrently created file.
    with path.open("xb"):
        pass
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()


class Store:
    def __init__(self, path: Path):
        path = Path(path)
        if not path.is_file() or path.is_symlink():
            raise ValueError("explicitly initialized ledger required")
        self.conn = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True)
        self.conn.execute("PRAGMA foreign_keys=ON")
        try:
            self.check_integrity()
        except (sqlite3.DatabaseError, ValueError):
            self.conn.close()
            raise
        if self.conn.execute("SELECT version FROM metadata").fetchone() != ("gate-b-ledger-1",):
            self.conn.close()
            raise ValueError("not a Gate B proof ledger")

    def close(self):
        self.conn.close()

    def check_integrity(self):
        # Recheck after collection as well as on opening: a workspace-managed
        # file may have changed while source payloads were being re-read.
        if self.conn.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ValueError("proof ledger integrity failure; do not reuse this artifact")

    def record(self, collection, evaluated):
        """Atomic local run. Append raw revisions and observations; no DELETEs."""
        run_id = str(uuid4())
        decisions = []
        self.check_integrity()
        with self.conn:
            self.conn.execute("INSERT INTO runs VALUES(?,?,?)", (run_id, canonical(collection.summary()), canonical(collection.attempts)))
            for page in collection.pages:
                self.conn.execute("INSERT INTO pages VALUES(?,?,?,?,?)", (run_id, page["page"], page["url"], page["body_sha256"], page["body"]))
            for fact, decision in evaluated:
                if fact.event_id is None:
                    self.conn.execute("INSERT OR IGNORE INTO quarantine VALUES(?,?,?,?)", (run_id, fact.raw_hash, canonical(fact.raw), canonical(fact.reasons)))
                    continue
                self.conn.execute("INSERT OR IGNORE INTO events VALUES(?,?)", (fact.event_id, canonical(fact.identity)))
                self.conn.execute("INSERT OR IGNORE INTO revisions VALUES(?,?,?)", (fact.event_id, fact.raw_hash, canonical(fact.raw)))
                self.conn.execute("INSERT OR IGNORE INTO observations VALUES(?,?,?)", (run_id, fact.event_id, fact.raw_hash))
                supplier = fact.normalized.get("supplier_id")
                existing = self.conn.execute("SELECT case_id,supplier_id FROM candidate_cases WHERE event_id=?", (fact.event_id,)).fetchone()
                reservation = None
                decision = dict(decision)
                revision_count = self.conn.execute("SELECT count(*) FROM revisions WHERE event_id=?", (fact.event_id,)).fetchone()[0]
                if revision_count > 1:
                    # Arrival order is not official revision authority. Replaying
                    # an old valid result must not revive a cancelled candidate.
                    decision["candidato"] = False
                    decision["revisao_status"] = "REVISAO_FACTUAL_REQUER_VALIDACAO"
                if existing and existing[1] != supplier:
                    decision["candidato"] = False
                    decision["continuidade_case"] = "REVISAO_TROCA_FORNECEDOR"
                elif existing:
                    reservation = existing[0]
                    decision["continuidade_case"] = "VINCULO_ISOLADO_NAO_OPERACIONAL"
                elif decision["candidato"]:
                    reservation = str(uuid4())
                    self.conn.execute("INSERT INTO candidate_cases VALUES(?,?,?)", (reservation, fact.event_id, supplier))
                    decision["continuidade_case"] = "VINCULO_ISOLADO_NAO_OPERACIONAL"
                # Inclusion of the case decision is deterministic after reservation.
                decision["case_id"] = reservation
                decision["event_id"] = fact.event_id
                decision["raw_hash"] = fact.raw_hash
                decision["normalizado"] = fact.normalized
                decision["enriquecimento_raw"] = fact.enrichment
                decision_id = digest(decision)
                self.conn.execute("INSERT OR IGNORE INTO decisions VALUES(?,?,?,?,?)", (decision_id, fact.event_id, fact.raw_hash, reservation, canonical(decision)))
                self.conn.execute("INSERT OR IGNORE INTO evaluations VALUES(?,?)", (run_id, decision_id))
                decisions.append({"decision_id": decision_id, **decision})
        return run_id, decisions

    def counts(self):
        return {name: self.conn.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
                for name in ("runs", "pages", "events", "revisions", "observations", "quarantine", "candidate_cases", "decisions", "evaluations")}
