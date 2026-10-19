#!/usr/bin/env python3
"""The paywall's backup, run by hand. Nothing here emails anyone.

    python scripts/fulfil.py cs_live_...     # a buyer lost their password: reprint it
    python scripts/fulfil.py --recent        # every session of ours since launch, paid or not
    python scripts/fulfil.py --comp          # a $0 checkout link that unlocks like a paid one
                                             # (a friend, a press copy, or an end-to-end test)
    python scripts/fulfil.py --comp-password <label>   # a password that unlocks with no Stripe session

The password lives in the session's metadata (minted by site/api/checkout.js) and in the
invoice footer Stripe emailed the buyer. Reads STRIPE_SECRET_KEY from ~/Desktop/bricks/.env
and ACCESS_SECRET from ./.env. Ported from ~/Desktop/msp-house-index/scripts/fulfil.py.
"""
import hashlib, hmac, json, secrets, sys
from datetime import date
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
OFFER = json.loads((ROOT / "site" / "offer.json").read_text())
SITE, PRODUCT = OFFER["site"], OFFER["product"]
ALPHA = "23456789BCDFGHJKMNPQRSTVWXYZ"  # same as site/api/_lib.js
LAUNCH = 1792368000


def env(path, key):
    for line in Path(path).expanduser().read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{key} missing from {path}")


def password(nonce, domain=""):
    mac = hmac.new(env(ROOT / ".env", "ACCESS_SECRET").encode(), (domain + nonce).encode(), hashlib.sha256).digest()
    raw = nonce + "".join(ALPHA[b % len(ALPHA)] for b in mac[:7])
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def stripe_session():
    s = requests.Session()
    s.auth = (env("~/Desktop/bricks/.env", "STRIPE_SECRET_KEY"), "")
    return s


def stripe(S, path, **form):
    r = S.post(f"https://api.stripe.com/v1/{path}", data=form) if form else S.get(f"https://api.stripe.com/v1/{path}")
    j = r.json()
    if "error" in j:
        sys.exit(f"stripe: {j['error'].get('message')}")
    return j


def show(s):
    m = s.get("metadata") or {}
    email = (s.get("customer_details") or {}).get("email")
    print(f"{s['id']}\n  status   {s['status']} / {s['payment_status']}  ${(s.get('amount_total') or 0) / 100:.2f}"
          f"\n  email    {email}\n  password {m.get('password')}\n  link     {SITE}/?pw={m.get('password')}"
          f"\n  emailed  {m.get('pw_emailed') or 'NOT YET'}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    if arg == "--comp-password":
        label = sys.argv[2] if len(sys.argv) > 2 else "comp"
        nonce = "".join(secrets.choice(ALPHA) for _ in range(5))
        pw = password(nonce, "comp:")
        log = ROOT / "private" / "comp_passwords.csv"
        log.parent.mkdir(exist_ok=True)
        with log.open("a") as f:
            f.write(f"{date.today()},{nonce},{label}\n")
        print(f"comp password for {label}: {pw}\n{SITE}/?pw={pw}")
        sys.exit()
    S = stripe_session()
    if arg == "--recent":
        for s in stripe(S, f"checkout/sessions?limit=100&created[gte]={LAUNCH}")["data"]:
            if (s.get("metadata") or {}).get("product") == PRODUCT:
                show(s)
    elif arg == "--comp":
        coupon = "KITCHEN-RECORD-COMP"
        if "error" in S.get(f"https://api.stripe.com/v1/coupons/{coupon}").json():
            stripe(S, "coupons", id=coupon, percent_off=100, duration="once", name="Kitchen Inspection Record comp")
        nonce = "".join(secrets.choice(ALPHA) for _ in range(5))
        pw = password(nonce)
        s = stripe(S, "checkout/sessions", **{
            "mode": "payment", "line_items[0][quantity]": 1,
            "line_items[0][price_data][currency]": "usd", "line_items[0][price_data][unit_amount]": OFFER["price_usd"] * 100,
            "line_items[0][price_data][product_data][name]": OFFER["name"],
            "discounts[0][coupon]": coupon, "customer_creation": "always",
            "metadata[product]": PRODUCT, "metadata[pw_nonce]": nonce, "metadata[password]": pw, "metadata[comp]": "1",
            "success_url": f"{SITE}/?paid={{CHECKOUT_SESSION_ID}}",
        })
        print(f"comp checkout (no card, $0): {s['url']}\nsession {s['id']}  password {pw}")
    else:
        show(stripe(S, f"checkout/sessions/{arg}"))
