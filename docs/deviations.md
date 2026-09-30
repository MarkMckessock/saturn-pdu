# Deviations from the reference design

**This file is R-0 control 1.** It is the single most important document in the
repository, and right now it is empty.

---

## Why this exists

There is **no independent review of this design** — a deliberate decision,
recorded as risk R-0 in `SPECIFICATION.md` §7. The compensating strategy is:

1. Start from **TI's published LM5116 reference schematic and board layout**.
2. Copy the power-stage geometry verbatim.
3. **Log every single departure from it here, with the reason.**

Risk concentrates in the deviations. A design that is 95% a proven reference
design plus a written list of the 5% that is not, is a design that can be
reviewed — by you, by a stranger on a forum, by anyone you eventually ask. A
design with no such list can only be reviewed by reading all of it.

**This list is the review checklist you would otherwise have paid for.**

## Rules

- **Every deviation gets a row.** Including ones that seem obviously fine. The
  ones that seem obviously fine are the ones that are not.
- **Write the row when you make the change**, not at the end. You will not
  remember why.
- "Because the reference part was out of stock" is a perfectly good reason.
  Write it down anyway.
- A deviation with an empty **Why** column is a deviation nobody has justified.
  Treat an empty Why as a defect.
- **Layout deviations matter more than schematic deviations.** At 250kHz and 48V,
  physical copper geometry determines whether the circuit works. That is the part
  a schematic review cannot catch and the part this log exists to expose.

## Reference material

| Document | What it is | Status |
|---|---|---|
| TI LM5116 datasheet (SNVS566) | Controller, design equations | To be filed in `reference/` |
| TI LM5116 EVM user guide | **Reference schematic and board layout** | To be filed in `reference/` |
| Coilcraft XAL1510 datasheet | Inductor | To be filed |
| TI INA226 datasheet | Telemetry | To be filed |

**Have the EVM layout open on screen beside the board while routing.** Not from
memory, not from a screenshot in a forum post. Open, side by side.

---

## Schematic deviations

| # | Reference does | This design does | Why | Risk | Checked at |
|---|---|---|---|---|---|
| _(none yet — WP-4b)_ | | | | | |

## Layout deviations

| # | Reference does | This design does | Why | Risk | Checked at |
|---|---|---|---|---|---|
| _(none yet — WP-4d)_ | | | | | |

## Component substitutions

| # | Reference part | Substituted | Why | Datasheet compared? | Risk |
|---|---|---|---|---|---|
| _(none yet — WP-3)_ | | | | | |

---

## Known deviations already committed by the specification

These are decided and are recorded now so the list starts honest rather than
starting empty-and-wrong.

| # | Reference/typical | This design | Why | Risk |
|---|---|---|---|---|
| D-1 | LM5116 EVM runs a lower V_in | **48V input** | The bus voltage, set by the PSU choice | Switching loss scales with V_in — the dominant loss (§thermal.md §3). Drives the 250kHz choice |
| D-2 | Typical EVM output is a low voltage at high current | **19V at 7A (133W)** | The MS-01's input requirement | Duty cycle 0.396 is unremarkable; the power level is what stresses the thermal design |
| D-3 | EVM has no output OVP crowbar | **SCR crowbar + independent comparator per channel** | P-1/P-2: a shorted high-side FET must not reach the node, and protection must work with the MCU unpowered | **This is an addition, not a substitution — it has no reference design behind it at all.** The highest-risk single item in this project |
| D-4 | EVM has no telemetry | **INA226 on each output** | F-3 | Low. Advisory only; nothing switches on a reading |
| D-5 | EVM is a single channel on its own board | **Two channels per board, three boards** | Panelisation, cheap field swap, contained thermal problems | Shared input node between two channels — check the bus-sag ride-through case (protection.md §2) |
| D-6 | EVM enable is a simple pin | **UVLO divider holds enable ON; MCU pulls down via open-drain** | F-5/S-4: fail-ON is a hard requirement | Low, and it fails in the safe direction |
| D-7 | Housekeeping supply taken from a PSU auxiliary rail | **48V bus → LM5164 → 12V/1A → fans; 12V → 5V/1A → logic** | The RSP-1000-48's aux is 5V/0.5A. At ~2.0W estimated draw that is 80% of it — the derating limit, not a margin — and the fans need 12V regardless | Low. The 48V bus is live whenever the PSU is on, independently of any channel's state, which is the exact property the aux rail was wanted for |

**D-3 deserves emphasis.** It is not a deviation from the reference — it is
circuitry the reference does not contain in any form. There is no published
layout to copy for it, and it is the exact circuit that stands between a failed
FET and a destroyed node. It is why the destructive bench test in
`protection.md` §5 item 4 is mandatory and must not be reasoned about instead of
performed.
