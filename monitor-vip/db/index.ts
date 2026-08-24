import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

// Conexão Supabase Postgres (observatorio-sg), schema `monitor`, via pooler de
// transação (porta 6543). Em serverless (Vercel), NÃO reutilizamos conexão em
// cache: um socket em cache morre quando o lambda congela e o próximo request
// pendura. Cada request abre uma conexão curta ao pooler (padrão do Supavisor)
// e ela se encerra por idle_timeout.
export function getSql() {
  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error(
      "DATABASE_URL não definida. Configure a connection string do Supabase (pooler, porta 6543) no ambiente.",
    );
  }
  return postgres(url, {
    max: 1,
    prepare: false,          // pooler de transação não suporta prepared statements
    ssl: "require",          // pooler exige SSL; postgres-js não lê sslmode da URL
    connect_timeout: 10,
    idle_timeout: 5,         // fecha a conexão logo após o request
    max_lifetime: 60,
    fetch_types: false,      // evita round-trip extra de introspecção de tipos
  });
}

// Mantido por compat; as rotas usam getSql() (SQL cru) — o pooler de transação
// não aceita os prepared statements que o drizzle emitiria.
export function getDb() {
  return drizzle(getSql(), { schema });
}
