export default {
  async fetch(request, env) {
    const origin = String(env.ORIGIN_URL || "").trim().replace(/\/$/, "");

    if (!origin) {
      return new Response("Cloudflare edge is not configured: ORIGIN_URL is missing.", {
        status: 503,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    const incoming = new URL(request.url);
    const target = new URL(incoming.pathname + incoming.search, origin);

    const headers = new Headers(request.headers);
    headers.set("X-Forwarded-Host", incoming.host);
    headers.set("X-Forwarded-Proto", "https");

    const upstreamRequest = new Request(target.toString(), {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    });

    const response = await fetch(upstreamRequest);
    const output = new Response(response.body, response);

    // Do not cache authenticated or state-changing application responses at the edge.
    if (request.method !== "GET" && request.method !== "HEAD") {
      output.headers.set("Cache-Control", "no-store");
    }

    return output;
  },
};
