export default {
  async fetch(request, env) {
    const origin = String(env.ORIGIN_URL || "").trim().replace(/\/$/, "");

    if (!origin) {
      return new Response("Cloudflare edge is not configured: ORIGIN_URL is missing.", {
        status: 503,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    let originUrl;
    try {
      originUrl = new URL(origin);
    } catch {
      return new Response("Cloudflare edge is misconfigured: ORIGIN_URL is invalid.", {
        status: 500,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    if (originUrl.protocol !== "https:") {
      return new Response("Cloudflare edge is misconfigured: ORIGIN_URL must use HTTPS.", {
        status: 500,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    const incoming = new URL(request.url);
    const target = new URL(incoming.pathname + incoming.search, originUrl);

    const headers = new Headers(request.headers);
    headers.set("X-Forwarded-Host", incoming.host);
    headers.set("X-Forwarded-Proto", incoming.protocol.replace(":", ""));
    headers.set("X-Forwarded-Port", incoming.port || "443");

    // Prefer Cloudflare's verified client IP instead of trusting a client-supplied
    // X-Forwarded-For header.
    const clientIp = request.headers.get("CF-Connecting-IP");
    if (clientIp) {
      headers.set("X-Forwarded-For", clientIp);
    } else {
      headers.delete("X-Forwarded-For");
    }

    const upstreamRequest = new Request(target.toString(), {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    });

    let response;
    try {
      response = await fetch(upstreamRequest);
    } catch {
      return new Response("Origin is temporarily unavailable.", {
        status: 502,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    const output = new Response(response.body, response);

    // Keep redirects on the public Cloudflare hostname. This prevents login,
    // checkout, and other redirects from leaking the origin hostname.
    const location = response.headers.get("Location");
    if (location) {
      try {
        const redirectUrl = new URL(location, originUrl);
        if (redirectUrl.origin === originUrl.origin) {
          redirectUrl.protocol = incoming.protocol;
          redirectUrl.host = incoming.host;
          output.headers.set("Location", redirectUrl.toString());
        }
      } catch {
        // Leave non-URL Location values untouched.
      }
    }

    // Do not cache authenticated or state-changing application responses at the edge.
    if (request.method !== "GET" && request.method !== "HEAD") {
      output.headers.set("Cache-Control", "no-store");
    }

    return output;
  },
};
