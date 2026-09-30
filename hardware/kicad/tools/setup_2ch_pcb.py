#!/usr/bin/env python3
"""WP-4c board setup for saturn-pdu-2ch. Run with KiCad's bundled Python:

  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      hardware/kicad/tools/setup_2ch_pcb.py

Creates the outline, mounting holes, 4-layer stackup, net classes and design
rules, then loads every footprint from the schematic netlist with its nets and
its schematic link, packed into a rough functional placement.

ONE-SHOT, like gen_2ch_sch.py: it overwrites saturn-pdu-2ch.kicad_pcb. Once
layout has started, change the board from the schematic with
"Tools > Update PCB from Schematic" (F8), never by re-running this.
"""
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.normpath(os.path.join(HERE, '..', 'saturn-pdu-2ch'))
PCB = os.path.join(PROJ, 'saturn-pdu-2ch.kicad_pcb')
SCH = os.path.join(PROJ, 'saturn-pdu-2ch.kicad_sch')
KICAD = '/Applications/KiCad/KiCad.app/Contents'
CLI = KICAD + '/MacOS/kicad-cli'
FPLIB = {'saturn-pdu': os.path.normpath(os.path.join(HERE, '..', 'lib', 'saturn-pdu.pretty'))}

# Board: upstream's 90 x 130 mm outline with 2 mm corner radius (read from the
# upstream .kicad_pcb in git history, 1U Minilab PSU V2). Origin offset so the
# board sits on the page.
OX, OY, W, H, RAD = 50.0, 40.0, 90.0, 130.0, 2.0
HOLE_INSET = 4.0
mm = pcbnew.FromMM


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


# ---------------------------------------------------------------- netlist --
def netlist():
    out = os.path.join(tempfile.mkdtemp(), 'n.xml')
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', out, SCH],
                   check=True, capture_output=True)
    root = ET.parse(out).getroot()
    comps = {}
    for c in root.find('components'):
        sp = c.find('sheetpath').get('tstamps')
        comps[c.get('ref')] = {
            'value': c.findtext('value'), 'footprint': c.findtext('footprint'),
            'path': sp + c.findtext('tstamps'),
            'sheetname': c.find('sheetpath').get('names'),
            'dnp': any(p.get('name') == 'dnp' for p in c.findall('property')),
            'fields': {f.get('name'): f.text or '' for f in c.findall('fields/field')
                       if f.get('name') not in ('Footprint', 'Datasheet', 'Description')},
        }
    pins = {}
    for n in root.find('nets'):
        for node in n.findall('node'):
            pins[(node.get('ref'), node.get('pin'))] = n.get('name')
    return comps, pins


# ------------------------------------------------------------- placement ---
# Power flows top (J1, 48 V in) to bottom (J2, 19 V out). Each channel owns a
# column; within it, parts are packed in this order so the functional blocks
# land roughly where they belong. This is a STARTING point for layout, not a
# layout: the switching loop must be rebuilt by hand against TI's EVM.
CH_ORDER = [
    'F01', 'D01', 'C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07',
    'Q01', 'Q02', 'R03', 'R01', 'R02', 'R04', 'R05', 'R06', 'C08',
    'U01', 'C20', 'C21', 'D03', 'R07', 'R08', 'R09', 'C15', 'D02', 'R10', 'R11', 'C16',
    'C17', 'R12', 'R13', 'R14', 'C18', 'C19', 'R15', 'Q03', 'R16', 'R17',
    'L01', 'C09', 'C10', 'C11', 'C12', 'C13', 'C14',
    'R18', 'U02', 'C22', 'R19',
    'Q05', 'Q04', 'U03', 'R20', 'R21', 'C23', 'R22', 'R23', 'R24', 'R25', 'C24',
]
TOP_BAND, BOTTOM_BAND, GAP = 16.0, 18.0, 0.5


def bbox(fp):
    r = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() \
        else fp.GetBoundingBox(False)
    return r


def put(fp, x, y):
    """Place fp so its courtyard's top-left corner is at board (x, y)."""
    r = bbox(fp)
    off = fp.GetPosition() - pcbnew.VECTOR2I(r.GetX(), r.GetY())
    fp.SetPosition(pt(x, y) + off)


def pack(fps, x0, x1, y0, y1):
    x, y, row_h = x0, y0, 0.0
    for fp in fps:
        r = bbox(fp)
        w, h = pcbnew.ToMM(r.GetWidth()), pcbnew.ToMM(r.GetHeight())
        if x + w > x1:
            x, y, row_h = x0, y + row_h + GAP, 0.0
        put(fp, x, y)
        x += w + GAP
        row_h = max(row_h, h)
    if y + row_h > y1:
        raise SystemExit(f'placement overflow: column {x0}-{x1} ends at y={y + row_h:.1f} > {y1}')
    return y + row_h


# ------------------------------------------------------------------ main ---
def main():
    comps, pins = netlist()
    if os.path.exists(PCB):
        os.remove(PCB)
    board = pcbnew.NewBoard(PCB)
    board.SetCopperLayerCount(4)
    tb = board.GetTitleBlock()
    tb.SetTitle('Saturn PDU 2-channel power board')
    tb.SetRevision('A')
    tb.SetCompany('saturn-pdu (CERN-OHL-S-2.0)')
    tb.SetComment(0, 'Placement is machine-packed: layout per SPECIFICATION WP-4d')

    # --- outline -------------------------------------------------------------
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(*a)); s.SetEnd(pt(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)

    def arc(c, start, ang):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetCenter(pt(*c)); s.SetStart(pt(*start)); s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)
    R = RAD
    seg((R, 0), (W - R, 0)); seg((W, R), (W, H - R))
    seg((W - R, H), (R, H)); seg((0, H - R), (0, R))
    arc((W - R, R), (W - R, 0), 90); arc((W - R, H - R), (W, H - R), 90)
    arc((R, H - R), (R, H), 90); arc((R, R), (0, R), 90)
    board.GetDesignSettings().SetAuxOrigin(pt(0, H))
    board.GetDesignSettings().SetGridOrigin(pt(0, H))

    # --- nets ----------------------------------------------------------------
    nets = {}
    for name in sorted(set(pins.values())):
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n

    # --- footprints ----------------------------------------------------------
    fps = {}
    for ref, c in comps.items():
        lib, name = c['footprint'].split(':')
        path = FPLIB.get(lib, f'{KICAD}/SharedSupport/footprints/{lib}.pretty')
        fp = pcbnew.FootprintLoad(path, name)
        if fp is None:
            raise SystemExit(f'{ref}: footprint {c["footprint"]} not found')
        fp.SetFPIDAsString(c['footprint'])
        fp.SetReference(ref)
        fp.SetValue(c['value'])
        fp.SetPath(pcbnew.KIID_PATH(c['path']))
        fp.SetSheetname(c['sheetname'].strip('/') or 'Root')
        fp.SetSheetfile('channel.kicad_sch' if c['sheetname'] != '/' else 'saturn-pdu-2ch.kicad_sch')
        fp.SetDNP(c['dnp'])
        fp.SetExcludedFromBOM(c['dnp'])
        for k, v in c['fields'].items():
            fp.SetField(k, v)
            fp.GetField(k).SetVisible(False)
        board.Add(fp)
        for pad in fp.Pads():
            num = pad.GetNumber()
            if not num:
                continue  # mechanical (NPTH peg, EP paste)
            net = pins.get((ref, num))
            if net is None:
                raise SystemExit(f'{ref} pad {num} has no pin in the netlist')
            pad.SetNet(nets[net])
        fps[ref] = fp

    # --- placement -----------------------------------------------------------
    col = (W - 3 * 2.0) / 2
    for ch, x0 in ((1, 2.0), (2, 2.0 + col + 2.0)):
        order = [f'{re.match(r"[A-Z]+", r).group()}{ch}{r[-2:]}' for r in CH_ORDER]
        missing = {r for r in fps if re.fullmatch(fr'[A-Z]+{ch}\d\d', r)} - set(order)
        if missing:
            raise SystemExit(f'CH{ch} parts not in CH_ORDER: {sorted(missing)}')
        end = pack([fps[r] for r in order], x0, x0 + col, TOP_BAND, H - BOTTOM_BAND)
        print(f'CH{ch} column packed to y={end:.1f} of {H - BOTTOM_BAND}')
        g = pcbnew.PCB_GROUP(board)
        g.SetName(f'CH{ch}')
        board.Add(g)
        for r in order:
            g.AddItem(fps[r])
    # connectors: 48 V in on the top edge, outputs and signals on the bottom edge
    def edge(ref, cx, top):
        r = bbox(fps[ref])
        w, h = pcbnew.ToMM(r.GetWidth()), pcbnew.ToMM(r.GetHeight())
        put(fps[ref], cx - w / 2, 2.0 if top else H - 2.0 - h)
    edge('J1', W / 2, True)
    edge('J2', W * 0.62, False)
    fps['J3'].SetOrientationDegrees(90)  # lie the 2x6 header along the edge
    edge('J3', W * 0.25, False)
    put(fps['RT1'], W / 2 - 20, 8)  # between the FET rows, clear of J1
    put(fps['C1'], W * 0.25 + 12, H - 8)  # 3V3 decoupling beside J3

    # --- mounting holes (M3, NPTH: no copper near the 48 V side) -------------
    for i, (x, y) in enumerate(((HOLE_INSET, HOLE_INSET), (W - HOLE_INSET, HOLE_INSET),
                                (HOLE_INSET, H - HOLE_INSET), (W - HOLE_INSET, H - HOLE_INSET))):
        h = pcbnew.FootprintLoad(f'{KICAD}/SharedSupport/footprints/MountingHole.pretty',
                                 'MountingHole_3.2mm_M3')
        h.SetFPIDAsString('MountingHole:MountingHole_3.2mm_M3')
        h.SetReference(f'H{i + 1}')
        h.SetPosition(pt(x, y))
        h.SetBoardOnly(True)
        h.Reference().SetVisible(False)
        board.Add(h)

    # --- GND plane on In1 (the return path for both switching loops) -------
    z = pcbnew.ZONE(board)
    z.SetLayer(pcbnew.In1_Cu)
    z.SetNet(nets['GND'])
    z.SetZoneName('GND_plane_In1')
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)):
        ol.Append(mm(OX + x), mm(OY + y))
    z.SetMinThickness(mm(0.25))
    z.SetLocalClearance(mm(0.3))
    board.Add(z)

    # --- silkscreen ----------------------------------------------------------
    for text, (x, y), size in (('SATURN PDU 2CH  REV A', (W / 2, TOP_BAND - 8), 1.5),
                               ('48V DC IN', (W / 2 + 14, 6), 1.2),
                               ('CERN-OHL-S-2.0', (W / 2, H - BOTTOM_BAND + 1.5), 1.0)):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text); t.SetPosition(pt(x, y)); t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size))); t.SetTextThickness(mm(size * 0.15))
        board.Add(t)

    design_rules(board)
    pcbnew.SaveBoard(PCB, board)
    add_stackup()
    print('written', PCB)


def design_rules(board):
    ds = board.GetDesignSettings()
    # JLCPCB 4-layer, 2 oz outer: 0.2 mm is its minimum trace/space on 2 oz.
    ds.m_MinClearance = mm(0.2)
    ds.m_TrackMinWidth = mm(0.2)
    ds.m_ViasMinSize = mm(0.5)
    ds.m_MinThroughDrill = mm(0.25)
    ds.m_ViasMinAnnularWidth = mm(0.13)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_HoleClearance = mm(0.25)
    ds.m_CopperEdgeClearance = mm(0.5)
    ds.m_SilkClearance = mm(0.0)
    ns = ds.m_NetSettings
    classes = [
        # name, track, clearance, via dia, via drill, patterns
        ('HV', 1.0, 0.2, 0.8, 0.4,
         ['+48V', '/CH*/VIN_F', '/CH*/SW', '/CH*/HB', '/CH*/HO', '/CH*/HO_G', '/CH*/SNUB']),
        ('POWER', 2.0, 0.2, 0.8, 0.4, ['/CH*/VOUT_REG', '/VOUT*', '/CH*/ISNS', 'GND']),
        ('GATE', 0.5, 0.2, 0.6, 0.3, ['/CH*/LO', '/CH*/LO_G']),
    ]
    for prio, (name, tw, cl, vd, vdr, pats) in enumerate(classes):
        nc = pcbnew.NETCLASS(name)
        nc.SetTrackWidth(mm(tw)); nc.SetClearance(mm(cl))
        nc.SetViaDiameter(mm(vd)); nc.SetViaDrill(mm(vdr))
        nc.SetPriority(prio)
        ns.SetNetclass(name, nc)
        for p in pats:
            ns.SetNetclassPatternAssignment(p, name)
    with open(os.path.join(PROJ, 'saturn-pdu-2ch.kicad_dru'), 'w') as f:
        f.write('''(version 1)

# 48 V spacing. IPC-2221B needs only 0.13 mm for 31-150 V on masked outer
# copper, so the netclass clearance of 0.2 mm already satisfies the standard.
# This rule adds margin wherever the layout has a choice, i.e. everything
# except pad-to-pad gaps, which the IC footprints fix (LM5116 pitch 0.65 mm).
(rule "48V domain to low-voltage copper"
  (condition "A.hasNetclass('HV') && !B.hasNetclass('HV') && !(A.Type == 'Pad' && B.Type == 'Pad')")
  (constraint clearance (min 0.5mm)))

# The switch node swings 0-48 V at 250 kHz: keep it off the INA226 / OVP
# sense and the I2C lines, which is where coupled noise would do harm.
(rule "Switch node to sense and I2C"
  (condition "A.NetName == '/CH*/SW' && (B.NetName == '/CH*/FB' || B.NetName == '/CH*/OVP_REF' || B.NetName == '/SDA' || B.NetName == '/SCL' || B.NetName == '/CH*/CS' || B.NetName == '/CH*/CSG')")
  (constraint clearance (min 1.0mm)))
''')


STACKUP = '''	(stackup
		(layer "F.SilkS" (type "Top Silk Screen"))
		(layer "F.Paste" (type "Top Solder Paste"))
		(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
		(layer "F.Cu" (type "copper") (thickness 0.07))
		(layer "dielectric 1" (type "prepreg") (thickness 0.2) (material "FR4") (epsilon_r 4.4) (loss_tangent 0.02))
		(layer "In1.Cu" (type "copper") (thickness 0.035))
		(layer "dielectric 2" (type "core") (thickness 0.99) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
		(layer "In2.Cu" (type "copper") (thickness 0.035))
		(layer "dielectric 3" (type "prepreg") (thickness 0.2) (material "FR4") (epsilon_r 4.4) (loss_tangent 0.02))
		(layer "B.Cu" (type "copper") (thickness 0.07))
		(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
		(layer "B.Paste" (type "Bottom Solder Paste"))
		(layer "B.SilkS" (type "Bottom Silk Screen"))
		(copper_finish "ENIG")
		(dielectric_constraints no)
	)
'''


def add_stackup():
    """4 layers, 2 oz outer / 1 oz inner, 1.62 mm (SPECIFICATION 4.6). The
    dielectric split is nominal: take the fab's own 2 oz stackup at order time."""
    s = open(PCB).read()
    s = re.sub(r'\(setup\n', '(setup\n' + STACKUP, s, count=1)
    s = s.replace('(general\n\t\t(thickness 1.6)', '(general\n\t\t(thickness 1.62)')
    open(PCB, 'w').write(s)


if __name__ == '__main__':
    main()
