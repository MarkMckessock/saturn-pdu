# Power budget

Derived from `params.yaml`. Values marked **PROVISIONAL** stand in for OPEN-6,
the six-node draw measurement that has not been taken.

---

## 1. What the load actually draws

The MS-01's nameplate is 19V / 9.47A / **180W** (Huntkey HKA18019095-6C).
**The design is deliberately not sized to that number.** Measured behaviour
differs sharply, and sizing to a nameplate no measurement supports would mean
buying a 1080W supply to serve a load that peaks near 690W.

| Condition | Per node | × 6 | Source |
|---|---|---|---|
| Idle, tuned Linux | ~13W | 78W | cloudmagazin |
| Idle, Windows | 25–30W | 180W | ServeTheHome |
| Sustained load | 90–95W | 570W | ServeTheHome |
| **Turbo, first ~45s** | **~115W** | **690W** | ServeTheHome |
| Nameplate | 180W | 1080W | Minisforum |

**Design point: 690W aggregate**, all six in turbo simultaneously.

> **All five figures are third-party. None was measured on your nodes running
> your workloads.** That is OPEN-6. It costs a ~$20 plug-in energy meter and one
> evening: run the real workload, then `stress-ng --cpu 0` on all six at once,
> record the peak. It is the cheapest high-value action in this project.

## 2. What the 48V rail must supply

At the design channel efficiency of 95%:

```
bus draw = 690W / 0.95 = 726W
```

Against the RSP-1000-48's 1008W, that is **72% of rated output.**

| Scenario | Output | Bus draw | % of RSP-1000-48 |
|---|---|---|---|
| Six idle (Linux) | 78W | 82W | 8% |
| Six idle (Windows) | 180W | 189W | 19% |
| Six sustained | 570W | 600W | **60%** |
| Six turbo (design point) | 690W | 726W | **72%** |
| Six at nameplate (not designed for) | 1080W | 1137W | 113% — exceeds |

**This was not always comfortable.** Against the originally specified RSP-750-48
the same 726W was **96% of rating**, and the argument for accepting it rested on
the turbo window being ~45 seconds and unsynchronised across six independent
Kubernetes nodes. That argument was sound but thin. It is no longer needed.

## 3. Why the supply changed, and what it bought

**The RSP-750-48 is discontinued.** Sourcing at WP-3 found it end-of-life —
several hundred units remain at distributors, but no long-term spares exist.

Three units were compared:

| | RSP-750-48 | **RSP-1000-48** | UHP-750-48 |
|---|---|---|---|
| Lifecycle | **Discontinued** | **Active** | Active |
| Availability | ~700 units remain | In stock | **17-week lead** |
| Capacity | 753.6W | **1008W** | 753.6W |
| Load at 726W peak | **96%** | **72%** | 96% |
| Efficiency | 92% | ~91% | **95%** |
| Cooling | Own fan | Own fan | **Fanless** |
| Size | 250 × 127 × 41 | 295 × 127 × 41 | 237 × 100 × 41 |
| Price | $186–237 | ~$230–260 | ~$194 |

**The RSP-1000-48 was fitted**, and the change cost nothing structurally: the
chassis and the 48V bus were *already* dimensioned to its 295mm length under M-2,
because it had been specified as the upgrade path. The upgrade path became the
build.

### What it bought

1. **Risk R-3 closes outright.** 72% of rating is not a marginal operating point.
2. **OPEN-6 stops being a gate.** The measurement was blocking a purchase because
   a high reading would have invalidated a 753.6W supply. At 1008W the design
   absorbs a reading **38% above** the estimate before the question reopens. Take
   the measurement — it is still the only real evidence in §1 — but it no longer
   blocks anything.
3. **An active part number**, so spares exist for the service life of the build.

### The near-miss worth recording

**The UHP-750-48 is Mean Well's actual successor and is better on two axes that
matter here:** 95% efficiency, and it is **completely silent** — no PSU fan, which
is almost certainly the loudest thing in this box and the binding constraint on
the ≤35 dBA idle target (T-3).

It was rejected on two counts:

- **A 17-week lead time.** Four months before the project can be completed.
- **Being fanless inverts the thermal budget.** The RSP exhausts its own ~72W of
  loss through its own fan, and that heat never enters the chassis budget. A
  fanless U-channel unit conducts its ~38W into whatever it is bolted to — the
  chassis — roughly **doubling** the airflow the design must handle (`thermal.md`
  §2), for a first-time build where thermal margin is already the thing being
  guessed at.

**Worth revisiting for a second unit**, where a four-month lead is not an obstacle
and the thermal design has been measured rather than calculated.

## 4. Per-channel budget

| Parameter | Value |
|---|---|
| Output | 19.0V, 7.0A continuous = **133W** |
| Covers | sustained 95W and turbo 115W, with 15% margin over turbo |
| Input | 48V at ~2.9A |
| Design efficiency | 95% (requirement E-6 is 94%) |
| Dissipation at 7A | ≤6.6W design target; ~3.6W modelled (see `thermal.md`) |
| Peak inductor current | 8.04A |
| Current limit | ~10.5A (≈1.5× rated) |

**Why 7A and not 9.47A.** Sizing each channel to the nameplate would mean
6 × 180W = 1080W of channel capacity on a 1008W supply — capacity that could
never be used simultaneously, paid for six times over in silicon, copper and
heat. 7A covers every measured condition including turbo.

## 5. Decision record — one large supply vs 2 × 450W

Analysed and **rejected**. Recorded so it is not re-litigated.

> The comparison below was made against the 753.6W RSP-750-48, and is preserved in
> those terms because that is the argument as it was actually decided. **Fitting the
> 1008W RSP-1000-48 only strengthens it** — the dual option's sole advantage was
> headroom (80% vs 96%), and the single supply now sits at **72%**, better than the
> dual arrangement it was being compared against.

| | 1 × RSP-750-48 | 2 × HRP-450-48 |
|---|---|---|
| Total capacity | 753.6W | 912W |
| Load at the 726W peak | 96% | **80%** |
| Efficiency | 92% | 89.5% (~22W more heat in 1U) |
| Footprint | 250 × 127 = 31,750 mm² | rotated 210 × 218 = 45,780 mm² |
| Side-by-side fit | n/a | **2 × 218 = 436mm in 438.7mm — does not fit** |
| AC inlets | 1 | 2 |
| Board architecture | 3 × identical 2-channel | forced to 2 × 3-channel |

**Dual genuinely wins on headroom.** That is the strongest argument for it and it
is a real one. It loses on three counts:

1. **It cannot sit side by side.** 1.35mm of clearance per side is inside
   sheet-metal tolerance, before airflow or cable routing is considered. Only a
   90° rotation fits, costing 44% more tray area in a chassis where area is the
   constraint.
2. **It forces two independent 48V domains.** HRP-450s have no active current
   sharing and cannot be paralleled. Two domains must not share a board's input,
   so the clean 3 × identical 2-channel architecture collapses into 2 × 3-channel
   — two board designs instead of one, and no panelisation saving.
3. **Its resilience benefit is partitioning, not redundancy.** 456W cannot carry
   six nodes at 690W, so a PSU failure drops three nodes rather than failing
   over. With three control-plane nodes split 2+1, half of all PSU failures lose
   quorum anyway. The backplane, the master switch and the chassis remain single
   points of failure either way.

**The headroom concern is better answered by the RSP-1000-48 drop-in**, which
also supports active current sharing should a second chassis ever be wanted.
Genuine cluster resilience belongs at the second-PDU level, not inside one 1U box.
