"""Generate the demo LTspice schematics (.asc) in schematics/ and the
example schematics in examples/.

Pin offsets of the built-in symbols and the rotation convention
(R90: (x,y)->(-y,x), R270: (x,y)->(y,-x)) were verified with `LTspice -netlist`.
Re-run after changing the layout:  python3 tools/make_schematics.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "schematics")
EXAMPLES = os.path.join(ROOT, "examples")


def write_if_changed(path, text):
    """Leave an unchanged file untouched (its date tells validate.py whether the
    simulation results are newer than the bench)."""
    if os.path.isfile(path) and open(path).read() == text:
        return
    open(path, "w").write(text)

ROT = {"R0": lambda x, y: (x, y), "R90": lambda x, y: (-y, x),
       "R180": lambda x, y: (-x, -y), "R270": lambda x, y: (y, -x),
       "M0": lambda x, y: (-x, y)}
PINS = {
    "res": [(16, 16), (16, 96)], "cap": [(16, 0), (16, 64)], "polcap": [(16, 0), (16, 64)],
    "ind": [(16, 16), (16, 96)], "voltage": [(0, 16), (0, 96)], "diode": [(16, 0), (16, 64)],
    "schottky": [(16, 0), (16, 64)], "zener": [(16, 0), (16, 64)],
    "nmos": [(48, 0), (0, 80), (48, 96)], "sw": [(0, 16), (0, 96), (-48, 80), (-48, 32)],
    "EFUSE48_MOD": [(-144, -96), (144, -96), (0, 144), (-144, 0), (-144, 32), (-144, 64),
                    (144, 0), (144, 32), (144, 64)],
    "VNF1048F": [(-144, -128), (-144, -96), (-144, -48), (-144, -16), (144, -128), (144, -96),
                 (144, -48), (144, -16), (0, 176), (144, 48), (-144, 48), (-144, 80),
                 (-144, 112), (144, 80)],
    "NTC10K_ST": [(-64, 0), (64, 0), (0, -48), (0, 48)],
    "BATTERY": [(0, -80), (0, 80), (80, 0)],
    "BATTERY_BMS": [(0, -96), (0, 96), (112, -32), (-112, 0), (112, 32)],
    "DCDC48_12": [(-128, -32), (128, -32), (0, 96), (-128, 32), (128, 32)],
    "WIRE": [(-80, 0), (80, 0), (0, -48), (0, 48)],
    "FI_SHORT": [(0, -64), (0, 64)], "bi": [(0, 0), (0, 80)],
    "OCSW": [(-96, -16), (96, -16), (0, 64), (-96, 16), (96, 16)],
    **{n: [(0, -64), (0, 64)] for n in ("TP_STEP", "TP_CRANK", "TP_LOADDUMP", "TP_ISO7637", "TP_RIPPLE")},
}
# reference parameter sets: same pins as their base models
PINS.update(BAT12_VARTA_E39=PINS["BATTERY"], BAT48_A123_8AH=PINS["BATTERY_BMS"],
            DCDC_TOSHIBA_RD210=PINS["DCDC48_12"])


# body extents of the built-in symbols (pins included), in the symbol frame
BODY = {"res": (0, 16, 32, 96), "ind": (0, 16, 32, 96), "cap": (0, 0, 32, 64), "polcap": (0, 0, 48, 64),
        "diode": (0, 0, 32, 64), "schottky": (0, 0, 32, 64), "zener": (-4, 0, 36, 64),
        "voltage": (-32, 16, 32, 96), "sw": (-48, 16, 32, 96), "nmos": (0, 0, 48, 96), "bi": (-32, 0, 32, 80)}
INV = {"R0": lambda x, y: (x, y), "R180": lambda x, y: (-x, -y), "M0": lambda x, y: (-x, y)}


def text_w(s, size=2):
    """Estimated width of a text in LTspice units (as tools/check_layout.py)."""
    return len(str(s)) * 0.58 * 16 * {0: 0.625, 1: 1.0, 2: 1.5, 3: 2.0}[size]


class Sch:
    def __init__(self, w=2400, h=1400):
        self.L = ["Version 4", f"SHEET 1 {w} {h}"]

    def part(self, sym, x, y, rot="R0", name=None, value=None, line=None, extra=(), lab="right", vsize=2):
        """lab: where a vertical built-in part shows its name and value,
        "right" or "left" of its body (vsize: font size of the value)."""
        self.L.append(f"SYMBOL {sym} {x} {y} {rot}")
        if rot in ("R90", "R270") and sym in ("res", "ind", "cap", "diode", "schottky", "zener"):
            cy = (BODY[sym][1] + BODY[sym][3]) // 2
            self.L += [f"WINDOW 0 0 {cy} VBottom 2", f"WINDOW 3 32 {cy} VTop 2"]
        elif sym in BODY and rot in INV and lab:
            pts = [ROT[rot](px, py) for px, py in ((BODY[sym][0], BODY[sym][1]), (BODY[sym][2], BODY[sym][3]))]
            xl, xr = min(p[0] for p in pts), max(p[0] for p in pts)
            ym = (pts[0][1] + pts[1][1]) / 2
            ax, just = (xr + 8, "Left") if lab == "right" else (xl - 8, "Right")
            if rot != "R0":                       # the window is given in the symbol frame
                just = {"Left": "Right", "Right": "Left"}[just]
            for wid, dy, size in ((0, -14, 2), (3, 14, vsize)):
                wx, wy = INV[rot](ax, int(ym + dy))
                self.L.append(f"WINDOW {wid} {wx} {wy} {just} {size}")
        if name:
            self.L.append(f"SYMATTR InstName {name}")
        if value is not None:
            self.L.append(f"SYMATTR Value {value}")
        if line:
            self.L.append(f"SYMATTR SpiceLine {line}")
        self.L += list(extra)
        return [(x + dx, y + dy) for dx, dy in (ROT[rot](px, py) for px, py in PINS[sym])]

    def wire(self, *pts):
        for a, b in zip(pts, pts[1:]):
            if tuple(a) != tuple(b):          # touching pins need no wire
                self.L.append(f"WIRE {a[0]} {a[1]} {b[0]} {b[1]}")

    def flag(self, p, net):
        self.L.append(f"FLAG {p[0]} {p[1]} {net}")

    def gnd(self, p):
        self.flag(p, "0")

    def stub(self, p, d, net, length=None):
        """Net label at the end of a short wire from pin p in direction d
        ((-1, 0) left, (1, 0) right, (0, -1) up, (0, 1) down), long enough for
        the label to clear the part. Returns the label point."""
        if length is None:
            length = 32 if d[0] == 0 else 16 * int((text_w(net) + 31) // 16)
        q = (p[0] + d[0] * length, p[1] + d[1] * length)
        self.wire(p, q)
        self.flag(q, net)
        return q

    def mid(self, a, b, net, at=0.5):
        """Wire a -> b (horizontal or vertical) with a net label at a grid point between them."""
        if a[1] == b[1]:
            m = (a[0] + 16 * round((b[0] - a[0]) * at / 16), a[1])
        else:
            m = (a[0], a[1] + 16 * round((b[1] - a[1]) * at / 16))
        self.wire(a, m, b)
        self.flag(m, net)
        return m

    def sources(self, srcs, x, y, vsize=1, gap=64):
        """A row of voltage sources (name, net, value) with their + pin labelled
        and - pin grounded, spaced by the width of their value text."""
        for nm, net, val in srcs:
            p = self.part("voltage", x, y, name=nm, value=val, vsize=vsize)
            self.stub(p[0], (0, -1), net)
            self.gnd(p[1])
            x += 16 * int((max(160, 40 + text_w(val, vsize), 40 + text_w(nm)) + gap + 15) // 16)
        return x

    def directives(self, x, y, lines, size=2):
        """A column of directives; returns the x where the next column can start."""
        dy = 32 if size >= 2 else 24
        for k, ln in enumerate(lines):
            self.text(x, y + dy * k, ln, size, True)
        return x + 16 * int((max(text_w(ln, size) for ln in lines) + 63) // 16)

    def box(self, x0, y0, x1, y1):
        """Dashed frame around a group of parts (drawing only)."""
        self.L.append(f"RECTANGLE Normal {x1} {y1} {x0} {y0} 2")

    def text(self, x, y, s, size=2, directive=False):
        self.L.append(f"TEXT {x} {y} Left {size} {'!' if directive else ';'}{s}")

    def save(self, fname, folder=OUT):
        os.makedirs(folder, exist_ok=True)
        write_if_changed(os.path.join(folder, fname), "\n".join(self.L) + "\n")
        print("  ->", os.path.relpath(os.path.join(folder, fname), ROOT))


# ---------------------------------------------------------------------------
def demo_module():
    """EFUSE48_MOD in a 48 V harness: start-up, hard short, CLR retry."""
    s = Sch(2400, 1000)
    y = 224  # power rail
    vb = s.part("voltage", 32, 240, name="Vbat", value=48)
    s.gnd(vb[1])
    rb = s.part("res", 192, 208, "R90", "Rbat", "10m")
    lb = s.part("ind", 320, 208, "R90", "Lbat", "1u")
    cb = s.part("cap", 384, y, name="Cbus", value="100u", line="Rser=30m")
    s.gnd(cb[1])
    tv = s.part("diode", 576, 288, "R180", "Dtvs", "EF_TVS58V")
    s.gnd(tv[0])
    x1 = s.part("EFUSE48_MOD", 880, 320, name="U1",
                line="RSENSE=1m OVC_CODE=13 HSC_CODE=12 VDS_CODE=14 NTC_CODE=4 TNOM_CODE=0")
    s.wire(vb[0], (32, y), rb[1]); s.wire(rb[0], lb[1])
    s.mid(lb[0], cb[0], "vbat"); s.wire(cb[0], tv[1]); s.wire(tv[1], x1[0])
    s.gnd(x1[2])
    df = s.part("schottky", 1296, 288, "R180", "Dfw", "EF_SCH100V")
    s.gnd(df[0])
    lh = s.part("ind", 1552, 208, "R90", "Lh", "1u")
    rh = s.part("res", 1680, 208, "R90", "Rh", "10m")
    cl = s.part("cap", 1728, y, name="Cload", value="220u", line="Rser=20m")
    s.gnd(cl[1])
    rl = s.part("res", 1872, 208, name="Rload", value=4.8)
    s.gnd(rl[1])
    sw = s.part("sw", 2144, 208, name="Ssc", value="SSHORT")
    s.gnd(sw[1]); s.gnd(sw[3]); s.stub(sw[2], (-1, 0), "sc")
    s.mid(x1[1], df[1], "out"); s.wire(df[1], lh[1]); s.wire(lh[0], rh[1])
    s.mid(rh[0], cl[0], "load")
    s.wire(cl[0], rl[0]); s.wire(rl[0], sw[0])
    for net, pin in (("en", 3), ("byp", 4), ("clr", 5)):
        s.stub(x1[pin], (-1, 0), net)
    for net, pin in (("diag", 6), ("cs", 7), ("tfet", 8)):
        s.stub(x1[pin], (1, 0), net)
    s.sources([("Ven", "en", "PWL(0 0 0.5m 0 0.501m 3.3)"), ("Vbyp", "byp", "0"),
               ("Vclr", "clr", "PWL(0 0 6m 0 6.001m 3.3 6.05m 3.3 6.051m 0 10m 0 10.001m 3.3 10.05m 3.3 10.051m 0)"),
               ("Vsc", "sc", "PWL(0 0 3m 0 3.0001m 1 9m 1 9.0001m 0)")], 96, 672)
    s.text(32, -40, "48 V eFuse channel (VNF1048F behavioral, EFUSE48_MOD): start-up, hard short at 3 ms, "
                    "CLR retry at 6 ms, short removed 9 ms, CLR 10 ms", 2)
    s.text(32, 0, "Probe internal status: V(u1:xu:hsht) V(u1:xu:fusel) V(u1:xu:fd) V(u1:xu:gcmd)  (LTspice 24+; XVII: V(u1:xu:...))", 1)
    x = s.directives(32, 888, [".include ../models/VNF1048F_beh.lib",
                               ".model SSHORT SW(Ron=5m Roff=1Meg Vt=0.5 Vh=-0.2)", ".tran 0 12m 0 0.2u"])
    s.directives(x, 888, [".meas tran t_trip find time when V(u1:xu:hsht)=0.5 rise=1",
                          ".meas tran ipk max -I(Lh) from 3m to 3.1m",
                          ".meas tran vbatpk max V(vbat) from 3m to 3.2m",
                          ".options plotwinsize=0",
                          ".save V(vbat) V(out) V(load) V(diag) V(cs) V(tfet) I(Lh) I(Lbat) V(u1:hsg) V(u1:g) "
                          "V(u1:drn) V(u1:xu:hsht) V(u1:xu:fusel) V(u1:xu:fd) V(u1:xu:gcmd)"], 1)
    s.save("demo_efuse48_module.asc")


def app_discrete():
    """Discrete application circuit around the VNF1048F symbol (DS13084 Fig. 16 + slew network)."""
    s = Sch(2300, 1300)
    y = 144                                   # power rail: battery -> shunt -> FET
    # --- battery and input
    vb = s.part("voltage", 48, 128, name="Vbat", value=48); s.gnd(vb[1])
    rb = s.part("res", 224, 128, "R90", "Rbat", "10m")
    s.wire(vb[0], rb[1])
    cvs1 = s.part("polcap", 336, y, name="Cvs1", value="100u", line="Rser=30m"); s.gnd(cvs1[1])
    s.mid(rb[0], cvs1[0], "vbat")
    cvs2 = s.part("cap", 480, y, name="Cvs2", value="100n"); s.gnd(cvs2[1]); s.wire(cvs1[0], cvs2[0])
    tvs = s.part("diode", 640, 208, "R180", "Dtvs", "EF_TVS58V"); s.gnd(tvs[0]); s.wire(cvs2[0], tvs[1])
    # --- shunt and FET
    rs = s.part("res", 912, 128, "R90", "Rsense", "1m"); s.wire(tvs[1], rs[1])
    m1 = s.part("nmos", 1040, y, name="M1", value="EF_FET100V")
    s.mid(rs[0], m1[0], "drn")
    s.stub(m1[1], (-1, 0), "g"); s.stub(m1[2], (0, 1), "out")
    # --- controller
    u = s.part("VNF1048F", 768, 576, name="U1",
               line="OVC_CODE=13 HSC_CODE=12 VDS_CODE=14 NTC_CODE=4 TNOM_CODE=0 FUSE_MODE=0 CPON=1")
    nets = ["vbat", "cp", "vbat", "drn", "hsg", "out", "ntc", "ntcm", "0", "diag", "en", "byp", "clr", "cs"]
    for k, (p, n) in enumerate(zip(u, nets)):
        if n == "0":
            s.gnd(p)
        else:
            s.stub(p, (-1, 0) if p[0] < 768 else (1, 0), n)
    ccp = s.part("cap", 432, 352, name="Ccp", value="470n")
    s.stub(ccp[0], (0, -1), "cp"); s.stub(ccp[1], (0, 1), "vbat")
    # --- gate network
    rgon = s.part("res", 1216, 336, "R90", "Rgon", "2.2k")
    s.stub(rgon[1], (-1, 0), "hsg"); s.stub(rgon[0], (1, 0), "g")
    rgof = s.part("res", 1216, 464, "R90", "Rgoff", "10"); s.stub(rgof[1], (-1, 0), "hsg")
    dgof = s.part("diode", 1424, 464, "R90", "Dgoff", "EF_DSW")
    s.mid(rgof[0], dgof[1], "goff"); s.stub(dgof[0], (1, 0), "g")
    csl = s.part("cap", 1632, 336, name="Cslew", value="47n"); s.stub(csl[0], (0, -1), "g"); s.gnd(csl[1])
    rgb = s.part("res", 1792, 320, name="Rgb", value="47k"); s.stub(rgb[0], (0, -1), "g"); s.stub(rgb[1], (0, 1), "out")
    dz = s.part("zener", 1984, 400, "R180", "Dzgs", "EF_DZ15")
    s.stub(dz[1], (0, -1), "g"); s.stub(dz[0], (0, 1), "out")
    # --- NTC bridge (NTC on the drain pad, temperature from source Vtpad)
    ntc = s.part("NTC10K_ST", 1248, 688, name="Xntc")
    s.stub(ntc[0], (-1, 0), "drn"); s.stub(ntc[2], (0, -1), "tpad"); s.gnd(ntc[3])
    rtr = s.part("res", 1536, 672, "R90", "Rtref", "10k")
    s.mid(ntc[1], rtr[1], "ntc"); s.stub(rtr[0], (1, 0), "ntcm")
    # --- logic side: DIAG pull-up
    rpu = s.part("res", 1792, 576, name="Rpu", value="4.7k")
    s.stub(rpu[0], (0, -1), "v33"); s.stub(rpu[1], (0, 1), "diag")
    # --- load side
    df = s.part("schottky", 1392, 208, "R180", "Dfw", "EF_SCH100V"); s.gnd(df[0])
    s.wire((1312, y), df[1]); s.flag((1312, y), "out")
    lh = s.part("ind", 1664, 128, "R90", "Lh", "1u"); s.wire(df[1], lh[1])
    cl = s.part("cap", 1728, y, name="Cload", value="220u", line="Rser=20m"); s.gnd(cl[1])
    s.mid(lh[0], cl[0], "load")
    rl = s.part("res", 1888, 128, name="Rload", value=4.8); s.wire(cl[0], rl[0]); s.gnd(rl[1])
    ro = s.part("res", 2064, 128, name="Rovl", value=2.4); s.wire(rl[0], ro[0])
    so = s.part("sw", 2080, 208, name="Sovl", value="SOVL"); s.wire(ro[1], so[0]); s.gnd(so[1])
    s.stub(so[2], (-1, 0), "ovl"); s.gnd(so[3])
    # --- sources
    s.sources([("Ven", "en", "PWL(0 0 0.5m 0 0.501m 3.3)"), ("Vbyp", "byp", "0"),
               ("Vclr", "clr", "PWL(0 0 80m 0 80.001m 3.3 80.1m 3.3 80.101m 0)"), ("V33", "v33", "3.3"),
               ("Vtpad", "tpad", "PWL(0 25 1 25)"), ("Vovl", "ovl", "PWL(0 0 5m 0 5.001m 1 75m 1 75.001m 0)")],
              64, 912)
    s.text(48, -64, "VNF1048F behavioral - discrete 48 V application (DS13084 Fig. 16 + gate slew network)", 2)
    s.text(48, -24, "0.5 ms ON (10 A) | 5 ms overload +20 A -> I2t trip after tNOM/16 = 62.5 ms | "
                    "75 ms overload removed | 80 ms CLR -> restart", 1)
    x = s.directives(48, 1120, [".include ../models/VNF1048F_beh.lib",
                                ".model SOVL SW(Ron=2m Roff=1Meg Vt=0.5 Vh=-0.2)", ".tran 0 100m 0 2u",
                                ".options plotwinsize=0"])
    s.directives(x, 1120, [".meas tran t_fuse find time when V(u1:fusel)=0.5 rise=1",
                           ".meas tran dt_fuse param t_fuse-5m",
                           ".meas tran iovl avg -I(Lh) from 20m to 30m",
                           ".meas tran vout_end avg V(out) from 95m to 100m",
                           ".save V(vbat) V(drn) V(out) V(load) V(hsg) V(g) V(cp) V(diag) V(cs) I(Lh) "
                           "V(u1:fusel) V(u1:fd) V(u1:gcmd) V(u1:xa)"], 1)
    s.save("app_vnf1048f_discrete.asc")


def demo_battery():
    """12 V battery with a starter-like load and a 48 V pack with BMS (pre-charge, load, short)."""
    s = Sch(2200, 1000)
    y = 224
    # --- 12 V: battery, terminal cap, cable, starter (locked rotor 8 mOhm, then 40 mOhm)
    b12 = s.part("BATTERY", 112, 320, name="U1", line="VNOM=12 SOC0=0.8 TBAT=-18")
    s.gnd(b12[1]); s.stub(b12[2], (1, 0), "soc12", 160)
    c12 = s.part("cap", 400, y, name="C12", value="1m", line="Rser=0.1"); s.gnd(c12[1])
    lc = s.part("ind", 576, 208, "R90", "Lcab", "1u")
    s.wire(b12[0], (112, y)); s.mid((112, y), c12[0], "v12"); s.wire(c12[0], lc[1])
    rlr = s.part("res", 640, 208, name="Rlr", value="8m")
    s.mid(lc[0], rlr[0], "starter")
    slr = s.part("sw", 656, 288, name="Slr", value="SST"); s.wire(rlr[1], slr[0]); s.gnd(slr[1])
    s.stub(slr[2], (-1, 0), "st1"); s.gnd(slr[3])
    rrun = s.part("res", 912, 208, name="Rrun", value="40m"); s.wire(rlr[0], rrun[0])
    srun = s.part("sw", 928, 288, name="Srun", value="SST"); s.wire(rrun[1], srun[0]); s.gnd(srun[1])
    s.stub(srun[2], (-1, 0), "st2"); s.gnd(srun[3])
    # --- 48 V: pack with BMS, harness, bus, load, short
    b48 = s.part("BATTERY_BMS", 1296, 336, name="U2", line="VNOM=48 SOC0=0.8 T_PRE=0.3 R_PRE=10")
    s.gnd(b48[1]); s.stub(b48[2], (1, 0), "soc48"); s.stub(b48[3], (-1, 0), "en"); s.stub(b48[4], (1, 0), "flt")
    lh = s.part("ind", 1520, 208, "R90", "Lharn", "2u")
    s.wire(b48[0], (1296, y)); s.mid((1296, y), lh[1], "vpack")
    cb = s.part("cap", 1584, y, name="Cbus", value="10m", line="Rser=5m"); s.gnd(cb[1])
    s.mid(lh[0], cb[0], "bus")
    rld = s.part("res", 1744, 208, name="Rload", value=1); s.wire(cb[0], rld[0])
    sld = s.part("sw", 1760, 288, name="Sload", value="SLD"); s.wire(rld[1], sld[0]); s.gnd(sld[1])
    s.stub(sld[2], (-1, 0), "ld"); s.gnd(sld[3])
    rsc = s.part("res", 2000, 208, name="Rsc", value="5m"); s.wire(rld[0], rsc[0])
    ssc = s.part("sw", 2016, 288, name="Ssc", value="SLD"); s.wire(rsc[1], ssc[0]); s.gnd(ssc[1])
    s.stub(ssc[2], (-1, 0), "sc"); s.gnd(ssc[3])
    s.sources([("Vst1", "st1", "PWL(0 0 0.1 0 0.1001 1 0.13 1 0.1301 0)"),
               ("Vst2", "st2", "PWL(0 0 0.13 0 0.1301 1 0.6 1 0.6001 0)"),
               ("Ven", "en", "PWL(0 0 10m 0 10.01m 3.3)"),
               ("Vld", "ld", "PWL(0 0 0.5 0 0.5001 1)"),
               ("Vsc", "sc", "PWL(0 0 0.8 0 0.8001 1)")], 96, 640)
    s.text(32, -40, "Battery models: 12 V BATTERY at -18 degC with a starter load (locked rotor 0.1 s, cranking "
                    "to 0.6 s) | 48 V BATTERY_BMS: EN 10 ms, pre-charge 0.3 s, 48 A load 0.5 s, short 0.8 s", 2)
    s.text(32, 0, "Probe: V(u1:s) raw SOC, V(u1:ocv) | V(u2:fl) fault latch, V(u2:x) switch state, "
                  "V(u2:pre) pre-charge, I(u2:Vsw) pack current", 1)
    x = s.directives(32, 864, [".include ../models/BATTERY_beh.lib",
                               ".model SST SW(Ron=0.1m Roff=1k Vt=0.5 Vh=-0.2)",
                               ".model SLD SW(Ron=0.1m Roff=1Meg Vt=0.5 Vh=-0.2)", ".tran 0 1 0 1m"])
    s.directives(x, 864, [".meas tran v12min min V(v12) from 0.1 to 0.13",
                          ".meas tran t_flt find time when V(flt)=1.65 rise=1",
                          ".meas tran dt_flt param t_flt-0.8001",
                          ".meas tran fltpre max V(flt) from 0 to 0.79",
                          ".options plotwinsize=0",
                          ".save V(v12) V(starter) V(soc12) V(vpack) V(bus) V(soc48) V(flt) V(en) I(Lcab) I(Lharn) "
                          "V(u1:s) V(u1:ocv) V(u2:fl) V(u2:x) V(u2:pre) I(u2:Vsw)"], 1)
    s.save("demo_battery.asc")


def demo_dcdc():
    """48 V source + feed -> DCDC48_12 -> 12 V battery and a switched 12 V load."""
    s = Sch(1700, 1000)
    y = 224
    vs = s.part("voltage", 48, 240, name="V48", value=48); s.gnd(vs[1])
    lf = s.part("ind", 208, 208, "R90", "Lfeed", "2u", line="Rser=10m")
    s.wire(vs[0], (48, y), lf[1])
    rb = s.part("res", 320, 208, name="Rbl", value="4.7k"); s.gnd(rb[1])
    s.mid(lf[0], rb[0], "vin")
    u = s.part("DCDC48_12", 640, 256, name="U1", line="VSET=14 PRATED=700")
    s.wire(rb[0], u[0]); s.gnd(u[2]); s.stub(u[3], (-1, 0), "en"); s.stub(u[4], (1, 0), "pg")
    lh = s.part("ind", 944, 208, "R90", "Lh12", "0.5u", line="Rser=2m")
    s.mid(u[1], lh[1], "v12")
    b12 = s.part("BATTERY", 1072, 304, name="U2", line="VNOM=12 SOC0=0.6")
    s.mid(lh[0], b12[0], "b12"); s.gnd(b12[1]); s.stub(b12[2], (1, 0), "soc12")
    rl = s.part("res", 1312, 208, name="Rbase", value="1.4"); s.wire(b12[0], rl[0]); s.gnd(rl[1])
    rp = s.part("res", 1456, 208, name="Rptc", value="0.3"); s.wire(rl[0], rp[0])
    sp = s.part("sw", 1472, 288, name="Sptc", value="SLD"); s.wire(rp[1], sp[0]); s.gnd(sp[1])
    s.stub(sp[2], (-1, 0), "ptc"); s.gnd(sp[3])
    s.sources([("Ven", "en", "PWL(0 0 1m 0 1.01m 3.3)"), ("Vptc", "ptc", "PWL(0 0 20m 0 20.01m 1 40m 1 40.01m 0)")],
              96, 592)
    s.text(32, -40, "700 W 48/12 V DC/DC: EN at 1 ms (soft-start onto the pre-biased 12 V battery, "
                    "then current limit), 40 A PTC load 20..40 ms", 2)
    s.text(32, 0, "Probe: V(u1:il) inductor current, V(u1:vref), V(u1:run), V(u1:ploss) | V(u2:s) 12 V battery SOC", 1)
    x = s.directives(32, 808, [".include ../models/DCDC48_12_beh.lib", ".include ../models/BATTERY_beh.lib",
                               ".model SLD SW(Ron=0.1m Roff=1Meg Vt=0.5 Vh=-0.2)", ".tran 0 60m 0 5u"])
    s.directives(x, 808, [".meas tran il_cl avg V(u1:il) from 10m to 19m",
                          ".meas tran iin avg -I(Lfeed) from 10m to 19m",
                          ".meas tran v12_ptc avg V(b12) from 30m to 39m",
                          ".options plotwinsize=0",
                          ".save V(vin) V(v12) V(b12) V(pg) V(soc12) I(Lfeed) I(Lh12) V(u1:il) V(u1:vref) V(u1:run) "
                          "V(u1:ploss)"], 1)
    s.save("demo_dcdc.asc")


# ---------------------------------------------------------------------------
#  examples/
# ---------------------------------------------------------------------------
def ex01_fiu_short():
    """Fail-operational dual 48 V supply: 800/48 V DC/DC - eFuses A..D - 48 V battery,
    XBW load fed from AB and CD; FIU shorts to GND at CD, AB and BC (one scenario each);
    selectivity check."""
    s = Sch(5600, 1900)
    y = 320                                   # power rail
    # --- 800 V source and 800/48 V DC/DC (averaged buck model, re-parameterized)
    # WIRE instances: Value hidden (the symbol says WIRE), name and SpiceLine
    # above-left (R0) or left (R90) of the wire, clear of the T and GND pins
    wire_r0 = ["WINDOW 0 -28 -64 Right 2", "WINDOW 3 0 0 Invisible 2", "WINDOW 39 -28 -40 Right 1"]
    wire_r90 = ["WINDOW 0 -14 72 VRight 2", "WINDOW 3 0 0 Invisible 2", "WINDOW 39 12 72 VRight 1"]
    vhv = s.part("voltage", -192, y - 16, name="Vhv", value=800, line="Rser=50m")
    s.gnd(vhv[1])
    dc = s.part("DCDC48_12", 176, y + 32, name="DCDC",
                line="VSET=48.2 PRATED=3000 VIN_ON=550 VIN_OFF=500 VIN_OVP=920 VOVP_HYS=20 "
                     "T_SS=1m P0=15 RLOSS=5m KSW=0.3m DCRUN=1")
    s.mid(vhv[0], dc[0], "hv")
    s.gnd(dc[2]); s.stub(dc[3], (-1, 0), "en"); s.stub(dc[4], (1, 0), "pg_dc")
    wdc = s.part("WIRE", 464, y, name="WDC", line="LEN=1 CSA=10", extra=wire_r0)
    s.mid(dc[1], wdc[0], "vdc"); s.stub(wdc[2], (0, -1), "tw_dc"); s.gnd(wdc[3])
    cpa = s.part("cap", 640, y, name="Cpa", value="100u", line="Rser=30m"); s.gnd(cpa[1])
    tva = s.part("diode", 880, y + 64, "R180", "Dta", "EF_TVS58V"); s.gnd(tva[0])
    s.mid(wdc[1], cpa[0], "pa"); s.wire(cpa[0], tva[1])
    # --- PDU: four bidirectional eFuses, each = two EFUSE48_MOD channels back to back
    #     (common source "m*"). "R" senses and interrupts current flowing to the right
    #     (towards the battery), "L" (mirrored) current flowing to the left.
    #     Time grading per direction: the channel nearest the fault is the fastest.
    grade = {"AR": "TD3", "AL": "TD0", "BR": "TD2", "BL": "TD1",
             "CR": "TD1", "CL": "TD2", "DR": "TD0", "DL": "TD3"}
    us = {"TD0": 3, "TD1": 9, "TD2": 15, "TD3": 21}
    nodes = ["pa", "ab", "bc", "cd", "pd"]
    x_vbat_r = [1024, 2048, 3072, 4096]       # VBAT pin of each "R" channel
    rail = [tva[1]]
    for k, e in enumerate("ABCD"):
        xr = x_vbat_r[k] + 144
        xl = xr + 352
        chans = []
        for nm, x, rot in ((e + "R", xr, "R0"), (e + "L", xl, "M0")):
            td = grade[nm]
            p = s.part("EFUSE48_MOD", x, y + 96, rot, nm,
                       line=f"OVC_CODE=22 HSC_CODE=15 VDS_CODE=30 C_SLEW={{CSLEW}} HSC_DLY={{{td}}} VDS_DLY={{{td}}}",
                       extra=["WINDOW 39 0 0 Invisible 2", "WINDOW 3 0 0 Invisible 2"])
            s.gnd(p[2]); s.stub(p[3], (-1, 0) if rot == "R0" else (1, 0), "en"); s.gnd(p[4]); s.gnd(p[5])
            arrow = "->" if nm.endswith("R") else "<-"
            s.text(x - 112, y + 288, f"{nm}: senses {arrow}  trip delay {us[td]} us", 1)
            chans.append(p)
        (r_, l_) = chans
        s.wire(r_[1], l_[1]); s.flag(r_[1], "m" + e.lower())
        rail.append(r_[0]); s.wire(rail[-2], r_[0])
        rail.append(l_[0]); s.flag(l_[0], nodes[k + 1])
        s.text(xr - 32, y - 96, f"eFuse {e}", 2)
    s.wire(rail[-1], (4864, y))
    s.box(992, y - 128, 4768, y + 304)
    s.text(1000, y - 160, "PDU: 4 bidirectional eFuses = 8 VNF1048F channels (EFUSE48_MOD), back to back, "
                          "same thresholds (INOM 39 A, hard short 160 A, VDS 1.8 V), graded hard-short / VDS delays", 1)
    # --- battery side
    tvd = s.part("diode", 4912, y + 64, "R180", "Dtd", "EF_TVS58V"); s.gnd(tvd[0])
    cpd = s.part("cap", 5056, y, name="Cpd", value="100u", line="Rser=30m"); s.gnd(cpd[1])
    wb = s.part("WIRE", 5248, y, name="WBAT", line="LEN=1 CSA=10", extra=wire_r0)
    s.wire((4864, y), tvd[1], cpd[0], wb[0]); s.stub(wb[2], (0, -1), "tw_bat"); s.gnd(wb[3])
    bat = s.part("BATTERY", 5472, y + 80, name="BAT", line="VNOM=48 SOC0=0.6")
    s.mid(wb[1], bat[0], "pb"); s.gnd(bat[1]); s.stub(bat[2], (1, 0), "soc")
    # --- XBW load: 2 m cables from AB and CD, ideal-diode ORing, 1 mF, 1 kW
    ld = []
    for nm, x, net in (("1", 1760, "ab"), ("2", 3776, "cd")):
        s.wire((x, y), (x, y + 320))
        w = s.part("WIRE", x, y + 400, "R90", "W" + nm, line="LEN=2 CSA=2.5", extra=wire_r90)
        s.stub(w[2], (1, 0), "tw" + nm); s.gnd(w[3])
        d = s.part("diode", x - 16, y + 544, name="Dor" + nm, value="DOR")
        s.mid(w[1], d[0], "l" + nm)
        ld.append(d[1])
    s.wire(ld[0], (1760, y + 640), (3776, y + 640), ld[1])
    s.flag((2848, y + 640), "rail")
    cx = s.part("cap", 2592, y + 640, name="Cxbw", value="1m", line="Rser=10m"); s.gnd(cx[1])
    bl = s.part("bi", 2848, y + 640, name="Bxbw",
                value="I={PLOAD}*limit((time-0.1m)/0.3m,0,1)/limit(V(rail),20,1k)*limit(V(rail)/20,0,1)")
    s.gnd(bl[1])
    s.box(1648, y + 560, 4032, y + 800)
    s.text(2016, y + 520, "XBW load (fail-operational, dual 48 V supply): ideal-diode ORing, 1 mF, 1 kW constant power "
                          "(ramped in 0.1..0.4 ms)", 1)
    # --- FIUs: one short to GND per bus node, each its own scenario (FID)
    for net, x, fid in (("AB", 1952, 2), ("BC", 2880, 3), ("CD", 3968, 1)):
        s.wire((x, y), (x, y + 272))
        fiu = s.part("FI_SHORT", x, y + 336, name="FIU_" + net,
                     line=f"ID={fid} FID={{FID}} RF=10m TF={{TFAULT}} TTR=1u")
        s.gnd(fiu[1])
        s.text(x - 64, y + 448, f"FIU {net} -> GND (FID {fid})", 1)
    # --- enable (eFuses and DC/DC): on from the DC operating point
    ven = s.part("voltage", -192, y + 336, name="Ven", value=3.3); s.stub(ven[0], (0, -1), "en"); s.gnd(ven[1])
    # --- title and notes
    s.text(32, -160, "ex01 - FIU short circuits on a fail-operational dual 48 V supply: is each fault isolated "
                     "selectively, and does the XBW load keep its power?", 2)
    s.text(32, -120, "800 V -> 48 V DC/DC --1 m-- [A]-AB-[B]-BC-[C]-CD-[D] --1 m-- 48 V battery | XBW load 1 kW / "
                     "1 mF on AB and CD (2 m each) | 10 mOhm short to GND at 1 ms", 1)
    s.text(32, -96, "Expected: FID 1 short CD: C (->) and D (<-) open, load on AB | FID 2 short AB: A (->) and B (<-) "
                    "open, load on CD | FID 3 short BC: B (->) and C (<-) open, load on both | FID 0 golden: "
                    "nothing trips | load rail always 36..52 V", 1)
    s.text(32, -72, "Starts in steady state (eFuses on, DC/DC running in the DC operating point). "
                    "Probe: V(cr:xu:flt) fault latch, V(cr:xu:hsht) hard short, V(ar:xu:xhcd:t) "
                    "hard-short timer (trips at 0.5), V(dcdc:il), I(w1:Vs).", 1)
    # --- directives
    yd = 1200
    for k, inc in enumerate(("VNF1048F_beh.lib", "DCDC48_12_beh.lib", "BATTERY_beh.lib", "HARNESS_beh.lib",
                             "FAULTS_beh.lib")):
        s.text(32, yd + 32 * k, f".include ../models/{inc}", 2, True)
    s.text(32, yd + 176, ".param FID=1 TFAULT=1m TSTOP=2.5m PLOAD=1k CSLEW=4.7n", 2, True)
    s.text(32, yd + 208, ".param T0=3u TS=6u TD0={T0} TD1={T0+TS} TD2={T0+2*TS} TD3={T0+3*TS}", 2, True)
    s.text(32, yd + 240, ".step param FID list 0 1 2 3", 2, True)
    s.text(32, yd + 272, ".model DOR D(Ron=5m Roff=1Meg Vfwd=20m)", 2, True)
    s.text(32, yd + 304, ".tran 0 {TSTOP} 0 0.5u", 2, True)
    s.text(32, yd + 336, ".options plotwinsize=0", 2, True)
    s.text(32, yd + 376, "FID: 0 = golden run, 1 = short CD, 2 = short AB, 3 = short BC (to GND)", 1)
    s.text(32, yd + 400, "CSLEW: eFuse gate slew capacitor; with >= 22 nF A and B trip as well on the CD short "
                         "(see README)", 1)
    ch = ["ar", "al", "br", "bl", "cr", "cl", "dr", "dl"]
    mid = {c: "m" + c[0] for c in ch}
    meas = [".meas tran railpre avg V(rail) from {TFAULT-0.2m} to {TFAULT}",
            ".meas tran railmin min V(rail) from {TFAULT} to {TSTOP}",
            ".meas tran railmax max V(rail) from {TFAULT} to {TSTOP}",
            ".meas tran rail_end avg V(rail) from {TSTOP-0.5m} to {TSTOP}",
            ".meas tran ab_end avg V(ab) from {TSTOP-0.5m} to {TSTOP}",
            ".meas tran bc_end avg V(bc) from {TSTOP-0.5m} to {TSTOP}",
            ".meas tran cd_end avg V(cd) from {TSTOP-0.5m} to {TSTOP}",
            ".meas tran iw1_end avg I(w1:Vs) from {TSTOP-0.5m} to {TSTOP}",
            ".meas tran iw2_end avg I(w2:Vs) from {TSTOP-0.5m} to {TSTOP}",
            ".meas tran idc_end avg I(wdc:Vs) from {TSTOP-0.5m} to {TSTOP}",
            ".meas tran ibat_end avg I(wbat:Vs) from {TSTOP-0.5m} to {TSTOP}",
            ".meas tran ipk_dc max I(wdc:Vs) from {TFAULT} to {TFAULT+0.1m}",
            ".meas tran ipk_bat max -I(wbat:Vs) from {TFAULT} to {TFAULT+0.1m}",
            ".meas tran vpa_max max V(pa) from {TFAULT} to {TSTOP}",
            ".meas tran vab_max max V(ab) from {TFAULT} to {TSTOP}",
            ".meas tran vcd_max max V(cd) from {TFAULT} to {TSTOP}",
            ".meas tran vpd_max max V(pd) from {TFAULT} to {TSTOP}",
            ".meas tran run_min min V(dcdc:run) from {TFAULT} to {TSTOP}",
            ".meas tran ildc_max max V(dcdc:il) from {TFAULT} to {TSTOP}",
            ".meas tran t52r find time when V(rail)=52 rise=1",
            ".meas tran t52f find time when V(rail)=52 fall=last",
            ".meas tran dt52 param t52f-t52r"]
    for c in ch:
        meas += [f".meas tran flt_{c} max V({c}:xu:flt)",
                 f".meas tran t_{c} find time when V({c}:xu:flt)=0.5 rise=1",
                 f".meas tran dt_{c} param t_{c}-TFAULT",
                 f".meas tran h_{c} max V({c}:xu:xhcd:t) from {{TFAULT}} to {{TSTOP}}",
                 f".meas tran v_{c} max V({c}:xu:xvdd:t) from {{TFAULT}} to {{TSTOP}}",
                 f".meas tran vds_{c} max V({c}:drn)-V({mid[c]}) from {{TFAULT}} to {{TSTOP}}",
                 f".meas tran tj_{c} max V({c}:tjf)"]
    for k, mline in enumerate(meas):
        s.text(1600 + 1040 * (k // 19), yd + 24 * (k % 19), mline, 1, True)
    saves = [".save V(hv) V(vdc) V(pa) V(ma) V(ab) V(mb) V(bc) V(mc) V(cd) V(md) V(pd) V(pb) V(l1) V(l2) V(rail)",
             ".save I(wdc:Vs) I(wbat:Vs) I(w1:Vs) I(w2:Vs) V(dcdc:il) V(dcdc:run)"]
    for c in ch:
        saves.append(f".save V({c}:xu:flt) V({c}:xu:hsht) V({c}:xu:vdsmax) V({c}:xu:gcmd) "
                     f"V({c}:xu:xhcd:t) V({c}:xu:xvdd:t) V({c}:drn) V({c}:tjf)")
    for k, sline in enumerate(saves):
        s.text(32, yd + 432 + 24 * k, sline, 1, True)
    s.save("ex01_fiu_short_selectivity.asc", EXAMPLES)


if __name__ == "__main__":
    demo_module()
    app_discrete()
    demo_battery()
    demo_dcdc()
    ex01_fiu_short()
