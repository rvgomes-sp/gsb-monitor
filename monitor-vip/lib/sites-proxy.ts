const forwardedRequestHeaders = ["accept", "content-type"];
const forwardedResponseHeaders = [
  "cache-control",
  "content-disposition",
  "content-length",
  "content-type",
  "etag",
];

export async function proxyToSites(request: Request, apiPath: string) {
  const origin = process.env.SITES_ORIGIN?.replace(/\/+$/, "");
  const bearer = process.env.SITES_BEARER_TOKEN;
  if (!origin || !bearer) {
    return Response.json(
      { error: "Ponte de dados ainda não configurada." },
      { status: 503 },
    );
  }

  const incomingUrl = new URL(request.url);
  const target = new URL(`${origin}${apiPath}`);
  target.search = incomingUrl.search;
  const headers = new Headers({
    "OAI-Sites-Authorization": `Bearer ${bearer}`,
  });
  for (const name of forwardedRequestHeaders) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const method = request.method.toUpperCase();
  const body = ["GET", "HEAD"].includes(method)
    ? undefined
    : await request.arrayBuffer();
  const upstream = await fetch(target, {
    method,
    headers,
    body,
    cache: "no-store",
    redirect: "manual",
  });
  const responseHeaders = new Headers();
  for (const name of forwardedResponseHeaders) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}
