# Protection design and FMEA

**The governing question for this entire document is one failure:** a high-side
MOSFET fails shorted drain-to-source, and 48V appears at a node's 19V input.

Everything else is ordinary engineering. That one case is what destroys hardware,
and it is the case that ordinary protection does not cover.

---

## 1. Why disabling a channel is not protection

Per-channel switching works by pulling the LM5116's UVLO pin low (§4.5.2 of the
specification). This is correct and sufficient for two things:

- commanded on/off switching
- faults the controller itself detects (overcurrent, undervoltage, thermal)

**It is useless against a shorted pass device.** When the high-side FET is a lump
of shorted silicon, turning off the thing that drives its gate changes nothing —
the short does not care whether it is being told to conduct. The output stays
connected to 48V.

This is why requirement **P-2** exists as a separate line from P-1, and it is why
every channel carries a crowbar.

## 2. Overvoltage protection — the crowbar

Each channel has an **OVP comparator with its own voltage reference, powered from
that channel's own output**, independent of the MCU, the firmware and the
regulation loop (P-1).

| Parameter | Value | Why |
|---|---|---|
| Trip point | **21.66V** (2.495V × (1 + 76.8k/10k), 0.1% divider, 1nF filter) | Above 19V + 10% so load-step overshoot does not nuisance-trip; well below the ~25V typical rating of a laptop-style DC input stage |
| Action | Fires an **SCR across the 19V output** | A crowbar shorts the output. It does not try to open a switch, because the switch is what failed |
| Circuit | TL431B → MMBTA56 PNP → BT151 gate (deviations.md D-12) | The PNP keeps the TL431 anode at ground, so the trip point is exact |
| Node sees | ~1.5V (SCR forward drop) | Regardless of what the buck stage is doing |
| Isolation | Fault current flows through the channel's **5A fast-blow 48V input fuse** until it clears | The crowbar protects; the fuse isolates |

**Division of labour, stated explicitly because it is the part people get wrong:**
the crowbar does not clear the fault, and the fuse does not act fast enough to
protect the node. The crowbar clamps in microseconds and holds; the fuse opens in
milliseconds and makes it permanent. Neither works alone.

### Fuse coordination

Fault path: `48V → shorted HS FET → inductor → SCR → ground`, current-limited by
the PSU at ~21A (trimmable to 110%).

A 5A fast-blow fuse seeing a sustained ~21A — **4.2× rating** — clears in the order
of 10–50ms. The SCR must be rated to carry that current for that duration.

> **The RSP-1000-48 substitution made this better, not worse.** The original
> RSP-750-48 limited at 15.7A, i.e. 3× the fuse rating. More fault current into a
> fast-blow fuse means a *shorter* clearing time, so the node sits behind the
> crowbar for less time. The cost is that the SCR must carry 21A rather than 15.7A
> for that window — a selection criterion, not a problem, and the window is
> shorter.

**This depends on the PSU's overload behaviour, which was checked.** The
RSP-1000-48 specifies **constant-current limiting**, which is the favourable case:

| PSU behaviour | Effect on fuse clearing |
|---|---|
| **Constant current** (RSP-1000-48) | PSU *holds* ~21A. Fuse sees a sustained 4.2× overload. Clears predictably in ~10–50ms |
| Hiccup | PSU pulses on and off. Fuse sees intermittent current with cooling gaps between pulses. **Clearing time becomes indeterminate** — the fuse might never clear, leaving the node behind a repeatedly-firing crowbar |
| Shutdown/latch | Whole bus drops. All six nodes lost to one channel's fault |

Had it been hiccup mode the entire coordination scheme would have needed
rethinking. It is not, so it does not.

### The residual nobody should skip past

**Constant-current limiting is shared across all six channels.** A crowbar event
on one channel pulls the *entire 48V bus* to its current limit until that
channel's fuse clears. For ~100ms the other five channels see a sagging rail.

**Each buck stage must ride through that without dropping its output.** This is
why per-channel input bulk capacitance is specified rather than pooled at the
backplane. It is an explicit bench test at stage 4, not an assumption:

> Fire a crowbar on channel 1 under full six-channel load and confirm channels
> 2–6 hold regulation throughout, on a scope, including the recovery.

## 3. Protection layers

| Layer | Device | Threshold | Covers |
|---|---|---|---|
| Mains | IEC inlet fuse | Per PSU inrush rating | Mains fault |
| Bus | 48V fuse | 20A | Backplane fault, wiring fault |
| Channel input | 5A fast-blow | 5A | Channel catastrophic failure; crowbar coordination |
| Channel regulation | LM5116 cycle-by-cycle current limit | ~10.5A | Output short, node fault, dangling-plug short |
| **Channel output** | **OVP comparator + SCR crowbar** | **~21.5V** | **Shorted pass device — the node-destroying mode** |
| Channel output | TVS | ~24V standoff | Transients; a second independent clamp |
| Bus | TVS | ~58V standoff | Transients |
| Thermal | NTC per board → MCU | Per T-2 | Fan failure, blocked airflow |
| Discharge | Bleed resistor per output | — | A commanded power cycle must actually discharge (P-9) |
| Advisory | Unconnected-output alert | <20mA while enabled | Live dangling plug (P-12). **Alerts only** |

## 4. FMEA

Severity: **C**atastrophic (destroys a node) · **M**ajor (cluster outage) ·
**m**inor (degraded, recoverable).

| # | Failure mode | Effect if unprotected | Sev | Control | Detected by | Residual |
|---|---|---|---|---|---|---|
| 1 | **High-side FET shorted D-S** | **48V on a 19V input. Node destroyed** | **C** | OVP comparator + SCR crowbar + 5A fuse (P-1, P-2, P-3); TVS as a second clamp | Telemetry goes dark on that port; fuse open | **Moderate — this is R-1.** Proven only by the destructive bench test, since there is no independent review |
| 2 | OVP comparator itself fails | Failure 1 becomes unprotected | **C** | Independent TVS clamp in parallel; comparator powered from its own output so its failure is not correlated with the MCU | Not detected in normal operation | **Moderate.** Two mechanisms with different failure modes, but no runtime self-test |
| 3 | Low-side FET shorted D-S | Output pulled to 0V; shoot-through on the next cycle | M | Current limit, then input fuse | Port reads 0V/0A | Low. Node loses power but is not damaged |
| 4 | Inductor saturates | Current runaway, FET destruction | M | XAL1510-223 at 18.7A I_sat vs 8.04A peak = **2.3× margin**; cycle-by-cycle limit | Current limit engages | Low. This is why the 9A first-draft part was rejected |
| 5 | Output shorted (dangling plug, cable damage) | ~200W into the short; melted connector | m | Cycle-by-cycle current limit at 10.5A; fuse if sustained | Telemetry; P-12 alert beforehand | Low-moderate. Locking plugs (M-7) and procedure are the real controls |
| 6 | **MCU crash, hang, or firmware fault** | **Cluster outage if outputs drop** | **M** | **Hardware fail-ON** — UVLO held enabled by a divider; MCU can only pull down (§4.5.2) | External monitoring | **Low.** Verified by pulling the MCU from its socket and confirming outputs hold |
| 7 | Firmware "helpfully" adds an autonomous power-off | Cluster outage on network blip | M | S-4 hard rule; a comment block in the ESPHome config explaining why | Code review | Low — but this is a *discipline* control, not an engineering one |
| 8 | Fan failure | Thermal runaway | M | Tach monitoring (T-5); NTC-driven thermal shutdown (P-10); 3 fans where 1 would do | Tach reports zero RPM | Low |
| 9 | NTC open or shorted | Thermal protection blind | M | Fail-safe sense direction: an open NTC must read *hot* and drive fans to full, never *cold* | Implausible reading alerts | Low, if the sense direction is right. **Verify this at stage 4** |
| 10 | PSU fails | **All six nodes lost** | **M** | **None. Accepted** — output redundancy explicitly rejected (§4.2.4) | DC OK signal goes low | **Accepted.** The answer is a second PDU, not a bigger one |
| 11 | Backplane fault / bus fuse opens | All six nodes lost | M | 20A bus fuse protects the wiring, not availability | Total telemetry loss | Accepted, same as 10 |
| 12 | Crowbar fires spuriously | That node loses power; fuse opens | m | Trip at 21.5V, well above overshoot | Port dark, fuse open | Low. Annoying, not damaging — the safe direction to fail |
| 13 | INA226 fails or I²C hangs | Telemetry lost | m | Telemetry is advisory; nothing switches on it | Sensor unavailable | Low — **by design.** No protection depends on a reading |
| 14 | Display crashes or is unplugged | Nothing | m | Separate device, UART client, no authority over power (F-9) | Obvious | **None.** Verified by unplugging it |
| 15 | Ethernet lost | No remote control | m | Outputs unaffected (S-4); front-panel button and display remain | Monitoring | Low |
| 16 | Node draws beyond 7A | Current limit engages, node browns out | m | 133W vs 115W measured turbo = 15% margin | Telemetry | Low, pending OPEN-6 |

### What the FMEA says when read as a whole

- **Rows 1 and 2 are the whole risk.** Everything else is minor, accepted
  deliberately, or fails in a safe direction.
- **No protection depends on software** (rows 6, 7, 13, 14). That is the single
  most important structural property of this design.
- **Rows 10 and 11 are accepted, not mitigated.** A single PSU and a single
  backplane mean a single PDU is a single point of failure for the whole cluster.
  This was analysed and chosen (§4.2.4). It should not come as a surprise later.
- **Row 9 is resolved in firmware, not hardware** (deviations.md D-14). An open
  NTC reads cold however it is wired, so firmware must treat any out-of-range
  reading as a fault: fans to 100% and an alert. WP-6 must implement it, and the
  bench test is to unplug the NTC and watch the fans go to full.

## 5. Verification

Protection is not signed off by this document. It is signed off by
SPECIFICATION §9.1, and specifically by these, **run twice — once on a fresh
board and once after the 72-hour burn-in**:

1. Output short → current limit engages, then the fuse clears
2. Force the OVP reference → crowbar fires, output clamps, input fuse clears
3. **Repeat (2) with the MCU physically removed** — this is the entire point of P-1
4. **Destructive: solder a wire drain-to-source across the high-side FET**, power
   up into a dummy load, and scope what the load actually sees including the
   first few microseconds. Sacrifice the FET. **This must be performed, not
   reasoned about**
5. Crowbar one channel under full six-channel load; confirm the other five hold
   through the ~100ms bus sag (§2, the residual)
6. Inrush into 2200µF without fuse operation
7. Pull the 48V feed mid-operation; confirm no output overshoot as the rail collapses
