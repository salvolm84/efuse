"""Generate the demo LTspice schematics (.asc) in schematics/.

Pin offsets of the built-in symbols and the rotation convention
(R90: (x,y)->(-y,x), R270: (x,y)->(y,-x)) were verified with `LTspice -netlist`.
Re-run after changing the layout:  python3 tools/make_schematics.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "schematics")

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
}


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
        open(os.path.join(OUT, fname), "w").write("\n".join(self.L) + "\n")
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
    tv = s.part("diode", 448, 288, "R180", "Dtvs", "TVS_58V")
    s.gnd(tv[0])
    x1 = s.part("EFUSE48_MOD", 640, 320, name="U1",
                line="RSENSE=1m OVC_CODE=13 HSC_CODE=12 VDS_CODE=14 NTC_CODE=4 TNOM_CODE=0")
    s.wire(vb[0], (32, y), rb[1]); s.wire(rb[0], lb[1])
    s.wire(lb[0], cb[0]); s.wire(cb[0], tv[1]); s.wire(tv[1], x1[0])
    s.flag(lb[0], "vbat")
    s.gnd(x1[2])
    df = s.part("schottky", 832, 288, "R180", "Dfw", "SCH_100V")
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
    tvs = s.part("diode", 448, 208, "R180", "Dtvs", "TVS_58V"); s.gnd(tvs[0]); s.flag(tvs[1], "vbat")
    # --- shunt and FET (top power path)
    rs = s.part("res", 1072, 112, "R90", "Rsense", "1m")
    s.flag(rs[1], "vbat"); s.flag(rs[0], "drn")
    m1 = s.part("nmos", 1184, 112, name="M1", value="FET100V_2M")
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
    df = s.part("schottky", 1648, 208, "R180", "Dfw", "SCH_100V"); s.gnd(df[0]); s.flag(df[1], "out")
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


if __name__ == "__main__":
    demo_module()
    app_discrete()
