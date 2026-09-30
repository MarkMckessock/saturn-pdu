# saturn-pdu

**A 1U rack PDU delivering six independently switched and metered 19V outputs,
for a six-node Minisforum MS-01 Kubernetes cluster.**

> **Status: draft specification. Nothing here has been built or bench-verified.**
> Every figure is analytical. Do not fabricate from this repository yet.

Derived from [Shrike-Lab/HomeLab-PDU-V1](https://github.com/Shrike-Lab/HomeLab-PDU-V1).
Licensed **CERN-OHL-S v2** (strongly reciprocal) -- see [`LICENSE`](LICENSE) and
[`NOTICE`](NOTICE).

---

## The problem

Six MS-01 nodes, six 180W bricks, six mains outlets, twelve cables, and no way
to see what any node draws or to power-cycle a wedged one without walking to the
rack.

## What this is

One 1U box: a single mains inlet, six 19V outputs, each switchable over the
network and each reporting volts, amps and watts.

```
IEC inlet ──► RSP-1000-48 ──► 48V bus ─┬──► [2ch board A] ──► ports 1,2
                  ▲                     ├──► [2ch board B] ──► ports 3,4
           remote ON/OFF                └──► [2ch board C] ──► ports 5,6
           (front button)                          │
                                          [control board]
                                          ESP32-S3 + wired Ethernet
                                          6x INA226 telemetry
                                          Prometheus /metrics
```

Each channel is an LM5116 synchronous buck, 48V down to 19V at 7A, with its own
fuse, its own current limit, and its own overvoltage crowbar that works **with
the microcontroller unpowered**.

## Three design rules that explain most of the decisions

1. **Outputs fail ON.** Channels are held on by resistors. The MCU can only turn
   one *off*, by actively pulling a pin down. An MCU that is crashed,
   unprogrammed, unpowered or physically removed leaves every node running.
   No firmware path may ever de-energise an output autonomously.
2. **Protection does not depend on software.** A shorted high-side transistor
   puts 48V on a 19V input and destroys a node. Disabling its controller
   achieves nothing when the transistor is a short, so each output carries an
   SCR crowbar with its own reference, powered from its own output.
3. **The display cannot break anything.** It is a separate device on a UART
   link, not the controller. Unplug it and all six outputs keep running and stay
   controllable over the network. A single tap can never de-energise a node.

## Honest cost comparison

About **$750-830** in parts, realistically **$900-1,100** for a first unit once
you budget the three board spins a first high-current layout needs. Six stock
bricks are $240-360.

A used switched-and-metered rack PDU (APC AP7921 class, $150-300) plugged into
your existing bricks gives you remote switching and per-outlet metering this
afternoon. **What this project buys over that is the 1U consolidation and the
elimination of six bricks -- a space and elegance goal, not a functional one.**
That is a fine reason to build it. It should just be the actual reason.

## Safety

**Read [`docs/safety.md`](docs/safety.md) before building or operating.**

The short version: the 19V outputs cannot shock you (IEC 62368-1 ES1), but a
live barrel plug dropped on a rack rail will melt itself. Unused ports stay off;
switch a port off before unplugging it. The mains side inside the chassis *can*
kill you -- unplug at the wall before opening the lid, and wait a minute.

## Repository layout

| Path | Contents |
|---|---|
| `params.yaml` | **Single source of truth.** Every dimension, rating and threshold used in more than one place. Docs, firmware and CAD all read from it |
| `docs/` | Specification, power budget, thermal, protection/FMEA, safety, upstream analysis, deviation log |
| `hardware/kicad/` | KiCad projects: 2-channel power board, control board, backplane |
| `cad/` | Parametric FreeCAD Python, plus STEP/STL exports |
| `firmware/` | ESPHome configuration for the control board and the display |
| `fab/` | Gerbers, BOM, pick-and-place |
| `reference/upstream-19in/` | Upstream's 19" B-rep solids, kept as dimensional reference |

## Build order

Stage-gated. **Do not order the full board set before stage 4 passes.**

| # | Stage | Gate |
|---|---|---|
| 0 | Measure the barrel jack and the real six-node draw | Both recorded |
| 1-2 | Schematics, BOM and sourcing | No unsourceable parts |
| 3 | LM5116 evaluation board, built and measured | A known-good reference exists |
| 4 | One 2-channel board: bring-up, fault injection, 72h burn-in, fault injection **again** | **Hard gate** |
| 5-6 | Control board, firmware, display, chassis | Fail-ON verified by pulling the MCU |
| 7 | **30-day canary on one worker node** | **Hard gate.** Any event resets to day zero |
| 8 | Remaining five nodes; control-plane nodes last | 24h six-node soak |

Full detail in [`docs/SPECIFICATION.md`](docs/SPECIFICATION.md) sections 8 and 9.

## Open items

Two measurements and one accepted risk. Both measurements carry provisional
values in `params.yaml` and neither blocks design work.

| ID | Item | Why it does not block |
|---|---|---|
| OPEN-5 | Barrel jack dimensions | Both candidate sizes share the same 8mm panel thread, so the panel cutout is identical. Only the part number is provisional |
| OPEN-6 | Real six-node peak draw | **Downgraded to informational.** The fitted RSP-1000-48 absorbs a reading 38% above estimate, so this validates the power budget rather than gating a purchase |
| OPEN-8 | Rear-panel output connector | **New at WP-3.** No panel-mount, locking, 5.5×2.5mm, ≥7A barrel jack exists anywhere. Three options in `fab/sourcing-notes.md` §3 — needs a decision before the rear panel is drawn |
| R-0 | No independent design review | **Accepted, not resolved.** Bench testing and the 30-day canary stand in for it. Residual risk is moderate and knowingly taken |

## Contributing

This is a personal homelab project, not a product. Issues and observations are
welcome -- particularly from anyone with power-electronics experience, given
R-0. Pull requests are not expected.

Derivatives must remain under CERN-OHL-S v2 and must publish editable source,
not only exports. Upstream arguably does not; this repository tries to.
