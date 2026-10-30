"""Generate the demo LTspice schematics (.asc) in schematics/.

Pin offsets of the built-in symbols and the rotation convention
(R90: (x,y)->(-y,x), R270: (x,y)->(y,-x)) were verified with `LTspice -netlist`.
Re-run after changing the layout:  python3 tools/make_schematics.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "schematics")


def write_if_changed(path, text):
    """Leave an unchanged file untouched (its date tells validate.py whether the
    simulation results are newer than the bench)."""
    if os.path.isfile(path) and open(path).read() == text:
        return
    open(path, "w").write(text)

ROT = {"R0": lambda x, y: (x, y), "R90": lambda x, y: (-y, x),
       "R180": lambda x, y: (-x, -y), "R270": lambda x, y: (y, -x)}
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

    def text(self, x, y, s, size=2, directive=False):
        self.L.append(f"TEXT {x} {y} Left {size} {'!' if directive else ';'}{s}")

    def save(self, fname):
        os.makedirs(OUT, exist_ok=True)
        write_if_changed(os.path.join(OUT, fname), "\n".join(self.L) + "\n")
        print("  ->", fname)


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


if __name__ == "__main__":
    demo_module()
    app_discrete()
    demo_battery()
    demo_dcdc()
