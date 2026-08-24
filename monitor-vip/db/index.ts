import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

// Conexão Supabase Postgres (observatorio-sg), schema `monitor`.
// DATABASE_URL: pooler de transação do Supabase (porta 6543).
// Serverless (Vercel): SSL explícito, sem prepared statements, timeouts curtos.
let client: ReturnType<typeof postgres> | null = null;

export function getSql() {
  if (!client) {
    const url = process.env.DATABASE_URL;
    if (!url) {
      throw new Error(
        "DATABASE_URL não definida. Configure a connection string do Supabase (pooler, porta 6543) no ambiente.",
      );
    }
    client = postgres(url, {
      max: 1,
      prepare: false,          // pooler de transação não suporta prepared statements
      ssl: "require",          // pooler exige SSL; sslmode da URL não é lido pelo postgres-js
      connect_timeout: 15,
      idle_timeout: 20,
      max_lifetime: 60 * 30,
    });
  }
  return client;
}

export function getDb() {
  return drizzle(getSql(), { schema });
}
