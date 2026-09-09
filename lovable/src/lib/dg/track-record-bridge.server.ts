/** Explicitly enabled loopback transport. Hosted runtimes have no archive access by default. */
type BridgeOptions = {
  env?: Record<string, string | undefined>;
  fetcher?: typeof fetch;
};

function reply(status: number, detail: string) {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: {
      "content-type": "application/json",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
    },
  });
}

export async function bridgeTrackRecord(
  request: Request,
  options: BridgeOptions = {},
): Promise<Response> {
  const env = options.env ?? (typeof process === "undefined" ? {} : process.env);
  const binding = env["NITRO_HOST"] ?? env["HOST"];
  if (env["DG_TRACK_RECORD_MODE"] !== "loopback" || binding !== "127.0.0.1")
    return reply(503, "Saved readings are not connected in this session.");
  let upstream: URL;
  try {
    upstream = new URL(env["DG_TRACK_RECORD_UPSTREAM"] ?? "");
    if (
      upstream.protocol !== "http:" ||
      upstream.hostname !== "127.0.0.1" ||
      !upstream.port ||
      upstream.pathname !== "/" ||
      upstream.search ||
      upstream.hash ||
      upstream.username ||
      upstream.password
    )
      throw Error("Only an explicit loopback service is allowed");
  } catch {
    return reply(503, "Saved readings are not connected in this session.");
  }
  const incoming = new URL(request.url);
  const origin = request.headers.get("origin");
  const site = request.headers.get("sec-fetch-site");
  if (
    incoming.protocol !== "http:" ||
    !["127.0.0.1", "localhost"].includes(incoming.hostname) ||
    request.headers.get("host") !== incoming.host ||
    (origin !== null && origin !== incoming.origin) ||
    (site !== null && !["same-origin", "none"].includes(site))
  )
    return reply(403, "This request must come from the local Dynasty Genius page.");
  if (!["GET", "POST"].includes(request.method)) return reply(405, "This action is not supported.");
  const capture = request.method === "POST";
  const expectedPath = "/api/private/track-record" + (capture ? "/capture" : "");
  if (
    incoming.pathname !== expectedPath ||
    [...incoming.searchParams.keys()].some((key) => key !== "snapshot_id") ||
    incoming.searchParams.getAll("snapshot_id").length > 1 ||
    (capture && incoming.search)
  )
    return reply(400, "The saved-reading request is invalid.");
  const selected = incoming.searchParams.get("snapshot_id");
  if (selected !== null && !/^[a-f0-9]{64}$/.test(selected))
    return reply(400, "The saved-reading selection is invalid.");
  let body: string | undefined;
  if (capture) {
    if (origin !== incoming.origin)
      return reply(403, "Saving must start from the local Dynasty Genius page.");
    if (!request.headers.get("content-type")?.toLowerCase().startsWith("application/json"))
      return reply(415, "The save request must be JSON.");
    body = await request.text();
    if (new TextEncoder().encode(body).length > 8192)
      return reply(413, "The save request is too large.");
    try {
      JSON.parse(body);
    } catch {
      return reply(400, "The save request is invalid.");
    }
  }
  const endpoint = new URL("/api/research/track-record" + (capture ? "/capture" : ""), upstream);
  if (selected) endpoint.searchParams.set("snapshot_id", selected);
  try {
    const response = await (options.fetcher ?? fetch)(endpoint, {
      method: request.method,
      ...(body === undefined ? {} : { body }),
      headers: capture ? { "content-type": "application/json" } : { accept: "application/json" },
      redirect: "manual",
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    if (
      (response.status >= 300 && response.status < 400) ||
      !response.headers.get("content-type")?.includes("application/json")
    )
      return reply(503, "Saved readings could not be reached. No other reading was substituted.");
    // Backend errors are deliberately generic. Preserve 409 and partial-success semantics.
    return new Response(await response.text(), {
      status: response.status,
      headers: {
        "content-type": "application/json",
        "cache-control": "no-store",
        "x-content-type-options": "nosniff",
      },
    });
  } catch {
    return reply(
      503,
      capture
        ? "The save response could not be confirmed. Refresh saved readings before trying again."
        : "Saved readings could not be reached. No other reading was substituted.",
    );
  }
}
