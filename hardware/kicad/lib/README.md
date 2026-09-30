# Project libraries — `hardware/kicad/lib/`

**WP-4a deliverable.** Symbols and footprints for the Saturn PDU boards.

## The rule this directory follows

> **Author only what KiCad 10.0.0 does not already ship. Use stock libraries for
> everything else, and record here which stock item was chosen and what it was checked
> against.**

Two reasons. First, a hand-authored footprint is an opportunity to get a land pattern
wrong, and a wrong land pattern is not caught by ERC, DRC or any bench test until the
board comes back from fab. Second, R-0 means there is no external reviewer — so the
review has to be a written, checkable record instead, and that record is this file.

Every row below was checked against the manufacturer's own drawing, not against a
distributor page or a third-party library. Datasheet revisions are named so the check can
be repeated.

---

## 1. Parts census

| Function | Part | Symbol | Footprint | Source |
|---|---|---|---|---|
| Buck controller | LM5116MH | `saturn-pdu:LM5116` | `Package_SO:ETSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3x4.2mm` | **symbol authored**, footprint stock (§2.1, §3.1) |
| High- and low-side FET | TI **CSD18563Q5A** (not BSC0702LS — D-10) | `Transistor_FET:CSD18563Q5A` | `saturn-pdu:TI_VSONP-8_5x6mm_P1.27mm` | symbol stock, **footprint derived** (§3.2) |
| Output inductor | Coilcraft XAL1510-223MEB | `saturn-pdu:L_XAL1510-223MEB` | `saturn-pdu:L_Coilcraft_XAL1510` | **both authored** (§2.2) |
| Telemetry | TI INA226 (DGS) | `Sensor_Energy:INA226` | `Package_SO:TSSOP-10_3x3mm_P0.5mm` | both stock — this footprint is TI's DGS0010A (VSSOP-10); KiCad names it TSSOP |
| OVP reference | TI **TL431B** (not TLV431 — §4) | `Reference_Voltage:TL431DBZ` | `Package_TO_SOT_SMD:SOT-23` | both stock (§3.3) |
| Crowbar SCR | BT151-500R | `Device:Q_SCR_KAG` | `Package_TO_SOT_THT:TO-220-3_Horizontal_TabDown` | both stock (§3.4) |
| Channel enable FET | 2N7002 | `Transistor_FET:2N7002` | `Package_TO_SOT_SMD:SOT-23` | both stock |
| Current sense / shunt | 7 mΩ, 2 mΩ | `Device:R_Shunt` | `Resistor_SMD:R_2512_6332Metric` | both stock |
| TVS | SMCJ58A (bus), SMCJ22A (output) | `Device:D_TVS` | `Diode_SMD:D_SMC` | both stock |
| Channel input fuse | 5 A, 48 V DC rated | `Device:Fuse` | **not yet chosen** | resolved at WP-4b |
| Board thermal sensor | 10 k NTC | `Device:Thermistor_NTC` | `Resistor_SMD:R_0805_2012Metric` | both stock |
| Board-to-backplane connector | not yet chosen | — | — | resolved at WP-4b |

Two rows are deliberately open. The fuse needs a part with a **DC** interrupt rating at
48 V — most small SMD fuses are specified for AC or for 32 V DC, and a fuse that cannot
break 48 V DC is worse than no fuse because it arcs. That is a selection problem, not a
library problem, and it belongs with the protection design in WP-4b.

---

## 2. What was authored here, and from what

### 2.1 `LM5116` (symbol)

Pin numbers, names and signal types transcribed from **TI SNVS499I, revised November
2023, Table 4-1 and Figure 4-1** (PWP package, 20-pin HTSSOP, top view). The exposed pad
is carried as pin 21, named `EP`, so that it cannot be silently left unconnected.

Two pin types were *not* copied verbatim from TI's table, and the reasons are recorded so
the deviation is visible:

- **`SW` (20)** — TI types it `O`. Modelled here as `passive`. The switch node is driven
  by the two MOSFETs as much as by the controller, and typing it as an output produces
  ERC noise that hides real errors.
- **`CSG` (13)** — TI types it `G` (ground). Modelled here as `passive`. It is the
  negative terminal of the current-sense resistor, not a ground pin, and typing it as
  power input would demand a power-source driver that does not exist.

`VIN`, `VCCX`, `HB`, `PGND` and `AGND` are `power_in`; `VCC` is `power_out`. That
combination makes ERC complain if the VCC decoupling, the bootstrap supply or either
ground is left floating — which is the point.

### 2.2 `L_XAL1510-223MEB` (symbol) and `L_Coilcraft_XAL1510` (footprint)

From **Coilcraft Document 947, revised 05/04/26**. KiCad's `Inductor_SMD` library carries
only the Coilcraft 0403HQ/0604HQ/0805HQ/1008HQ/1515SQ/2222SQ families, so this one had to
be drawn.

| Dimension | Datasheet | In the footprint |
|---|---|---|
| Body | 15.2 × 16.2 mm, 10.0 mm max height | `F.Fab` outline 15.2 × 16.2 |
| Land pad | 0.125 in / 3.18 mm × 0.520 in / 13.2 mm | 3.18 × 13.2 mm |
| Land pitch | 0.417 in / 10.6 mm | pads at x = ±5.3 mm |
| Courtyard | — | body + 0.25 mm all round |

**Pad 1 is the marked start (short) lead.** Coilcraft's drawing carries the note
*"Indicates direction of terminals and start (short) lead. Connect high dv/dt here for
lowest EMI."* Pad 1 therefore goes to the **switch node**, and pad 2 to the output. Both
terminals are electrically identical, so getting this backwards costs radiated noise, not
function — but it is free to get right, and it is marked on `F.Fab` with a triangle as
well as on silkscreen with a dot.

**Solder paste is reduced by 0.25 mm per side (≈81 % of pad area).** Coilcraft publish no
stencil recommendation for this part. A 3.18 × 13.2 mm aperture at 100 % deposits a large
volume of paste under a 13 g component; the reduction is a conventional hedge against
float and squeeze-out. It is a judgement, not a vendor figure, and is flagged as such
here so it can be revisited if the first board shows poor wetting.

Electrical figures confirmed against the same datasheet: 22 µH ±20 %, **I_sat 18.7 A**
(−30 % inductance), **I_rms 14 A** at 40 °C rise / 10.5 A at 20 °C rise, **DCR 14.5 mΩ
typical, 16.0 mΩ maximum**, SRF 6.3 MHz. These match `docs/SPECIFICATION.md` §4.3.2.1.

---

## 3. Stock items, and what each was checked against

### 3.1 `Package_SO:ETSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3x4.2mm` — LM5116

TI's `PWP0020A` drawing (4214869/A) gives a package thermal pad of 3.15/2.85 ×
4.35/4.05 mm — nominally 3.0 × 4.2 mm, which is exactly what this footprint provides.
Body 4.4 × 6.5 mm, 20 pins at 0.65 mm pitch, both matching. TI's own land-pattern example
uses a slightly larger, solder-mask-defined 3.15 × 4.35 mm thermal pad; the 0.15 mm
difference is immaterial for a controller dissipating a fraction of a watt, and the
IPC-derived stock footprint is the more widely-proven geometry.

### 3.2 `saturn-pdu:TI_VSONP-8_5x6mm_P1.27mm` — CSD18563Q5A

**Why the FET changed.** WP-3 fitted the Infineon BSC0702LS. At WP-4b the LM5116 start-up
rule was checked: its VCC regulator is guaranteed to only 15 mA, and must supply
(Q_g,HS + Q_g,LS) × f_sw. The BSC0702LS pair is ~68 nC at 7.4 V → ~17 mA at 250 kHz, which
fails. CSD18563Q5A (TI SLPS444C): Q_g 7.3/9.5 nC at 4.5 V and 15/20 nC at 10 V (typ/max),
so ~7.5 mA per pair. Recorded as D-10.

**Why a derived footprint.** KiCad's `CSD18563Q5A` symbol defaults to
`Package_TO_SOT_SMD:TDSON-8-1`, which is Infineon's pattern, **not TI's**: drain-to-lead gap
1.25 mm vs TI's ~0.55 mm, overall span 6.65 mm vs 6.25 mm. KiCad's
`Package_SON:VSONP-8-1EP_5x6_P1.27mm` *does* match TI's recommended land pattern — leads
0.7 × 0.7 mm at x = ±2.8 mm, main drain pad 4.35 × 4.51 mm at x = +0.33 mm, four paste-only
window-pane apertures — but numbers its pads 1 = S, 2 = G, 3 = D, which does not match the
symbol (1–3 S, 4 G, 5 D).

The project copy is that footprint with **only the pad numbers changed**: the four left
leads, top to bottom, become 1, 2, 3, 4; the main pad and the four right leads all become 5.
Geometry, courtyard, silkscreen and 3D model are untouched. It is a derivative of the KiCad
library and carries its **CC-BY-SA 4.0** licence (with KiCad's library exception).

When assigning in the schematic, override the symbol's default footprint — leaving
`TDSON-8-1` in place would be a silent, board-killing error.

The superseded BSC0702LS check (Infineon rev 2.5 against `TDSON-8-1`) remains valid if the
second source, Infineon BSC094N06LS5 (also PG-TDSON-8), is ever fitted.

### 3.3 `Reference_Voltage:TL431DBZ` — TL431B

SOT-23-3 pin order is **not** consistent across the TL431/TL432/TLV431 family, so it was
checked explicitly. TI SLVS543AF Table 5-1 gives, for the DBZ package:
**1 = CATHODE, 2 = REF, 3 = ANODE.** KiCad's symbol declares 1 = K, 2 = REF, 3 = A.
Match.

### 3.4 `Device:Q_SCR_KAG` — BT151-500R

Symbol pin order is 1 = K, 2 = A, 3 = G. The BT151 series pinning is
**1 = cathode, 2 = anode, 3 = gate, tab = anode.** Match.

`TO-220-3_Horizontal_TabDown` is specified rather than the vertical variant: 1U leaves
40 mm of internal height (M-6) and a lying-down TO-220 is both shorter and less
vulnerable to vibration. **The tab is the anode**, which on this circuit is the 19 V
output node, so the tab pad must be poured as part of that net and must not be tied to
chassis or ground.

Ratings that matter for the crowbar (P-2, P-3): I_T(RMS) 12 A, I_T(AV) 7.5 A,
**I_TSM 132 A**, I²t ≈ 88 A²s. The crowbar event is ~21 A for 10–50 ms, which is
21² × 0.05 ≈ **22 A²s** — about a quarter of the device's rating. The 500 V blocking
rating is far beyond anything this circuit sees; it is incidental to picking a part with
this surge capability in a cheap, universally-stocked package.

---

## 4. Erratum against `fab/bom.csv` — TLV431A is the wrong part

The WP-3 BOM specified **TLV431A** for the OVP reference (`U5`, `U6`). Checking the
datasheet while building this library showed that will not work:

| | TLV431 | TL431 |
|---|---|---|
| Cathode voltage, absolute maximum | **7 V** | **37 V** |
| Cathode voltage, operating | V_ref to 6 V | V_ref to 36 V |
| V_ref | 1.24 V | 2.495 V |
| SOT-23-3 pinout | 1 = REF, 2 = K, 3 = A | 1 = K, 2 = REF, 3 = A |

The OVP reference sits across the channel's own **19 V** output. In the quiescent state —
which is almost all of the time — the cathode is held near that rail through its bias
resistor. A TLV431 would be operated at roughly **three times its absolute maximum
cathode voltage**, continuously, on every channel.

This is not a subtle failure. It would have been assembled, it would have worked on the
bench for some period, and then the part protecting against a shorted high-side FET
(R-1, the failure mode that destroys nodes) would have died silently — leaving the
crowbar unable to fire while every other test still passed.

**Corrected to TL431B** (0.5 % initial tolerance, DBZ/SOT-23-3). The pinouts differ
between the two families as well, so the substitution is not drop-in and the schematic
must use `Reference_Voltage:TL431DBZ`.

`fab/bom.csv` and `docs/deviations.md` are updated accordingly.

---

## 5. Using these libraries

The project library tables in each board directory register:

```
saturn-pdu   ${KIPRJMOD}/../lib/saturn-pdu.kicad_sym
saturn-pdu   ${KIPRJMOD}/../lib/saturn-pdu.pretty
```

Nothing here depends on a per-machine path or on a global KiCad configuration, so a
clean checkout opens correctly (L-3).

To re-verify after a KiCad upgrade:

```sh
kicad-cli sym upgrade hardware/kicad/lib/saturn-pdu.kicad_sym
kicad-cli fp  upgrade hardware/kicad/lib/saturn-pdu.pretty
kicad-cli sym export svg -o /tmp/s hardware/kicad/lib/saturn-pdu.kicad_sym
kicad-cli fp  export svg -o /tmp/f hardware/kicad/lib/saturn-pdu.pretty
```

`upgrade` reporting *"was not updated"* means the files are already current format.
