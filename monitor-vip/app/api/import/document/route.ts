import { getSql } from "../../../../db";
import { ensureDatabase } from "../../../../db/runtime";
import { putDocument } from "../../../../lib/storage";

function importToken() {
  return process.env.IMPORT_TOKEN ?? "";
}

export async function POST(request: Request) {
  const supplied = request.headers.get("x-import-token") ?? "";
  if (!importToken() || supplied !== importToken()) {
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
  await putDocument(key, bytes, contentType);
  const now = new Date().toISOString();
  const label = fileName.toLocaleLowerCase().includes("edital") ? "Abrir edital" : fileName;
  const documentType = fileName.split(".").pop()?.toLowerCase() ?? "";
  const sql = getSql();
  await sql`INSERT INTO monitor.documents(
    process_id,label,object_key,sha256,document_type,reading_status,created_at
  ) VALUES(${processId},${label},${key},${sha256},${documentType},${readingStatus},${now})
  ON CONFLICT(process_id,object_key) DO UPDATE SET
    label=excluded.label,sha256=excluded.sha256,
    document_type=excluded.document_type,reading_status=excluded.reading_status`;
  return Response.json({ status: "OK", process_id: processId, key, bytes: bytes.byteLength });
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
