import { integer, real, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const outreach = sqliteTable("outreach", {
  processId: text("process_id").primaryKey(),
  status: text("status").notNull().default("NAO_INICIADO"),
  decisionMaker: text("decision_maker").notNull().default(""),
  email: text("email").notNull().default(""),
  phone: text("phone").notNull().default(""),
  lastContactAt: text("last_contact_at").notNull().default(""),
  sentAt: text("sent_at").notNull().default(""),
  nextFollowUpAt: text("next_follow_up_at").notNull().default(""),
  subject: text("subject").notNull().default(""),
  body: text("body").notNull().default(""),
  notes: text("notes").notNull().default(""),
  operator: text("operator").notNull().default("Ana Fonseca"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

export const outreachHistory = sqliteTable("outreach_history", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  processId: text("process_id").notNull(),
  at: text("at").notNull(),
  event: text("event").notNull(),
  fieldsJson: text("fields_json").notNull(),
  status: text("status").notNull(),
  operator: text("operator").notNull(),
});

export const proposals = sqliteTable("proposals", {
  number: text("number").primaryKey(),
  createdAt: text("created_at").notNull(),
  status: text("status").notNull(),
  processId: text("process_id").notNull(),
  supplier: text("supplier").notNull(),
  supplierCnpj: text("supplier_cnpj").notNull().default(""),
  agency: text("agency").notNull().default(""),
  tender: text("tender").notNull().default(""),
  administrativeProcess: text("administrative_process").notNull().default(""),
  decisionMaker: text("decision_maker").notNull().default(""),
  contractValue: real("contract_value").notNull(),
  guaranteePercentage: real("guarantee_percentage").notNull(),
  insuredAmount: real("insured_amount").notNull(),
  annualRate: real("annual_rate").notNull(),
  termMonths: integer("term_months").notNull(),
  estimatedPremium: real("estimated_premium").notNull(),
  notes: text("notes").notNull().default(""),
  operator: text("operator").notNull().default("Ana Fonseca"),
});

export const counters = sqliteTable("counters", {
  key: text("key").primaryKey(),
  value: integer("value").notNull(),
});

export const documentJobs = sqliteTable("document_jobs", {
  processId: text("process_id").primaryKey(),
  status: text("status").notNull(),
  requestedAt: text("requested_at").notNull(),
  updatedAt: text("updated_at").notNull(),
  payloadJson: text("payload_json").notNull(),
});

export const documents = sqliteTable("documents", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  processId: text("process_id").notNull(),
  label: text("label").notNull(),
  objectKey: text("object_key").notNull(),
  sha256: text("sha256").notNull().default(""),
  documentType: text("document_type").notNull().default(""),
  readingStatus: text("reading_status").notNull().default(""),
  createdAt: text("created_at").notNull(),
});

export const feedMetadata = sqliteTable("feed_metadata", {
  id: integer("id").primaryKey(),
  payloadJson: text("payload_json").notNull(),
  updatedAt: text("updated_at").notNull(),
});

export const opportunities = sqliteTable("opportunities", {
  id: text("id").primaryKey(),
  position: integer("position").notNull(),
  processId: text("process_id").notNull(),
  supplierCnpj: text("supplier_cnpj").notNull(),
  route: text("route").notNull(),
  contractValue: real("contract_value").notNull(),
  payloadJson: text("payload_json").notNull(),
  updatedAt: text("updated_at").notNull(),
});
