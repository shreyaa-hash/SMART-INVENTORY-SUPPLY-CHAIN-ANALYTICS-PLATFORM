import test from "node:test";
import assert from "node:assert/strict";
import { apiGet, downloadCsv } from "../src/services/api.js";

test("apiGet sends filters and parses live JSON", async () => {
  const originalFetch = globalThis.fetch;
  let requestUrl = "";
  globalThis.fetch = async (url) => {
    requestUrl = url;
    return { ok: true, json: async () => ({ value: 12 }) };
  };
  try {
    assert.deepEqual(await apiGet("/api/products", { offset: 10, empty: "" }), { value: 12 });
    assert.match(requestUrl, /offset=10/);
    assert.doesNotMatch(requestUrl, /empty/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("apiGet surfaces backend errors instead of success-shaped fallbacks", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({ detail: "Database unavailable" }) });
  try {
    await assert.rejects(apiGet("/api/health"), /Database unavailable/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("downloadCsv quotes values and triggers a named CSV download", async () => {
  const originalDocument = globalThis.document;
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;
  let blob;
  let revokedUrl;
  const link = { clickCalled: false, click() { this.clickCalled = true; } };
  globalThis.document = { createElement: (tag) => {
    assert.equal(tag, "a");
    return link;
  } };
  URL.createObjectURL = (value) => {
    blob = value;
    return "blob:csv-test";
  };
  URL.revokeObjectURL = (value) => { revokedUrl = value; };
  try {
    downloadCsv("report.csv", [{ name: "A,B", note: 'a "quote"' }]);
    assert.equal(link.download, "report.csv");
    assert.equal(link.clickCalled, true);
    assert.equal(revokedUrl, "blob:csv-test");
    assert.equal(await blob.text(), '"name","note"\r\n"A,B","a ""quote"""');
  } finally {
    if (originalDocument === undefined) delete globalThis.document;
    else globalThis.document = originalDocument;
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  }
});
