# Sourcing notes — WP-3

**Checked 2026-09-30.** Prices and stock move. Everything here must be re-checked at the
moment you actually order, and the `verified` column in `bom.csv` says which lines were
looked up live and which are catalogue estimates.

| `verified` | Meaning |
|---|---|
| `LIVE` | Distributor page or listing read on 2026-09-30. Stock and price are real numbers from that day |
| `EST` | Catalogue-typical part and price. Not looked up. Commodity items — resistors, ceramics, TVS, fuses — where the risk is a few cents, not availability |
| `OPEN` | No part selected. A decision is required — **none remain** |

Thirteen lines were verified live: everything on the critical path, everything expensive,
and everything that turned out to be wrong.

---

## 1. Three things the spec got wrong

### 1.1 The specified MOSFET does not exist

`SPECIFICATION.md` §4.3.3 names **PSMN5R2-60YS**. There is no such Nexperia part. The real
one is **PSMN5R5-60YS** — same 5.2mΩ, same 60V, same LFPAK56 — and it is **out of stock at
LCSC** ($2.16, zero units).

**Substituted: Infineon BSC0702LS.** It is better on every axis that matters, and it is the
cheapest of the three:

| | PSMN5R5-60YS (spec'd) | **BSC0702LS (fitted)** |
|---|---|---|
| V_ds | 60V | 60V |
| R_ds(on) @ V_gs = 10V | 5.2mΩ max | **2.7mΩ max** |
| R_ds(on) @ V_gs = 4.5V | not characterised | **3.9mΩ max** |
| Q_g @ 10V | 56nC | **43nC** |
| Package | LFPAK56 | TDSON-8 (SuperSO8, 5×6mm) |
| LCSC stock | **0** | **8,427** |
| Price @ 10 | $2.16 | **$1.38** |

**The logic-level rating is the part that matters.** The LM5116 drives its gates from an
internal 7.4V rail, not 10V. A standard-level FET characterised only at 10V is being run
below its spec point, and you are guessing at the real R_ds(on). The BSC0702LS is
characterised at 4.5V as well, so 7.4V sits comfortably between two specified points and
the worst case is bounded by the 3.9mΩ figure rather than estimated.

**Effect on the loss budget** (§4.3.3, per channel at 7A, R_ds(on) hot = 1.5× the 4.5V max
figure = 5.85mΩ — deliberately the pessimistic end):

| | Spec'd | Fitted |
|---|---|---|
| HS conduction | 0.16W | 0.12W |
| LS conduction | 0.23W | 0.17W |
| Gate drive | 0.11W | 0.08W |

Roughly 0.13W per channel, 0.8W across six. Not significant — **switching loss still
dominates at 1.68W** and none of this changes that. The reason to prefer the part is
availability and a bounded worst case, not the 0.8W.

Recorded as **D-8** in `deviations.md`.

### 1.2 The inductor's ratings were misread — but the choice holds

`SPECIFICATION.md` §4.3.2.1 records the XAL1510-223 as "I_sat 18.7A, DCR 14.5mΩ".
Distributor listings say "14A, 0.016 Ω". Both are correct; they are **different
parameters**, and the spec quoted one of each:

| Parameter | Value | What it means |
|---|---|---|
| **I_sat** | **18.7A** | Current at which inductance drops 30%. The saturation limit |
| **I_rms** | **14A** | Current for a 40°C temperature rise. The thermal limit |
| DCR typ | 14.5mΩ | Typical |
| DCR max | **16mΩ** | Worst case — the number to design to |

**The 2.3× saturation margin claimed in §4.3.2.1 is real** (18.7A against an 8.04A peak),
and I_rms 14A against 7A RMS is a further 2× on the thermal limit. The part is correctly
chosen. The only correction is that the loss calculation should use the **16mΩ maximum**,
not the 14.5mΩ typical: conduction loss is **0.78W**, not 0.71W. Add 0.4W across six
channels to the chassis thermal budget. Still inside the 38W in `thermal.md`.

### 1.3 The cost model was wrong in both directions

| Line | Spec estimate | Actual | Delta |
|---|---|---|---|
| LM5116 | $5.13 | **$1.88** | −$3.25 |
| INA226 | $2.50 | **$0.63** | −$1.87 |
| MOSFETs ×2 | $1.80 | **$2.76** | +$0.96 |
| Inductor | $3.50 | **$7.55** | **+$4.05** |
| **Per channel** | **~$25** | **~$21.30** | **−$3.70** |

The inductor is now the most expensive part in the channel — more than the controller and
both FETs combined. That is the price of the 2.3× saturation margin, and it is still the
right trade, but it is worth knowing where the money goes.

---

## 2. Long lead and low stock — order these first

| Part | Situation | What to do |
|---|---|---|
| **LM5116-12EVAL/NOPB** — $136.12 | **3–5 units in stock across all distributors. 12-week factory lead** | **Order at WP-3, today.** It is not needed until build stage 3, but there will not be one in 12 weeks if you wait. This is R-0 control 2 and it is the only known-good reference you will have |
| **Mean Well RSP-1000-48** — $267.90 | 211 at DigiKey, 331 at Mouser, **but a 17–19 week factory lead**. Mouser shows 390 more arriving 2026-11-02 | Buy it when you commit to the build, not after. The RSP-750-48 went end-of-life while this document was being written; do not assume stock persists |
| **LILYGO T-Display-S3 Touch** — $25 | **Single source.** Not stocked by DigiKey or Mouser. No distributor part fits 1U | **Buy two.** If LILYGO discontinues it there is no drop-in, and F-8 becomes a redesign |
| Nexperia PSMN5R5-60YS | Out of stock at LCSC | Not used. Kept as the second source, from DigiKey/Mouser |

Everything else on the critical path has four-figure stock: LM5116 19,990 · INA226 43,755 ·
BSC0702LS 8,427 · LM5164 13,462.

---

## 3. OPEN-8 — RESOLVED

**Locking was dropped** (user decision, 2026-09-30). That reduced the requirement from
"panel-mount, locking, 5.5 × 2.5mm, ≥7A" — which does not exist — to "5.5 × 2.5mm, ≥7A",
which does.

**Fitted: Kycon KLDHCX-8-0202-B.** 8A, 24VDC, 5.5mm OD / 2.5mm ID, right-angle through
hole, $1.81 at qty 10, **5,196 in stock at Mouser** and 104 at DigiKey.

### Why this was hard to find

| Manufacturer | Panel-mount 5.5 × 2.5mm ceiling |
|---|---|
| Same Sky (ex-CUI) | **5.0A** across their entire panel-mount line (PJ-005B, PJ-064B, PJ-065B, PJ-066B, PJ-067B, PJ-090BH) |
| Switchcraft | 5A |
| Kycon, panel-mount | 5A |
| **Kycon, PCB right-angle** | **8A — KLDHCX-8 series** |

The 5.5 × 2.5mm barrel is a consumer-laptop connector and the whole industry treats 5A as
its ceiling **when it is panel-mounted**. The higher-rated parts exist only as board-mount,
because the current rating depends on the termination and a soldered PCB joint carries more
than a panel jack's solder tags.

### The consequence: a new small board

KLDHCX-8-0202-B is right-angle through-hole, so **it cannot bolt to the rear panel.** It
goes on a small 2-layer **output board** behind the panel carrying all six jacks, with the
barrels protruding through six clearance holes. Added to `bom.csv` as assembly `OUT`
(~$20 including the board).

That board is also the natural home for the six output TVS diodes, which moved there from
the 2-channel boards — a clamp belongs next to the connector it protects, not 150mm of wire
away.

### Margin

| | Current | vs 8A rating |
|---|---|---|
| Sustained (measured, six nodes) | ~5.0A | 63% |
| Turbo, ~45s | ~6.05A | 76% |
| Channel design capability (E-2) | 7A | 88% |
| Channel current limit (P-4) | ~10.5A | **131% — fault only** |

Comfortable on every real operating point. The 7A in E-2 is what the *channel* can deliver,
not what the *load* draws. Above the current limit the jack is over its rating, but that is
a fault condition the crowbar and fuse exist to end in milliseconds.

### What dropping the locking requirement costs

Recorded honestly in `docs/safety.md` §2: the locking collar was one of four controls
against a dangling live plug, and **the P-12 unconnected-output alert and the operating
procedure are now the whole response.** That is a thinner set than the earlier draft
claimed. It is judged acceptable because the hazard is ES1 to a person, is inherited from
the six existing bricks rather than introduced by this design, and — unlike a brick — can
be de-energised from anywhere.

---

## 4. Refreshed cost model

Replaces `SPECIFICATION.md` §5.

| | Cost |
|---|---|
| 6 buck channels (silicon, magnetics, protection, passives) | $128 |
| 3× 2-channel PCBs, 4-layer | $20 |
| Control board | $31 |
| T-Display-S3 Touch | $25 |
| Backplane + bus fuse | $28 |
| PCBA setup and assembly | $120 |
| **Electronics** | **$372** |
| Mean Well RSP-1000-48 | $268 |
| 3× Noctua NF-A4x20 PWM | $45 |
| IEC inlet, latching button, PSU mating connector | $18 |
| 6× 18AWG interconnect cables | $30 |
| Sheet metal, printed panels, fasteners, bus wiring | $135 |
| **Chassis and power** | **$496** |
| Output board (6× jacks + TVS + PCB) | $20 |
| **Build cost, one unit** | **$939** |
| LM5116 evaluation board (one-off, R-0 control 2) | $136 |
| **First unit, all in** | **$1,076** |

**Plus board re-spins.** R-2 says budget three, at $30–80 and 2–3 weeks each: **add
$150–250.** A realistic first-unit figure is **$1,200–1,330.**

Against the spec's $780–860 estimate this is up about $150, almost entirely the PSU
($268 rather than $165 — the RSP-750-48 was cheaper before it was discontinued) and the
inductor. The silicon came in under estimate.

**The honest comparison in §5 of the specification still stands, and is now slightly worse
for this project:** six stock Minisforum bricks are $240–360, and a used switched-and-
metered rack PDU driving those bricks gets you remote switching and per-outlet metering for
$150–300 in an afternoon. What $1,200 buys over that is the 1U consolidation and the
elimination of six bricks. That was always the actual reason, and it is a fine one.
