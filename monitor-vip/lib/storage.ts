/** Supabase Storage (bucket `editais`) via REST — substitui o R2 do Cloudflare.
 *
 * Env exigidos (server-side apenas — NUNCA expor ao browser):
 *   SUPABASE_URL               ex.: https://<ref>.supabase.co
 *   SUPABASE_SERVICE_ROLE_KEY  service role (Storage privado)
 */

const BUCKET = "editais";

function config() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error(
      "SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY não definidos — Storage de editais indisponível.",
    );
  }
  return { url: url.replace(/\/$/, ""), key };
}

export async function putDocument(
  objectKey: string,
  bytes: ArrayBuffer,
  contentType: string,
): Promise<void> {
  const { url, key } = config();
  const res = await fetch(`${url}/storage/v1/object/${BUCKET}/${objectKey}`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${key}`,
      "content-type": contentType,
      "x-upsert": "true",
    },
    body: bytes,
  });
  if (!res.ok) {
    throw new Error(`Storage PUT falhou (${res.status}): ${await res.text()}`);
  }
}

export async function getDocument(
  objectKey: string,
): Promise<{ body: ReadableStream<Uint8Array>; contentType: string } | null> {
  const { url, key } = config();
  const res = await fetch(`${url}/storage/v1/object/${BUCKET}/${objectKey}`, {
    headers: { authorization: `Bearer ${key}` },
  });
  if (res.status === 404 || res.status === 400) return null;
  if (!res.ok || !res.body) {
    throw new Error(`Storage GET falhou (${res.status})`);
  }
  return {
    body: res.body,
    contentType: res.headers.get("content-type") ?? "application/octet-stream",
  };
}
