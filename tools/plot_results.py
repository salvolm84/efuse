"""Plot the test-bench results into docs/img/*.png.

    python3 tools/plot_results.py            # all test benches
    python3 tools/plot_results.py tb03 tb07  # selected ones

Run the simulations first (tools/run_ltspice.sh testbenches/*.cir).
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ltraw import LTRaw, meas_log  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TB = os.path.join(ROOT, "testbenches")
IMG = os.path.join(ROOT, "docs", "img")

# categorical slots in fixed order (validated reference palette)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": "#b9b8b2", "axes.labelcolor": INK2, "xtick.color": INK2,
    "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6,
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "legend.frameon": False, "legend.fontsize": 8,
})


def raw(name):
    return LTRaw(os.path.join(TB, name + ".raw"))


def panels(n, title, h=2.0, sharex=True):
    fig, ax = plt.subplots(n, 1, sharex=sharex, figsize=(9, 0.6 + h * n))
    fig.suptitle(title, x=0.02, ha="left", fontsize=11, fontweight="bold", color=INK)
    return fig, np.atleast_1d(ax)


def plot(ax, x, y, label, k, **kw):
    ax.plot(x, y, color=C[k], label=label, **kw)


def finish(fig, ax, xlabel, fname):
    for a in ax:
        h, _ = a.get_legend_handles_labels()
        if len(h) > 1:
            a.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    ax[-1].set_xlabel(xlabel)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    os.makedirs(IMG, exist_ok=True)
    fig.savefig(os.path.join(IMG, fname), dpi=110)
    plt.close(fig)
    print("  ->", fname)


def win(t, a, b):
    return (t >= a) & (t <= b)


# ---------------------------------------------------------------------------
def tb01():
    r = raw("tb01_startup_inrush"); t = r["time"] * 1e3
    fig, ax = panels(4, "tb01 - start-up into 220 uF || 4.8 Ohm (slew-controlled inrush)")
    plot(ax[0], t, r["V(vbat)"], "VBAT", 0); plot(ax[0], t, r["V(out)"], "OUT", 1)
    plot(ax[0], t, r["V(x1:cp)"], "CP", 2); plot(ax[0], t, r["V(x1:hsg)"], "HS_GATE", 3)
    ax[0].set_ylabel("V")
    plot(ax[1], t, r["I(Lh)"], "I(load)", 0); ax[1].set_ylabel("A")
    ax[1].axhline(21.8, color=INK2, ls="--", lw=0.8); ax[1].text(0.05, 22.5, "INOM 21.8 A", color=INK2, fontsize=8)
    plot(ax[2], t, r["V(x1:xu:xa)"], "x = I/INOM", 0); plot(ax[2], t, r["V(x1:xu:fd)"], "fuse state fd", 1)
    ax[2].set_ylabel("-")
    plot(ax[3], t, r["V(x1:xu:gcmd)"], "gate command", 0); plot(ax[3], t, r["V(diag)"] / 3.3, "DIAG (norm.)", 1)
    ax[3].set_ylabel("logic")
    finish(fig, ax, "time [ms]", "tb01_startup_inrush.png")


def tb02():
    r = raw("tb02_hard_short"); t = r["time"]
    fig, ax = panels(4, "tb02 - hard short at the load connector (zoom: 10 us before to 40 us after)")
    m = win(t, 2.99e-3, 3.04e-3); tu = (t[m] - 3e-3) * 1e6
    plot(ax[0], tu, r["V(vbat)"][m], "VBAT", 0); plot(ax[0], tu, r["V(out)"][m], "OUT", 1)
    plot(ax[0], tu, r["V(x1:g)"][m], "FET gate", 2); plot(ax[0], tu, r["V(x1:drn)"][m], "FET drain", 3)
    ax[0].set_ylabel("V")
    plot(ax[1], tu, r["I(Lh)"][m], "I(FET / harness)", 0); plot(ax[1], tu, r["I(Lbat)"][m], "I(battery)", 1)
    ax[1].axhline(105.6, color=INK2, ls="--", lw=0.8); ax[1].text(-9, 112, "IHSC 105.6 A", color=INK2, fontsize=8)
    ax[1].set_ylabel("A")
    plot(ax[2], tu, r["V(x1:g)"][m] - r["V(out)"][m], "VGS (FET)", 0)
    ax[2].set_ylabel("V")
    plot(ax[3], tu, r["V(x1:xu:hsht)"][m], "HSHT latch", 0); plot(ax[3], tu, r["V(x1:xu:gcmd)"][m], "gate command", 1)
    plot(ax[3], tu, r["V(diag)"][m] / 3.3, "DIAG (norm.)", 2); ax[3].set_ylabel("logic")
    finish(fig, ax, "time after short [us]", "tb02_hard_short_zoom.png")

    fig, ax = panels(3, "tb02 - full sequence: short at 3 ms, CLR/retry at 6 ms, short removed 9 ms, CLR 10 ms")
    tm = t * 1e3
    plot(ax[0], tm, r["V(out)"], "OUT", 1); plot(ax[0], tm, r["V(vbat)"], "VBAT", 0); ax[0].set_ylabel("V")
    plot(ax[1], tm, r["I(Lh)"], "I(FET)", 0); ax[1].set_ylabel("A")
    plot(ax[2], tm, r["V(x1:xu:hsht)"], "HSHT", 0); plot(ax[2], tm, r["V(x1:xu:fusel)"] * 0.9, "FUSE_LATCH (x0.9)", 1)
    plot(ax[2], tm, r["V(diag)"] / 3.3, "DIAG (norm.)", 2); ax[2].set_ylabel("logic")
    finish(fig, ax, "time [ms]", "tb02_hard_short_sequence.png")


def tb03():
    m = meas_log(os.path.join(TB, "tb03_i2t_curve.log"))
    tt, xa = np.array(m["ttrip"]), np.array(m["xavg"])
    xs, ts = xa[0::2], tt[0::2]      # FUSE_MODE 0 (stepwise)
    xi, ti = xa[1::2], tt[1::2]      # FUSE_MODE 1 (ideal)
    vocm, tnom = 6.0, 1.0
    x = np.logspace(np.log10(1.0005), np.log10(160 / 6), 4000)
    ideal = np.minimum(tnom, tnom / 32 / (x ** 2 - 1))
    mm = np.maximum(0, np.floor(np.log2(32 * (x ** 2 - 1))))
    step = tnom / 2 ** mm
    # breakpoints digitised from DS13084 Figure 4 (mV, s)
    fig4 = [(6.17, 1), (6.34, .5), (6.62, .25), (7.40, .125), (8.44, .0625), (10.3, .03125),
            (13.4, .0156), (18.0, .0078), (24.6, .0039), (34.4, .00195), (48.0, .00098),
            (68.0, .00049), (96.0, .000244), (135.3, .000122), (160, .000061)]
    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.set_title("tb03 - eFuse current-vs-time curve, VOC = 6 mV, VHSC = 160 mV, tNOM = 1 s (DS13084 Fig. 4)",
                 loc="left")
    ax.loglog(x * vocm, step, color=C[0], label="stepwise  t = tNOM/2^m (model eq.)", lw=1.4)
    ax.loglog(x * vocm, ideal, color=C[1], ls="--", label="ideal  t = (tNOM/32)/(x^2-1)", lw=1.2)
    ax.loglog(xs * vocm, ts, "o", color=C[0], ms=7, mfc=SURF, mew=1.6, label="LTspice, FUSE_MODE=0")
    ax.loglog(xi * vocm, ti, "s", color=C[1], ms=6, mfc=SURF, mew=1.6, label="LTspice, FUSE_MODE=1")
    fx, fy = zip(*fig4)
    ax.loglog(fx, fy, "x", color=C[2], ms=8, mew=1.8, label="DS13084 Fig. 4 (digitised step ends)")
    ax.axvline(6, color=INK2, lw=0.8, ls=":"); ax.axvline(160, color=INK2, lw=0.8, ls=":")
    ax.text(6.1, 2e-5, "VOC_THRS", color=INK2, fontsize=8, rotation=90)
    ax.text(163, 2e-5, "VHSC_THRS -> hard short (5 us)", color=INK2, fontsize=8, rotation=90)
    ax.set_xlabel("VSENSE = I x RSENSE [mV]   (INOM = 6 A with 1 mOhm)"); ax.set_ylabel("trip time [s]")
    ax.set_xlim(3, 400); ax.set_ylim(1e-5, 10)
    ax.legend(loc="upper right")
    fig.tight_layout(); fig.savefig(os.path.join(IMG, "tb03_i2t_curve.png"), dpi=110); plt.close(fig)
    print("  -> tb03_i2t_curve.png")


def tb04():
    r = raw("tb04_pwm_rms")
    m = meas_log(os.path.join(TB, "tb04_pwm_rms.log"))
    D = [0.25, 0.30, 0.35, 0.50]
    fig, ax = panels(2, "tb04 - PWM load 200 Hz, 40 A peak: fuse state fd vs duty (trip at fd = 1)", h=2.4,
                     sharex=False)
    for k, d in enumerate(D):
        t = r.get("time", k); fd = r.get("V(x1:xu:fd)", k)
        plot(ax[0], t, fd, f"D = {d:.2f}  (I_RMS/INOM = {math.sqrt(d) * 39.2 / 21.8:.2f})", k)
    ax[0].set_ylabel("fd [-]"); ax[0].axhline(1, color=INK2, lw=0.8, ls="--")
    ax[0].set_xlabel("time [s]")
    t = r.get("time", 3); mk = win(t, 0.018, 0.042)
    plot(ax[1], t[mk] * 1e3, r.get("I(Lh)", 3)[mk], "I(eFuse), D = 0.50", 3)
    ax[1].set_ylabel("A")
    ax[1].set_title("eFuse current detail (D = 0.50)", loc="left", fontsize=9, fontweight="normal")
    finish(fig, ax, "time [ms]", "tb04_pwm_rms.png")


def tb05():
    r = raw("tb05_vds_desat")
    fig, ax = panels(3, "tb05 - VDS desaturation & 960 us blanking: C_SLEW 47 nF (ok) vs 470 nF (VDS_MAX)")
    for k, lab in enumerate(["C_SLEW = 47 nF", "C_SLEW = 470 nF"]):
        t = r.get("time", k) * 1e3
        plot(ax[0], t, r.get("V(out)", k), "OUT, " + lab, k)
        plot(ax[1], t, r.get("V(x1:drn)", k) - r.get("V(out)", k), "VDS, " + lab, k)
        plot(ax[2], t, r.get("V(x1:xu:vdsmax)", k) * (1 - 0.05 * k), "VDS_MAX, " + lab, k)
    ax[0].set_ylabel("V"); ax[1].set_ylabel("V"); ax[1].set_ylim(-2, 50)
    ax[1].axvspan(0.5, 1.46, color=GRID, alpha=0.6, lw=0); ax[1].text(0.55, 44, "VDS blanking 960 us", color=INK2, fontsize=8)
    ax[1].axhline(1.0, color=INK2, lw=0.8, ls="--")
    ax[2].set_ylabel("logic")
    finish(fig, ax, "time [ms]", "tb05_vds_desat.png")


def tb06():
    r = raw("tb06_supply_transients"); t = r["time"] * 1e3
    fig, ax = panels(3, "tb06 - 48 V supply profile: over-voltage to 70 V, dips to 24 V / 6 V / 4 V (UV)")
    plot(ax[0], t, r["V(vbat)"], "VBAT", 0); plot(ax[0], t, r["V(out)"], "OUT", 1); ax[0].set_ylabel("V")
    plot(ax[1], t, r["V(x1:g)"] - r["V(out)"], "VGS (FET)", 0); plot(ax[1], t, r["V(x1:cp)"] - r["V(vbat)"], "VCP - VS", 1)
    ax[1].set_ylabel("V")
    plot(ax[2], t, r["V(x1:xu:uv)"], "UV shutdown", 0); plot(ax[2], t, r["V(x1:xu:gcmd)"] * 0.95, "gate command (x0.95)", 1)
    plot(ax[2], t, r["V(diag)"] / 3.3 * 0.9, "DIAG (norm. x0.9)", 2); ax[2].set_ylabel("logic")
    finish(fig, ax, "time [ms]", "tb06_supply_transients.png")


def tb07():
    r = raw("tb07_ntc_overtemp"); t = r["time"]
    fig, ax = panels(3, "tb07 - external FET over-temperature via NTC (TAMB 105 C, 23 A, NTC_CODE 4 = 120 C)")
    plot(ax[0], t, r["V(tfet)"], "FET junction", 0); plot(ax[0], t, r["V(x1:tcf)"], "pad / NTC", 1)
    ax[0].axhline(120, color=INK2, lw=0.8, ls="--"); ax[0].set_ylabel("deg C")
    plot(ax[1], t, (r["V(x1:drn)"] - r["V(x1:ntc)"]) * 1e3, "VNTC", 0)
    ax[1].axhline(70.38, color=INK2, lw=0.8, ls="--"); ax[1].text(0.2, 73, "VNTC_THRS_4 = 70.38 mV", color=INK2, fontsize=8)
    ax[1].set_ylabel("mV")
    plot(ax[2], t, r["V(x1:xu:ntcovt)"], "NTC_OVT latch", 0); plot(ax[2], t, r["V(x1:xu:gcmd)"] * 0.95, "gate command (x0.95)", 1)
    plot(ax[2], t, r["V(diag)"] / 3.3 * 0.9, "DIAG (norm. x0.9)", 2); ax[2].set_ylabel("logic")
    finish(fig, ax, "time [s]", "tb07_ntc_overtemp.png")


def tb08():
    r = raw("tb08_standby_autoon"); t = r["time"] * 1e3
    fig, ax = panels(4, "tb08 - stand-by on the low-current bypass, load wake-up -> hardware AUTO-ON")
    plot(ax[0], t, r["V(vbat)"], "VBAT", 0); plot(ax[0], t, r["V(out)"], "OUT", 1); ax[0].set_ylabel("V")
    ax[0].set_ylim(40, 50)
    plot(ax[1], t, r["V(x1:cp)"] - r["V(vbat)"], "VCP - VS", 0); plot(ax[1], t, r["V(x1:hsg)"] - r["V(out)"], "VGS at HS_GATE", 1)
    ax[1].set_ylabel("V")
    plot(ax[2], t, r["I(Rsleep)"] + r["I(Rwake)"], "load current", 0); ax[2].set_ylabel("A")
    plot(ax[3], t, r["V(x1:xu:byp)"], "bypass on", 0); plot(ax[3], t, r["V(x1:xu:autoon)"] * 0.95, "AUTO-ON (x0.95)", 1)
    plot(ax[3], t, r["V(diag)"] / 3.3 * 0.9, "DIAG (norm. x0.9)", 2); ax[3].set_ylabel("logic")
    finish(fig, ax, "time [ms]", "tb08_standby_autoon.png")


def tb09():
    r = raw("tb09_inductive_turnoff")
    fig, ax = panels(3, "tb09 - switching off a 2 mH / 10 A inductive load: with vs without freewheel diode")
    labs = {0: "no freewheel (FW=0)", 1: "Schottky freewheel (FW=1)"}
    for k in range(r.nsteps):
        t = r.get("time", k); mk = win(t, 9.9e-3, 11.6e-3); tm = (t[mk] - 10e-3) * 1e3
        plot(ax[0], tm, r.get("V(out)", k)[mk], "OUT, " + labs[k], k)
        plot(ax[1], tm, r.get("V(x1:drn)", k)[mk] - r.get("V(out)", k)[mk], "VDS, " + labs[k], k)
        plot(ax[2], tm, r.get("I(Lload)", k)[mk], "I(L), " + labs[k], k)
    ax[0].set_ylabel("V"); ax[1].set_ylabel("V"); ax[2].set_ylabel("A")
    ax[1].axhline(100, color=INK2, lw=0.8, ls="--"); ax[1].text(1.0, 92, "FET BV = 100 V (avalanche)", color=INK2, fontsize=8)
    finish(fig, ax, "time after OUTCTL off [ms]", "tb09_inductive_turnoff.png")


def tb10():
    r = raw("tb10_zonal_system"); t = r["time"] * 1e3
    fig, ax = panels(3, "tb10 - zonal PDU: CH1 DC/DC 1 kW + CH2 motor; CH2 shorted at 15 ms")
    plot(ax[0], t, r["V(bus)"], "48 V bus", 0); plot(ax[0], t, r["V(d1)"], "DC/DC input (CH1)", 1)
    plot(ax[0], t, r["V(m2)"], "motor node (CH2)", 2); ax[0].set_ylabel("V")
    plot(ax[1], t, r["I(Lh1)"], "I CH1", 1); plot(ax[1], t, r["I(Lh2)"], "I CH2", 2); ax[1].set_ylabel("A")
    ax[1].set_ylim(-20, 120)
    plot(ax[2], t, r["V(diag1)"] / 3.3, "DIAG CH1", 1); plot(ax[2], t, r["V(diag2)"] / 3.3 * 0.95, "DIAG CH2 (x0.95)", 2)
    plot(ax[2], t, r["V(dcen)"] * 0.9, "DC/DC enabled (x0.9)", 0); ax[2].set_ylabel("logic")
    finish(fig, ax, "time [ms]", "tb10_zonal_system.png")


def tb11():
    r = raw("tb11_precharge_dvdt")
    m = meas_log(os.path.join(TB, "tb11_precharge_dvdt.log"))
    CL = [0.22, 0.47, 1.0, 2.2, 4.7]               # mF  (inner .step)
    CS = [22, 47, 68, 100, 220]                    # nF  (outer .step)
    fig, ax = panels(3, "tb11 - dV/dt pre-charge of 1 mF: C_SLEW 22 nF (HSC) ... 68 nF (ok) ... 220 nF (VDS)")
    for j, cs in enumerate(CS):
        k = j * len(CL) + 2                         # C_LOAD = 1 mF
        t = r.get("time", k) * 1e3
        plot(ax[0], t, r.get("V(out)", k), f"C_SLEW = {cs} nF", j)
        plot(ax[1], t, r.get("I(Lh)", k), f"C_SLEW = {cs} nF", j)
        plot(ax[2], t, r.get("V(x1:xu:hsht)", k) + 1.2 * r.get("V(x1:xu:vdsmax)", k) - 0.03 * j,
             f"C_SLEW = {cs} nF", j)
    ax[0].set_ylabel("V(OUT) [V]")
    ax[1].set_ylabel("I(load) [A]"); ax[1].axhline(105.6, color=INK2, ls="--", lw=0.8)
    ax[1].text(0.05, 109, "IHSC 105.6 A", color=INK2, fontsize=8); ax[1].set_ylim(-20, 140)
    for a in ax[:2]:
        a.axvspan(0.5, 1.46, color=GRID, alpha=0.5, lw=0)
    ax[0].text(0.55, 50, "VDS blanking 960 us", color=INK2, fontsize=8); ax[0].set_ylim(0, 58)
    ax[2].set_yticks([0, 1, 1.2]); ax[2].set_yticklabels(["no fault", "HSHT", "VDS_MAX"])
    ax[2].set_ylabel("latched fault")
    finish(fig, ax, "time [ms]", "tb11_precharge_dvdt.png")

    # design-window map: dV/dt (from the 10 -> 20 V slope of the 0.22 mF run) vs C_LOAD
    sr = [10 / (m["t20v"][j * 5] - m["t10v"][j * 5]) / 1e3 for j in range(len(CS))]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.set_title("tb11 - design window of dV/dt pre-charge (IHSC 105.6 A, VDS blanking 960 us, VBAT 48 V)",
                 loc="left")
    cl = np.logspace(np.log10(0.1), np.log10(10), 200)
    ax.loglog(cl, 105.6 / cl, color=C[7], lw=1.2, ls="--")
    ax.text(0.75, 290, "HSC-trip region:  C_LOAD x dV/dt > IHSC", color=C[7], fontsize=8)
    ax.text(0.75, 13, "VDS-trip region: ramp longer than the blanking", color=C[3], fontsize=8)
    ax.axhline(46, color=C[3], lw=1.2, ls="--")
    ax.text(0.105, 41, "VDS-blanking limit: OUT must reach ~47 V within 960 us  (~46 V/ms)", color=C[3], fontsize=8)
    ax.fill_between(cl, 46, np.maximum(46, 105.6 / cl), color=C[2], alpha=0.10, lw=0)
    done = set()
    for j in range(len(CS)):
        for i, c in enumerate(CL):
            k = j * len(CL) + i
            hsc = not math.isnan(m["t_hsc"][k]); vds = not math.isnan(m["t_vds"][k])
            lab, mk, col = (("HSC trip", "x", C[7]) if hsc else ("VDS trip", "^", C[3]) if vds
                            else ("PASS", "o", C[2]))
            ax.loglog(c, sr[j], mk, color=col, ms=9, mew=2, mfc=SURF if mk != "x" else col,
                      label=None if lab in done else lab)
            done.add(lab)
            if not (hsc or vds):
                ax.annotate(f"{m['ipk'][k]:.0f} A", (c, sr[j]), textcoords="offset points", xytext=(7, 4),
                            fontsize=7, color=INK2)
    for j, cs in enumerate(CS):
        ax.text(6.4, sr[j], f"C_SLEW {cs} nF", va="center", fontsize=8, color=INK2)
    ax.text(0.6, 75, "window", color=C[2], fontsize=10, fontweight="bold")
    ax.set_xlim(0.1, 13); ax.set_ylim(10, 400)
    ax.set_xlabel("load capacitance C_LOAD [mF]"); ax.set_ylabel("output slew rate dV/dt [V/ms]")
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout(); fig.savefig(os.path.join(IMG, "tb11_precharge_window.png"), dpi=110); plt.close(fig)
    print("  -> tb11_precharge_window.png")


def tb12():
    r = raw("tb12_precharge_resistor")
    tau = 4.7 * 4.7e-3
    N = [1, 2, 3, 5]
    fig, ax = panels(3, "tb12 - resistor pre-charge (4.7 Ohm, 4.7 mF, tau 22 ms): eFuse hand-over after 1/2/3/5 tau",
                     sharex=False)
    for k, n in enumerate(N):
        t = r.get("time", k); tho = 1e-3 + n * tau
        plot(ax[0], t * 1e3, r.get("V(load)", k), f"hand-over at {n} tau", k)
        mk = win(t, tho - 0.1e-3, tho + 1.2e-3)
        ifet = (r.get("V(vbat)", k) - r.get("V(x1:drn)", k)) * 1e3 * r.get("V(x1:xu:gcmd)", k)
        plot(ax[1], (t[mk] - tho) * 1e3, ifet[mk], f"{n} tau", k)
    ax[0].set_ylabel("V(load) [V]"); ax[0].set_xlabel("time [ms]")
    ax[1].axhline(105.6, color=INK2, ls="--", lw=0.8); ax[1].text(-0.08, 110, "IHSC 105.6 A", color=INK2, fontsize=8)
    ax[1].set_ylabel("FET current [A]"); ax[1].set_xlabel("time after OUTCTL (hand-over) [ms]"); ax[1].set_ylim(-5, 130)
    k = 3; t = r.get("time", k); mk = t < 1e-3 + 5 * tau
    p = r.get("V(pc)", k)[mk] - r.get("V(out)", k)[mk]
    pw = p * r.get("I(Rpre)", k)[mk]
    e = np.concatenate([[0], np.cumsum(0.5 * (pw[1:] + pw[:-1]) * np.diff(t[mk]))])
    plot(ax[2], t[mk] * 1e3, pw, "resistor power [W]", 0)
    plot(ax[2], t[mk] * 1e3, e * 100, "resistor energy [J x 100]", 1)
    ax[2].set_ylabel("W  /  J x 100"); ax[2].set_xlabel("time [ms]")
    ax[2].set_title(f"pre-charge resistor, 5 tau case: peak {pw[t[mk] > 1.02e-3].max():.0f} W, total {e[-1]:.2f} J",
                    loc="left", fontsize=9, fontweight="normal")
    finish(fig, ax, "time [ms]", "tb12_precharge_resistor.png")


def tb13():
    r = raw("tb13_precharge_methods")
    labs = ["resistor 4.8 Ohm", "constant current 10 A", "switch-mode (buck, 8-12 A)"]
    fig, ax = panels(3, "tb13 - pre-charge methods compared on 4.7 mF at ~10 A: time and energy lost")
    for k, lab in enumerate(labs):
        t = r.get("time", k)
        plot(ax[0], t * 1e3, r.get("V(load)", k), lab, k, ls=":" if k == 2 else "-", lw=2.2 if k == 2 else 1.6)
        plot(ax[1], t * 1e3, r.get("I(Vpout)", k), lab, k, lw=0.8 if k == 2 else 1.8, zorder=1 if k == 2 else 3)
        pl = r.get("V(vbat)", k) * r.get("I(Vpin)", k) - r.get("V(out)", k) * r.get("I(Vpout)", k)
        e = np.concatenate([[0], np.cumsum(0.5 * (pl[1:] + pl[:-1]) * np.diff(t))])
        plot(ax[2], t * 1e3, e, lab, k)
    ax[0].axhline(0.95 * 48, color=INK2, ls="--", lw=0.8); ax[0].text(70, 41, "hand-over at 95 % VBAT", color=INK2, fontsize=8)
    ax[0].set_ylabel("V(load) [V]"); ax[1].set_ylabel("pre-charge current [A]"); ax[1].set_ylim(-1, 14)
    ax[2].set_ylabel("energy lost [J]")
    finish(fig, ax, "time [ms]", "tb13_precharge_methods.png")


def tb14():
    r = raw("tb14_precharge_faults")
    labs = ["normal", "short at load (50 mOhm)", "leaky load (10 Ohm)", "DC/DC not gated by PG"]
    fig, ax = panels(4, "tb14 - supervised pre-charge: checkpoint at 1 tau (> 40 %), timeout 100 ms, hand-over at 95 %")
    for k, lab in enumerate(labs):
        t = r.get("time", k) * 1e3
        plot(ax[0], t, r.get("V(load)", k), lab, k)
        plot(ax[1], t, r.get("I(Rpre)", k), lab, k)
        plot(ax[2], t, r.get("V(dcen)", k) * (1 - 0.05 * k), lab, k)
        plot(ax[3], t, r.get("V(abort)", k) * (1 - 0.05 * k) - 1.2 * r.get("V(pg)", k) * (k == 0), lab, k)
    for a in ax:
        a.axvline(1 + 22.09, color=INK2, lw=0.8, ls=":"); a.axvline(101, color=INK2, lw=0.8, ls=":")
    ax[0].axhline(0.95 * 48, color=INK2, ls="--", lw=0.8); ax[0].axhline(0.4 * 48, color=INK2, ls="--", lw=0.8)
    ax[0].text(24.5, 15.5, "checkpoint: > 40 % at 1 tau", color=INK2, fontsize=8)
    ax[0].text(102, 41, "timeout", color=INK2, fontsize=8)
    ax[0].set_ylabel("V(load) [V]"); ax[1].set_ylabel("I(RPRE) [A]")
    ax[2].set_ylabel("DC/DC on"); ax[3].set_ylabel("logic")
    ax[3].set_yticks([-1.2, 0, 1]); ax[3].set_yticklabels(["PG (normal)", "0", "ABORT"])
    finish(fig, ax, "time [ms]", "tb14_precharge_faults.png")


ALL = dict(tb01=tb01, tb02=tb02, tb03=tb03, tb04=tb04, tb05=tb05, tb06=tb06,
           tb07=tb07, tb08=tb08, tb09=tb09, tb10=tb10, tb11=tb11, tb12=tb12,
           tb13=tb13, tb14=tb14)

if __name__ == "__main__":
    sel = sys.argv[1:] or list(ALL)
    for k in sel:
        print(k)
        ALL[k]()
