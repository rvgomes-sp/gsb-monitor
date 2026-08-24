import { env } from "cloudflare:workers";
import { ensureDatabase } from "../../../../db/runtime";

export async function POST(request: Request) {
  const supplied = request.headers.get("x-import-token") ?? "";
  if (!env.IMPORT_TOKEN || supplied !== env.IMPORT_TOKEN) {
    return Response.json({ error: "Não autorizado." }, { status: 401 });
  }
  await ensureDatabase();
  const processId = request.headers.get("x-process-id")?.trim() ?? "";
  const encodedName = request.headers.get("x-file-name")?.trim() ?? "";
  const fileName = decodeURIComponent(encodedName).replace(/[\\/:*?"<>|]/g, "_");
  const sha256 = request.headers.get("x-sha256")?.trim() ?? "";
  const readingStatus = request.headers.get("x-reading-status")?.trim() ?? "DISPONIVEL";
  const contentType = request.headers.get("content-type") ?? "application/octet-stream";
  if (!processId || !fileName) {
    return Response.json({ error: "Identificação do documento ausente." }, { status: 400 });
  }
  const key = `editais/${processId.replace(/[^\w.-]/g, "_")}/${fileName}`;
  const bytes = await request.arrayBuffer();
  await env.DOCUMENTS.put(key, bytes, { httpMetadata: { contentType } });
  const now = new Date().toISOString();
  await env.DB.prepare(`INSERT INTO documents(
    process_id,label,object_key,sha256,document_type,reading_status,created_at
  ) VALUES(?,?,?,?,?,?,?)
  ON CONFLICT(process_id,object_key) DO UPDATE SET
    label=excluded.label,sha256=excluded.sha256,
    document_type=excluded.document_type,reading_status=excluded.reading_status`)
    .bind(
      processId,
      fileName.toLocaleLowerCase().includes("edital") ? "Abrir edital" : fileName,
      key,
      sha256,
      fileName.split(".").pop()?.toLowerCase() ?? "",
      readingStatus,
      now,
    ).run();
  return Response.json({ status: "OK", process_id: processId, key, bytes: bytes.byteLength });
}
