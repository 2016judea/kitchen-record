// GET /api/data?id=<licence>  -> one restaurant's paid part: fix list, follow-up risk, peer table
// GET /api/data               -> every restaurant's paid part (gzipped JSON)
// Password in the x-password header (or ?pw=). The data is bundled with this function
// (api/_full/, uploaded by scripts/deploy.py from private/bundle/), never in public site/.
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");
const { checkPassword, nonceIsPaid } = require("./_lib");

const DIR = process.env.FULL_DIR || path.join(__dirname, "_full");
let FULL_GZ = null, FULL = null;

module.exports = async (req, res) => {
  const pw = req.headers["x-password"] || req.query.pw;
  const ok = checkPassword(pw);
  if (!ok) return res.status(401).json({ error: "That password didn't match. Check the email from Brick & Mortar, or reply to it for help." });
  try {
    if (ok.kind === "paid" && !(await nonceIsPaid(ok.nonce))) return res.status(402).json({ error: "That password's payment hasn't gone through. If you just paid, wait a minute and try again." });
  } catch (e) {
    console.error("[data] paid check:", e.message);
    return res.status(502).json({ error: "Couldn't check the password right now. Try again in a minute." });
  }
  res.setHeader("Cache-Control", "private, no-store");
  res.setHeader("X-Access", ok.kind);
  FULL_GZ ??= fs.readFileSync(path.join(DIR, "full.json.gz"));
  const id = String(req.query.id || "");
  if (!id) {
    console.log(`[unlock] ${ok.kind} ${ok.nonce} all`);
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Content-Encoding", "gzip");
    return res.status(200).end(FULL_GZ);
  }
  if (!/^[A-Z0-9]{1,20}$/.test(id)) return res.status(400).json({ error: "bad id" });
  FULL ??= JSON.parse(zlib.gunzipSync(FULL_GZ));
  const d = FULL[id];
  if (!d) return res.status(404).json({ error: "no such restaurant" });
  console.log(`[unlock] ${ok.kind} ${ok.nonce} ${id}`);
  res.status(200).json(d);
};
