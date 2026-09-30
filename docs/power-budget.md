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

Against the RSP-750-48's 753.6W, that is **96.3% of rated output.**

**This is tight, and it is stated plainly rather than smoothed over.** Two things
make it acceptable:

1. **The turbo window is ~45 seconds and is not synchronised.** Six independent
   Kubernetes nodes do not enter turbo together except under a deliberately
   synchronised benchmark — which is precisely the OPEN-6 test, i.e. the one
   case where you should expect to see the number and will be watching for it.
2. **Sustained all-six load draws 600W from the bus** (570W / 0.95), which is
   **80% of rated** — a comfortable continuous operating point.

| Scenario | Output | Bus draw | % of RSP-750-48 |
|---|---|---|---|
| Six idle (Linux) | 78W | 82W | 11% |
| Six idle (Windows) | 180W | 189W | 25% |
| Six sustained | 570W | 600W | **80%** |
| Six turbo (design point) | 690W | 726W | **96%** |
| Six at nameplate (not designed for) | 1080W | 1137W | 151% — exceeds |

## 3. Headroom and the upgrade path

The **RSP-750-48** (250mm) and **RSP-1000-48** (295mm) share an identical
**127 × 41mm cross-section**. The chassis and the 48V bus are dimensioned to the
*longer* RSP-1000-48, so either drops in without redesign (M-2).

**Build with the 750W.** The per-channel telemetry (F-3) then produces the
evidence for whether the 1000W is ever warranted — which is one of the principal
justifications for building the metering at all, rather than a nice-to-have.

**Risk if OPEN-6 comes in high:** a ~$165 part swap into a chassis already sized
for it. This is why deferring the measurement is safe: it changes a purchase, not
a layout.

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
6 × 180W = 1080W of channel capacity on a 753.6W supply — capacity that could
never be used simultaneously, paid for six times over in silicon, copper and
heat. 7A covers every measured condition including turbo.

## 5. Decision record — 1 × 750W vs 2 × 450W

Analysed and **rejected**. Recorded so it is not re-litigated.

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
