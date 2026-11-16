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
    **{n: [(0, -64), (0, 64)] for n in ("TP_STEP", "TP_CRANK", "TP_LOADDUMP", "TP_ISO7637", "TP_RIPPLE")},
}
# reference parameter sets: same pins as their base models
PINS.update(BAT12_VARTA_E39=PINS["BATTERY"], BAT48_A123_8AH=PINS["BATTERY_BMS"],
            DCDC_TOSHIBA_RD210=PINS["DCDC48_12"])


class Sch:
    def __init__(self, w=2400, h=1400):
        self.L = ["Version 4", f"SHEET 1 {w} {h}"]

    def part(self, sym, x, y, rot="R0", name=None, value=None, line=None, extra=()):
        self.L.append(f"SYMBOL {sym} {x} {y} {rot}")
        if rot in ("R90", "R270") and sym in ("res", "ind", "cap", "diode", "schottky", "zener"):
            self.L += ["WINDOW 0 0 56 VBottom 2", "WINDOW 3 32 56 VTop 2"]
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
            self.L.append(f"WIRE {a[0]} {a[1]} {b[0]} {b[1]}")

    def flag(self, p, net):
        self.L.append(f"FLAG {p[0]} {p[1]} {net}")

    def gnd(self, p):
        self.flag(p, "0")

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
    s = Sch(1700, 900)
    y = 224  # power rail
    vb = s.part("voltage", 32, 240, name="Vbat", value=48)
    s.gnd(vb[1])
    rb = s.part("res", 192, 208, "R90", "Rbat", "10m")
    lb = s.part("ind", 288, 208, "R90", "Lbat", "1u")
    cb = s.part("cap", 336, y, name="Cbus", value="100u", line="Rser=30m")
    s.gnd(cb[1])
    tv = s.part("diode", 448, 288, "R180", "Dtvs", "EF_TVS58V")
    s.gnd(tv[0])
    x1 = s.part("EFUSE48_MOD", 640, 320, name="U1",
                line="RSENSE=1m OVC_CODE=13 HSC_CODE=12 VDS_CODE=14 NTC_CODE=4 TNOM_CODE=0")
    s.wire(vb[0], (32, y), rb[1]); s.wire(rb[0], lb[1])
    s.wire(lb[0], cb[0]); s.wire(cb[0], tv[1]); s.wire(tv[1], x1[0])
    s.flag(lb[0], "vbat")
    s.gnd(x1[2])
    df = s.part("schottky", 832, 288, "R180", "Dfw", "EF_SCH100V")
    s.gnd(df[0])
    lh = s.part("ind", 944, 208, "R90", "Lh", "1u")
    rh = s.part("res", 1040, 208, "R90", "Rh", "10m")
    cl = s.part("cap", 1088, y, name="Cload", value="220u", line="Rser=20m")
    s.gnd(cl[1])
    rl = s.part("res", 1184, 208, name="Rload", value=4.8)
    s.gnd(rl[1])
    sw = s.part("sw", 1296, 208, name="Ssc", value="SSHORT")
    s.gnd(sw[1]); s.gnd(sw[3]); s.flag(sw[2], "sc")
    s.wire(x1[1], df[1]); s.wire(df[1], lh[1]); s.wire(lh[0], rh[1]); s.wire(rh[0], cl[0])
    s.wire(cl[0], rl[0]); s.wire(rl[0], sw[0])
    s.flag(x1[1], "out"); s.flag(rh[0], "load")
    for k, (net, pin) in enumerate([("en", 3), ("byp", 4), ("clr", 5)]):
        s.flag(x1[pin], net)
    s.flag(x1[6], "diag"); s.flag(x1[7], "cs"); s.flag(x1[8], "tfet")
    srcs = [("Ven", "en", "PWL(0 0 0.5m 0 0.501m 3.3)"), ("Vbyp", "byp", "0"),
            ("Vclr", "clr", "PWL(0 0 6m 0 6.001m 3.3 6.05m 3.3 6.051m 0 10m 0 10.001m 3.3 10.05m 3.3 10.051m 0)"),
            ("Vsc", "sc", "PWL(0 0 3m 0 3.0001m 1 9m 1 9.0001m 0)")]
    for k, (nm, net, val) in enumerate(srcs):
        p = s.part("voltage", 160 + 352 * k, 608, name=nm, value=val)
        s.flag(p[0], net); s.gnd(p[1])
    s.text(32, -40, "48 V eFuse channel (VNF1048F behavioral, EFUSE48_MOD): start-up, hard short at 3 ms, "
                    "CLR retry at 6 ms, short removed 9 ms, CLR 10 ms", 2)
    s.text(32, 0, "Probe internal status: V(u1:xu:hsht) V(u1:xu:fusel) V(u1:xu:fd) V(u1:xu:gcmd)  (LTspice 24+; XVII: V(u1:xu:...))", 1)
    s.text(32, 776, ".include ../models/VNF1048F_beh.lib", 2, True)
    s.text(32, 808, ".model SSHORT SW(Ron=5m Roff=1Meg Vt=0.5 Vh=-0.2)", 2, True)
    s.text(32, 840, ".tran 0 12m 0 0.2u", 2, True)
    s.text(704, 776, ".meas tran t_trip find time when V(u1:xu:hsht)=0.5 rise=1", 1, True)
    s.text(704, 800, ".meas tran ipk max -I(Lh) from 3m to 3.1m", 1, True)
    s.text(704, 824, ".meas tran vbatpk max V(vbat) from 3m to 3.2m", 1, True)
    s.text(704, 848, ".options plotwinsize=0", 1, True)
    s.text(704, 872, ".save V(vbat) V(out) V(load) V(diag) V(cs) V(tfet) I(Lh) I(Lbat) V(u1:hsg) V(u1:g) "
                     "V(u1:drn) V(u1:xu:hsht) V(u1:xu:fusel) V(u1:xu:fd) V(u1:xu:gcmd)", 1, True)
    s.save("demo_efuse48_module.asc")


def app_discrete():
    """Discrete application circuit around the VNF1048F symbol (DS13084 Fig. 16 + slew network)."""
    s = Sch(2000, 1300)
    # --- battery and input
    vb = s.part("voltage", 48, 160, name="Vbat", value=48); s.gnd(vb[1])
    rb = s.part("res", 224, 128, "R90", "Rbat", "10m")
    s.wire(vb[0], (48, 144), rb[1]); s.flag(rb[0], "vbat")
    cvs1 = s.part("polcap", 272, 144, name="Cvs1", value="100u", line="Rser=30m"); s.gnd(cvs1[1])
    s.flag(cvs1[0], "vbat")
    cvs2 = s.part("cap", 352, 144, name="Cvs2", value="100n"); s.gnd(cvs2[1]); s.flag(cvs2[0], "vbat")
    tvs = s.part("diode", 448, 208, "R180", "Dtvs", "EF_TVS58V"); s.gnd(tvs[0]); s.flag(tvs[1], "vbat")
    # --- shunt and FET (top power path)
    rs = s.part("res", 1072, 112, "R90", "Rsense", "1m")
    s.flag(rs[1], "vbat"); s.flag(rs[0], "drn")
    m1 = s.part("nmos", 1184, 112, name="M1", value="EF_FET100V")
    s.flag(m1[0], "drn"); s.flag(m1[1], "g"); s.flag(m1[2], "out")
    # --- controller
    u = s.part("VNF1048F", 768, 576, name="U1",
               line="OVC_CODE=13 HSC_CODE=12 VDS_CODE=14 NTC_CODE=4 TNOM_CODE=0 FUSE_MODE=0 CPON=1")
    nets = ["vbat", "cp", "vbat", "drn", "hsg", "out", "ntc", "ntcm", "0", "diag", "en", "byp", "clr", "cs"]
    for p, n in zip(u, nets):
        s.flag(p, n)
    ccp = s.part("cap", 448, 352, name="Ccp", value="470n"); s.flag(ccp[0], "cp"); s.flag(ccp[1], "vbat")
    # --- gate network
    rgon = s.part("res", 1168, 336, "R90", "Rgon", "2.2k"); s.flag(rgon[1], "hsg"); s.flag(rgon[0], "g")
    rgof = s.part("res", 1168, 432, "R90", "Rgoff", "10"); s.flag(rgof[1], "hsg"); s.flag(rgof[0], "goff")
    dgof = s.part("diode", 1232, 432, "R90", "Dgoff", "EF_DSW")
    s.flag(dgof[0], "g"); s.flag(dgof[1], "goff")
    csl = s.part("cap", 1296, 336, name="Cslew", value="47n"); s.flag(csl[0], "g"); s.gnd(csl[1])
    rgb = s.part("res", 1392, 320, name="Rgb", value="47k"); s.flag(rgb[0], "g"); s.flag(rgb[1], "out")
    dz = s.part("zener", 1488, 400, "R180", "Dzgs", "EF_DZ15"); s.flag(dz[1], "g"); s.flag(dz[0], "out")
    # --- NTC bridge (NTC on the drain pad, temperature from source Vtpad)
    ntc = s.part("NTC10K_ST", 1216, 656, name="Xntc"); s.flag(ntc[0], "drn"); s.flag(ntc[1], "ntc")
    s.flag(ntc[2], "tpad"); s.gnd(ntc[3])
    rtr = s.part("res", 1360, 640, "R90", "Rtref", "10k"); s.flag(rtr[1], "ntc"); s.flag(rtr[0], "ntcm")
    vtp = s.part("voltage", 1504, 640, name="Vtpad", value="PWL(0 25 1 25)"); s.flag(vtp[0], "tpad")
    s.gnd(vtp[1])
    # --- logic side
    v33 = s.part("voltage", 1184, 816, name="V33", value=3.3); s.flag(v33[0], "v33"); s.gnd(v33[1])
    rpu = s.part("res", 1312, 800, name="Rpu", value="4.7k"); s.flag(rpu[0], "v33"); s.flag(rpu[1], "diag")
    srcs = [("Ven", "en", "PWL(0 0 0.5m 0 0.501m 3.3)"), ("Vbyp", "byp", "0"),
            ("Vclr", "clr", "PWL(0 0 80m 0 80.001m 3.3 80.1m 3.3 80.101m 0)")]
    for k, (nm, net, val) in enumerate(srcs):
        p = s.part("voltage", 64 + 208 * k, 816, name=nm, value=val); s.flag(p[0], net); s.gnd(p[1])
    # --- load side
    df = s.part("schottky", 1648, 208, "R180", "Dfw", "EF_SCH100V"); s.gnd(df[0]); s.flag(df[1], "out")
    lh = s.part("ind", 1808, 112, "R90", "Lh", "1u"); s.flag(lh[1], "out"); s.flag(lh[0], "load")
    cl = s.part("cap", 1840, 144, name="Cload", value="220u", line="Rser=20m"); s.flag(cl[0], "load")
    s.gnd(cl[1])
    rl = s.part("res", 1936, 128, name="Rload", value=4.8); s.flag(rl[0], "load"); s.gnd(rl[1])
    ro = s.part("res", 2032, 128, name="Rovl", value=2.4); s.flag(ro[0], "load"); s.flag(ro[1], "sovl")
    so = s.part("sw", 2032, 224, name="Sovl", value="SOVL"); s.flag(so[0], "sovl"); s.gnd(so[1])
    s.flag(so[2], "ovl"); s.gnd(so[3])
    vo = s.part("voltage", 1920, 416, name="Vovl", value="PWL(0 0 5m 0 5.001m 1 75m 1 75.001m 0)")
    s.flag(vo[0], "ovl"); s.gnd(vo[1])
    s.text(48, -64, "VNF1048F behavioral - discrete 48 V application (DS13084 Fig. 16 + gate slew network)", 2)
    s.text(48, -24, "0.5 ms ON (10 A) | 5 ms overload +20 A -> I2t trip after tNOM/16 = 62.5 ms | "
                    "75 ms overload removed | 80 ms CLR -> restart", 1)
    s.text(48, 992, ".include ../models/VNF1048F_beh.lib", 2, True)
    s.text(48, 1024, ".model SOVL SW(Ron=2m Roff=1Meg Vt=0.5 Vh=-0.2)", 2, True)
    s.text(48, 1056, ".tran 0 100m 0 2u", 2, True)
    s.text(48, 1088, ".options plotwinsize=0", 2, True)
    s.text(704, 992, ".meas tran t_fuse find time when V(u1:fusel)=0.5 rise=1", 1, True)
    s.text(704, 1016, ".meas tran dt_fuse param t_fuse-5m", 1, True)
    s.text(704, 1040, ".meas tran iovl avg -I(Lh) from 20m to 30m", 1, True)
    s.text(704, 1064, ".meas tran vout_end avg V(out) from 95m to 100m", 1, True)
    s.text(704, 1088, ".save V(vbat) V(drn) V(out) V(load) V(hsg) V(g) V(cp) V(diag) V(cs) I(Lh) "
                      "V(u1:fusel) V(u1:fd) V(u1:gcmd) V(u1:xa)", 1, True)
    s.save("app_vnf1048f_discrete.asc")


def demo_battery():
    """12 V battery with a starter-like load and a 48 V pack with BMS (pre-charge, load, short)."""
    s = Sch(1900, 1000)
    y = 224
    # --- 12 V: battery, terminal cap, cable, starter (locked rotor 8 mOhm, then 40 mOhm)
    b12 = s.part("BATTERY", 112, 320, name="U1", line="VNOM=12 SOC0=0.8 TBAT=-18")
    s.gnd(b12[1]); s.flag(b12[2], "soc12")
    c12 = s.part("cap", 240, y, name="C12", value="1m", line="Rser=0.1"); s.gnd(c12[1])
    lc = s.part("ind", 384, 208, "R90", "Lcab", "1u")
    s.wire(b12[0], (112, y), c12[0]); s.wire(c12[0], lc[1]); s.flag(b12[0], "v12")
    rlr = s.part("res", 416, 208, name="Rlr", value="8m"); s.wire(lc[0], rlr[0])
    slr = s.part("sw", 416, 304, name="Slr", value="SST"); s.wire(rlr[1], slr[0]); s.gnd(slr[1])
    s.flag(slr[2], "st1"); s.gnd(slr[3])
    rrun = s.part("res", 528, 208, name="Rrun", value="40m"); s.wire(rlr[0], rrun[0])
    srun = s.part("sw", 528, 304, name="Srun", value="SST"); s.wire(rrun[1], srun[0]); s.gnd(srun[1])
    s.flag(srun[2], "st2"); s.gnd(srun[3])
    s.flag(lc[0], "starter")
    # --- 48 V: pack with BMS, harness, bus, load, short
    b48 = s.part("BATTERY_BMS", 1008, 336, name="U2", line="VNOM=48 SOC0=0.8 T_PRE=0.3 R_PRE=10")
    s.gnd(b48[1]); s.flag(b48[2], "soc48"); s.flag(b48[3], "en"); s.flag(b48[4], "flt")
    lh = s.part("ind", 1152, 208, "R90", "Lharn", "2u")
    s.wire(b48[0], (1008, y), lh[1]); s.flag(b48[0], "vpack")
    cb = s.part("cap", 1184, y, name="Cbus", value="10m", line="Rser=5m"); s.gnd(cb[1])
    s.wire(lh[0], cb[0]); s.flag(cb[0], "bus")
    rld = s.part("res", 1312, 208, name="Rload", value=1); s.wire(cb[0], rld[0])
    sld = s.part("sw", 1312, 304, name="Sload", value="SLD"); s.wire(rld[1], sld[0]); s.gnd(sld[1])
    s.flag(sld[2], "ld"); s.gnd(sld[3])
    rsc = s.part("res", 1440, 208, name="Rsc", value="5m"); s.wire(rld[0], rsc[0])
    ssc = s.part("sw", 1440, 304, name="Ssc", value="SLD"); s.wire(rsc[1], ssc[0]); s.gnd(ssc[1])
    s.flag(ssc[2], "sc"); s.gnd(ssc[3])
    srcs = [("Vst1", "st1", "PWL(0 0 0.1 0 0.1001 1 0.13 1 0.1301 0)"),
            ("Vst2", "st2", "PWL(0 0 0.13 0 0.1301 1 0.6 1 0.6001 0)"),
            ("Ven", "en", "PWL(0 0 10m 0 10.01m 3.3)"),
            ("Vld", "ld", "PWL(0 0 0.5 0 0.5001 1)"),
            ("Vsc", "sc", "PWL(0 0 0.8 0 0.8001 1)")]
    for k, (nm, net, val) in enumerate(srcs):
        p = s.part("voltage", 96 + 320 * k, 592, name=nm, value=val)
        s.flag(p[0], net); s.gnd(p[1])
    s.text(32, -40, "Battery models: 12 V BATTERY at -18 degC with a starter load (locked rotor 0.1 s, cranking "
                    "to 0.6 s) | 48 V BATTERY_BMS: EN 10 ms, pre-charge 0.3 s, 48 A load 0.5 s, short 0.8 s", 2)
    s.text(32, 0, "Probe: V(u1:s) raw SOC, V(u1:ocv) | V(u2:fl) fault latch, V(u2:x) switch state, "
                  "V(u2:pre) pre-charge, I(u2:Vsw) pack current", 1)
    s.text(32, 776, ".include ../models/BATTERY_beh.lib", 2, True)
    s.text(32, 808, ".model SST SW(Ron=0.1m Roff=1k Vt=0.5 Vh=-0.2)", 2, True)
    s.text(32, 840, ".model SLD SW(Ron=0.1m Roff=1Meg Vt=0.5 Vh=-0.2)", 2, True)
    s.text(32, 872, ".tran 0 1 0 1m", 2, True)
    s.text(800, 776, ".meas tran v12min min V(v12) from 0.1 to 0.13", 1, True)
    s.text(800, 800, ".meas tran t_flt find time when V(flt)=1.65 rise=1", 1, True)
    s.text(800, 824, ".meas tran dt_flt param t_flt-0.8001", 1, True)
    s.text(800, 848, ".meas tran fltpre max V(flt) from 0 to 0.79", 1, True)
    s.text(800, 872, ".options plotwinsize=0", 1, True)
    s.text(800, 896, ".save V(v12) V(starter) V(soc12) V(vpack) V(bus) V(soc48) V(flt) V(en) I(Lcab) I(Lharn) "
                     "V(u1:s) V(u1:ocv) V(u2:fl) V(u2:x) V(u2:pre) I(u2:Vsw)", 1, True)
    s.save("demo_battery.asc")


def demo_dcdc():
    """48 V source + feed -> DCDC48_12 -> 12 V battery and a switched 12 V load."""
    s = Sch(1500, 900)
    y = 224
    vs = s.part("voltage", 48, 240, name="V48", value=48); s.gnd(vs[1])
    lf = s.part("ind", 208, 208, "R90", "Lfeed", "2u", line="Rser=10m")
    s.wire(vs[0], (48, y), lf[1]); s.flag(lf[0], "vin")
    rb = s.part("res", 288, 208, name="Rbl", value="4.7k"); s.wire(lf[0], rb[0]); s.gnd(rb[1])
    u = s.part("DCDC48_12", 528, 256, name="U1", line="VSET=14 PRATED=700")
    s.wire(lf[0], (304, y), u[0]); s.gnd(u[2]); s.flag(u[3], "en"); s.flag(u[4], "pg")
    lh = s.part("ind", 768, 208, "R90", "Lh12", "0.5u", line="Rser=2m")
    s.wire(u[1], lh[1]); s.flag(u[1], "v12"); s.flag(lh[0], "b12")
    b12 = s.part("BATTERY", 880, 304, name="U2", line="VNOM=12 SOC0=0.6")
    s.wire(lh[0], (880, y), b12[0]); s.gnd(b12[1]); s.flag(b12[2], "soc12")
    rl = s.part("res", 992, 208, name="Rbase", value="1.4"); s.wire((880, y), rl[0]); s.gnd(rl[1])
    rp = s.part("res", 1104, 208, name="Rptc", value="0.3"); s.wire(rl[0], rp[0])
    sp = s.part("sw", 1104, 304, name="Sptc", value="SLD"); s.wire(rp[1], sp[0]); s.gnd(sp[1])
    s.flag(sp[2], "ptc"); s.gnd(sp[3])
    srcs = [("Ven", "en", "PWL(0 0 1m 0 1.01m 3.3)"), ("Vptc", "ptc", "PWL(0 0 20m 0 20.01m 1 40m 1 40.01m 0)")]
    for k, (nm, net, val) in enumerate(srcs):
        p = s.part("voltage", 96 + 320 * k, 592, name=nm, value=val); s.flag(p[0], net); s.gnd(p[1])
    s.text(32, -40, "700 W 48/12 V DC/DC: EN at 1 ms (soft-start onto the pre-biased 12 V battery, "
                    "then current limit), 40 A PTC load 20..40 ms", 2)
    s.text(32, 0, "Probe: V(u1:il) inductor current, V(u1:vref), V(u1:run), V(u1:ploss) | V(u2:s) 12 V battery SOC", 1)
    s.text(32, 776, ".include ../models/DCDC48_12_beh.lib", 2, True)
    s.text(32, 808, ".include ../models/BATTERY_beh.lib", 2, True)
    s.text(32, 840, ".model SLD SW(Ron=0.1m Roff=1Meg Vt=0.5 Vh=-0.2)", 2, True)
    s.text(32, 872, ".tran 0 60m 0 5u", 2, True)
    s.text(704, 776, ".meas tran il_cl avg V(u1:il) from 10m to 19m", 1, True)
    s.text(704, 800, ".meas tran iin avg -I(Lfeed) from 10m to 19m", 1, True)
    s.text(704, 824, ".meas tran v12_ptc avg V(b12) from 30m to 39m", 1, True)
    s.text(704, 848, ".options plotwinsize=0", 1, True)
    s.text(704, 872, ".save V(vin) V(v12) V(b12) V(pg) V(soc12) I(Lfeed) I(Lh12) V(u1:il) V(u1:vref) V(u1:run) "
                     "V(u1:ploss)", 1, True)
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
    vhv = s.part("voltage", 96, y - 16, name="Vhv", value=800, line="Rser=50m")
    s.gnd(vhv[1])
    dc = s.part("DCDC48_12", 368, y + 32, name="DCDC",
                line="VSET=48.2 PRATED=3000 VIN_ON=550 VIN_OFF=500 VIN_OVP=920 VOVP_HYS=20 "
                     "T_SS=1m P0=15 RLOSS=5m KSW=0.3m DCRUN=1")
    s.wire(vhv[0], dc[0]); s.flag(vhv[0], "hv")
    s.gnd(dc[2]); s.flag(dc[3], "en"); s.flag(dc[4], "pg_dc")
    wdc = s.part("WIRE", 656, y, name="WDC", line="LEN=1 CSA=10")
    s.wire(dc[1], wdc[0]); s.flag(dc[1], "vdc"); s.flag(wdc[2], "tw_dc"); s.gnd(wdc[3])
    cpa = s.part("cap", 800, y, name="Cpa", value="100u", line="Rser=30m"); s.gnd(cpa[1])
    tva = s.part("diode", 928, y + 64, "R180", "Dta", "EF_TVS58V"); s.gnd(tva[0])
    # --- PDU: four bidirectional eFuses, each = two EFUSE48_MOD channels back to back
    #     (common source "m*"). "R" senses and interrupts current flowing to the right
    #     (towards the battery), "L" (mirrored) current flowing to the left.
    #     Time grading per direction: the channel nearest the fault is the fastest.
    grade = {"AR": "TD3", "AL": "TD0", "BR": "TD2", "BL": "TD1",
             "CR": "TD1", "CL": "TD2", "DR": "TD0", "DL": "TD3"}
    us = {"TD0": 3, "TD1": 9, "TD2": 15, "TD3": 21}
    nodes = ["pa", "ab", "bc", "cd", "pd"]
    x_vbat_r = [1024, 2048, 3072, 4096]       # VBAT pin of each "R" channel
    rail = [(736, y)]
    for k, e in enumerate("ABCD"):
        xr = x_vbat_r[k] + 144
        xl = xr + 352
        chans = []
        for nm, x, rot in ((e + "R", xr, "R0"), (e + "L", xl, "M0")):
            td = grade[nm]
            p = s.part("EFUSE48_MOD", x, y + 96, rot, nm,
                       line=f"OVC_CODE=22 HSC_CODE=15 VDS_CODE=30 C_SLEW={{CSLEW}} HSC_DLY={{{td}}} VDS_DLY={{{td}}}",
                       extra=["WINDOW 39 0 0 Invisible 2"])
            s.gnd(p[2]); s.flag(p[3], "en"); s.gnd(p[4]); s.gnd(p[5])
            arrow = "->" if nm.endswith("R") else "<-"
            s.text(x - 112, y + 264, f"{nm}: senses {arrow}  trip delay {us[td]} us", 1)
            chans.append(p)
        (r_, l_) = chans
        s.wire(r_[1], l_[1]); s.flag(r_[1], "m" + e.lower())
        rail.append(r_[0]); s.wire(rail[-2], r_[0])
        rail.append(l_[0]); s.flag(l_[0], nodes[k + 1])
        s.text(xr - 32, y - 96, f"eFuse {e}", 2)
    s.wire(rail[-1], (4864, y))
    s.flag((736, y), "pa")
    s.box(992, y - 128, 4768, y + 304)
    s.text(1000, y - 160, "PDU: 4 bidirectional eFuses = 8 VNF1048F channels (EFUSE48_MOD), back to back, "
                          "same thresholds (INOM 39 A, hard short 160 A, VDS 1.8 V), graded hard-short / VDS delays", 1)
    # --- battery side
    tvd = s.part("diode", 4880, y + 64, "R180", "Dtd", "EF_TVS58V"); s.gnd(tvd[0])
    cpd = s.part("cap", 4944, y, name="Cpd", value="100u", line="Rser=30m"); s.gnd(cpd[1])
    wb = s.part("WIRE", 5152, y, name="WBAT", line="LEN=1 CSA=10")
    s.wire((4864, y), wb[0]); s.flag(wb[2], "tw_bat"); s.gnd(wb[3])
    bat = s.part("BATTERY", 5376, y + 80, name="BAT", line="VNOM=48 SOC0=0.6")
    s.wire(wb[1], bat[0]); s.flag(bat[0], "pb"); s.gnd(bat[1]); s.flag(bat[2], "soc")
    # --- XBW load: 2 m cables from AB and CD, ideal-diode ORing, 1 mF, 1 kW
    ld = []
    for nm, x, net in (("1", 1856, "ab"), ("2", 3840, "cd")):
        s.wire((x, y), (x, y + 320))
        w = s.part("WIRE", x, y + 400, "R90", "W" + nm, line="LEN=2 CSA=2.5")
        s.flag(w[2], "tw" + nm); s.gnd(w[3]); s.flag(w[1], "l" + nm)
        d = s.part("diode", x - 16, y + 480, name="Dor" + nm, value="DOR")
        ld.append(d[1])
    s.wire(ld[0], (1856, y + 640), (3840, y + 640), ld[1])
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
    ven = s.part("voltage", 96, y + 336, name="Ven", value=3.3); s.flag(ven[0], "en"); s.gnd(ven[1])
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
    s.text(32, yd + 384, "FID: 0 = golden run, 1 = short CD, 2 = short AB, 3 = short BC (to GND) | CSLEW: eFuse "
                         "gate slew capacitor; with >= 22 nF A and B trip as well on the CD short (see README)", 1)
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
        s.text(1440 + 1040 * (k // 19), yd + 24 * (k % 19), mline, 1, True)
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
