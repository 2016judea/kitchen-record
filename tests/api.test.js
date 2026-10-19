// The API's gate, driven with a fake (req, res) the way Vercel calls it. No network.
//   node --test tests/*.test.js
const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");
const fs = require("node:fs");
const crypto = require("node:crypto");

process.env.ACCESS_SECRET = "test-secret-not-the-real-one";
process.env.STRIPE_SECRET_KEY = "sk_test_unused";
process.env.FULL_DIR = path.join(__dirname, "..", "private", "bundle");
const lib = require("../site/api/_lib.js");
const data = require("../site/api/data.js");
const checkout = require("../site/api/checkout.js");
const status = require("../site/api/session-status.js");

function res() {
  const r = { code: 200, headers: {}, body: null };
  r.status = (c) => { r.code = c; return r; };
  r.setHeader = (k, v) => { r.headers[k.toLowerCase()] = v; };
  r.json = (o) => { r.body = o; return r; };
  r.end = (b) => { r.body = b; return r; };
  return r;
}
const req = (q = {}, headers = {}, method = "GET") => ({ query: q, headers, method });
const have = fs.existsSync(path.join(process.env.FULL_DIR, "full.json.gz"));

test("a password we never issued fails the HMAC without a network call", () => {
  assert.equal(lib.checkPassword("AAAA-BBBB-CCCC"), null);
  assert.equal(lib.checkPassword(""), null);
  assert.equal(lib.checkPassword("short"), null);
});

test("a minted password round-trips, in any case or spacing", () => {
  const { nonce, password } = lib.newPassword();
  assert.match(password, /^[23456789BCDFGHJKMNPQRSTVWXYZ]{4}-[23456789BCDFGHJKMNPQRSTVWXYZ]{4}-[23456789BCDFGHJKMNPQRSTVWXYZ]{4}$/);
  assert.deepEqual(lib.checkPassword(password), { nonce, kind: "paid" });
  assert.deepEqual(lib.checkPassword(password.toLowerCase().replace(/-/g, " ")), { nonce, kind: "paid" });
});

test("GET /api/data with no password is 401", async () => {
  const r = res();
  await data(req({ id: "LIC386562" }), r);
  assert.equal(r.code, 401);
  assert.match(r.body.error, /password/);
});

test("GET /api/data with a wrong password is 401", async () => {
  const r = res();
  await data(req({ id: "LIC386562" }, { "x-password": "ZZZZ-ZZZZ-ZZZZ" }), r);
  assert.equal(r.code, 401);
});

test("a comp password opens one restaurant's paid part and nothing free leaks back", { skip: !have && "no bundle" }, async () => {
  // comp passwords are HMAC under the "comp:" domain; mint one the way fulfil.py --comp-password does
  const ALPHA = "23456789BCDFGHJKMNPQRSTVWXYZ";
  const nonce = "QQQQQ";
  const mac = Array.from(crypto.createHmac("sha256", process.env.ACCESS_SECRET).update("comp:" + nonce).digest().subarray(0, 7), (b) => ALPHA[b % ALPHA.length]).join("");
  const pw = nonce + mac;
  assert.deepEqual(lib.checkPassword(pw), { nonce, kind: "comp" });
  const meta = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "site", "public", "meta.json")));
  const r = res();
  await data(req({ id: meta.example }, { "x-password": pw }), r);
  assert.equal(r.code, 200, JSON.stringify(r.body));
  assert.equal(r.headers["x-access"], "comp");
  assert.equal(r.headers["cache-control"], "private, no-store");
  assert.ok(Array.isArray(r.body.fix) && r.body.fix.length >= 2);
  assert.ok(r.body.fix[0].checks && r.body.fix[0].fix);
  assert.ok(r.body.risk && typeof r.body.risk.rate === "number");
  assert.ok(r.body.peers.some((p) => p.me));
  const bad = res();
  await data(req({ id: "LIC0000000" }, { "x-password": pw }), bad);
  assert.equal(bad.code, 404);
  const ugly = res();
  await data(req({ id: "../etc" }, { "x-password": pw }), ugly);
  assert.equal(ugly.code, 400);
});

test("POST only on /api/checkout", async () => {
  const r = res();
  await checkout(req({}, {}, "GET"), r);
  assert.equal(r.code, 405);
});

test("session-status rejects a malformed session id", async () => {
  const r = res();
  await status(req({ session_id: "nope" }), r);
  assert.equal(r.code, 400);
});

test("the product id matches the router registration name", () => {
  assert.equal(lib.PRODUCT, "kitchen-record");
  assert.equal(lib.offer.price_usd, JSON.parse(fs.readFileSync(path.join(__dirname, "..", "site", "public", "meta.json"))).price_usd);
});
