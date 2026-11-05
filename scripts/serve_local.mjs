// Local server for driving the real page and the real API handlers (no `vercel` CLI on this Mac).
//   node scripts/serve_local.mjs [port]
// Serves site/public/ statically, rewrites /for/<token> to index.html like site/vercel.json, and routes
// /api/<name> to site/api/<name>.js with a Vercel-shaped (req, res). FULL_DIR points /api/data at
// private/bundle/. Env comes from ./.env plus ~/Desktop/workspace/bricks/.env (Stripe/Mailgun) if present.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SITE = path.join(ROOT, "site");
const PUB = path.join(SITE, "public"); // the only static tree, like outputDirectory "public"
const require = createRequire(import.meta.url);
for (const f of [path.join(ROOT, ".env"), path.join(process.env.HOME, "Desktop/workspace/bricks/.env")]) {
  if (!fs.existsSync(f)) continue;
  for (const line of fs.readFileSync(f, "utf8").split("\n")) {
    const m = /^([A-Z_]+)=(.*)$/.exec(line.trim());
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
}
process.env.FULL_DIR ||= path.join(ROOT, "private", "bundle");
process.env.SITE_URL ||= `http://localhost:${process.argv[2] || 8787}`;
const TYPES = { ".html": "text/html; charset=utf-8", ".json": "application/json", ".js": "text/javascript", ".webp": "image/webp", ".png": "image/png", ".css": "text/css" };

function shapeRes(res) {
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (o) => { res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(o)); return res; };
  return res;
}

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, "http://x");
  if (u.pathname.startsWith("/api/")) {
    const name = u.pathname.slice(5).replace(/[^a-z-]/g, "");
    const mod = path.join(SITE, "api", name + ".js");
    if (!fs.existsSync(mod)) return shapeRes(res).status(404).json({ error: "no such route" });
    req.query = Object.fromEntries(u.searchParams);
    try { await require(mod)(req, shapeRes(res)); } catch (e) { console.error(e); shapeRes(res).status(500).json({ error: e.message }); }
    return;
  }
  let p = u.pathname;
  if (/^\/for\/[^/]+\/?$/.test(p) || p === "/") p = "/index.html";
  if (p.startsWith("/api/_full")) { res.statusCode = 302; res.setHeader("Location", "/"); return res.end(); }
  const f = path.join(PUB, path.normalize(p));
  if (!f.startsWith(PUB) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.statusCode = 404; return res.end("not found"); }
  res.setHeader("Content-Type", TYPES[path.extname(f)] || "application/octet-stream");
  fs.createReadStream(f).pipe(res);
});
const port = Number(process.argv[2] || 8787);
server.listen(port, () => console.log(`kitchen-record on http://localhost:${port}  (FULL_DIR=${process.env.FULL_DIR})`));
