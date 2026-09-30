# Upstream analysis

What was extracted from [Shrike-Lab/HomeLab-PDU-V1](https://github.com/Shrike-Lab/HomeLab-PDU-V1),
how, and what could not be.

This exists to satisfy CERN-OHL-S v2 §3.3 and to make the inheritance decisions
in `NOTICE` auditable rather than asserted.

> The upstream fabrication files are no longer in this repository's working tree
> — they describe a board this project discards. They remain available upstream
> and in this repository's git history (commit `c22372e` and earlier).

---

## 1. Why so little was inherited

Two facts, established before any design work:

**1. The load is incompatible.** The MS-01 takes 19V through a barrel jack and
[cannot be powered over USB-C](https://www.galaxus.at/en/s1/questionandanswer/hello-can-the-mini-pc-also-be-supplied-with-power-via-usb-c-or-is-it-only-possible-with-the-mains-ad-782803);
Minisforum support confirms the barrel jack is required. Every USB-C PD module,
the PD-specific board and the 24V rail are therefore useless here.

**2. Upstream publishes no editable source.** A census of all 149 files found
zero `.kicad_*`, `.f3d`, `.FCStd`, `.SLDPRT` or EasyEDA files — only STEP/STL
exports, Gerbers, ODB++ and PDFs. STEP headers show SolidWorks 2025; Gerber
headers show KiCad 9.0.7, project `1U Minilab PSU V2`. Both originals are
withheld.

CERN-OHL-S v2 requires the **Source** — "the preferred form for making
modifications". Exports are not that. This is noted without hostility: it is a
generously shared project. But it means anything inherited had to be
reverse-engineered from fabrication outputs, and it is why `L-3` exists as a
requirement on *this* project.

## 2. What was extracted, and from where

| Property | Value | Source file | Method |
|---|---|---|---|
| Board outline | **90 × 130 mm** (X 51.8→141.8, Y −38.3→−168.3) | `Edge_Cuts.gm1` | Coordinate extents |
| Stackup | 2-layer, 1.6mm, 2oz | README, confirmed by pour-heavy layout | Stated + inferred |
| Trace apertures | 0.8 / 1.0 / **2.0 mm max** | `F_Cu.gtl` | Aperture definition list |
| Copper pours | 17 regions top, 1 bottom (GND plane) | `F_Cu.gtl`, `B_Cu.gbl` | `G36` region count |
| Drill sizes | 0.6 / 0.75 / 1.0 / 1.8 / 3.2 mm PTH | `.drl` | Tool tables |
| Mounting holes | **3.0 mm NPTH × 4** | `.drl` | Tool tables |
| Through-hole netlist | Complete | `HomeLab-PSU-V1_netlist.ipc` | IPC-D-356 parse |
| Part values | Complete | `bom.csv`, `README.md` | Direct |

## 3. Reconstructed topology

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

**Upstream's board performs no power conversion.** It is a passive fan-out: one
master switch, fusing, TVS clamping, bulk capacitance, and headers for five
purchased PD modules and one purchased buck module.

**This design inverts that — conversion *is* the board.** That single difference
is why the schematic could not be inherited even in outline.

## 4. Inheritance decisions

| Element | Decision | Justification |
|---|---|---|
| Fuse + TVS + bulk cap per channel | **Inherit**, rescaled | Sound pattern. 3A → 5A input fuse; TVS standoff 26V → 58V (bus) / 24V (output) |
| Master switch via latching button | **Inherit the concept, change the implementation** | Drive the PSU's remote ON/OFF rather than commutating 15A of 48V through a FET — an option upstream did not have with the HRP-300 |
| Fan rail from the switched main rail | **Inherit**, add MCU PWM | Upstream tunes RPM by trimming a buck module's output voltage: open-loop and crude |
| 4 × 3.0mm NPTH mounting pattern | **Inherit** | Compatible with upstream's PCB tray and reinforcement bracket |
| 90 × 130mm board footprint | **Reference only** | A useful sanity check that a 2-channel board fits the tray |
| 19" chassis geometry (`.stp`) | **Inherit as dimensional reference** | True B-rep solids, dimensionally trustworthy — unlike the mesh-only printed parts |
| Power path, PD modules, 24V rail | **Discard** | Incompatible with the load |
| 2-layer / 2oz / 15A stackup | **Discard** | Under-specified for an 800W-class board with switching nodes |

## 5. Defect found in upstream

**`Q1` is specified inconsistently.**

| Source | Part | Type |
|---|---|---|
| `README.md` BOM | `NCEP40PT15D` | **N-channel**, 40V |
| JLCPCB `bom.csv` (LCSC field) | `IRF9540NPBF` | **P-channel**, 100V |

These are opposite polarity and not interchangeable.

**The CSV is correct.** The surrounding gate network settles it: a 100k pull-up
to the source rail, a 12V zener clamping V_gs, and a drive that pulls the gate
*low* to turn the device on. That is unambiguously a **P-channel high-side
switch**. An N-channel device in that circuit would be off when commanded on, and
would need a charge pump or bootstrap that is not present.

**Building from the README alone yields a non-functioning board.** Recorded here
for the benefit of anyone else working from that repository. The affected circuit
is not inherited by this project, so no further action is taken.

## 6. What could not be extracted

**The schematic PDFs contain no machine-readable text.** Both are ~34KB with no
embedded fonts and no `Tj`/`TJ` text-showing operators — KiCad plotted every
label as vector strokes. No net names, designators or values are programmatically
recoverable. Rendering them for human review requires `brew install poppler`.

**The IPC-356 netlist covers through-hole pads only.** SMD connectivity is absent.
The exact wiring of the Q1 gate network in §3 is therefore **inferred from part
values and standard practice, not extracted**. It is almost certainly the textbook
arrangement — and §5's conclusion does not depend on the fine detail, only on the
pull-up-and-pull-low topology, which the part values establish on their own. But
it is an inference and it is labelled as one.

Neither gap is material, because the power path is not being copied.
