# Kitchen Inspection Record — the ideal data model

Written 2026-10-18 before the data was pulled (BUSINESS.md rule 5). The need:
a Minneapolis restaurant owner pastes their address and learns, before the
inspector comes back, what the inspector will check and what to fix. The step
taken over is *knowing what to fix before the next visit*.

## Entities

### Restaurant
One licensed food business the city inspects.

| field | answers |
|---|---|
| `id` | the city's licence number, so two "Pho 79"s stay apart |
| `name`, `address` | what the owner pastes in, and what the inspector writes down |
| `neighbourhood` | who the peers are (the city's own neighbourhood name) |
| `category`, `risk_level` | is this a restaurant, and how often the city comes (risk 3 = most often) |
| `lat`, `lon` | map it; nearest peers if the neighbourhood is thin |

### Inspection
One visit by the inspector.

| field | answers |
|---|---|
| `id`, `restaurant_id`, `date` | which visit, whose, when |
| `type` | Routine (scheduled), Follow-Up (they came back), Verification (checking one fix) |
| `score` | the number the owner remembers; 100 minus points taken |
| `result` | complete / closed / other |
| `p1_count`, `p2_count`, `p3_count` | how bad the visit was, by priority |

### Violation
One line the inspector wrote.

| field | answers |
|---|---|
| `inspection_id`, `code` | which visit, which rule (`MN Rule 4626.xxxx`) |
| `priority` | 1 = can make someone sick, 2 = helps prevent that, 3 = housekeeping |
| `code_text` | the rule in the city's words |
| `inspector_comment` | what the inspector actually saw |
| `status` | corrected on site, or still open |
| `points` | what it cost on the score |

### Code (the fix dictionary)
One rule, explained once.

| field | answers |
|---|---|
| `code` | the key |
| `plain` | the rule in 5th-grade English |
| `inspector_checks` | what the inspector physically does to check it on the follow-up |
| `fix` | what to do today so it passes |
| `n_restaurants`, `n_hits` | how common it is across the city (so "everyone gets this one" is a true sentence) |

### Neighbourhood peer set
Every restaurant in the same city neighbourhood.

| field | answers |
|---|---|
| `neighbourhood`, `n_restaurants` | is the peer set big enough to mean anything (≥15) |
| `score_p10`, `score_p50`, `score_p90` | where you sit: below p10 is the bottom tenth of your block |
| `p1_rate` | share of routine inspections there with at least one Priority-1 |
| `top_codes[]` | what your neighbours keep getting written up for |

## Derived, per restaurant

| field | answers | from |
|---|---|---|
| `score_history[]` | the line on the chart | Inspection.score by date, Routine only |
| `repeated_p1[]` | codes written up on ≥2 of your inspections, with how many times and the last date | Violation grouped by code |
| `most_repeated` | the one sentence of the free slice | top of `repeated_p1` by count, then recency |
| `fix_list[]` | each repeated code → plain, inspector_checks, fix, last comment | `repeated_p1` × Code |
| `followup_risk` | will they come back after your next routine? | the city's own rule (score ≤ 91 → follow-up) applied to your last score + your history of follow-ups |
| `peer_rows[]` | the named comparison table | Restaurant × latest Inspection for the same neighbourhood |

## Joins
Restaurant 1—n Inspection 1—n Violation n—1 Code. Restaurant n—1 Neighbourhood.

## Free vs paid

Free: `score_history`, neighbourhood `score_p10/50/90`, `most_repeated` (code + plain).
Paid: `fix_list`, `followup_risk`, `peer_rows`, the full `repeated_p1`.

## Reality check (filled in after the pull — see below)

Filled 2026-10-18 from the City of Minneapolis Food_Inspections ArcGIS layer
(open public record, 48,811 violation-rows, 2023-01-03 → 2026-10-16).

| field | status |
|---|---|
| Restaurant.* | filled. `HealthFacilityIDNumber`, `BusinessName`, `FullAddress`, `Neighborhood`, `FacilityCategory`, `RiskLevel`, lat/lon. |
| Inspection.type/score/date | filled. `InspectionResult` is always "Complete": **no closure flag exists** in the public layer. Closures are not published here. |
| Inspection.p1/p2/p3 counts | filled, counted from violation rows. An inspection with no violations is one row with null violation fields. |
| Violation.* | filled, including `InspectorComments` and `ViolationStatus`. |
| Code.plain / inspector_checks / fix | hand-written for the codes that cover the repeated Priority-1 cases (`scripts/codes.py`); every other code falls back to the city's `FoodCodeText`, which is already plain. |
| Neighbourhood peers | filled; 32 neighbourhoods have ≥15 restaurants, the rest show the city-wide spread, labelled. |
| followup_risk | filled from the city's published rule (score ≤ 91 → follow-up) plus the restaurant's own follow-up count. **Not a model**; a rule and a count. |
| Closure / licence action | **cannot be filled** from the public layer. The page never claims it. |

Nothing in the ideal model was dropped to fit the data; the one field reality
lacks (closure) was an input to the price, not to the product, and the price
arithmetic in README uses the follow-up instead.
