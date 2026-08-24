import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

// Conexão Supabase Postgres (observatorio-sg), schema `monitor`.
// DATABASE_URL: usar o pooler do Supabase (porta 6543, sslmode=require)
// em ambiente serverless (Vercel).
let client: ReturnType<typeof postgres> | null = null;

export function getSql() {
  if (!client) {
    const url = process.env.DATABASE_URL;
    if (!url) {
      throw new Error(
        "DATABASE_URL não definida. Configure a connection string do Supabase (pooler, sslmode=require) no ambiente.",
      );
    }
    client = postgres(url, { max: 1, prepare: false });
  }
  return client;
}

export function getDb() {
  return drizzle(getSql(), { schema });
}
