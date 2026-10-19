#!/usr/bin/env python3
"""Deploy site/ to Vercel over the REST API (no CLI). Needs VERCEL_TOKEN (~/Desktop/bricks/.env).
site/ is the free slice plus api/; private/bundle/ (the paid part) goes up as api/_full/,
bundled with /api/data only. outputDirectory is "public": with "." every uploaded file,
api/_full/ included, was a static URL (/api/%5Ffull/full.json.gz answered 200, 2026-10-19).
Ported from ~/Desktop/msp-house-index/scripts/deploy.py."""
import hashlib, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

TEAM = "team_XnhPzBEcaSfEmZFo9M2isLFY"
PROJECT = "kitchen-record"
ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BUNDLE = ROOT / "private" / "bundle"
API = "https://api.vercel.com"


def token():
    if os.environ.get("VERCEL_TOKEN"):
        return os.environ["VERCEL_TOKEN"]
    for line in (Path.home() / "Desktop/bricks/.env").read_text().splitlines():
        if line.startswith("VERCEL_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit("VERCEL_TOKEN missing")


H = {"Authorization": f"Bearer {token()}"}
S = requests.Session()
S.mount("https://", requests.adapters.HTTPAdapter(pool_maxsize=16))


def upload(item):
    p, rel = item
    b = p.read_bytes()
    sha = hashlib.sha1(b).hexdigest()
    for _ in range(4):
        try:
            r = S.post(f"{API}/v2/files?teamId={TEAM}", data=b, headers={**H, "x-vercel-digest": sha, "Content-Type": "application/octet-stream"}, timeout=60)
            if r.ok:
                break
        except requests.RequestException:
            pass
        time.sleep(2)
    else:
        sys.exit(f"upload failed: {p}")
    return {"file": rel, "sha": sha, "size": len(b)}


def main():
    assert (BUNDLE / "full.json.gz").exists(), "run make build: private/bundle/ is what the paywall serves"
    paths = [(p, str(p.relative_to(SITE))) for p in sorted(SITE.rglob("*")) if p.is_file() and not p.name.startswith(".") and "_full" not in p.parts]
    paths += [(p, "api/_full/" + str(p.relative_to(BUNDLE))) for p in sorted(BUNDLE.rglob("*")) if p.is_file()]
    with ThreadPoolExecutor(16) as ex:
        files = list(ex.map(upload, paths))
    print(f"uploaded {len(files)} files")
    d = requests.post(f"{API}/v13/deployments?teamId={TEAM}&forceNew=1", headers=H, json={
        "name": PROJECT, "project": PROJECT, "target": "production", "files": files,
        "projectSettings": {"framework": None, "buildCommand": "echo build", "outputDirectory": "public", "installCommand": "echo skip"},
    }).json()
    print("deployment", d.get("id"), d.get("readyState"), d.get("error"))
    s = {}
    for _ in range(200):
        s = requests.get(f"{API}/v13/deployments/{d['id']}?teamId={TEAM}", headers=H).json()
        if s.get("readyState") in ("READY", "ERROR"):
            break
        time.sleep(3)
    print("state", s.get("readyState"), "instantStatic", s.get("isInstantStatic"))
    prj = requests.get(f"{API}/v9/projects/{PROJECT}?teamId={TEAM}", headers=H).json()
    if not (prj.get("webAnalytics") or {}).get("enabledAt"):
        print("analytics", requests.post(f"{API}/web/insights/toggle?projectId={prj['id']}&teamId={TEAM}", headers=H, json={"value": True}).json())
    print("aliases", (prj.get("targets", {}).get("production") or {}).get("alias"))


if __name__ == "__main__":
    main()
