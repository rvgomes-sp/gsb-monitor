import { env } from "cloudflare:workers";

let ready: Promise<void> | null = null;

export function ensureDatabase(): Promise<void> {
  if (!ready) ready = initialize();
  return ready;
}

async function initialize() {
  const db = env.DB;
  if (!db) throw new Error("Banco D1 indisponível.");

  await db.batch([
    db.prepare(`CREATE TABLE IF NOT EXISTS outreach (
      process_id TEXT PRIMARY KEY,
      status TEXT NOT NULL DEFAULT 'NAO_INICIADO',
      decision_maker TEXT NOT NULL DEFAULT '',
      email TEXT NOT NULL DEFAULT '',
      phone TEXT NOT NULL DEFAULT '',
      last_contact_at TEXT NOT NULL DEFAULT '',
      sent_at TEXT NOT NULL DEFAULT '',
      next_follow_up_at TEXT NOT NULL DEFAULT '',
      subject TEXT NOT NULL DEFAULT '',
      body TEXT NOT NULL DEFAULT '',
      notes TEXT NOT NULL DEFAULT '',
      operator TEXT NOT NULL DEFAULT 'Ana Fonseca',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS outreach_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      process_id TEXT NOT NULL,
      at TEXT NOT NULL,
      event TEXT NOT NULL,
      fields_json TEXT NOT NULL,
      status TEXT NOT NULL,
      operator TEXT NOT NULL
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS proposals (
      number TEXT PRIMARY KEY,
      created_at TEXT NOT NULL,
      status TEXT NOT NULL,
      process_id TEXT NOT NULL,
      supplier TEXT NOT NULL,
      supplier_cnpj TEXT NOT NULL DEFAULT '',
      agency TEXT NOT NULL DEFAULT '',
      tender TEXT NOT NULL DEFAULT '',
      administrative_process TEXT NOT NULL DEFAULT '',
      decision_maker TEXT NOT NULL DEFAULT '',
      contract_value REAL NOT NULL,
      guarantee_percentage REAL NOT NULL,
      insured_amount REAL NOT NULL,
      annual_rate REAL NOT NULL,
      term_months INTEGER NOT NULL,
      estimated_premium REAL NOT NULL,
      notes TEXT NOT NULL DEFAULT '',
      operator TEXT NOT NULL DEFAULT 'Ana Fonseca'
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS counters (
      key TEXT PRIMARY KEY,
      value INTEGER NOT NULL
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS document_jobs (
      process_id TEXT PRIMARY KEY,
      status TEXT NOT NULL,
      requested_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS documents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      process_id TEXT NOT NULL,
      label TEXT NOT NULL,
      object_key TEXT NOT NULL,
      sha256 TEXT NOT NULL DEFAULT '',
      document_type TEXT NOT NULL DEFAULT '',
      reading_status TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS feed_metadata (
      id INTEGER PRIMARY KEY,
      payload_json TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS opportunities (
      id TEXT PRIMARY KEY,
      position INTEGER NOT NULL,
      process_id TEXT NOT NULL,
      supplier_cnpj TEXT NOT NULL,
      route TEXT NOT NULL,
      contract_value REAL NOT NULL,
      payload_json TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )`),
    db.prepare("CREATE INDEX IF NOT EXISTS idx_outreach_follow_up ON outreach(next_follow_up_at, status)"),
    db.prepare("CREATE INDEX IF NOT EXISTS idx_history_process ON outreach_history(process_id, id)"),
    db.prepare("CREATE INDEX IF NOT EXISTS idx_proposals_process ON proposals(process_id, created_at)"),
    db.prepare("CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_process_key ON documents(process_id, object_key)"),
    db.prepare("CREATE INDEX IF NOT EXISTS idx_opportunities_process ON opportunities(process_id, position)"),
    db.prepare("CREATE INDEX IF NOT EXISTS idx_opportunities_route_value ON opportunities(route, contract_value)"),
  ]);

  const now = new Date().toISOString();
  await db.batch([
    db.prepare(`INSERT OR IGNORE INTO outreach
      (process_id,status,decision_maker,email,notes,operator,created_at,updated_at,sent_at,next_follow_up_at)
      VALUES(?,?,?,?,?,?,?,?,?,?)`)
      .bind(
        "04892707000291-1-000011/2025", "ENVIADO", "Eladio Messias",
        "eladio@etamconstrutora.com.br",
        "E-mail enviado também para Giancarlo Ciola — Diretor.",
        "Ana Fonseca", now, now, "2026-07-27T15:52:12-03:00", "2026-07-30",
      ),
    db.prepare(`INSERT OR IGNORE INTO outreach
      (process_id,status,decision_maker,email,notes,operator,created_at,updated_at,sent_at,next_follow_up_at)
      VALUES(?,?,?,?,?,?,?,?,?,?)`)
      .bind(
        "08334385000135-1-000006/2026", "ENVIADO", "Bernardo Serrano",
        "bernardo@construtoraagaspar.com.br",
        "Diretor. Presidente: Arnaldo Neto Gaspar.",
        "Ana Fonseca", now, now, "2026-07-27T15:54:04-03:00", "2026-07-30",
      ),
    db.prepare(`INSERT OR IGNORE INTO outreach
      (process_id,status,operator,created_at,updated_at)
      VALUES(?,?,?,?,?)`)
      .bind(
        "35382109000115-1-000002/2026", "EM_PREPARACAO",
        "Ana Fonseca", now, now,
      ),
  ]);
}
