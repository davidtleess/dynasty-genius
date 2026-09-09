import assert from "node:assert/strict";
import test from "node:test";
import { bridgeTrackRecord } from "../src/lib/dg/track-record-bridge.server.ts";

const env = {
  DG_TRACK_RECORD_MODE: "loopback",
  DG_TRACK_RECORD_UPSTREAM: "http://127.0.0.1:8800",
  HOST: "127.0.0.1",
};
const url = "http://127.0.0.1:8798/api/private/track-record";
function request(method = "GET", headers: Record<string, string> = {}, body?: string) {
  return new Request(url + (method === "POST" ? "/capture" : ""), {
    method,
    headers: { host: "127.0.0.1:8798", ...headers },
    ...(body === undefined ? {} : { body }),
  });
}

test("bridge disabled by default, without touching upstream", async () => {
  let called = false;
  const response = await bridgeTrackRecord(request(), {
    env: {},
    fetcher: async () => {
      called = true;
      return new Response("{}");
    },
  });
  assert.equal(response.status, 503);
  assert.equal(called, false);
});

test("only explicit local binding and upstream accepted", async () => {
  for (const changed of [
    { HOST: "0.0.0.0" },
    { DG_TRACK_RECORD_UPSTREAM: "https://example.com" },
    { DG_TRACK_RECORD_UPSTREAM: "http://127.0.0.1:8800/private" },
    { DG_TRACK_RECORD_UPSTREAM: "http://secret@127.0.0.1:8800" },
  ]) {
    const response = await bridgeTrackRecord(request(), {
      env: { ...env, ...changed },
      fetcher: async () => {
        throw Error("must not fetch");
      },
    });
    assert.equal(response.status, 503);
  }
});

test("external host or origin and cross-site fetch refuse before reading data", async () => {
  for (const headers of [
    { host: "attacker.example" },
    { origin: "https://attacker.example" },
    { "sec-fetch-site": "cross-site" },
  ]) {
    const response = await bridgeTrackRecord(request("GET", headers), {
      env,
      fetcher: async () => {
        throw Error("must not fetch");
      },
    });
    assert.equal(response.status, 403);
  }
});

test("GET forwards only validated snapshot selection with no caching", async () => {
  const selected = "a".repeat(64);
  const req = new Request(url + "?snapshot_id=" + selected, {
    headers: { host: "127.0.0.1:8798" },
  });
  let seen = "";
  const response = await bridgeTrackRecord(req, {
    env,
    fetcher: async (input, init) => {
      seen = String(input);
      assert.equal(init?.redirect, "manual");
      assert.equal(init?.cache, "no-store");
      return new Response('{"ok":true}', { headers: { "content-type": "application/json" } });
    },
  });
  assert.equal(seen, "http://127.0.0.1:8800/api/research/track-record?snapshot_id=" + selected);
  assert.match(response.headers.get("cache-control") ?? "", /no-store/);
  assert.deepEqual(await response.json(), { ok: true });
});

test("arbitrary query paths and methods rejected", async () => {
  for (const req of [
    new Request(url + "?upstream=https://attacker.example", {
      headers: { host: "127.0.0.1:8798" },
    }),
    new Request(url + "?snapshot_id=..", { headers: { host: "127.0.0.1:8798" } }),
    request("DELETE"),
  ]) {
    const response = await bridgeTrackRecord(req, {
      env,
      fetcher: async () => {
        throw Error("must not fetch");
      },
    });
    assert.ok([400, 405].includes(response.status));
  }
});

test("capture requires same origin and JSON and preserves actual partial-success body", async () => {
  const noOrigin = await bridgeTrackRecord(
    request("POST", { "content-type": "application/json" }, "{}"),
    { env },
  );
  assert.equal(noOrigin.status, 403);
  const body = '{"snapshot_status":"saved","enrollment_status":"input_unavailable"}';
  const response = await bridgeTrackRecord(
    request(
      "POST",
      { "content-type": "application/json", origin: "http://127.0.0.1:8798" },
      '{"expected":{}}',
    ),
    {
      env,
      fetcher: async (input, init) => {
        assert.equal(String(input), "http://127.0.0.1:8800/api/research/track-record/capture");
        assert.equal(init?.body, '{"expected":{}}');
        return new Response(body, { headers: { "content-type": "application/json" } });
      },
    },
  );
  assert.equal(await response.text(), body);
});

test("redirect, timeout and non-JSON upstream do not leak internal details", async () => {
  for (const fetcher of [
    async () =>
      new Response(null, { status: 302, headers: { location: "https://external.example" } }),
    async () => {
      throw Error("private secret/path");
    },
    async () => new Response("private secret/path"),
  ]) {
    const response = await bridgeTrackRecord(request(), { env, fetcher });
    assert.equal(response.status, 503);
    assert.doesNotMatch(await response.text(), /secret|external\.example/);
  }
});
