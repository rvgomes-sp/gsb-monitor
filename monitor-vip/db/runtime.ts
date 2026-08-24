import { getSql } from "./index";

let ready: Promise<void> | null = null;

export function ensureDatabase(): Promise<void> {
  if (!ready) ready = initialize();
  return ready;
}

async function initialize() {
  const sql = getSql();

  await sql`CREATE SCHEMA IF NOT EXISTS monitor`;

  await sql`CREATE TABLE IF NOT EXISTS monitor.outreach (
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
  )`;

  await sql`CREATE TABLE IF NOT EXISTS monitor.outreach_history (
    id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    process_id TEXT NOT NULL,
    at TEXT NOT NULL,
    event TEXT NOT NULL,
    fields_json TEXT NOT NULL,
    status TEXT NOT NULL,
    operator TEXT NOT NULL
  )`;

  await sql`CREATE TABLE IF NOT EXISTS monitor.proposals (
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
    contract_value DOUBLE PRECISION NOT NULL,
    guarantee_percentage DOUBLE PRECISION NOT NULL,
    insured_amount DOUBLE PRECISION NOT NULL,
    annual_rate DOUBLE PRECISION NOT NULL,
    term_months INTEGER NOT NULL,
    estimated_premium DOUBLE PRECISION NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    operator TEXT NOT NULL DEFAULT 'Ana Fonseca'
  )`;

  await sql`CREATE TABLE IF NOT EXISTS monitor.counters (
    key TEXT PRIMARY KEY,
    value INTEGER NOT NULL
  )`;

  await sql`CREATE TABLE IF NOT EXISTS monitor.document_jobs (
    process_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
  )`;

  await sql`CREATE TABLE IF NOT EXISTS monitor.documents (
    id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    process_id TEXT NOT NULL,
    label TEXT NOT NULL,
    object_key TEXT NOT NULL,
    sha256 TEXT NOT NULL DEFAULT '',
    document_type TEXT NOT NULL DEFAULT '',
    reading_status TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (process_id, object_key)
  )`;

  await sql`CREATE TABLE IF NOT EXISTS monitor.feed_metadata (
    id INTEGER PRIMARY KEY,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )`;

  await sql`CREATE TABLE IF NOT EXISTS monitor.opportunities (
    id TEXT PRIMARY KEY,
    position INTEGER NOT NULL,
    process_id TEXT NOT NULL,
    supplier_cnpj TEXT NOT NULL,
    route TEXT NOT NULL,
    contract_value DOUBLE PRECISION NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )`;
}
