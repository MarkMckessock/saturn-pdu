# Sourcing notes — WP-3

**Checked 2026-09-30.** Prices and stock move. Everything here must be re-checked at the
moment you actually order, and the `verified` column in `bom.csv` says which lines were
looked up live and which are catalogue estimates.

| `verified` | Meaning |
|---|---|
| `LIVE` | Distributor page or listing read on 2026-09-30. Stock and price are real numbers from that day |
| `EST` | Catalogue-typical part and price. Not looked up. Commodity items — resistors, ceramics, TVS, fuses — where the risk is a few cents, not availability |
| `OPEN` | No part selected. A decision is required |

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

## 3. OPEN-8 — there is no connector that meets the spec

**This is the one thing sourcing could not close, and it needs a decision.**

`params.yaml` asks for a panel-mount 5.5 × 2.5mm barrel jack that is **locking** (M-7,
added after the live-plug safety discussion) and rated **≥10A**. Searching the tier-1
catalogues, **that part does not exist.** The closest options each fail on something:

| Part | Locking | Panel mount | Rating | Barrel | Fails on |
|---|---|---|---|---|---|
| Kycon KLDHCX-8-0202-A | Yes | **No — PCB right-angle** | 8A, 24V | 5.5 × **2.0** | Mount and inner diameter |
| Kycon KLDHCX-0202-A-LT | Yes | No — PCB | **5A** | 5.5 × 2.5 | Rating and mount |
| Kycon KLDX-0202-A | Yes | No — PCB | 5A | 5.5 × 2.5 | Rating and mount |
| Generic panel-mount barrel | **No** | Yes | typically 5A | 5.5 × 2.5 | Rating and locking |
| Switchcraft panel jacks | No | Yes | 5A | 5.5 × 2.5 | Rating and locking |

The pattern is consistent: **the 5.5 × 2.5mm barrel format tops out around 5–8A across the
whole industry**, because it is a consumer-laptop connector, and the locking variants are
all designed to be soldered to a board rather than bolted to a panel.

### The options, in plain terms

**The MS-01 end is not in question.** The MS-01 has a fixed barrel socket and will not be
modified, so the cable's node end is a 5.5 × 2.5mm barrel plug whatever happens. The
question is only **what goes on the back of the PDU.**

**Option A — accept a 5A-class panel barrel jack, drop the locking requirement.**
Cheapest and simplest, and the picture on the back of the box stays as described. But 5A is
below the 7A the channel is designed to deliver, so the connector becomes the weakest link
in the chain, and M-7 is reversed — cables can be pulled out by accident again.

**Option B — a 2-pin PCB-mount locking jack on a small board behind the panel.**
Keeps the barrel format and gets the locking, at 5A. Adds a small PCB and a panel cutout
per port. Still 5A.

**Option C — change the PDU-side connector to something properly rated.**
Use a Molex Mini-Fit Jr latching connector on the rear panel (9A per circuit, four circuits
with two per polarity, positive latch, tier-1 rated) and make the cable Mini-Fit Jr →
barrel. The back of the box no longer shows six barrel jacks; it shows six latching
connectors.

This is the only option that meets both M-7 and the 7A rating, and it has a second benefit:
**the panel side becomes a recessed female contact instead of an exposed pin**, which is a
strict improvement on the live-plug analysis in `docs/safety.md` §2. It is also the
connector family upstream already used for its own 24V input (`upstream-analysis.md`).

Cost is comparable — around $2–3 per port either way.

**Nothing downstream of the rear panel changes in any option.** This is a connector and a
cable, not a redesign. It does need deciding before the rear panel is drawn (WP-7).

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
| **Electronics** | **$352** |
| Mean Well RSP-1000-48 | $268 |
| 3× Noctua NF-A4x20 PWM | $45 |
| IEC inlet, latching button, PSU mating connector | $18 |
| Output connectors + 6× interconnect cables | $45 |
| Sheet metal, printed panels, fasteners, bus wiring | $135 |
| **Chassis and power** | **$511** |
| **Build cost, one unit** | **$936** |
| LM5116 evaluation board (one-off, R-0 control 2) | $136 |
| **First unit, all in** | **$1,072** |

**Plus board re-spins.** R-2 says budget three, at $30–80 and 2–3 weeks each: **add
$150–250.** A realistic first-unit figure is **$1,200–1,300.**

Against the spec's $780–860 estimate this is up about $150, almost entirely the PSU
($268 rather than $165 — the RSP-750-48 was cheaper before it was discontinued) and the
inductor. The silicon came in under estimate.

**The honest comparison in §5 of the specification still stands, and is now slightly worse
for this project:** six stock Minisforum bricks are $240–360, and a used switched-and-
metered rack PDU driving those bricks gets you remote switching and per-outlet metering for
$150–300 in an afternoon. What $1,200 buys over that is the 1U consolidation and the
elimination of six bricks. That was always the actual reason, and it is a fine one.
