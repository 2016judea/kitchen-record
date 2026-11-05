# Kitchen Inspection Record

**Live:** https://kitchen-record.vercel.app

A Minneapolis restaurant owner types their address. They get their health inspection
scores against their neighbourhood, and the one Priority-1 line the inspector keeps
writing them up for, in plain words. The full record turns every repeated line into the
fix list the inspector checks on the follow-up, says how likely the follow-up is, and
names the neighbours.

The step taken over: knowing what to fix before the next visit.

## What it is built on

The City of Minneapolis Food Inspections layer (Open Data, ArcGIS, public record): every
violation line from every routine, follow-up and verification inspection since
2023-01-03, with the inspector's own comment. `scripts/fetch.py` pulls it fresh (cached
per day in `data/cache/`), `scripts/build.py` turns it into the model in `DATA_MODEL.md`.

Numbers on 2026-10-19: 1,552 restaurants, 4,531 routine inspections through 2026-10-13;
656 restaurants repeat the same Priority-1 code on two or more visits; 32 neighbourhoods
with 15 or more restaurants. Restaurant routine scores: bottom tenth 84, median 94, top
tenth 100. The city's rule (its own page, read 2026-10-18): a follow-up is done at 91 or
lower, about 14 days later, to check the fixes. Measured here: 88 in 100 routine
inspections at 91 or lower got a follow-up within 45 days; 1 in 100 above 91 did.

No number on the page is typed. The plain-English fixes (`scripts/codes.py`) are ours,
written against the Minnesota Food Code text the city prints with each line; everything
else is the city's record or arithmetic on it.

## Free vs paid

Free, for any restaurant: the score history against the neighbourhood's bottom tenth,
median and top tenth (blue = yours, sand = your neighbours), the most-repeated
Priority-1 line in plain words, and the counts of repeated lines and follow-ups.

Paid, one price: the fix list (each repeated line → what the inspector checks → what to
do, with the inspector's last comment), the follow-up risk, and the named peer table.
The password unlocks every restaurant, so a group or a consultant buys once.

## Price

**$40, once.** Hypothesis, 2026-10-19. One use is one follow-up visit avoided. The city
does not publish a Minneapolis reinspection fee; the state framework (MN Stat. 28A.085)
sets a reinspection at the greater of half the licence fee or $500 for the firms it
licenses, and a follow-up costs the owner a manager's half day plus the rushed fixes.
Call one avoided follow-up about $400; a tenth of that is $40. Revise on evidence:
checkouts opened vs paid, by variant (see Distribution).

## The paywall

Ported from `~/Desktop/workspace/msp-house-index` (product-paywall skill). Only `site/public/` is served
statically (the free slice `site/public/data/free.json` and `site/public/meta.json`); `scripts/build.py` writes the paid
part to `private/bundle/full.json.gz` (gitignored), which `scripts/deploy.py` uploads as
`api/_full/`, read only by `/api/data`. With `outputDirectory: "."` that file was a public URL
(`/api/%5Ffull/full.json.gz`, 200, found and closed 2026-10-19); `tests/test_paywall.py` pins it.

| route | does |
|---|---|
| `POST /api/checkout` | Stripe embedded Checkout on the Brick & Mortar account; mints the buyer's password (nonce + HMAC under `ACCESS_SECRET`) into the session metadata and the invoice footer |
| `POST /api/stripe-webhook` | `checkout.session.completed`, delivered through `~/Desktop/workspace/stripe-router` (no per-product endpoint): emails the password once, and Aidan a sale notice |
| `GET /api/session-status` | the return page: paid or not; sends the password email if the webhook has not |
| `GET /api/data?id=LIC…` | password in `x-password`: one restaurant's fix list, risk and peers; without `id`, all of them |

Vercel env: `ACCESS_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` (router),
`MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, `MAILGUN_FROM`, `SITE_URL`, `NOTIFY_EMAIL`.
A lost password: `python scripts/fulfil.py <session_id>`; every sale: `--recent`; a
$0 end-to-end: `--comp`; a password with no session: `--comp-password <label>`.

Analytics: Vercel Web Analytics (enabled on the project, tag in the page) and the shared
PostHog block. Events: `preview_open` (with the A/B variant), `search`,
`open_restaurant`, `checkout_open`, `password_open`, `unlock`, `paid`.

## Run it

```bash
uv sync
make fetch      # ~1 min: 25 pages from the city's ArcGIS layer, cached per day
make build      # seconds: site/data/free.json, site/meta.json, private/bundle/full.json.gz
make test       # pytest + node --test, logs in data/pytest.log and data/node.log
node scripts/serve_local.mjs   # the real page and API handlers on :8787
make deploy     # REST upload to Vercel (VERCEL_TOKEN from ~/Desktop/workspace/bricks/.env)
```

## Distribution

Round 1 is drafted, not sent, in `outreach/round1/` (gitignored ledger and drafts): 50
recipients, 39 restaurants, 6 restaurant groups, 5 food-safety trainers. Every email was read on
the recipient's own site on 2026-10-19 (`outreach/verify_sites.py`; Overture's listing email was
only a lead, and matched a DoubleTree to starbucks.com), deduped against the outreach ledger by
address and domain. `outreach/draft_round1.py` writes them; `scripts/build_for.py` ships the
token map. Trainers have no inspection row of their own, so their page opens on the worked
example and their opener quotes their own course page. Three
segments: Minneapolis restaurants with an email on their own site or listing, restaurant
groups and commissaries, and Minnesota food-safety consultants and trainers. Each
recipient's `/for/<token>/` page opens on their own restaurant; a recipient with no
inspection row of their own is held, never sent the example.

**A/B, one variable, pooled across the seven products shipped 2026-10-18/19:** variant A
names the price in the email; variant B leaves it to the page. Alternated within each
segment; `variant` is in the ledger and fired on `preview_open`, never in the URL.
Hypothesis: naming the price in the email lowers clicks and raises paid-per-click. Read
at day 3: visits, `checkout_open`, `paid`, replies, by variant and pooled.

## What the ideal model could not fill

Closures and licence actions are not in the public layer (`InspectionResult` is always
"Complete"); the page never claims them. See `DATA_MODEL.md`.

Private repo: the paid bundle was never committed, but the free slice and the dictionary
are the product's substance, and the outreach ledger stays local.
