# saturn-pdu-2ch — 2-channel power board

Open `saturn-pdu-2ch.kicad_pro` in KiCad 10.

| File | What it is | Made by |
|---|---|---|
| `saturn-pdu-2ch.kicad_sch`, `channel.kicad_sch` | Schematic. Top sheet + one channel sheet used twice (CH1, CH2) | `tools/gen_2ch_sch.py` (WP-4b) |
| `saturn-pdu-2ch.kicad_pcb` | Board: outline, holes, stackup, rules, every part loaded and linked | `tools/setup_2ch_pcb.py` (WP-4c) |
| `saturn-pdu-2ch.kicad_dru` | Custom design rules (48 V spacing, switch-node keep-away) | `tools/setup_2ch_pcb.py` |

**Both generator scripts are one-shot.** They overwrite their output. After any hand
edit, change the board from the schematic with *Tools → Update PCB from Schematic*
(F8), never by re-running a script.

## State at the end of WP-4c

- ERC: 0 errors, 0 warnings.
- DRC with schematic parity: **0 parity issues, no errors other than unrouted
  connections.** The remaining warnings are silkscreen labels overlapping each other,
  which go away as parts are spread out.
- Board: 90 × 130 mm, 2 mm corner radius (upstream's outline), 4 × M3 holes 4 mm in from
  each corner.
- Stackup: 4 layers, 2 oz outer / 1 oz inner, 1.62 mm, ENIG. The dielectric split is
  nominal — swap in the fab's own 2 oz stackup when ordering.
- In1.Cu has a full GND plane (press **B** to fill it). In2.Cu is free.

### Net classes

| Class | Nets | Track | Clearance |
|---|---|---|---|
| HV | +48V, VIN_F, SW, HB, HO, HO_G, SNUB | 1.0 mm | 0.2 mm (0.5 mm to non-HV copper, except pad-to-pad inside a part) |
| POWER | VOUT_REG, VOUT1/2, ISNS, GND | 2.0 mm | 0.2 mm |
| GATE | LO, LO_G | 0.5 mm | 0.2 mm |
| Default | everything else | 0.2 mm | 0.2 mm |

The track widths are only defaults. **Carry the 7 A paths in copper pours, not tracks.**

## Placement is a starting point, not a layout

Parts are packed in two columns, one per channel. Power flows from top (J1, 48 V in) to
bottom (J2, 19 V out). Each channel is a KiCad group, so it moves as one.

The order inside a column is roughly right, but the spacing is not. Do the layout
(WP-4d) with **TI's LM5116 EVM layout open beside it** (R-0 control 1). Put every place
you depart from it in `docs/deviations.md`.

## Layout checklist, most important first

1. **Hot loop as small as possible.** Input ceramics (C103–C106) → high-side FET (Q101) →
   low-side FET (Q102) → sense resistor (R103) → back to the ceramics' ground. Keep them
   side by side on the top layer, with the In1 GND plane directly underneath. This loop's
   size sets the switch-node spike, and the D-10 bench gate requires that spike to stay
   at or below 54 V.
2. **Keep the switch node (SW) small.** It only needs to join the FETs and L101. Don't
   pour extra copper on it. Keep it away from FB, CS, OVP_REF and I²C (a DRC rule
   enforces 1 mm).
3. **Kelvin sense.** CS and CSG are 0 Ω links (R104, R105). Route them as a close pair
   straight to R103's pads, not onto the power copper. Do the same for the INA226 inputs
   (VOUT_REG and VOUT) at R118's pads.
4. **Gate drive.** Run HO next to SW and LO next to GND, both short, from U101 to the
   FETs.
5. **Analog ground.** The LM5116 exposed pad is the star point. Place the FB divider
   (R112/R113), the compensation parts (R114, C118, C119) and the RT, SS, RAMP and VCC
   parts next to U101, grounded to its pad area rather than to the power path.
6. **Heat.** Put a thermal-via array under both FETs, into the In1 plane. The inductor,
   R103, R118 and R119 all need copper to spread heat into.
7. **Crowbar.** The SCR (Q105) goes near J2, across VOUT with short, wide copper. The
   OVP divider (R120/R121) senses at the output, not at the inductor.
8. **Snubber (R106/C108, not fitted).** Place it hard across Q102's drain and source so
   it works if it is ever needed.
9. **Connectors.** Pour +48V from J1 to both fuses. Run each VOUT to J2 pins as a pour
   and use both pins.
