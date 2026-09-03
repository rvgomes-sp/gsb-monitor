/** Gate B: retired destructive import. No DB imports or request-time DDL.
 * Historical implementation remains recoverable from Git, never executed here.
 */
export async function POST(request: Request) {
  const token = process.env.IMPORT_TOKEN ?? "";
  if (!token || request.headers.get("x-import-token") !== token) {
    return Response.json({ error: "Não autorizado." }, { status: 401 });
  }
  return Response.json({
    error: "IMPORT_SNAPSHOT_RETIRED",
    message: "Substituição integral da carteira desativada. Gate C não autorizado.",
    operational_writes: 0,
  }, { status: 410 });
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
