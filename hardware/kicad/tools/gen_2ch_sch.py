#!/usr/bin/env python3
"""Generate the saturn-pdu-2ch schematic (WP-4b).

ONE-SHOT GENERATOR. It writes a netlist-correct schematic in which every pin is
wired to a named label; the drawing is machine-placed and is meant to be tidied
by hand in Eeschema. **Do not re-run it after hand edits** -- it overwrites.

Values are from docs/deviations.md and the WP-4b design calculations. Nets are
named in the NETS comments below; the channel sheet is instantiated twice.
"""
import copy
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from sexpr import Q, dump, find, find1, parse  # noqa: E402

KI = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/'
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.join(HERE, '..', 'saturn-pdu-2ch')
PROJECT = 'saturn-pdu-2ch'
LIBS = {
    'saturn-pdu': os.path.join(HERE, '..', 'lib', 'saturn-pdu.kicad_sym'),
}
NS = uuid.UUID('6f1c3a52-0d7e-4b8e-9d5a-5a7e2c1d0001')


def uid(*parts):
    return Q(str(uuid.uuid5(NS, '/'.join(str(p) for p in parts))))


ROOT = uid('root')
SHEETS = {1: uid('sheet', 1), 2: uid('sheet', 2)}
CHAN_UUID = uid('channel-file')

# ---------------------------------------------------------------- library ---
_libcache = {}


def _lib(name):
    if name not in _libcache:
        path = LIBS.get(name, KI + name + '.kicad_sym')
        _libcache[name] = {s[1]: s for s in find(parse(open(path).read()), 'symbol')}
    return _libcache[name]


def load_symbol(lib_id):
    lib, name = lib_id.split(':')
    node = copy.deepcopy(_lib(lib)[name])
    ext = find1(node, 'extends')
    if ext:
        parent = load_symbol(f'{lib}:{ext[1]}')
        pname = parent[1].split(':')[1]
        child_props = {p[1]: p for p in find(node, 'property')}
        out = [x for x in parent]
        for i, x in enumerate(out):
            if isinstance(x, list) and x[0] == 'property' and x[1] in child_props:
                out[i] = child_props.pop(x[1])
            if isinstance(x, list) and x[0] == 'symbol':
                x[1] = Q(x[1].replace(pname + '_', name + '_', 1))
        idx = max(i for i, x in enumerate(out) if isinstance(x, list) and x[0] == 'property')
        for p in child_props.values():
            idx += 1
            out.insert(idx, p)
        node = out
    node[1] = Q(lib_id)
    return node


def symbol_pins(sym):
    pins = []
    for sub in find(sym, 'symbol'):
        if sub[1].endswith('_2'):  # De Morgan alternate body
            continue
        for p in find(sub, 'pin'):
            at = find1(p, 'at')
            pins.append({
                'num': str(find1(p, 'number')[1]),
                'name': str(find1(p, 'name')[1]),
                'type': p[1],
                'x': float(at[1]), 'y': float(at[2]), 'ang': int(float(at[3])),
            })
    return pins


# ------------------------------------------------------------- sheet body ---
class Sheet:
    def __init__(self, paths):
        """paths: {path_str: ref_prefix_fn} -- one entry per sheet instance."""
        self.items = []
        self.lib = {}
        self.paths = paths
        self.pwr = 0

    def _instances(self, refs):
        return ['instances', ['project', Q(PROJECT)] + [
            ['path', Q(p), ['reference', Q(refs[p])], ['unit', 1]] for p in self.paths]]

    def place(self, lib_id, x, y, refs, value, fp='', nets=None, dnp=False,
              fields=None, hier=(), rot=0):
        sym = self.lib.setdefault(lib_id, load_symbol(lib_id))
        key = (lib_id, x, y)
        props = [
            ('Reference', refs[next(iter(refs))], (x + 2.54, y - 6.0), False),
            ('Value', value, (x + 2.54, y + 6.0), False),
            ('Footprint', fp, (x, y), True),
            ('Datasheet', '', (x, y), True),
        ]
        for k, v in (fields or {}).items():
            props.append((k, v, (x, y), True))
        node = ['symbol', ['lib_id', Q(lib_id)], ['at', x, y, rot], ['unit', 1],
                ['exclude_from_sim', 'no'], ['in_bom', 'no' if dnp else 'yes'],
                ['on_board', 'yes'], ['dnp', 'yes' if dnp else 'no'], ['uuid', uid(key)]]
        for name, val, (px, py), hide in props:
            eff = ['effects', ['font', ['size', 1.27, 1.27]]]
            if hide:
                eff.append(['hide', 'yes'])
            node.append(['property', Q(name), Q(val), ['at', px, py, 0], eff])
        pins = symbol_pins(sym)
        seen = set()
        for p in pins:
            node.append(['pin', Q(p['num']), ['uuid', uid(key, 'pin', p['num'])]])
        node.append(self._instances(refs))
        self.items.append(node)
        # wire every pin to its net
        nets = nets or {}
        for p in pins:
            net = nets.get(p['num'], nets.get(p['name']))
            if net is None:
                raise SystemExit(f'{lib_id} {refs} pin {p["num"]}/{p["name"]} unassigned')
            px, py = round(x + p['x'], 4), round(y - p['y'], 4)
            if (px, py) in seen:
                continue
            seen.add((px, py))
            if net == 'NC':
                self.items.append(['no_connect', ['at', px, py], ['uuid', uid(key, 'nc', p['num'])]])
                continue
            dx, dy = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[p['ang']]
            ex, ey = round(px + 2.54 * dx, 4), round(py + 2.54 * dy, 4)
            self.wire(px, py, ex, ey, (key, p['num']))
            self.attach(net, ex, ey, (dx, dy), (key, p['num']), hier)

    def wire(self, x1, y1, x2, y2, key):
        self.items.append(['wire', ['pts', ['xy', x1, y1], ['xy', x2, y2]],
                           ['stroke', ['width', 0], ['type', 'default']], ['uuid', uid(key, 'w')]])

    def attach(self, net, x, y, d, key, hier=()):
        ang, just = {(-1, 0): (180, 'right'), (1, 0): (0, 'left'),
                     (0, 1): (270, 'right'), (0, -1): (90, 'left')}[d]
        if net in ('GND', '+48V', '+3V3'):
            self.power(net, x, y, d, key)
        elif net in hier:
            self.items.append(['hierarchical_label', Q(net), ['shape', 'bidirectional'],
                               ['at', x, y, ang],
                               ['effects', ['font', ['size', 1.27, 1.27]], ['justify', just]],
                               ['uuid', uid(key, 'hl')]])
        else:
            self.items.append(['label', Q(net), ['at', x, y, ang],
                               ['effects', ['font', ['size', 1.27, 1.27]], ['justify', just, 'bottom']],
                               ['uuid', uid(key, 'l')]])

    def power(self, net, x, y, d, key, flag=False):
        lib_id = 'power:PWR_FLAG' if flag else f'power:{net}'
        self.pwr += 1
        n = self.pwr
        refs = {p: (f'#FLG{pref}{n:02d}' if flag else f'#PWR{pref}{n:02d}')
                for p, pref in self.paths.items()}
        if net == 'GND' and not flag:
            rot = {(0, 1): 0, (0, -1): 180, (-1, 0): 270, (1, 0): 90}[d]
        else:
            rot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[d]
        sym = self.lib.setdefault(lib_id, load_symbol(lib_id))
        node = ['symbol', ['lib_id', Q(lib_id)], ['at', x, y, rot], ['unit', 1],
                ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
                ['dnp', 'no'], ['uuid', uid(key, 'pwr', lib_id)]]
        for name, val, hide in (('Reference', refs[next(iter(refs))], True),
                                ('Value', 'PWR_FLAG' if flag else net, flag is False and False),
                                ('Footprint', '', True), ('Datasheet', '', True)):
            eff = ['effects', ['font', ['size', 1.27, 1.27]]]
            if hide:
                eff.append(['hide', 'yes'])
            node.append(['property', Q(name), Q(val), ['at', x, y + (3.2 if rot == 0 and net == 'GND' else -3.2), 0], eff])
        node.append(['pin', Q('1'), ['uuid', uid(key, 'pwrpin', lib_id)]])
        node.append(self._instances(refs))
        self.items.append(node)

    def flag(self, net, x, y):
        """PWR_FLAG on a wire stub labelled `net`."""
        key = ('flag', net, x, y)
        self.power(net, x, y, (0, -1), key, flag=True)
        self.wire(x, y, x, y + 2.54, key)
        self.attach(net, x, y + 2.54, (0, 1), key)

    def render(self, file_uuid, paper, title, extra=()):
        head = ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')],
                ['generator_version', Q('9.0')], ['uuid', file_uuid], ['paper', Q(paper)],
                ['title_block', ['title', Q(title)], ['rev', Q('A')],
                 ['company', Q('saturn-pdu (CERN-OHL-S-2.0)')],
                 ['comment', 1, Q('Generated by hardware/kicad/tools/gen_2ch_sch.py - tidy by hand')]],
                ['lib_symbols'] + list(self.lib.values())]
        return dump(head + self.items + list(extra)) + '\n'


# ------------------------------------------------------------ channel ------
R0603, R0805, R2512 = ('Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_0805_2012Metric',
                       'Resistor_SMD:R_2512_6332Metric')
C0603, C0805, C1210 = ('Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_0805_2012Metric',
                       'Capacitor_SMD:C_1210_3225Metric')
FET = 'saturn-pdu:TI_VSONP-8_5x6mm_P1.27mm'
SOT23 = 'Package_TO_SOT_SMD:SOT-23'

# (ref, lib_id, value, footprint, {pin: net}, dnp, fields)
CHANNEL = [
    # --- controller -------------------------------------------------------
    ('U01', 'saturn-pdu:LM5116', 'LM5116MH', 'Package_SO:ETSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3x4.2mm',
     {'1': 'VIN_F', '4': 'EN', '2': 'UVLO', '3': 'RT', '5': 'RAMP', '7': 'SS', '8': 'FB',
      '9': 'COMP', '10': 'VOUT_REG', '11': 'DEMB', '16': 'VCC', '17': 'GND', '18': 'HB',
      '19': 'HO', '20': 'SW', '15': 'LO', '12': 'CS', '13': 'CSG', '14': 'GND', '6': 'GND',
      '21': 'GND'}, False, {'MPN': 'LM5116MHX/NOPB'}),
    # --- power stage ------------------------------------------------------
    ('F01', 'Device:Fuse', '5A F 125VDC', 'Fuse:Fuse_Littelfuse-NANO2-451_453',
     {'1': '+48V', '2': 'VIN_F'}, False, {'MPN': 'Littelfuse 0453005.MR'}),
    ('D01', 'Device:D_Zener', 'SMCJ58A', 'Diode_SMD:D_SMC', {'K': 'VIN_F', 'A': 'GND'}, False,
     {'MPN': 'Littelfuse SMCJ58A'}),
    ('C01', 'Device:C_Polarized', '100u 63V', 'Capacitor_SMD:CP_Elec_10x10.5',
     {'1': 'VIN_F', '2': 'GND'}, False, {'MPN': 'Panasonic EEEFK1J101P'}),
    ('C02', 'Device:C_Polarized', '100u 63V', 'Capacitor_SMD:CP_Elec_10x10.5',
     {'1': 'VIN_F', '2': 'GND'}, False, {'MPN': 'Panasonic EEEFK1J101P'}),
    *[(f'C0{i}', 'Device:C', '2.2u 100V X7R', C1210, {'1': 'VIN_F', '2': 'GND'}, False,
       {'MPN': 'Murata GRM32ER72A225KA35L'}) for i in (3, 4, 5, 6)],
    ('C07', 'Device:C', '100n 100V', C0805, {'1': 'VIN_F', '2': 'GND'}, False, {}),
    ('Q01', 'Transistor_FET:CSD18563Q5A', 'CSD18563Q5A', FET,
     {'S': 'SW', 'G': 'HO_G', 'D': 'VIN_F'}, False, {'MPN': 'CSD18563Q5A'}),
    ('Q02', 'Transistor_FET:CSD18563Q5A', 'CSD18563Q5A', FET,
     {'S': 'ISNS', 'G': 'LO_G', 'D': 'SW'}, False, {'MPN': 'CSD18563Q5A'}),
    ('R01', 'Device:R', '0R', R0603, {'1': 'HO', '2': 'HO_G'}, False, {}),
    ('R02', 'Device:R', '0R', R0603, {'1': 'LO', '2': 'LO_G'}, False, {}),
    ('R03', 'Device:R', '7m 1W', R2512, {'1': 'ISNS', '2': 'GND'}, False,
     {'MPN': 'Bourns CRA2512-FZ-R007ELF'}),
    ('R04', 'Device:R', '0R', R0603, {'1': 'CS', '2': 'ISNS'}, False,
     {'Note': 'Kelvin: route to Q02 source pad'}),
    ('R05', 'Device:R', '0R', R0603, {'1': 'CSG', '2': 'GND'}, False,
     {'Note': 'Kelvin: route to R03 ground pad'}),
    ('R06', 'Device:R', '2.2R', 'Resistor_SMD:R_1206_3216Metric', {'1': 'SW', '2': 'SNUB'}, True,
     {'Note': 'LS snubber, tune on bench (D-10 spike gate)'}),
    ('C08', 'Device:C', '1n 100V', C0805, {'1': 'SNUB', '2': 'GND'}, True,
     {'Note': 'LS snubber, tune on bench (D-10 spike gate)'}),
    ('L01', 'saturn-pdu:L_XAL1510-223MEB', '22u', 'saturn-pdu:L_Coilcraft_XAL1510',
     {'1': 'SW', '2': 'VOUT_REG'}, False, {'MPN': 'Coilcraft XAL1510-223MEB'}),
    ('C09', 'Device:C_Polarized', '220u 35V', 'Capacitor_SMD:CP_Elec_8x10',
     {'1': 'VOUT_REG', '2': 'GND'}, False, {'MPN': 'Panasonic EEHZA1V221P'}),
    ('C10', 'Device:C_Polarized', '220u 35V', 'Capacitor_SMD:CP_Elec_8x10',
     {'1': 'VOUT_REG', '2': 'GND'}, False, {'MPN': 'Panasonic EEHZA1V221P'}),
    *[(f'C{i}', 'Device:C', '22u 50V X7R', C1210, {'1': 'VOUT_REG', '2': 'GND'}, False,
       {'MPN': 'Murata GRM32ER71H226KE15L'}) for i in (11, 12, 13, 14)],
    # --- controller support -----------------------------------------------
    ('R07', 'Device:R', '1M', R0603, {'1': 'VIN_F', '2': 'EN'}, False, {}),
    ('R08', 'Device:R', '100k', R0603, {'1': 'VIN_F', '2': 'UVLO'}, False, {'Note': 'RUV2'}),
    ('R09', 'Device:R', '4.12k 1%', R0603, {'1': 'UVLO', '2': 'GND'}, False, {'Note': 'RUV1'}),
    ('C15', 'Device:C', '1u 25V', C0603, {'1': 'UVLO', '2': 'GND'}, False, {'Note': 'CFT hiccup timer'}),
    ('D02', 'Diode:BAS316', 'BAS316', 'Diode_SMD:D_SOD-323', {'A': 'UVLO', 'K': 'VIN_F'}, False,
     {'Note': 'Discharges CFT on input UV (datasheet 8.2.2)'}),
    ('R10', 'Device:R', '12.4k 1%', R0603, {'1': 'RT', '2': 'GND'}, False, {'Note': '250 kHz'}),
    ('R11', 'Device:R', '182k 1%', R0603, {'1': 'RAMP', '2': 'VCC'}, False, {'Note': 'RRAMP, VOUT > 7.5V'}),
    ('C16', 'Device:C', '1n C0G', C0603, {'1': 'RAMP', '2': 'GND'}, False, {}),
    ('C17', 'Device:C', '150n', C0603, {'1': 'SS', '2': 'GND'}, False, {'Note': '~18 ms soft-start'}),
    ('R12', 'Device:R', '17.8k 0.1%', R0603, {'1': 'VOUT_REG', '2': 'FB'}, False, {'Note': 'RFB2'}),
    ('R13', 'Device:R', '1.21k 0.1%', R0603, {'1': 'FB', '2': 'GND'}, False, {'Note': 'RFB1 -> 19.09 V'}),
    ('R14', 'Device:R', '169k 1%', R0603, {'1': 'COMP', '2': 'COMP_RC'}, False, {}),
    ('C18', 'Device:C', '2.2n C0G', C0603, {'1': 'COMP_RC', '2': 'FB'}, False, {}),
    ('C19', 'Device:C', '10p C0G', C0603, {'1': 'COMP', '2': 'FB'}, False, {}),
    ('R15', 'Device:R', '10k', R0603, {'1': 'DEMB', '2': 'GND'}, False, {}),
    ('C20', 'Device:C', '1u 25V', C0603, {'1': 'VCC', '2': 'GND'}, False, {}),
    ('D03', 'Diode:BAS316', 'BAS316', 'Diode_SMD:D_SOD-323', {'A': 'VCC', 'K': 'HB'}, False,
     {'Note': 'Bootstrap diode (TI EVM: CMPD2003)'}),
    ('C21', 'Device:C', '1u 25V', C0603, {'1': 'HB', '2': 'SW'}, False, {}),
    # --- remote disable (fail-ON) -----------------------------------------
    ('Q03', 'Transistor_FET:2N7002', '2N7002', SOT23, {'G': 'OFF_G', 'S': 'GND', 'D': 'UVLO'},
     False, {}),
    ('R16', 'Device:R', '1k', R0603, {'1': 'OFF', '2': 'OFF_G'}, False, {}),
    ('R17', 'Device:R', '100k', R0603, {'1': 'OFF_G', '2': 'GND'}, False,
     {'Note': 'Holds channel ON with control board absent (F-5)'}),
    # --- output, telemetry ------------------------------------------------
    ('R18', 'Device:R', '2m 1W', R2512, {'1': 'VOUT_REG', '2': 'VOUT'}, False,
     {'MPN': 'Vishay WSL2512R0020FEA', 'Note': 'Kelvin-route INA226 inputs to the pads'}),
    ('U02', 'Sensor_Energy:INA226', 'INA226AIDGSR', 'Package_SO:TSSOP-10_3x3mm_P0.5mm',
     {'A1': 'A1', 'A0': 'A0', '~{Alert}': 'NC', 'SDA': 'SDA', 'SCL': 'SCL', 'VS': '+3V3',
      'GND': 'GND', 'Vbus': 'VOUT', 'Vin-': 'VOUT', 'Vin+': 'VOUT_REG'}, False, {}),
    ('C22', 'Device:C', '100n', C0603, {'1': '+3V3', '2': 'GND'}, False, {}),
    ('R19', 'Device:R', '4.7k 1W', R2512, {'1': 'VOUT', '2': 'GND'}, False, {'Note': 'Bleed (P-9)'}),
    # --- OVP crowbar (D-3) ------------------------------------------------
    ('R20', 'Device:R', '76.8k 0.1%', R0603, {'1': 'VOUT', '2': 'OVP_REF'}, False,
     {'Note': 'Trip = 2.495 x (1 + 76.8/10) = 21.66 V'}),
    ('R21', 'Device:R', '10k 0.1%', R0603, {'1': 'OVP_REF', '2': 'GND'}, False, {}),
    ('C23', 'Device:C', '1n', C0603, {'1': 'OVP_REF', '2': 'GND'}, False, {'Note': '~9 us filter'}),
    ('U03', 'Reference_Voltage:TL431DBZ', 'TL431BIDBZR', SOT23,
     {'K': 'OVP_K', 'REF': 'OVP_REF', 'A': 'GND'}, False, {}),
    ('R22', 'Device:R', '10k', R0603, {'1': 'VOUT', '2': 'OVP_B'}, False, {}),
    ('R23', 'Device:R', '1k', R0603, {'1': 'OVP_B', '2': 'OVP_K'}, False, {}),
    ('Q04', 'Transistor_BJT:MMBTA56', 'MMBTA56', SOT23, {'B': 'OVP_B', 'E': 'VOUT', 'C': 'OVP_DRV'},
     False, {'Note': '80V PNP: keeps TL431 anode at GND so the trip point is exact'}),
    ('R24', 'Device:R', '220R', R0805, {'1': 'OVP_DRV', '2': 'SCR_G'}, False, {}),
    ('R25', 'Device:R', '1k', R0603, {'1': 'SCR_G', '2': 'GND'}, False, {}),
    ('C24', 'Device:C', '10n', C0603, {'1': 'SCR_G', '2': 'GND'}, False, {'Note': 'dv/dt immunity'}),
    ('Q05', 'Device:Q_SCR_KAG', 'BT151-500R', 'Package_TO_SOT_THT:TO-220-3_Horizontal_TabDown',
     {'K': 'GND', 'A': 'VOUT', 'G': 'SCR_G'}, False, {'MPN': 'WeEn BT151-500R'}),
]
HIER = ('VOUT', 'OFF', 'SDA', 'SCL', 'A0', 'A1')


def channel_sheet():
    paths = {f'/{ROOT}/{SHEETS[n]}': str(n) for n in (1, 2)}
    sh = Sheet(paths)
    col_w, row_h, x0, y0, cols = 38.1, 33.02, 30.48, 35.56, 10
    slot = 0
    for ref, lib_id, val, fp, nets, dnp, fields in CHANNEL:
        span = 2 if lib_id.endswith(('LM5116', 'INA226')) else 1
        if slot % cols + span > cols:
            slot += cols - slot % cols
        x = round(x0 + (slot % cols) * col_w + (span - 1) * col_w / 2, 2)
        y = round(y0 + (slot // cols) * row_h, 2)
        x, y = round(x / 1.27) * 1.27, round(y / 1.27) * 1.27
        slot += span
        refs = {p: f'{ref[:-2]}{n}{ref[-2:]}' for p, n in paths.items()}
        sh.place(lib_id, round(x, 2), round(y, 2), refs, val, fp, nets, dnp, fields, HIER)
    # PWR_FLAGs: nets whose power_in pins are fed only through passives
    fy = round((y0 + (slot // cols + 1) * row_h) / 1.27) * 1.27
    for i, net in enumerate(('VIN_F', 'HB')):
        sh.flag(net, round((x0 + i * col_w) / 1.27) * 1.27, fy)
    return sh.render(CHAN_UUID, 'A3', 'Buck channel: 48 V -> 19.1 V / 7 A, OVP crowbar, INA226')


# ---------------------------------------------------------------- top ------
def top_sheet():
    sh = Sheet({f'/{ROOT}': ''})
    sh.pwr = 900
    J = 'Connector_Generic:'
    parts = [
        ('J1', J + 'Conn_02x02_Odd_Even', '48V IN', 'Connector_Molex:Molex_Mini-Fit_Jr_5566-04A_2x02_P4.20mm_Vertical',
         {'1': '+48V', '2': '+48V', '3': 'GND', '4': 'GND'}, {'MPN': 'Molex Mini-Fit Jr 5566-04A'}),
        ('J2', J + 'Conn_02x04_Odd_Even', '19V OUT', 'Connector_Molex:Molex_Mini-Fit_Jr_5566-08A_2x04_P4.20mm_Vertical',
         {'1': 'VOUT1', '2': 'VOUT1', '3': 'GND', '4': 'GND', '5': 'VOUT2', '6': 'VOUT2',
          '7': 'GND', '8': 'GND'}, {'MPN': 'Molex Mini-Fit Jr 5566-08A', 'Note': '2 pins per rail: 3.5 A/pin'}),
        ('J3', J + 'Conn_02x06_Odd_Even', 'CTRL', 'Connector_IDC:IDC-Header_2x06_P2.54mm_Vertical',
         {'1': '+3V3', '2': 'GND', '3': 'SDA', '4': 'GND', '5': 'SCL', '6': 'GND', '7': 'CH1_OFF',
          '8': 'CH2_OFF', '9': 'NTC', '10': 'GND', '11': 'BOARD_ID', '12': 'GND'},
         {'Note': 'I2C pull-ups live on the control board'}),
        ('RT1', 'Device:Thermistor_NTC', '10k B3950', R0603, {'1': 'NTC', '2': 'GND'},
         {'MPN': 'Murata NCP18XH103F03RB', 'Note': 'Firmware treats open/short as HOT (FMEA 9)'}),
        ('C1', 'Device:C', '1u', C0603, {'1': '+3V3', '2': 'GND'}, {}),
    ]
    for i, (ref, lib_id, val, fp, nets, fields) in enumerate(parts):
        x, y = 40.64 + i * 45.72, 50.8
        sh.place(lib_id, x, y, {f'/{ROOT}': ref}, val, fp, nets, False, fields)
    for i, net in enumerate(('+48V', 'GND', '+3V3')):
        sh.flag(net, 40.64 + i * 20.32, 88.9)
    extra = []
    for n in (1, 2):
        sx, sy, w, h = 165.1 + (n - 1) * 60.96, 101.6, 25.4, 22.86
        sheet = ['sheet', ['at', sx, sy], ['size', w, h], ['exclude_from_sim', 'no'],
                 ['in_bom', 'yes'], ['on_board', 'yes'], ['dnp', 'no'],
                 ['stroke', ['width', 0.1524], ['type', 'solid']],
                 ['fill', ['color', 0, 0, 0, 0.0]], ['uuid', SHEETS[n]],
                 ['property', Q('Sheetname'), Q(f'CH{n}'), ['at', sx, sy - 0.7, 0],
                  ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'bottom']]],
                 ['property', Q('Sheetfile'), Q('channel.kicad_sch'), ['at', sx, sy + h + 0.6, 0],
                  ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'top']]]]
        conn = {'VOUT': f'VOUT{n}', 'OFF': f'CH{n}_OFF', 'SDA': 'SDA', 'SCL': 'SCL',
                'A0': 'GND' if n == 1 else '+3V3', 'A1': 'BOARD_ID'}
        for k, pin in enumerate(HIER):
            py = sy + 2.54 + k * 3.81
            py = round(py / 1.27) * 1.27
            px = sx + w
            key = ('sheetpin', n, pin)
            sheet.append(['pin', Q(pin), 'bidirectional', ['at', px, py, 0],
                          ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'right']],
                          ['uuid', uid(key)]])
            sh.wire(px, py, px + 5.08, py, key)
            sh.attach(conn[pin], px + 5.08, py, (1, 0), key)
        sheet.append(['instances', ['project', Q(PROJECT),
                                    ['path', Q(f'/{ROOT}'), ['page', Q(str(n + 1))]]]])
        extra.append(sheet)
    extra.append(['sheet_instances', ['path', Q('/'), ['page', Q('1')]]])
    extra.append(['embedded_fonts', 'no'])
    return sh.render(ROOT, 'A3', 'Saturn PDU 2-channel power board', extra)


if __name__ == '__main__':
    open(os.path.join(PROJ_DIR, 'channel.kicad_sch'), 'w').write(channel_sheet())
    open(os.path.join(PROJ_DIR, f'{PROJECT}.kicad_sch'), 'w').write(top_sheet())
    print('written')
