# Saturn PDU — Design Specification v0.1 (DRAFT, pre-review)

**Project:** 1U rack PDU delivering six independently switched and metered 19V outputs
for a six-node Minisforum MS-01 Kubernetes cluster.
**Derived from:** [Shrike-Lab/HomeLab-PDU-V1](https://github.com/Shrike-Lab/HomeLab-PDU-V1) (CERN-OHL-S v2)
**Status:** Draft for review. **Nothing here has been built or bench-verified.**
All calculations are analytical and must be confirmed against manufacturer datasheets
and on hardware before fabrication. Sections marked **[OPEN]** are unresolved.

---

## 1. Context and scope

### 1.1 Problem

Six MS-01 nodes each ship with a 180W 19V external brick. That is six bricks, six mains
outlets, twelve cables and no visibility into per-node power. There is no way to power
cycle a wedged node without physical access to the rack.

### 1.2 Goal

One 1U unit: single mains inlet, six 19V outputs, each independently switchable over the
network and each metered for voltage, current and power.

### 1.3 Out of scope

- Mains-side redundancy, UPS or ATS functions
- Genuine N+1 output redundancy (see §4.2.4 — explicitly rejected)
- Powering anything other than 19V DC loads
- Prometheus/Grafana/Gatus integration on the Saturn side (follow-on, §10)

### 1.4 Relationship to upstream

Upstream is a 5× 65W USB-C PD distribution board fed from a 300W/24V supply. Two facts
determine how much can be inherited:

1. **The load is incompatible.** The MS-01 takes 19V via a barrel jack and
   [cannot be powered over USB-C](https://www.galaxus.at/en/s1/questionandanswer/hello-can-the-mini-pc-also-be-supplied-with-power-via-usb-c-or-is-it-only-possible-with-the-mains-ad-782803);
   Minisforum support confirms the barrel jack is required. Every USB-C PD module, the
   PD-specific board and the 24V rail are discarded.
2. **Upstream publishes no editable source.** A census of all 149 files found zero
   `.kicad_*`, `.f3d`, `.FCStd`, `.SLDPRT` or EasyEDA files — only STEP/STL exports,
   Gerbers, ODB++ and PDFs. STEP headers show SolidWorks 2025; Gerber headers show
   KiCad 9.0.7 (project `1U Minilab PSU V2`). Both originals are withheld.

This is therefore a **new design that inherits upstream's mechanical architecture and
protection patterns**, not a modification of upstream's electronics. See §2.

---

## 2. Upstream analysis (reverse-engineered from fab files)

### 2.1 What was extracted

| Property | Value | Source |
|---|---|---|
| Board outline | **90 × 130 mm** (X 51.8→141.8, Y −38.3→−168.3) | `Edge_Cuts.gm1` |
| Stackup | 2-layer, 1.6mm, 2oz | README; confirmed by pour-heavy layout |
| Trace apertures | 0.8 / 1.0 / **2.0 mm max** | `F_Cu.gtl` aperture list |
| Copper pours | 17 regions top, 1 bottom (GND plane) | `G36` region count |
| Drills | 0.6 / 0.75 / 1.0 / 1.8 / 3.2 mm PTH; **3.0 mm NPTH ×4** mounting | `.drl` tool tables |

### 2.2 Reconstructed topology

Through-hole connectivity is fully recoverable from `HomeLab-PSU-V1_netlist.ipc`:

```
J1 (Molex Mini-Fit Jr) +24V ─► F1 15A ─► Q1 high-side P-FET ─► +24V_SWITCHED
                                          ▲ gate: R4 100k, D7 12V zener,
                                            R2 47k, R3 100R, latched from J2 button
        D6 SMCJ26A bulk TVS, C1/C2 470µF
                                             │
        ┌────────────┬────────────┬──────────┴─┬────────────┐
     F2 3A        F3 3A        F4 3A        F5 3A        F6 3A
        │            │            │            │            │
     J3/J8       J4/J9      J5/J10      J6/J11      J7/J12    ◄── XPM52C PD modules
     + D1–D5 SMBJ26A TVS, C5–C9 470µF, C10–C14 1µF, C15–C19 100nF
                                             │
                              J13 ─► buck module ─► J15/J16 ─► J17/J18 fan headers
```

**Upstream's board performs no power conversion.** It is a passive fan-out: one master
switch, fusing, TVS clamping, bulk capacitance, and headers for five purchased PD modules
and one purchased buck module. This design inverts that — conversion *is* the board.

### 2.3 Inheritance decisions

| Element | Decision | Justification |
|---|---|---|
| Fuse + TVS + bulk cap per channel | **Inherit**, rescaled | Sound pattern; 3A→5A input fuse, TVS standoff 26V→58V (bus) / 24V (output) |
| Master switch via latching button | **Inherit concept, change implementation** | Use the PSU's remote ON/OFF rather than commutating 15A of 48V through a FET — an option upstream did not have with the HRP-300 |
| Fan rail from switched main rail | **Inherit**, add MCU PWM | Upstream tunes RPM by trimming a buck's output voltage; open-loop and crude |
| 4× 3.0mm NPTH mounting pattern | **Inherit** | Compatible with upstream's PCB tray / reinforcement bracket concept |
| 90×130mm board footprint | **Reference only** | Useful sanity check that a 2-channel board fits the tray |
| Power path, PD modules, 24V rail | **Discard** | Incompatible with the load |
| 2-layer / 2oz / 15A | **Discard** | Under-specified for 800W class |

### 2.4 Defect found in upstream — do not inherit

`Q1` is `NCEP40PT15D` (N-channel, 40V) in the README BOM but `IRF9540NPBF`
(**P-channel**, 100V) in the JLCPCB `bom.csv` LCSC field. These are opposite polarity and
not interchangeable. The gate network (100k pull-up, 12V zener clamp, pulled low to turn
on) is unambiguously a **P-channel** high-side switch, so the CSV is correct and the
README is wrong. Building from the README alone yields a non-functioning board.

### 2.5 What could not be extracted

- **The schematic PDFs contain no machine-readable text.** Both are ~34KB with no
  embedded fonts and no `Tj`/`TJ` operators — KiCad plotted every label as vector
  strokes. No net names, designators or values are programmatically recoverable.
  Rendering them for human review requires `brew install poppler`.
- **The IPC-356 netlist covers through-hole pads only.** SMD connectivity is absent, so
  the exact wiring of the Q1 gate network is **inferred from part values and standard
  practice, not extracted**. It is almost certainly the textbook arrangement, but this
  is an inference and is labelled as such.

Neither gap is material, because the power path is not being copied.

---

## 3. Requirements

Priority: **M** mandatory · **S** should · **C** could.

### 3.1 Functional

| ID | Pri | Requirement | Justification |
|---|---|---|---|
| F-1 | M | Six independent 19V DC outputs, each on a panel-mount barrel jack | Matches stock MS-01 input; no node-side modification |
| F-2 | M | Each output independently switchable on/off over the network | Primary purpose: recover a wedged node without rack access |
| F-3 | M | Each output reports voltage, current and power | Sizing evidence (§4.2.3) and per-node cost attribution |
| F-4 | M | Master power control via front-panel latching button | Local override; inherited from upstream |
| F-5 | M | Outputs default to ON at power-up without network or MCU | A PDU that needs a working control plane to deliver power is a liability |
| F-6 | S | Per-output status indication on the front panel | At-a-glance diagnosis at the rack |
| F-7 | C | Per-output soft-start sequencing/stagger at power-on | Reduces aggregate inrush; not required if per-channel soft-start suffices |
| F-8 | S | **Front-panel colour display showing live aggregate and per-node power draw** | Answers "what is this cluster drawing right now" without a laptop or a network |
| F-9 | M | **The display must not be able to switch a node off in a single touch, and its failure must not affect power delivery** | It is a rack front panel — cables and hands brush past it. A one-tap node shutdown is an accidental-outage machine |

### 3.2 Electrical

| ID | Pri | Requirement | Justification |
|---|---|---|---|
| E-1 | M | Output 19.0V ±2% from no load to rated load | MS-01 spec is 19V; laptop-style inputs tolerate ±5% |
| E-2 | M | ≥7A continuous per output (133W) | Covers measured sustained (95W) and turbo (115W) with margin |
| E-3 | M | Output ripple ≤200 mVpp at rated load | ~1% of 19V; conservative for a DC input stage |
| E-4 | M | Aggregate continuous output ≥690W | Six nodes at measured turbo (§4.2.1) |
| E-5 | M | Universal AC input 100–240V, 50/60Hz, active PFC | Mains-agnostic; PFC required at this power |
| E-6 | S | Conversion efficiency ≥94% per channel at 7A | Sets the thermal budget (§4.7) |
| E-7 | M | Load-step 0→7A without exceeding E-1 bounds beyond transient recovery | Nodes step load hard on turbo entry |

### 3.3 Protection and safety

| ID | Pri | Requirement | Justification |
|---|---|---|---|
| P-1 | M | **Per-output OVP that operates with the MCU unpowered** | A shorted high-side FET puts 48V on a 19V input. This is the one failure mode that destroys nodes; it must not depend on firmware |
| P-2 | M | OVP must protect the load even if the pass device is shorted | Disabling a controller does nothing when its FET is a short — requires a crowbar (§4.4.2) |
| P-3 | M | Per-channel input fusing, coordinated with the crowbar | Isolates a failed channel; the crowbar holds the output down until it clears |
| P-4 | M | Per-channel cycle-by-cycle current limit | Handles output short and node fault without fuse operation |
| P-5 | M | Mains fusing at the IEC inlet | Standard practice; inherited from upstream |
| P-6 | M | Bus-level fusing on the 48V rail | Protects wiring and PSU against a backplane fault |
| P-7 | M | TVS on the 48V bus and on each 19V output | Transient clamping |
| P-8 | M | Controlled soft-start into the MS-01's input capacitance | Prevents inrush-induced fuse operation and rail sag |
| P-9 | M | Output bleed so a commanded power cycle actually discharges | An output that coasts at 15V is not a power cycle |
| P-10 | M | Thermal monitoring per board with automatic shutdown | Last-resort protection against fan failure or blocked airflow |
| P-11 | M | No user-accessible mains voltage with the lid fitted | Basic electrical safety |
| P-12 | S | Alert when a port is energised but drawing no current | An enabled port at 19V drawing <20mA has nothing plugged in — a live barrel plug is loose in the rack. **Alert only; it must never switch the port off** (see S-4) |

### 3.4 Mechanical

| ID | Pri | Requirement | Justification |
|---|---|---|---|
| M-1 | M | 19" rack, 1U (≤44.45mm), standard ear spacing | Target rack |
| M-2 | M | Chassis accepts the RSP-1000-48 (295 × 127 × 41mm) | Fitted unit as of WP-3. The envelope is unchanged from when this was written as an upgrade path — which is why the switch cost nothing (§4.2.3) |
| M-3 | M | All six barrel jacks, IEC inlet and RJ45 on the rear panel | Cables exit rearward in a rack |
| M-7 | S | Output jacks accept a **locking** (threaded-collar) barrel plug | Prevents the accidental disconnection that leaves a live plug dangling — the most common way §4.8.1's hazard actually occurs |
| M-4 | M | Master button and status indication on the front panel | Operated from the front |
| M-5 | S | 3D-printed panels fit a 220×220mm bed | Inherited from upstream; keeps the design home-printable |
| M-6 | M | Board-mounted components ≤40mm tall | 41mm PSU in a 43mm envelope — height is the binding axis |

### 3.5 Thermal and acoustic

| ID | Pri | Requirement | Justification |
|---|---|---|---|
| T-1 | M | Sustain rated output at 35°C ambient without thermal throttle | Realistic rack inlet temperature |
| T-2 | M | No component above 80% of its rated maximum temperature at rated load | Derating for service life |
| T-3 | S | ≤35 dBA at cluster idle | It lives in a homelab, not a datacentre |
| T-4 | M | Fan speed driven by measured board temperature | Quiet at idle, adequate under load |
| T-5 | M | Fan failure detected and reported | Tach feedback; silent fan failure precedes thermal failure |

### 3.6 Control and software

| ID | Pri | Requirement | Justification |
|---|---|---|---|
| S-1 | M | Wired Ethernet, not WiFi | A PDU you cannot reach is worthless; it sits in a rack next to a switch |
| S-2 | M | Per-port on/off/cycle over HTTP | Scriptable recovery |
| S-3 | M | Prometheus-compatible metrics endpoint | Saturn already runs Prometheus |
| S-4 | M | **Loss of network, MCU crash or firmware failure must not drop output power** | Restates F-5 from the software side; the watchdog must never disable outputs |
| S-5 | S | OTA firmware update | It will be inside a closed chassis in a rack |
| S-6 | S | Report PSU health if the PSU exposes a DC-OK signal | Early warning |
| S-7 | C | MQTT publication | Convenience for home automation |

### 3.7 Licensing and documentation

| ID | Pri | Requirement | Justification |
|---|---|---|---|
| L-1 | M | Licensed CERN-OHL-S v2 | Upstream is strongly reciprocal; not optional |
| L-2 | M | Modifications documented relative to upstream | CERN-OHL-S §3.3 |
| L-3 | M | **Publish editable source** (KiCad projects, FreeCAD models), not only exports | The licence requires the preferred form for modification — upstream arguably fails this; this derivative should not |
| L-4 | M | ShrikeLab name and logo not carried into this derivative | CERN-OHL-S §7 grants no trademark rights |

---

## 4. Design

### 4.1 System architecture

```
IEC inlet (fused) ──► RSP-1000-48 ──► 48V bus (fused) ──► backplane
                        ▲                                    │
                remote ON/OFF                                 │
                from latching button                          │
                        ┌───────────────────────┬─────────────┴─────────┐
                   [2ch board A]           [2ch board B]           [2ch board C]
                    ch1    ch2              ch3    ch4              ch5    ch6
                        │                       │                       │
   per channel: 5A fuse ─► LM5116 sync buck 48V→19V/7A ─► 2mΩ shunt ─► TVS ─► barrel jack
                           + independent OVP comparator ─► crowbar SCR
                        │                       │                       │
                   [control board]  ESP32-S3 + W5500
                      ├─ I²C  → 6× INA226        V / A / W per node
                      ├─ GPIO → 6× LM5116 UVLO   per-node enable (open-drain, fail-ON)
                      ├─ PWM  → 3× NF-A4x20 + tach, NTC-driven
                      └─ front panel: latching button, 6 status LEDs
```

### 4.2 Power budget and PSU selection

#### 4.2.1 Load characterisation

MS-01 nameplate is 19V/9.47A/180W (Huntkey HKA18019095-6C). Measured behaviour differs
sharply and is what the design is sized against:

| Condition | Per node | ×6 | Source |
|---|---|---|---|
| Idle, tuned Linux | ~13W | 78W | cloudmagazin |
| Idle, Windows | 25–30W | 180W | ServeTheHome |
| Sustained load | 90–95W | 570W | ServeTheHome |
| Turbo, first ~45s | ~115W | 690W | ServeTheHome |
| Nameplate | 180W | 1080W | Minisforum |

**Design point: 690W aggregate** (all six in turbo). Sizing to the 1080W nameplate would
be sizing to a number no measurement supports.

#### 4.2.2 Rail loading

At 95% channel efficiency, 690W delivered draws **726W** from the 48V rail — **72% of
the RSP-1000-48's 1008W.** Sustained all-six load draws 600W (60%).

This is comfortable, and it was not always so. See §4.2.3.

#### 4.2.3 Selection

**Mean Well RSP-1000-48** — 48V, 21A, 1008W, 295 × 127 × 41 mm, ~91%, active PFC,
built-in fan, remote sense, remote ON/OFF, DC OK, 1U profile.

**This is a change from the RSP-1000-48 specified in earlier drafts, made at WP-3 when
sourcing revealed the RSP-1000-48 is discontinued.** The reasoning is recorded because
the change closes a risk rather than merely substituting a part:

| | RSP-1000-48 (was) | **RSP-1000-48 (is)** | UHP-750-48 (considered) |
|---|---|---|---|
| Lifecycle | **Discontinued** | **Active** | Active |
| Availability | ~700 units remain | In stock | **17-week lead** |
| Output | 753.6W | **1008W** | 753.6W |
| Load at the 726W peak | **96%** | **72%** | 96% |
| Efficiency | 92% | ~91% | **95%** |
| Cooling | Own fan | Own fan | **Fanless — its ~38W becomes the chassis's problem** |
| Size | 250 × 127 × 41 | 295 × 127 × 41 | 237 × 100 × 41 |
| Price | $186–237 | ~$230–260 | ~$194 |

**Three consequences, all favourable:**

1. **The chassis does not change.** It was already dimensioned to the 295mm RSP-1000-48
   under M-2, precisely so this unit would drop in. The upgrade path became the build.
2. **Risk R-3 closes outright.** 72% of rating is not a marginal operating point, so the
   headroom question that motivated M-2 no longer exists.
3. **OPEN-6 is downgraded from a hard gate to informational.** The six-node measurement
   was a gate because a high reading would have invalidated a 753.6W supply. At 1008W the
   design tolerates a measurement 38% above the estimate before the question reopens.
   The measurement is still worth taking — it is still the only real evidence in §4.2.1 —
   but it no longer blocks a purchase.

**The UHP-750-48 was the interesting near-miss.** It is Mean Well's actual successor and
is better on two axes that matter here: 95% efficiency, and **completely silent**, which
would have helped T-3 more than anything else in the design, since the PSU's own fan is
likely the loudest thing in the box. It was rejected on a 17-week lead time and because
being fanless inverts the thermal budget — its ~38W of loss stops being self-managed and
becomes chassis dissipation, roughly doubling the airflow the design must handle (§4.7).
Worth revisiting for a second unit, where a four-month lead is not an obstacle.

**Mount the PSU with its long axis across the rack width.** At 295mm of the 438.7mm
internal width it consumes only 127mm of depth, so upstream's `19in_Dual-Tray` depth of
~213mm suffices. Remaining volume: a full-width **438.7 × 86 mm** band (37,728 mm²) plus
a **143.7 × 127 mm** pocket beside the PSU — ample for three 2-channel boards, the control
board and the backplane. **Height, not depth, is the binding constraint** (M-6).

#### 4.2.4 Decision record: single large supply vs 2× 450W

Analysed and rejected. Recorded so it is not re-litigated.

> Originally argued against the 753.6W RSP-750-48, where the dual option's headroom
> advantage was its strongest card. **With the RSP-1000-48 fitted (§4.2.3) the single
> supply now wins on headroom too**, so the argument below only got stronger. It is
> preserved because the three structural objections are what actually decided it, and
> they are unchanged.

| | 1× RSP-1000-48 | 2× HRP-450-48 |
|---|---|---|
| Total | **1008W** | 912W |
| Load at 726W peak | **72%** | 80% |
| Efficiency | 92% | 89.5% (~22W more heat in 1U) |
| Footprint | 250×127 = 31,750 mm² | rotated 210×218 = 45,780 mm² |
| Side-by-side fit | n/a | **2×218 = 436mm in 438.7mm — does not fit** |
| AC inlets | 1 | 2 |
| Board architecture | 3× identical 2-channel | forced to 2× 3-channel |

Dual no longer wins on headroom at all — 1008W beats 912W, and 72% beats 80%. When this
was written against the 753.6W unit it did, and that was the strongest argument for it.
It lost then on three structural counts, all of which still stand:

1. **It cannot sit side-by-side.** 1.35mm per side is inside sheet-metal tolerance,
   before airflow or cable routing. Only a 90° rotation works, costing 44% more tray area.
2. **It forces two independent 48V domains.** HRP-450s have no active current sharing and
   cannot be paralleled. Two domains must not share a board's input, so the 3× identical
   2-channel architecture collapses into 2× 3-channel.
3. **Its resilience benefit is partitioning, not redundancy.** 456W cannot carry six nodes
   at 690W, so a PSU failure drops three nodes rather than failing over. With three
   control-plane nodes split 2+1, half of all PSU failures lose quorum anyway. The
   backplane, master switch and chassis fan remain single points of failure regardless.

The headroom concern was answered by fitting the RSP-1000-48 outright (§4.2.3), which also supports
active current sharing if a second chassis is ever wanted. Genuine cluster resilience
belongs at the second-PDU level, not inside one 1U box.

### 4.3 Buck channel design

#### 4.3.1 Controller selection

**TI LM5116** — 6–100V input, current-mode synchronous buck controller, external N-FETs.
TI characterises it as *"most efficient for output currents of 2A to 10A"* with discrete
SO-8 MOSFETs; 7A sits mid-range. Current-mode control simplifies compensation relative to
the voltage-mode LM5146.

#### 4.3.1.1 OPEN-1 / R-7 — RESOLVED: the integrated-FET route is not thermally viable

R-0 and R-2 both argued for an integrated-FET regulator to cut layout risk. That option
was investigated properly and **fails on thermals.** The reasoning is recorded because the
conclusion is load-bearing.

**Candidates.** Only one part in the 60V-class integrated family reaches a 48V bus:

| Part | V_in max | I_out | Verdict |
|---|---|---|---|
| LT8645S | 65V | 8A | Voltage range OK, **thermals fail** — see below |
| LT8648S / LT8648SP | **42V** | 15A | **Excluded** — below a 48V bus |
| LT8641 | 65V | 3.5A | Insufficient current |

**Output voltage was not the obstacle.** The LT8645S range is 0.97V to (V_in − 0.5V), so
19V from 48V is comfortably inside it. This was the stated concern in R-7 and it is wrong.

**Package dissipation is the obstacle.** The datasheet gives **θ_JA = 31°C/W**,
θ_JC(pad) = 6°C/W, T_J(max) = 125°C. At 133W output:

| Assumed efficiency | P_diss | T_J at 35°C ambient (θ_JA = 31) |
|---|---|---|
| 95% | 7.0W | **252°C** |
| 96% | 5.5W | **207°C** |
| 96%, generous θ_JA = 15°C/W (heavy copper) | 5.5W | **118°C — no margin** |

Even the most favourable case sits on the 125°C limit, and it requires simultaneously
assuming best-case efficiency *and* a θ_JA half the datasheet figure. **There is no
operating point with usable margin.**

**Why.** The 8A rating is real, but it is a rating at low output *power*. At 5V/8A the
part delivers 40W and dissipates ~3W. Here it would deliver 133W. Conduction losses scale
with I² regardless of V_out, and all of it lands in one 4 × 7 mm package.

**The discrete route wins precisely because it is discrete.** Two SO-8 FETs each carry
their own losses into their own thermal pad, with the inductor's ~0.7W in a third package.
The dominant single-component load is the high-side FET at ~1.84W (§4.3.3); at a
pour-assisted θ_JA of ~35°C/W that is a 64°C rise, so T_J ≈ 99°C at 35°C ambient with
forced air still to come. Spreading the heat is not a side benefit here — it is the
requirement.

**Decision: LM5116 + discrete MOSFETs. Confirmed, not defaulted.**

> **This closes OPEN-1 and R-7, and it escalates R-0.** The layout-risk mitigation that
> integrated FETs would have provided is unavailable. **Independent schematic and layout
> review is therefore mandatory, not advisory.**

#### 4.3.2 Operating point

| Parameter | Value | Derivation |
|---|---|---|
| V_in | 48V | Rail |
| V_out | 19.0V | MS-01 spec |
| I_out | 7A continuous (133W) | E-2 |
| Duty cycle D | 0.396 ideal, ~0.41 with losses | V_out/V_in |
| f_sw | **250 kHz** | See §4.3.3 — trades switching loss against inductor size |
| Ripple ΔI_L | 30% of I_out = 2.1A target | Standard practice |

**Inductor:** `L = V_out(1−D) / (f_sw · ΔI_L) = 19 × 0.604 / (250k × 2.1) = 21.9 µH` → **22 µH standard**.
At 22µH and 250kHz, actual `ΔI_L = 19 × 0.604 / (250k × 22µ) = 2.09A`, so `I_pk = 7 + 1.04 = 8.04A`.

#### 4.3.2.1 OPEN-2 — RESOLVED: Coilcraft XAL1510-223

The first-draft part (Bourns SRP1265A-220M) was rated **9A** against an 8.04A peak — 12%
margin, and saturation derates with temperature. Rejected. Sourced replacements:

| Part | L | I_sat | DCR typ | Size | Verdict |
|---|---|---|---|---|---|
| **Coilcraft XAL1510-223** | 22µH | **18.7A** | 14.5mΩ | 15.5×16.5×10mm | **Selected** |
| Coilcraft XAL1510-153 | 15µH | 23.0A | 9.2mΩ | same | Alternate, see below |
| Würth 74439370220 | 22µH | 22.4A (30% drop) | — | 15.4×16.4×10mm | Viable second source |
| Bourns SRP1265A-220M | 22µH | 9.0A | 12mΩ | — | **Rejected** |

**XAL1510-223 selected.** 18.7A saturation against an 8.04A peak is **2.3× margin**, which
survives thermal derating and fault transients without argument. It holds the designed 30%
ripple, and at 10mm tall it is untroubled by the 1U envelope.

**Cost of the choice:** DCR is 14.5mΩ, not the ≤8mΩ originally targeted. Conduction loss
rises from 0.39W to **0.71W** per channel — 0.32W × 6 = ~1.9W more heat in the chassis.
Accepted; saturation margin is worth more than 2W of fan duty.

**XAL1510-153 (15µH) is the alternate**, and is better on paper — 23A I_sat and 9.2mΩ DCR,
so 0.45W instead of 0.71W. It is not the primary because at 15µH the ripple rises to 3.06A
(44%), above the 20–40% band, which increases output-capacitor RMS current and core loss.
**Revisit it if the thermal measurement at stage 3 shows the 22µH part's DCR loss is the
binding constraint** — that is a measurement, not a guess, and the parts are pin-compatible.

#### 4.3.3 Loss budget (per channel at 7A)

Assuming 60V / ~5.2mΩ MOSFETs (e.g. PSMN5R2-60YS), R_ds(on) hot ≈ 1.5× nominal:

| Loss | Value | Derivation |
|---|---|---|
| HS conduction | 0.16W | `I² · R_ds · D = 49 × 0.0078 × 0.41` |
| LS conduction | 0.23W | `49 × 0.0078 × 0.59` |
| **HS switching** | **1.68W** | `0.5 · V_in · I_out · (t_r+t_f) · f_sw = 0.5 × 48 × 7 × 40n × 250k` |
| Gate drive | 0.11W | `Q_g · V_drv · f_sw × 2` |
| Inductor DCR | 0.39W | `49 × 0.008` |
| Inductor core | ~0.20W | Estimate |
| Current-sense 7mΩ | 0.34W | `49 × 0.007` — requires a 1W part |
| INA226 shunt 2mΩ | 0.10W | `49 × 0.002` |
| Caps ESR, controller I_q, copper | ~0.4W | Estimate |
| **Accounted total** | **~3.6W** | → 97.4% |
| **Design target** | **≤6.6W** | **95%**, with margin for unmodelled loss |

**Switching loss dominates at 48V input** — 1.68W of an accounted 3.6W, in one package.
This drives three decisions: 250kHz rather than 300kHz+; low-Q_g FET selection as a
primary criterion; and it is the strongest technical argument for evaluating the
integrated-FET LT8645S under [OPEN-1].

Design efficiency is held at **95%**, not the 97.4% the accounted losses suggest, because
the model omits layout-dependent losses. 94% is the requirement (E-6).

#### 4.3.4 Component targets

| Item | Specification |
|---|---|
| MOSFETs | ≥60V V_ds, ≤6mΩ R_ds(on), low Q_g, thermally-padded SO-8/PQFN |
| Inductor | 22µH, I_sat ≥12A, I_rms ≥8A, DCR ≤8mΩ, shielded |
| Current sense | 7mΩ, ≥1W, ≤100ppm/°C, 2512 |
| Telemetry shunt | 2mΩ, ≥0.5W, ≤50ppm/°C |
| Output caps | 35V rated, low-ESR polymer + ceramic, ripple per E-3 |
| Input caps | 100V ceramic + 63V bulk |

Current limit set at ~1.5× rated (≈10.5A) via the sense resistor (P-4).

### 4.4 Protection design

#### 4.4.1 Why enable-pin shutdown is insufficient

Per-channel switching is implemented by pulling the LM5116 UVLO pin low (§4.5.2), which
also provides soft-start on every power-on (P-8). **This is adequate for commanded
switching and for controller-detected faults, and inadequate for a shorted high-side
FET** — when the pass device is a short, disabling its controller achieves nothing. P-2
exists because of this, and it drives §4.4.2.

#### 4.4.2 Output OVP — crowbar

Each channel carries an **OVP comparator with its own reference, powered from the
channel's own output**, independent of the MCU and of the regulation loop (P-1).

- **Trip point ~21.5V.** Above 19V + 10% to avoid nuisance trips on load-step overshoot;
  below the ~25V rating typical of a laptop-style DC input stage.
- On trip the comparator fires an **SCR crowbar across the 19V output**, clamping the node
  input to the SCR forward drop (~1.5V) regardless of what the buck stage is doing.
- The crowbar draws fault current through the channel's **5A fast-blow 48V input fuse**
  until it clears, isolating the channel permanently.

**Coordination:** the fault path is 48V → shorted HS FET → inductor → SCR → ground,
current-limited by the PSU (~21A). At ~3× rating a 5A fast-blow clears in the order of
100ms. During that window the node sees the SCR drop, not 48V. The crowbar does the
protecting; the fuse does the isolating. The SCR must be rated for the PSU's limited
current for that duration.

**OPEN-3 — RESOLVED, favourably.** The RSP-1000-48's overload behaviour is specified as
**"over load (constant current limiting)"**. This is the best of the three possible
behaviours for crowbar coordination:

- **Constant current** means that during a crowbar event the PSU *holds* current at its
  limit (21A rated, trimmable to 110%) rather than shutting down or hiccupping. A 5A
  fast-blow fuse seeing a sustained ~21A — 4.2× rating — clears predictably, in the order
  of 10–50ms. **The RSP-1000-48 improved this** over the originally specified RSP-750-48's
  15.7A: more fault current into a fast-blow fuse means a shorter clearing time, so the
  node sits behind the crowbar for less of it. The cost is an SCR that must carry 21A
  rather than 15.7A for that window — a selection criterion, not a problem.
- Had it been **hiccup** mode, the PSU would have pulsed on and off, the fuse would have
  seen an intermittent current with long cooling gaps, and clearing time would have become
  indeterminate — the fuse might never clear while the node sat behind a repeatedly-firing
  crowbar. That failure mode does not arise here.

The unit also carries short circuit, over voltage and over temperature protection, and is
UL 62368-1 / TÜV EN 62368-1 approved.

> **Residual, for the R-0 reviewer:** constant-current limiting is shared across all six
> channels. A crowbar on one channel pulls the *whole bus* to its current limit until that
> channel's fuse clears, so for ~100ms the other five channels see a sagging 48V rail.
> Each buck stage must ride through that without dropping its output — this is why input
> bulk capacitance per channel is specified, and it is a specific item to put in front of
> the reviewer rather than assume.

#### 4.4.3 Protection summary

| Layer | Device | Threshold | Covers |
|---|---|---|---|
| Mains | IEC inlet fuse | Per PSU inrush rating | Mains fault |
| Bus | 48V fuse | 20A | Backplane fault |
| Channel input | 5A fast-blow | 5A | Channel catastrophic failure; crowbar coordination |
| Channel regulation | LM5116 current limit | ~10.5A | Output short, node fault |
| Channel output | **OVP comparator + SCR crowbar** | ~21.5V | **Shorted pass device — the node-destroying mode** |
| Channel output | TVS | ~24V standoff | Transients |
| Bus | TVS | ~58V standoff | Transients |
| Thermal | NTC per board → MCU | Per T-2 | Fan failure, blocked airflow |
| Discharge | Bleed resistor per output | — | P-9 |

### 4.5 Control and telemetry

#### 4.5.1 Metering

**INA226** per channel, high-side on the 19V output, 2mΩ shunt.

- At 7A: 14mV across the shunt, against the INA226's ±81.92mV range — 17% of range, so
  headroom for fault currents while retaining resolution.
- Bus-voltage common mode 19V, against a 36V maximum. Compliant.
- Current LSB ≈ 214µA (7A / 32768). Resolution is far beyond what is needed.
- Six devices on one I²C bus; the INA226's A0/A1 pins give 16 addresses. No multiplexing.

#### 4.5.2 Switching — fail-ON is a requirement, not a default

Each channel's LM5116 UVLO pin is held in the **enabled** state by its own resistor
divider from the 48V rail. The MCU disables a channel by pulling that node low through an
**open-drain** N-FET.

This satisfies F-5 and S-4 directly: an unpowered, crashed, unprogrammed or removed MCU
leaves every output **on**. There is no firmware state in which the PDU drops power it was
not told to drop. **The watchdog must reset the MCU, never disable outputs.**

#### 4.5.3 Master switching

The front-panel latching button drives the **PSU's remote ON/OFF input** rather than
switching 48V through a FET. This avoids commutating ~15A and eliminates upstream's
master-FET entirely — an option upstream did not have with the HRP-300.

**OPEN-4 — RESOLVED.** The RSP-1000-48 has **built-in remote ON/OFF control, a DC OK
signal, remote sense, and a 5V auxiliary output**, all on connector **CN50** (Hirose
DF11-12DP-2DS, 12-pin; the mating DF11-12DS-2C and its crimps are a BOM line).

Remote ON/OFF is a **dry contact between CN50 pin 6 (on/off) and pin 2 (−S)**: shorted
turns the output on, open turns it off. The front-panel latching button does exactly this.
No AC-side relay, no master FET, no 15A commutation anywhere in the design.

> **Note the pinout differs from the RSP-750 series**, which uses pin 13 to pin 14. If you
> have the RSP-750 wiring in your head from an earlier draft of this document, discard it.

**The DC OK signal satisfies S-6** as a plain GPIO input, no extra hardware. Output current
is trimmable 40–110% via an external DC signal — not used in normal operation, but it means
the bus current limit can be *lowered* during bring-up to make early faults gentler (R-0
control 8).

##### The auxiliary rail is not used, and that is deliberate

The RSP-1000-48's aux output is **5V at 0.5A — 2.5W**. Earlier drafts, written against the
RSP-750's 12V aux, planned to run the control board and display from it. That does not work
here, for two independent reasons:

1. **It is too small.** ESP32-S3 (~0.4W) + W5500 (~0.45W) + display with backlight (~0.75W)
   + six INA226s + the LED expander comes to roughly **2.0W of the 2.5W available — 80%**,
   which is the derating limit (T-2), not a margin.
2. **The fans need 12V regardless.** Three NF-A4x20 PWM cannot run from a 5V rail at all.

**Housekeeping therefore comes from the 48V bus**, via a small **LM5164** (100V input, 1A,
integrated FET) producing 12V for the fans, and a second stage producing 5V for the logic.

This is not a compromise — it is better than the original plan. The property the aux rail
was wanted for was *"the MCU stays alive and telemetry keeps reporting even with every
output channel disabled or faulted."* **The 48V bus is live whenever the PSU is on,
independently of whether any channel is enabled**, so it provides exactly that property
with an order of magnitude more current available. The aux rail is brought to a header and
left unpopulated, available as a standby feed if a use for it ever appears.

#### 4.5.4 MCU and connectivity

**Housekeeping supply** (see §4.5.3): 48V bus → LM5164 → 12V/1A → fans; 12V → 5V/1A →
logic. Estimated draw ~2.0W. The control board is therefore alive whenever the PSU is on,
regardless of the state of any output channel.

**ESP32-S3** with **W5500** SPI Ethernet (S-1). GPIO budget: 6 enable + 2 I²C + 4 SPI +
3 fan PWM + 3 tach + 1 button + 3 NTC ADC ≈ 22, plus status LEDs via an I²C expander to
conserve pins. Comfortably within the S-3's ~45 usable GPIO.

#### 4.5.5 Firmware

**ESPHome**, not bare ESP-IDF. Native `ina226`, `switch`, `fan` and NTC components, a
built-in Prometheus endpoint (S-3) and OTA (S-5) reduce this to configuration rather than
a C firmware project — proportionate for six switches and eighteen sensors.

```
GET  /metrics                    saturn_pdu_watts{port="3"} 94.2
POST /switch/port_3/turn_off
```

### 4.5.6 Front-panel display (F-8, F-9)

**1U is the whole problem here.** The panel is 44.45mm tall; after rack ears, folds and
mounting margin roughly **38mm of usable window height** remains. That single number
eliminates most touchscreens before any other consideration:

| Option | Module size | Fits 38mm? | Touch |
|---|---|---|---|
| **LILYGO T-Display-S3 Touch** — 1.9" 170×320 IPS | **60.8 × 25.5 mm** | **Yes, comfortably** | **Capacitive (CST816)** |
| 0.96" OLED SSD1306 | 27 × 27 mm | Yes | No |
| 2.42" OLED SSD1309 | 72 × 42 mm | Marginal | No |
| 2.8" TFT 240×320 | 69 × 50 mm | **No** | Capacitive available |
| 3.5" TFT | 85 × 55 mm | **No** | — |

**Selected: LILYGO T-Display-S3 Touch** — 1.9" 170×320 colour IPS (ST7789) with a CST816
capacitive touch layer, ~$25, and existing ESPHome/LVGL community support. It is the only
option found that is both a genuine colour touchscreen and physically fits 1U. The
landscape 320×170 aspect suits a rack panel well: one wide row per node.

**It runs as a separate device, not as the main controller.** The board carries its own
ESP32-S3, but its display bus consumes ~15 GPIO and the breakout cannot also serve the 22
GPIO the control board needs (§4.5.4). More importantly, **F-9 requires that a hung or
crashed display cannot affect power delivery.** So:

- The **control board** owns all six enable lines, the INA226 bus, the fans and the button.
  It is the only thing that can change a power state.
- The **display board** is a client. It reads telemetry from the control board over UART
  and renders it. If it crashes, hangs, or is unplugged entirely, nothing downstream
  notices. Both are powered from the PSU's 12V auxiliary rail (§4.5.3).

**What it shows** — aggregate watts as the headline figure, then six rows of
per-node V / A / W and on/off state, plus fan RPM and board temperature.

**Touch behaviour, per F-9:** navigation and paging are free. **Power control requires two
deliberate steps** — select a node, then hold a confirm control for 2 seconds, with the
node's name shown. A single tap can never de-energise anything. An idle timeout returns to
the read-only aggregate view.

### 4.6 Board architecture

**3× identical 2-channel boards** on a passive backplane carrying 48V, I²C and enable
lines, plus a separate control board.

Justification: one small board design is prototyped and bench-tested at ~$30/spin before
committing to the full set; a failed channel is a cheap field swap; thermal and layout
problems are contained. **The controllers are not the cost driver — assembly is** (§5),
and three identical boards panelise into a single PCBA setup fee.

The MCU is kept off the high-current boards to isolate its ground reference from the
switching nodes.

**Stackup:** 4-layer, 2oz outer / 1oz inner. Upstream's 2-layer/2oz carried 15A via copper
pours; this design carries 15.1A on the bus and 7A per output with switching nodes present,
so inner planes are needed for the return path and thermal spreading.

### 4.7 Thermal design

At the 690W design point, the buck stages dissipate `690/0.95 − 690 ≈ 36W`, plus ~2W of
control — **~38W inside the chassis**. PSU losses (~60W at 92%) are exhausted by the PSU's
own fan and are not part of this budget.

Airflow for a 15°C rise:
`V = P / (ρ · c_p · ΔT) = 38 / (1.2 × 1005 × 15) = 2.1 L/s ≈ 4.5 CFM`

**3× Noctua NF-A4x20 PWM** (~9.4 CFM free air each). Even heavily derated for static
pressure this is several times the requirement; three are specified for distribution
across the three boards and for T-5 tolerance, not because one is insufficient. Fan speed
is NTC-driven (T-4) with tach feedback (T-5), which also serves T-3 — at cluster idle
(~78–180W) dissipation is under 10W and the fans can sit near minimum.

### 4.8 Mechanical design

- Re-model parametrically in **FreeCAD** and publish the source (L-3). Upstream's 19"
  `.stp` files are retained as dimensional reference — they are true B-rep solids and
  dimensionally trustworthy, unlike the mesh-only printed parts.
- Envelope: 483.2mm across ears, 438.7mm internal, ~43mm height, ~213mm depth.
- **Rear panel:** 6× barrel jacks, IEC inlet (fused), RJ45.
- **Front panel:** latching button, 6 status LEDs.
- Board mounting inherits upstream's 4× 3.0mm NPTH pattern.

**[OPEN-5] The barrel jack size is unverified.** Web sources do not state it reliably;
it is most likely 5.5×2.5mm centre-positive. **Measure a stock MS-01 plug with calipers
before any footprint or panel cutout is drawn.** This gates all mechanical work.

Barrel jacks at 7A run warm; specify a panel jack rated ≥10A, not a generic part.
Specify a **locking** (threaded-collar, Switchcraft S760K class) jack per M-7.

#### 4.8.1 The interconnect cable — and the live-plug question

**Six cables are required and they are not in upstream's BOM or in any earlier
draft of this one.** The stock Huntkey brick's cable is **captive** — the plug end
is permanently attached to the brick — so it cannot be reused. These are new leads
with a **barrel plug at both ends**.

**Specify 18AWG.** At 7A over a 0.5m run (1m of conductor there and back):

| Gauge | Resistance | Drop at 7A | Dissipated in the cable |
|---|---|---|---|
| **18AWG** | ~21 mΩ/m | **0.15V** | **1.0W** |
| 20AWG | ~33 mΩ/m | 0.23V | 1.6W |
| 22AWG | ~53 mΩ/m | 0.37V | 2.6W |

Most cheap DC extension leads are 20–22AWG and rated 3–5A. Specify the gauge; do
not buy on price.

**This consumes part of the E-1 budget.** E-1's ±2% is ±0.38V *measured at the PDU
jack*. An 18AWG lead spends 0.15V of it before the node sees anything, so the
regulator setpoint is trimmed slightly high (**~19.1V**) rather than dead-on 19.0V.
A 22AWG lead would spend almost the entire budget by itself.

**On exposed live plugs.** A cable connected at the PDU but not at a node presents
a live 19V male plug with tip and sleeve ~1mm apart. Two separate questions:

- **Shock hazard: none.** IEC 62368-1 classes DC below 60V as **ES1** — no
  electrical energy hazard. A 19V plug is safe to handle.
- **Short-circuit hazard: real.** Dropped on a rack rail or a screw, it bridges 19V
  through a source good for 10.5A before current limiting — ~200W into a pinhead
  contact. Sparks, a melted plug, a scorch mark, possibly welding itself to what it
  touched.

**This hazard is inherited, not introduced.** Every stock brick already ends in a
live male plug with 9.47A behind it; six bricks means six of them in the rack
today. What the PDU adds is the ability to **de-energise a dangling cable
remotely**, which no brick can do. Controls: locking jacks (M-7), the P-12 alert,
and the operating procedure in `docs/safety.md` — unused ports stay off, and a port
is switched off before it is unplugged.

---

## 5. Cost

Qty-10 distributor pricing, indicative, to be verified against live stock.

**Per channel ≈ $27:** LM5116 $1.31 (LCSC, verified) · FETs ×2 $1.80 · inductor $3.50 · INA226 $2.50 ·
sense + shunt $1.30 · output caps $4.80 · input caps $3.00 · OVP + crowbar $1.20 ·
fuse + TVS $1.45 · passives $0.60 · barrel jack $2.00.

| Item | Cost |
|---|---|
| 6 channels | $164 |
| 3× 4-layer PCB (5pcs) | $40 |
| PCBA setup + assembly | $120 |
| Control board | $30 |
| T-Display-S3 Touch display (F-8) | $25 |
| Backplane | $15 |
| Wiring, connectors | $25 |
| 6× 18AWG locking interconnect cables (§4.8.1) | $30 |
| **Electronics** | **~$450** |
| RSP-1000-48 | ~$245 |
| Fans, IEC, button | ~$65 |
| Sheet metal, printed panels, fasteners | ~$120 |
| **Total per unit** | **~$780–860** |

**Excludes prototype iterations, and R-2 says budget three board spins** — add ~$150–250
and several weeks. A realistic all-in first-unit figure is **$900–1,100**, plus the R-0
review if paid ($200–500).

Six stock Minisforum bricks are ~$240–360, so this is 3–4× the thing it replaces. The
delta buys remote per-node power control, per-node telemetry, a front-panel display and
1U consolidation. Worth naming plainly: a used switched-and-metered rack PDU (APC AP7921
class, ~$150–300) plugged into the six existing bricks delivers remote switching and
per-outlet metering for a fraction of this, in an afternoon. **What this project buys over
that is the 1U consolidation and the elimination of six bricks — a space and elegance
goal, not a functional one.** That is a perfectly good reason to build it; it should just
be the actual reason.

---

## 6. Open items

| ID | Item | Status | Outcome |
|---|---|---|---|
| OPEN-1 | LM5116 + discretes vs integrated FETs | ✅ **Closed** | **LM5116 + discretes.** Integrated fails on package thermals (§4.3.1.1) |
| OPEN-2 | Inductor saturation rating | ✅ **Closed** | **Coilcraft XAL1510-223**, I_sat 18.7A = 2.3× margin (§4.3.2.1) |
| OPEN-3 | Crowbar/fuse coordination vs PSU overcurrent | ✅ **Closed** | Constant-current limiting — the favourable case (§4.4.2) |
| OPEN-4 | RSP-1000-48 remote ON/OFF | ✅ **Closed** | Built in, plus DC OK, remote sense and a 12V aux rail (§4.5.3) |
| R-7 | 19V from an integrated regulator | ✅ **Closed** | Voltage was never the issue; thermals were. Merged into OPEN-1 |
| **OPEN-5** | **Barrel jack dimensions** | 🔴 **Open — needs you** | Physical caliper measurement. Gates all mechanical work |
| **OPEN-6** | **Real six-node peak power draw** | 🟡 **Open — informational** | Was a gate against a 753.6W supply. At 1008W the design absorbs a reading 38% above estimate, so this now validates §4.2 rather than blocking it |
| **R-0** | **Independent schematic + layout review** | 🔴 **Accepted, not resolved** | Declined. Compensating controls in §7 carry the full weight (§4.3.1.1) |
| OPEN-7 | PSU discontinued | ✅ **Closed** | RSP-1000-48 EOL → **RSP-1000-48**, which also closes R-3 (§4.2.3) |

**Everything that could be closed from datasheets has been closed.** The three remaining
items are a physical measurement, a physical measurement, and a decision — none of which
can be answered from a datasheet, and all three gate fabrication rather than design.

---

## 7. Risks and how each is closed out

### R-0 — No power-electronics expertise in the review loop

**This is the dominant risk and I under-weighted it in the first draft.** It is larger
than any individual circuit risk below, because it is the risk that removes the safety net
under all of them.

**Plain terms:** I can produce a specification that reads correctly, uses the right
formulas, and is still wrong in ways neither of us would spot. Power electronics is
unforgiving — a design that is 95% right does not run 95% as well, it fails. The failures
are concentrated in the things that do not appear on a schematic at all: physical copper
geometry, parasitic inductance in the switching loop, ground return paths, thermal
coupling between parts. Those are learned by building, and 750W of mains-derived power
into $4,200 of computers is an expensive classroom.

**What it costs if unaddressed:** the realistic bad outcome is not "it doesn't work" —
that is recoverable. It is a channel that works on the bench, then fails shorted at 03:00
in month four and puts 48V into a node.

**Decision taken: no external review. Bench testing only.** Recorded as a deliberate
choice, not an oversight. The integrated-FET mitigation also failed on thermals
(§4.3.1.1), so **two of the three planned mitigations for R-0 are unavailable** and the
remaining programme has to carry the full weight. It is set out below and is materially
more demanding than the first draft, because it is now the only thing there is.

**Compensating controls — none require expertise you don't have:**

| # | Control | Cost | What it buys |
|---|---|---|---|
| 1 | **Start from the vendor reference design and log every deviation** | Free | TI publishes a complete LM5116 schematic *and* board layout. Copy the power stage geometry verbatim. Risk concentrates in the deviations, so a written deviation list becomes the review checklist you'd otherwise have paid for |
| 2 | **Buy the LM5116 evaluation board and measure it first** | ~$100 | Gives a *known-good reference*. When your board misbehaves, comparing against a working board separates "my design is wrong" from "my expectations are wrong" — the single hardest thing to judge without experience |
| 3 | **Destructive OVP proof** (§9.1) | ~$5 | Deliberately solder drain-to-source across a high-side FET and confirm the crowbar saves a dummy load. This *is* the failure mode that kills nodes. Do not simulate it — cause it |
| 4 | **Never bench-test into an MS-01** | ~$30 resistive dummy load | Bring-up failures are expected and should be cheap |
| 5 | **72-hour burn-in into dummy loads before any node connects** | Time only | Latent defects — marginal solder, an over-stressed part — surface under sustained heat, not in a 30-minute test |
| 6 | **Re-run fault injection *after* burn-in** | Time only | Confirms protection still works on a thermally-aged board, not just a fresh one |
| 7 | **30-day canary on one worker node** (§9.4) | Time only | **The most valuable control here.** It converts the worst case from "six nodes die" to "one worker dies", and buys a month for latent faults to appear |
| 8 | **Trim the PSU current limit down during bring-up** | Free | RSP-1000-48 output current is trimmable to 40% (§4.5.3). Early faults are gentler |

> **Residual risk is accepted and non-trivial.** Controls 3, 5, 6 and 7 are the ones that
> matter most; 7 in particular is what stops a latent design error from being a
> whole-cluster event. **Stage 4's fault injection and the stage 7 canary are hard gates.**

An offer, not a substitute: I can run a structured design review against TI's published
reference material and a standard power-supply checklist when the schematic exists. That
is weaker than a competent human reviewer and should not be mistaken for one, but it is
better than nothing and it costs only time.

### R-1 — OVP fails and 48V reaches a node · **Critical**

**Plain terms:** the switching transistor that chops 48V down to 19V can fail shorted.
When it does, the full 48V appears at the barrel jack. An MS-01's input stage will not
survive that. The protection has to act in microseconds and has to work when the
regulator, the microcontroller and the firmware have all already failed.

**Cost if it happens:** one MS-01 (~$700). If the cause is common to all channels — a
design error rather than a component failure — up to six (~$4,200).

**How it is closed:**

1. **Crowbar, not just shutdown** (§4.4.2). A shorted transistor cannot be switched off,
   so the protection must short the output instead and blow the fuse. This is already in
   the design and is the correct pattern.
2. **A second, independent clamp.** A TVS diode across each output, sized to conduct hard
   at ~22V, in parallel with the crowbar. Two mechanisms, different failure modes, ~$0.40.
3. **Deliberate fault injection on the bench, into a dummy load, before any node is ever
   connected** (§9.1) — including with the MCU physically removed. Measure what the load
   actually sees. If it exceeds ~22V for any measurable time, the design is not finished.
4. **Proven destructively, not by reasoning.** With no external review (R-0), the
   drain-to-source short test in §9.1 is the *only* real evidence this protection works.
   It is cheap, it is definitive, and it must be performed on a fresh board and again
   after burn-in.
5. **The 30-day canary (§9.4)** bounds the consequence if 1–4 have all missed something.

Residual risk after all five: **moderate, and knowingly accepted.** It would have been low
with an independent review. It never reaches zero on a custom design.

### R-2 — The first high-current board layout is defective · **High**

**Plain terms:** at 250kHz and 48V, whether the circuit works depends on the physical
arrangement of copper as much as on the schematic. Get it wrong and you see overheating,
electrical noise, or instability that no amount of schematic review would have caught.

**Cost:** $30–80 and 2–3 weeks per re-spin. Money and time, not hardware damage.

**How it is closed:** one 2-channel board built and proven before the full set is ordered
(§8, already in the design); vendor reference layout copied verbatim; **budget three board
spins, not one** — a first-time high-current layout that works on the first attempt is
luck, not planning. Plan the schedule and the money around three.

### R-3 — the supply proves marginal · **CLOSED at WP-3**

**Plain terms:** the power supply might run out of headroom under real load.

**This risk existed because the RSP-750-48 was a 753.6W supply carrying a 726W peak —
96% of its rating.** Sourcing found that unit discontinued, and its replacement changed
the arithmetic rather than preserving it:

| | Was (RSP-1000-48) | Now (RSP-1000-48) |
|---|---|---|
| Capacity | 753.6W | 1008W |
| Peak load | **96%** | **72%** |
| Headroom before the question reopens | none | a measurement **38% above** the estimate |

**Closed.** 72% is not a marginal operating point. The chassis was already dimensioned for
this exact unit under M-2, so closing the risk cost nothing but the price difference.

**The measurement is still worth taking**, and it is still the only real evidence behind
§4.2.1 — every figure there is third-party. But it is now **informational rather than a
gate**:

> Buy a plug-in energy meter (~$20). Run all six nodes through a power strip on real
> workloads, then `stress-ng --cpu 0` on all six simultaneously. Record the peak.

An evening's work that replaces five third-party numbers with your own. Do it — just not
before you can order parts.

### R-4 — A firmware fault drops node power · **High if unmitigated**

**Plain terms:** a software bug or a crashed controller kills the cluster.

**How it is closed:** hardware, not software. Outputs are held on by resistors and can
only be turned *off* by the MCU actively pulling a pin down (§4.5.2). An MCU that is
crashed, unprogrammed, unpowered or physically removed leaves every output on. Verified by
pulling the MCU out of its socket and confirming outputs stay up (§9.2).

**One rule that must never be broken:** no firmware feature that turns outputs off on
network loss, watchdog expiry, or any autonomous condition. Outputs turn off only on an
explicit command or a hardware protection event. Residual risk after this: low.

### R-5 — Upstream's BOM defect propagates · **Low**

Identified (§2.4) and the affected circuit is not inherited. No further action.

### R-6 — 226MB of upstream history in the fork · **Low**

Cosmetic. Accepted deliberately in exchange for explicit lineage.

### R-7 — Integrated-FET regulator unavailable · **RESOLVED — and it materialised**

Investigated (§4.3.1.1). The concern was misdirected — output *voltage* was never the
problem, **package dissipation** is. No 60V-class integrated regulator can dissipate the
losses of a 133W channel in its own package. The controller-plus-discrete-FET route is
therefore forced.

**The contingency stated when this risk was written has triggered: the R-0 external review
is now mandatory rather than strongly recommended.** The single mitigation that would have
reduced layout risk for a non-expert builder is not available, so the remaining mitigation
has to carry the full weight.

---

## 8. Build order

Stage-gated. **Do not order the full board set before stage 3 passes.**

| # | Stage | Gate to clear before proceeding |
|---|---|---|
| 0 | **Barrel jack measured with calipers** (OPEN-5). Six-node draw (OPEN-6) is now informational — take it, but it no longer gates | OPEN-5 recorded |
| 1 | **Schematic** — LM5116 channel, protection, control board, backplane | — |
| 2 | **Sourcing** — full BOM, live stock, live pricing | No unsourceable parts |
| 3 | **LM5116 evaluation board** — buy, build, measure (R-0 control 2) | A working reference exists to compare against |
| 4 | **One 2-channel board** — layout → fab → bring-up → fault injection → 72h burn-in → **fault injection again** (§9.1) | 🔴 **Hard gate.** Every fault-injection test passes both before *and* after burn-in, including with the MCU removed and with a FET deliberately shorted |
| 5 | **Control board, display, firmware** against the proven channel board | Fail-ON verified by pulling the MCU; display verified irrelevant to power delivery |
| 6 | **Remaining two boards, chassis, panels**, integration | — |
| 7 | **30-day canary** — one worker node only (§9.4) | 🔴 **Hard gate.** 30 days, no fault, no thermal drift |
| 8 | **Remaining five nodes, six-node soak** | 24h at cluster-typical load |

Stage 0 costs almost nothing and can start today. **Stages 4 and 7 are the gates that now
carry the risk R-0 would otherwise have been reviewed out of.**

---

## 9. Verification

> **A power-supply design cannot be signed off by analysis or simulation. The schematic
> must be reviewed by a competent engineer before money is spent on fabrication, and the
> board must be bench-tested before any MS-01 is connected.** Every figure in §4.3.3 is
> analytical and unverified.

### 9.1 Stage 3 — single board, no MS-01 present

| Check | Requirement | Method |
|---|---|---|
| Regulation | E-1 | 19.0V ±2%, no load → 7A |
| Ripple | E-3 | ≤200 mVpp on a scope at 7A |
| Transient | E-7 | 0→7A load step, recovery within bounds |
| Efficiency | E-6 | ≥94% at 7A |
| Thermal | T-2 | 30-min soak at 7A, IR camera on FETs, inductor, sense resistor |
| Telemetry | F-3 | INA226 vs bench meter at 1A / 4A / 7A |

Powered from a **current-limited bench supply**, not the RSP-1000-48, so a fault cannot
deliver 1000W into a mistake.

**Deliberate fault injection — run the full set twice: once on the fresh board, and again
after the 72-hour burn-in.** A protection circuit that works cold and fails on a
thermally-aged board is the exact scenario the canary stage exists to catch, and catching
it here instead is far cheaper.

- Output short → current limit engages, then fuse clears (P-4, P-3)
- Force the OVP reference → crowbar fires, output clamps, input fuse clears (P-1, P-2)
- **Repeat the OVP test with the MCU physically removed** — this is the point of P-1
- **Destructive test — solder a wire drain-to-source across the high-side FET, then power
  up into a dummy load.** Measure what the load actually sees, on a scope, including the
  first few microseconds. This is the failure mode that destroys nodes; it is the one test
  that must not be reasoned about instead of performed. Sacrifice the FET. Expected
  result: load never exceeds ~22V, crowbar fires, input fuse clears.
- Inrush into a 2200µF load without fuse operation (P-8)
- Pull the 48V feed mid-operation; confirm no output overshoot on collapse

**72-hour burn-in** at 7A per channel into dummy loads, logging board temperature. Then
repeat everything above.

### 9.2 Stage 4 — control

- `POST /switch/port_1/turn_off` drops the rail to 0V and the bleed discharges it (P-9)
- `curl http://saturn-pdu.local/metrics` returns plausible per-port values (S-3)
- Fan curve ramps against a heated NTC; tach reports a stalled fan (T-4, T-5)
- **Unplug Ethernet → outputs stay up** (S-4)
- **Hold the MCU in reset → outputs stay up** (F-5, S-4)
- Display shows aggregate and per-node watts matching the bench meter (F-8)
- **Unplug the display entirely → all six outputs stay up and remain controllable over the
  network** (F-9)
- **Single tap anywhere on the display cannot de-energise a node**; power-off requires
  select-then-hold-2s and names the node (F-9)

### 9.3 Stages 5–6 — single-node integration

- One MS-01 powered from the **bench supply** through a full boot and a `stress-ng` run,
  before the RSP-1000-48 is ever in the path
- Remote power cycle brings that node back through POST cleanly (F-2)
- Chassis assembled, fans and display in place, 24-hour soak at that node's typical load
  while monitoring T-1 and T-2

### 9.4 Stage 7 — the 30-day canary

**The most important gate in this document, given the decision on R-0.**

Connect **exactly one channel to exactly one MS-01 — a worker node, never a control-plane
node.** The other five nodes stay on their stock bricks for the full 30 days.

Rationale: every test in §9.1–9.3 is a test you thought to run. A latent design error, by
definition, is one nobody thought of. Thirty days of real duty cycle — real thermal
cycling, real load steps, real idle periods — is the only thing that exercises the cases
no test plan contains. If something is going to fail, this is where it should happen, to
one replaceable worker rather than to the cluster.

**Pass criteria, all thirty days:**

- No protection event of any kind
- No drift in output voltage or in the channel's operating temperature between day 1 and
  day 30
- Node uptime equals or betters the stock brick it replaced
- Logged per-channel telemetry shows no anomaly against the other five nodes' known load

**Any protection event, any measurable thermal drift, or any unexplained node reboot
resets the clock to day zero and requires the cause to be found first.** Not "monitored" —
found.

Only on a clean thirty days do the other five nodes move across.

### 9.5 Stage 8 — full cluster

- Remaining five nodes moved across only after a clean canary month
- Six nodes on the RSP-1000-48; log aggregate draw through synchronised `stress-ng` across
  all six — **this is the empirical answer to §4.2.2** and determines whether the
  RSP-1000-48 swap is warranted
- Remote power cycle verified on every node (F-2)
- 24-hour soak at cluster-typical load, monitoring T-1 and T-2
- Move control-plane nodes across **last**

---

## 10. Repository and licensing

Fork `Shrike-Lab/HomeLab-PDU-V1` → `MarkMckessock/saturn-pdu`.

> Accepted trade-off: the fork carries upstream's 226MB of history permanently; deleting
> files from the working tree does not shrink it. Chosen for explicit lineage.

```
saturn-pdu/
├── LICENSE                     CERN-OHL-S v2, verbatim (L-1)
├── NOTICE                      derivation + changelog vs upstream (L-2)
├── README.md                   architecture, build, safety
├── params.yaml                 ⭐ single source of truth; holds both PROVISIONAL values
├── docs/
│   ├── SPECIFICATION.md        this document
│   ├── power-budget.md         load analysis, derating, PSU headroom
│   ├── thermal.md              airflow, dissipation, fan curve
│   ├── protection.md           fusing, OVP, crowbar coordination, FMEA
│   ├── safety.md              mains vs DC hazards, live-plug handling, bench rules
│   ├── upstream-analysis.md    §2, incl. the Q1 BOM defect
│   └── deviations.md           every departure from TI's reference design (R-0 control 1)
├── hardware/kicad/
│   ├── lib/                    project symbols + footprints
│   ├── saturn-pdu-2ch/         ← build and test this FIRST
│   ├── saturn-pdu-ctrl/
│   └── saturn-pdu-bp/
├── cad/                        parametric FreeCAD Python + STEP/STL exports (L-3)
├── firmware/
│   ├── saturn-pdu.yaml         control board
│   ├── saturn-pdu-display.yaml T-Display-S3 Touch
│   └── protocol.md             UART protocol between them
├── fab/                        gerbers, BOM, pick-and-place
└── reference/upstream-19in/    upstream 19in .stp, dimensional reference
```

Delete from the fork: all 10in variants, all USB-C PD assets, ShrikeLab branding (L-4),
`.github/FUNDING.yml`.

---

## 11. Implementation plan

### 11.0 Toolchain — verified present

| Tool | Status | Note |
|---|---|---|
| **KiCad 10.0.0** | ✅ Installed | `kicad-cli` at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`; `pcbnew` Python scripting available via bundled Python 3.9. Opens upstream's 9.0.7 gerbers without issue |
| **gh 2.92.0** | ✅ Authenticated as `MarkMckessock`, SSH | Can fork and push |
| **Python 3.14.4** | ✅ | For BOM tooling and parameter generation |
| **FreeCAD** | ❌ Not installed | `brew install --cask freecad` — needed at WP-6, not before |
| **ESPHome** | ❌ Not installed | `pipx install esphome` — needed at WP-5, not before |
| **poppler** | ❌ Not installed | `brew install poppler` — only to *view* upstream's schematic PDFs. Optional |

### 11.1 Placeholder strategy — how the two skipped measurements are handled

Both deferred measurements become **named parameters with provisional values in a single
file**, `params.yaml` at the repo root. Documentation, firmware and CAD scripts all read
from it. When a real measurement arrives it is changed in exactly one place.

```yaml
# params.yaml — single source of truth. PROVISIONAL values are marked.
output_connector:
  type: barrel_jack
  outer_diameter_mm: 5.5      # PROVISIONAL (OPEN-5) — measure stock MS-01 plug
  inner_diameter_mm: 2.5      # PROVISIONAL (OPEN-5) — 2.1 is the other candidate
  polarity: centre_positive   # PROVISIONAL (OPEN-5)
  panel_thread_mm: 8.0        # NOT provisional — see note below
power_budget:
  per_node_sustained_w: 95    # PROVISIONAL (OPEN-6) — ServeTheHome, not measured
  per_node_turbo_w: 115       # PROVISIONAL (OPEN-6)
  aggregate_design_w: 690     # PROVISIONAL (OPEN-6) — derived
```

**Neither placeholder actually blocks anything, which is why deferring them is safe:**

- **OPEN-5 does not block the chassis.** 5.5×2.5mm and 5.5×2.1mm jacks share the same
  panel-mount thread, so the rear panel cutout is identical either way. Only the *jack part
  number* is provisional, and that is a stage-2 purchasing decision, not a design one.
  Polarity is a wiring decision made at assembly. **Risk if wrong: one wrong $2 part.**
- **OPEN-6 does not block the design.** The architecture already hedges via the
  RSP-1000-48 drop-in (§4.2.3), and the chassis is dimensioned for the larger unit
  regardless. A measurement that comes in higher changes a purchase, not a layout.
  **Risk if wrong: a $165 PSU swap into a chassis already sized for it.**

> Both are carried as **GitHub issues** so they cannot be silently forgotten, and both are
> re-flagged as gates at WP-8 (before ordering) rather than now.

### 11.2 Work packages

Each work package lists its deliverable and who does it. **"Me"** means I can complete it
in-session; **"You"** means it needs hands, a GUI, or money.

#### WP-1 · Repository scaffold — *Me*

1. `gh repo fork Shrike-Lab/HomeLab-PDU-V1 --fork-name saturn-pdu --clone`
2. Branch `main`, no PRs to upstream (this is a divergent derivative, not a contribution)
3. **Remove:** all 10in variants, all USB-C PD assets, ShrikeLab branding and logos (L-4),
   `.github/FUNDING.yml`
4. **Preserve:** upstream 19in `.stp` files → `reference/upstream-19in/` (dimensional
   reference, §4.8)
5. **Add:** `LICENSE` (CERN-OHL-S v2 verbatim, L-1), `NOTICE` (derivation + changelog vs
   upstream, L-2), `README.md`, `params.yaml`, `.gitignore` for KiCad backups/autosaves
6. Directory tree per §10

**Deliverable:** a clean repo that builds nothing yet but is correctly licensed and attributed.

#### WP-2 · Documentation set — *Me*

- `docs/SPECIFICATION.md` — this document
- `docs/power-budget.md` — load analysis, derating, PSU headroom, the 2×450W decision record
- `docs/thermal.md` — dissipation budget, airflow calculation, fan curve
- `docs/protection.md` — fusing, OVP, crowbar coordination, and a written **FMEA** table
- `docs/safety.md` — mains vs DC hazard separation, live barrel-plug handling, bench rules
- `docs/upstream-analysis.md` — §2, including the Q1 BOM defect
- `docs/deviations.md` — **starts empty; every departure from TI's reference design gets a
  row.** This is R-0 control 1 and becomes the review checklist

#### WP-3 · BOM and sourcing — *Me, then You to order*

- `fab/bom.csv` — every part, with manufacturer PN, LCSC/DigiKey/Mouser PNs, live stock
  and qty-10 pricing, checked at time of writing
- Second-source column for every part on the critical path
- Flag anything with <1000 units stock or >8 week lead
- **Refresh §5 cost model against real numbers** rather than estimates

**You:** order the **LM5116 evaluation board** (~$100, R-0 control 2). Long lead — order at
WP-3, it is not needed until WP-8.

#### WP-4 · KiCad — 2-channel power board — *Me for schematic, You for layout*

This is the highest-risk artifact and the plan reflects that.

**4a. Libraries — Me.** Symbols and footprints for LM5116, INA226, XAL1510-223, the chosen
MOSFETs, the OVP comparator and SCR, fuses, TVS, barrel jack. Verified against datasheet
drawings, committed to `hardware/kicad/lib/`.

**4b. Schematic — Me.** Full net-by-net design: power stage, compensation network, current
sense, OVP comparator + crowbar, INA226 telemetry, per-channel fusing and TVS, backplane
connector. Driven to **ERC-clean** via `kicad-cli sch erc`.

> Honest caveat: I author `.kicad_sch` as text. The result will be electrically correct and
> ERC-clean, but the *drawing* will look machine-placed. Expect to spend an hour in the
> Schematic Editor tidying it into something readable — which is also the best way for you
> to actually understand what it does before you build it.

**4c. Board setup — Me.** Board outline, 4-layer stackup (2oz/1oz, §4.6), design rules for
2oz copper and 48V clearances, netlist import, initial component placement via `pcbnew`
scripting.

**4d. Layout and routing — You, at the GUI.** I am not doing this, and it is not a
limitation I am working around — it is the correct division. Per R-2 and R-0 control 1,
the power-stage geometry must be **copied from TI's published LM5116 reference layout**,
which means having it open on screen beside your board. Every deviation gets a row in
`docs/deviations.md`. Driven to **DRC-clean** via `kicad-cli pcb drc`.

**4e. Fab outputs — Me.** Gerbers, drill, IPC-356 netlist, pick-and-place, assembly
drawings via `kicad-cli`. Published as editable source *and* exports (L-3).

#### WP-5 · KiCad — control board and backplane — *Me for schematic, You for layout*

Same split as WP-4, but **materially lower risk** — these are signal-level boards with no
switching power stage.

- **Control board:** ESP32-S3, W5500 Ethernet, 12V-aux input regulator, 6× open-drain
  enable drivers, I²C to 6× INA226, 3× fan PWM + tach, 3× NTC, button input, LED expander,
  UART to the display, DC-OK input
- **Backplane:** passive. 48V distribution (copper pour or busbar for 15.1A), I²C, enable
  lines, board-to-board connectors, bus fuse and TVS

#### WP-6 · Firmware — *Me*

- `firmware/saturn-pdu.yaml` — ESPHome for the control board. Six `switch` entities, six
  `ina226` sensors, fan curve from NTC, tach monitoring, DC-OK, Prometheus endpoint, OTA.
  **Fail-ON semantics enforced in hardware (§4.5.2); the firmware must contain no
  autonomous power-off path** (S-4) — this gets a comment block explaining why, so nobody
  "helpfully" adds one later
- `firmware/saturn-pdu-display.yaml` — ESPHome + LVGL for the T-Display-S3 Touch. Read-only
  aggregate view, per-node rows, two-step confirm for any power action (F-9)
- `firmware/protocol.md` — the UART protocol between them
- Validated with `esphome config` (syntax and schema) — **not** flashed until WP-8

#### WP-7 · Mechanical CAD — *Me for scripts, You to review in the GUI*

FreeCAD is not installed, but the model is authored as **parametric Python** that reads
`params.yaml`, so it can be written now and run once FreeCAD is installed.

- `cad/chassis.py` — 1U enclosure, dimensioned for the **RSP-1000-48** (M-2)
- `cad/panel_front.py` — display window (60.8 × 25.5mm), button, 6 LEDs
- `cad/panel_rear.py` — 6× barrel jack cutouts, IEC inlet, RJ45
- `cad/trays.py` — PSU mount, 3× board trays on the inherited 4× 3.0mm NPTH pattern
- STEP and STL exports committed alongside the scripts (L-3 satisfied by the scripts, not
  the exports)

#### WP-8 · Build and verification — *You*

Follows §8 stages 3–8 and §9 exactly. **This is where the two placeholders must be
resolved**, because they become purchasing decisions:

- Measure the barrel jack → update `params.yaml` → confirm the ordered part
- Measure six-node draw → update `params.yaml`. **No longer a purchasing gate** (R-3 closed);
  it validates §4.2.1 and informs whether a second unit is ever warranted

### 11.3 Sequencing

```
WP-1 scaffold ──► WP-2 docs ──► WP-3 BOM ──┬──► [order eval board, long lead]
                                            │
                     WP-4 power board  ◄────┤
                     WP-5 ctrl+backplane ◄──┤   (these three run in parallel;
                     WP-6 firmware      ◄───┤    none depends on another)
                     WP-7 CAD          ◄────┘
                                            │
                                            ▼
                                  WP-8 build & verify
                          resolve params.yaml placeholders here
```

WP-4 through WP-7 are independent. **WP-6 firmware and WP-7 CAD carry almost no risk and
produce something visible early** — a good place to start if you want momentum before the
power board consumes the attention it deserves.

### 11.4 What I will not do

Stated plainly so there is no ambiguity later:

- **PCB routing of the power stage.** Per R-2 and R-0, it must copy TI's reference
  geometry with a human comparing the two. I can place components and set rules; the
  routing decisions are yours.
- **Flash firmware or run anything on hardware.**
- **Order parts or spend money.**
- **Sign off the design as safe.** The spec's §9 preamble stands: with no external review,
  the bench programme in §9.1 and the canary in §9.4 are what stands between a design
  error and your nodes.

### Follow-ons (out of scope)

- Scrape `/metrics` into Saturn's Prometheus; Gatus check for PDU reachability
- Per-node power panel in Grafana
- LAN-only by design; if the UI is ever exposed externally it requires a Zero Trust entry
  per `CLAUDE.md`
