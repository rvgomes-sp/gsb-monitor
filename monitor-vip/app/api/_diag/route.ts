// DIAGNÓSTICO TEMPORÁRIO — reporta presença de env vars, NUNCA valores.
// Remover após confirmar a configuração no Vercel.
export async function GET() {
  const acc = process.env.PORTAL_ACCOUNTS ?? "";
  let parsedEmails: string[] = [];
  let parseError = "";
  try {
    if (acc) {
      const obj = JSON.parse(acc);
      parsedEmails = Object.keys(obj).map((e) => e.replace(/(.).*(@.*)/, "$1***$2"));
    }
  } catch (e) {
    parseError = e instanceof Error ? e.message : "parse falhou";
  }
  return Response.json({
    has_DATABASE_URL: Boolean(process.env.DATABASE_URL),
    has_PORTAL_AUTH_SECRET: Boolean(process.env.PORTAL_AUTH_SECRET),
    has_IMPORT_TOKEN: Boolean(process.env.IMPORT_TOKEN),
    has_PORTAL_ACCOUNTS: Boolean(acc),
    portal_accounts_len: acc.length,
    portal_accounts_parse_error: parseError,
    portal_accounts_emails: parsedEmails,
    node_env: process.env.NODE_ENV,
  });
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
