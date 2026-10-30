"""Plot the test-bench results into docs/img/*.png.

    python3 tools/plot_results.py            # all test benches
    python3 tools/plot_results.py tb03 tb07  # selected ones

Run the simulations first (tools/run_ltspice.sh -j 4 testbenches/*.cir).
Exits non-zero if any plot failed; the other plots are still written.
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



# ---------------------------------------------------------------------------
# Interview companion benches (tb15..tb36) and post-processed figures (iv_*).
# See interview/pdn_48v_12v_interview_guide.md.
# ---------------------------------------------------------------------------
def ifet(r, k=0, pre="x1:"):
    """FET current from the 1 mOhm shunt drop (unlike I(Lh), it stops at turn-off)."""
    return (r.get("V(vbat)", k) - r.get(f"V({pre}drn)", k)) * 1e3


def tb15():
    r = raw("tb15_12v_vs_48v")
    m = meas_log(os.path.join(TB, "tb15_12v_vs_48v.log"))
    labs = ["12 V, 2.5 mm2", "12 V, 16 mm2", "48 V, 2.5 mm2", "48 V, 0.75 mm2"]
    fig, ax = panels(3, "tb15 - 1 kW over 3 m of wire: 12 V vs 48 V (load on at 2 ms, bolted short at 20 ms)",
                     sharex=False)
    for k, lab in enumerate(labs):
        t = r.get("time", k)
        mk = t < 19.5e-3
        plot(ax[0], t[mk] * 1e3, r.get("I(Lw)", k)[mk], f"{lab}: {m['iw'][k]:.0f} A, {m['pwire'][k]:.0f} W in the wire", k)
        plot(ax[1], t[mk] * 1e3, r.get("V(load)", k)[mk], f"{lab}: {m['vl'][k]:.1f} V at the load", k)
        mk = win(t, 19.98e-3, 20.3e-3)
        plot(ax[2], (t[mk] - 20e-3) * 1e6, r.get("I(Lw)", k)[mk], f"{lab}: {m['isc'][k]:.0f} A", k)
    ax[0].set_ylabel("wire current [A]"); ax[0].set_xlabel("time [ms]")
    ax[1].set_ylabel("load voltage [V]"); ax[1].set_xlabel("time [ms]")
    ax[2].set_ylabel("short current [A]"); ax[2].set_xlabel("time after the short [us]")
    ax[2].set_title("bolted short at the load: slope V/L, prospective current V/R_loop", loc="left",
                    fontsize=9, fontweight="normal")
    finish(fig, ax, "time after the short [us]", "tb15_12v_vs_48v.png")


def tb16():
    r = raw("tb16_thermal_memory")
    labs = ["pulse train, thermal memory (KCOOL 1)", "pulse train, no memory (KCOOL 1000)",
            "DC at the same RMS (25 A)"]
    fig, ax = panels(3, "tb16 - repetitive 35 A pulses (20 ms on / 40 ms off) on an 18 A base load", sharex=False)
    for k, lab in enumerate(labs):
        t = r.get("time", k)
        mk = win(t, 0.05, 0.45)
        if k != 1:
            plot(ax[0], t[mk], r.get("I(Lh)", k)[mk], lab, k, lw=1.0)
        plot(ax[1], t[mk], r.get("V(x1:xu:fd)", k)[mk], lab, k)
        plot(ax[2], t, r.get("V(tw)", k), lab, k)
    ax[0].axhline(21.8, color=INK2, ls="--", lw=0.8); ax[0].text(0.052, 23, "INOM 21.8 A", color=INK2, fontsize=8)
    ax[0].set_ylabel("eFuse current [A]"); ax[0].set_xlabel("time [s]")
    ax[1].axhline(1, color=INK2, ls="--", lw=0.8); ax[1].set_ylabel("fuse state fd"); ax[1].set_xlabel("time [s]")
    ax[2].axhline(125, color=C[7], ls="--", lw=0.8)
    ax[2].text(0.2, 127, "insulation limit 125 C (assumed)", color=C[7], fontsize=8)
    ax[2].set_ylabel("wire temperature [C]")
    ax[2].set_title("wire model: +50 K at INOM, tau 3 s, 70 C ambient", loc="left", fontsize=9,
                    fontweight="normal")
    finish(fig, ax, "time [s]", "tb16_thermal_memory.png")


def tb17():
    r = raw("tb17_latch_vs_limit"); t = r["time"]
    m = meas_log(os.path.join(TB, "tb17_latch_vs_limit.log"))
    mk = win(t, 0.99e-3, 2.2e-3); tm = (t[mk] - 1e-3) * 1e3
    fig, ax = panels(3, "tb17 - same 5 mOhm short: latch-off (VNF1048F) vs linear current limit at the same 105.6 A")
    ia = (r["V(vba)"] - r["V(x1:drn)"]) * 1e3; ib = (r["V(vbb)"] - r["V(db)"]) * 1e3
    plot(ax[0], tm, ia[mk], f"latch-off: {m['ea'][0] * 1e3:.0f} mJ in the FET", 0)
    plot(ax[0], tm, ib[mk], f"current limit: {m['eb'][0]:.1f} J in the FET", 1)
    ax[0].set_ylabel("FET current [A]"); ax[0].set_ylim(-20, 360)
    plot(ax[1], tm, r["V(x1:drn)"][mk] - r["V(outa)"][mk], "latch-off", 0)
    plot(ax[1], tm, r["V(db)"][mk] - r["V(outb)"][mk], "current limit", 1)
    ax[1].set_ylabel("VDS [V]")
    plot(ax[2], tm, r["V(tfeta)"][mk], "latch-off", 0); plot(ax[2], tm, r["V(tjb)"][mk], "current limit", 1)
    ax[2].axhline(175, color=C[7], ls="--", lw=0.8); ax[2].text(0.02, 185, "Tj max 175 C", color=C[7], fontsize=8)
    ax[2].set_ylabel("FET junction [C]")
    finish(fig, ax, "time after the short [ms]", "tb17_latch_vs_limit.png")


def tb18():
    r = raw("tb18_short_di_dt")
    m = meas_log(os.path.join(TB, "tb18_short_di_dt.log"))
    LH = [0.5, 1, 2, 5]
    fig, ax = panels(3, "tb18 - hard short: the load-harness inductance sets di/dt, trip time and peak current")
    for k, lh in enumerate(LH):
        t = r.get("time", k); mk = win(t, 2.998e-3, 3.06e-3); tu = (t[mk] - 3e-3) * 1e6
        lab = f"LH = {lh:g} uH: latch at {m['dt_trip'][k] * 1e6:.1f} us, {m['ipk'][k]:.0f} A"
        plot(ax[0], tu, ifet(r, k)[mk], lab, k)
        plot(ax[1], tu, r.get("V(vbat)", k)[mk], f"LH = {lh:g} uH", k)
        plot(ax[2], tu, r.get("V(x1:xu:hsht)", k)[mk] * (1 - 0.04 * k), f"LH = {lh:g} uH", k)
    ax[0].axhline(105.6, color=INK2, ls="--", lw=0.8); ax[0].text(-1.8, 118, "IHSC 105.6 A", color=INK2, fontsize=8)
    ax[0].set_ylabel("FET current [A]"); ax[1].set_ylabel("VBAT [V]"); ax[2].set_ylabel("HSHT latch")
    finish(fig, ax, "time after the short [us]", "tb18_short_di_dt.png")


def tb19():
    r = raw("tb19_turnoff_speed")
    m = meas_log(os.path.join(TB, "tb19_turnoff_speed.log"))
    labs = ["RG_OFF 10 Ohm", "RG_OFF 100 Ohm", "RG_OFF 1 kOhm", "no fast path"]
    fig, ax = panels(3, "tb19 - hard short: speed of the gate turn-off path (RG_OFF) vs peak current, VBAT and FET heat")
    for k, lab in enumerate(labs):
        t = r.get("time", k); mk = win(t, 2.99e-3, 3.7e-3); tu = (t[mk] - 3e-3) * 1e6
        plot(ax[0], tu, ifet(r, k)[mk], f"{lab}: {m['ipk'][k]:.0f} A, {m['e_fet'][k]:.2g} J", k)
        plot(ax[1], tu, r.get("V(vbat)", k)[mk], f"{lab}: {m['vbatpk'][k]:.0f} V peak", k)
        plot(ax[2], tu, r.get("V(tfet)", k)[mk], lab, k)
    ax[0].set_ylabel("FET current [A]")
    ax[1].axhline(70, color=C[7], ls="--", lw=0.8); ax[1].text(600, 72, "VS abs. max 70 V", color=C[7], fontsize=8, ha="right")
    ax[1].set_ylabel("VBAT [V]"); ax[2].set_ylabel("FET junction [C]")
    finish(fig, ax, "time after the short [us]", "tb19_turnoff_speed.png")


def tb20():
    r = raw("tb20_sense_error")
    m = meas_log(os.path.join(TB, "tb20_sense_error.log"))
    RS = [0.9, 1.0, 1.1, 1.2]
    fig, ax = panels(2, "tb20 - 40 A overload, fixed settings (VOC 21.8 mV, ideal curve): sense resistance error",
                     h=2.4)
    for k, rs in enumerate(RS):
        t = r.get("time", k) * 1e3
        lab = f"sensed R {rs:.1f} mOhm: INOM_eff {21.8 / rs:.1f} A, trip {m['ttrip'][k] * 1e3:.1f} ms"
        plot(ax[0], t, r.get("V(x1:xu:fd)", k), lab, k)
        plot(ax[1], t, r.get("V(x1:xu:xa)", k), f"sensed R {rs:.1f} mOhm", k)
    ax[0].axhline(1, color=INK2, ls="--", lw=0.8); ax[0].set_ylabel("fuse state fd")
    ax[1].set_ylabel("x = I_sensed / INOM"); ax[1].axvline(5, color=INK2, lw=0.8, ls=":")
    finish(fig, ax, "time [ms]", "tb20_sense_error.png")


def tb21():
    r = raw("tb21_inductive_clamp")
    m = meas_log(os.path.join(TB, "tb21_inductive_clamp.log"))
    labs = ["no clamp (FET avalanche)", "Schottky freewheel", "Schottky + 33 V zener"]
    fig, ax = panels(3, "tb21 - switching off 2 mH / 10 A: three demagnetization paths")
    for k, lab in enumerate(labs):
        t = r.get("time", k); mk = win(t, 9.9e-3, 11.4e-3); tm = (t[mk] - 10e-3) * 1e3
        plot(ax[0], tm, r.get("V(out)", k)[mk], f"{lab}: {m['vout_min'][k]:.1f} V", k)
        plot(ax[1], tm, r.get("V(x1:drn)", k)[mk] - r.get("V(out)", k)[mk], lab, k)
        plot(ax[2], tm, r.get("I(Lload)", k)[mk], f"{lab}: to 1 A in {m['dt_decay'][k] * 1e3:.2f} ms", k)
    ax[0].axhline(-10, color=C[7], ls="--", lw=0.8); ax[0].text(0.05, -17, "OUT pin -10 V (10 us)", color=C[7], fontsize=8)
    ax[0].set_ylabel("OUT [V]"); ax[1].set_ylabel("VDS [V]"); ax[2].set_ylabel("load current [A]")
    ax[1].axhline(100, color=INK2, ls="--", lw=0.8); ax[1].text(1.3, 92, "FET BV 100 V", color=INK2, fontsize=8, ha="right")
    finish(fig, ax, "time after OUTCTL off [ms]", "tb21_inductive_clamp.png")


def tb22():
    r = raw("tb22_parallel_fets"); t = r["time"] * 1e3
    m = meas_log(os.path.join(TB, "tb22_parallel_fets.log"))
    fig, ax = panels(3, "tb22 - two parallel FETs, VGS(th) 3.0 V vs 3.5 V: 1 mF dV/dt start-up, then 40 A at 3 ms")
    plot(ax[0], t, r["Id(M1)"], f"M1 (Vth 3.0 V): {m['e1'][0]:.2f} J in the ramp", 0)
    plot(ax[0], t, r["Id(M2)"], f"M2 (Vth 3.5 V): {m['e2'][0]:.2f} J in the ramp", 1)
    ax[0].set_ylabel("drain current [A]")
    plot(ax[1], t, r["V(out)"], "OUT", 0); plot(ax[1], t, r["V(drn)"] - r["V(out)"], "VDS", 1)
    ax[1].set_ylabel("V")
    plot(ax[2], t, r["V(tj1)"], "M1 junction", 0); plot(ax[2], t, r["V(tj2)"], "M2 junction", 1)
    ax[2].set_ylabel("deg C")
    for a in ax[:1]:
        a.axvspan(0.5, 1.2, color=GRID, alpha=0.5, lw=0)
    ax[0].text(0.55, 60, "linear mode", color=INK2, fontsize=8); ax[0].text(3.3, 26, "fully on", color=INK2, fontsize=8)
    finish(fig, ax, "time [ms]", "tb22_parallel_fets.png")


def tb23():
    r = raw("tb23_linear_soa")
    m = meas_log(os.path.join(TB, "tb23_linear_soa.log"))
    CL = [0.22, 0.47, 1.0]
    fig, ax = panels(3, "tb23 - FET in linear mode during a dV/dt start-up (C_SLEW 68 nF, TAMB 85 C)")
    for k, c in enumerate(CL):
        t = r.get("time", k); mk = win(t, 0.4e-3, 2e-3); tm = t[mk] * 1e3
        p_ = (r.get("V(x1:drn)", k) - r.get("V(out)", k)) * ifet(r, k)
        plot(ax[0], tm, p_[mk] / 1e3, f"C_LOAD {c:g} mF: {m['e_fet'][k]:.2f} J", k)
        plot(ax[1], tm, r.get("V(tfet)", k)[mk], f"C_LOAD {c:g} mF: {m['tjpk'][k]:.0f} C", k)
        plot(ax[2], tm, r.get("V(x1:tcf)", k)[mk], f"C_LOAD {c:g} mF", k)
    ax[0].set_ylabel("FET power [kW]"); ax[1].set_ylabel("junction [C]"); ax[2].set_ylabel("drain pad / NTC [C]")
    ax[2].set_ylim(84.5, 86)
    finish(fig, ax, "time [ms]", "tb23_linear_soa.png")


def tb24():
    r = raw("tb24_back_to_back"); t = r["time"] * 1e3
    fig, ax = panels(3, "tb24 - back-driven motor (55 V EMF): single FET vs back-to-back FETs (channel ON 3-6 ms)")
    plot(ax[0], t, r["I(Lha)"], "single FET", 0); plot(ax[0], t, r["I(Lhb)"], "back-to-back", 1)
    ax[0].set_ylabel("channel current [A]\n(negative = reverse)")
    plot(ax[1], t, r["V(csa)"] * 1e3, "single FET", 0); plot(ax[1], t, r["V(csb)"] * 1e3, "back-to-back", 1)
    ax[1].set_ylabel("CS readback [mV]"); ax[1].set_ylim(-1, 5)
    plot(ax[2], t, r["V(emf)"], "motor EMF", 2); plot(ax[2], t, r["V(vba)"], "bus (single)", 0)
    plot(ax[2], t, r["V(lb)"], "load (back-to-back)", 1); ax[2].set_ylabel("V")
    for a in ax:
        a.axvspan(3, 6, color=GRID, alpha=0.5, lw=0)
    ax[0].text(3.1, 3, "channel ON", color=INK2, fontsize=8)
    finish(fig, ax, "time [ms]", "tb24_back_to_back.png")


def tb25():
    r = raw("tb25_supply_clamp")
    m = meas_log(os.path.join(TB, "tb25_supply_clamp.log"))
    labs = ["100 uF + TVS (tb02)", "100 uF, no TVS", "22 uF, no TVS", "22 uF + TVS", "22 uF + remote TVS (300 nH)",
            "100 uF + TVS, no freewheel"]
    fig, ax = panels(3, "tb25 - interrupting a 340 A short: bus capacitance, TVS placement, freewheel diode")
    for k, lab in enumerate(labs):
        t = r.get("time", k); mk = win(t, 2.995e-3, 3.1e-3); tu = (t[mk] - 3e-3) * 1e6
        if k < 5:
            plot(ax[0], tu, r.get("V(vbat)", k)[mk], f"{lab}: {m['vbatpk'][k]:.0f} V", k)
        ls = "--" if k == 5 else "-"
        if k in (0, 5):
            plot(ax[1], tu, r.get("V(out)", k)[mk], f"{lab}: {m['voutmin'][k]:.0f} V", k, ls=ls)
        plot(ax[2], tu, r.get("V(x1:drn)", k)[mk] - r.get("V(out)", k)[mk], f"{lab}: {m['vdspk'][k]:.0f} V", k,
             ls=ls)
    ax[0].axhline(70, color=C[7], ls="--", lw=0.8); ax[0].text(98, 72, "VS abs. max 70 V", color=C[7], fontsize=8, ha="right")
    ax[0].set_ylabel("VBAT at the PDU [V]")
    ax[1].axhline(-10, color=C[7], ls="--", lw=0.8); ax[1].text(98, -7, "OUT pin -10 V", color=C[7], fontsize=8, ha="right")
    ax[1].set_ylabel("OUT [V]")
    ax[2].axhline(100, color=INK2, ls="--", lw=0.8); ax[2].set_ylabel("FET VDS [V]")
    finish(fig, ax, "time after the short [us]", "tb25_supply_clamp.png")


def tb26():
    r = raw("tb26_hard_turn_on")
    m = meas_log(os.path.join(TB, "tb26_hard_turn_on.log"))
    labs = ["hard switch, no protection", "hard switch, protections on", "dV/dt control (C_SLEW 68 nF)"]
    fig, ax = panels(3, "tb26 - switching on 1 mF: hard switch vs slew-rate control")
    for k, lab in enumerate(labs):
        t = r.get("time", k); mk = win(t, 0.45e-3, 1.6e-3); tm = t[mk] * 1e3
        plot(ax[0], tm, r.get("I(Lh)", k)[mk], f"{lab}: {m['ipk'][k]:.0f} A peak", k)
        plot(ax[1], tm, r.get("V(load)", k)[mk], lab, k)
        plot(ax[2], tm, r.get("V(vbat)", k)[mk], f"{lab}: min {m['vbatmin'][k]:.0f} V", k)
    ax[0].axhline(105.6, color=INK2, ls="--", lw=0.8); ax[0].text(1.55, 120, "IHSC 105.6 A", color=INK2, fontsize=8, ha="right")
    ax[0].set_ylabel("inrush [A]"); ax[1].set_ylabel("V(load) [V]"); ax[2].set_ylabel("VBAT [V]")
    finish(fig, ax, "time [ms]", "tb26_hard_turn_on.png")


def tb27():
    r = raw("tb27_half_energy")
    m = meas_log(os.path.join(TB, "tb27_half_energy.log"))
    R = [1, 4.7, 22, 100]
    fig, ax = panels(2, "tb27 - charging 4.7 mF to 48 V through R: the resistor always takes 1/2 C V^2",
                     h=2.6)
    for k, rr in enumerate(R):
        t = r.get("time", k); mk = t > 1.0005e-3; tm = (t[mk] - 1e-3) * 1e3
        plot(ax[0], tm, r.get("V(load)", k)[mk], f"R = {rr:g} Ohm: 95 % after {m['t95'][k] * 1e3 - 1:.0f} ms", k)
        pr = (r.get("V(pc)", k) - r.get("V(load)", k)) * r.get("I(Rpre)", k)
        plot(ax[1], tm, pr[mk], f"R = {rr:g} Ohm: {m['ppk'][k]:.0f} W peak, {m['e_r'][k]:.2f} J total", k)
    for a in ax:
        a.set_xscale("log"); a.set_xlim(0.05, 2600)
    ax[0].set_ylabel("V(C) [V]"); ax[1].set_ylabel("resistor power [W]"); ax[1].set_yscale("log")
    ax[1].set_ylim(1, 5000)
    finish(fig, ax, "time after switch-on [ms]", "tb27_half_energy.png")


def tb28():
    r = raw("tb28_bypass_precharge")
    m = meas_log(os.path.join(TB, "tb28_bypass_precharge.log"))
    labs = ["C_LOAD 0.1 mF", "C_LOAD 1 mF"]
    fig, ax = panels(3, "tb28 - pre-charge through the low-current bypass: AUTO-ON takes over within 5 us")
    for k, lab in enumerate(labs):
        t = r.get("time", k); mk = win(t, 0.95e-3, 1.8e-3); tm = t[mk] * 1e3
        plot(ax[0], tm, r.get("V(load)", k)[mk], lab, k)
        plot(ax[1], tm, r.get("I(Lh)", k)[mk], f"{lab}: {m['ipk'][k]:.0f} A peak", k)
        plot(ax[2], tm, r.get("V(x1:xu:autoon)", k)[mk] * (1 - 0.05 * k), f"AUTO-ON, {lab}", k)
        plot(ax[2], tm, r.get("V(x1:xu:hsht)", k)[mk] * 0.8 - 0.05 * k, f"HSHT (x0.8), {lab}", k, ls="--")
    ax[0].set_ylabel("V(load) [V]"); ax[1].set_ylabel("load current [A]"); ax[2].set_ylabel("logic")
    ax[1].axhline(105.6, color=INK2, ls="--", lw=0.8)
    finish(fig, ax, "time [ms]  (BYPCTL on at 1 ms, OUTCTL stays off)", "tb28_bypass_precharge.png")


def tb29():
    r = raw("tb29_cross_short")
    m = meas_log(os.path.join(TB, "tb29_cross_short.log"))
    labs = ["to the 12 V battery wire", "to a DC/DC-fed 12 V branch", "same + 12 V OV monitor"]
    fig, ax = panels(3, "tb29 - 48 V harness touches a 12 V wire at 5 ms")
    for k, lab in enumerate(labs):
        t = r.get("time", k); mk = win(t, 4.95e-3, 7e-3); tm = t[mk] * 1e3
        plot(ax[0], tm, r.get("V(n12)", k)[mk], f"{lab}: peak {m['v12max'][k]:.0f} V", k)
        plot(ax[1], tm, r.get("I(Lh)", k)[mk], lab, k)
        plot(ax[2], tm, r.get("V(x1:xu:flt)", k)[mk] * (1 - 0.05 * k), lab, k)
    ax[0].axhline(16, color=C[7], ls="--", lw=0.8); ax[0].text(6.95, 18, "16 V", color=C[7], fontsize=8, ha="right")
    ax[0].set_ylabel("12 V node [V]"); ax[1].set_ylabel("48 V eFuse current [A]")
    ax[1].axhline(21.8, color=INK2, ls="--", lw=0.8); ax[1].set_ylim(-10, 160)
    ax[2].set_ylabel("eFuse latched off")
    finish(fig, ax, "time [ms]", "tb29_cross_short.png")


def tb30():
    r = raw("tb30_ground_fault")
    labs = ["ground OK", "ground degraded to 0.2 Ohm", "ground lost"]
    fig, ax = panels(3, "tb30 - load ECU ground fault at 5 ms: offset and loss")
    for k, lab in enumerate(labs):
        t = r.get("time", k); mk = win(t, 3e-3, 10e-3); tm = t[mk] * 1e3
        plot(ax[0], tm, r.get("V(lg)", k)[mk], lab, k)
        plot(ax[1], tm, r.get("V(rxi)", k)[mk], lab, k)
        plot(ax[2], tm, r.get("I(Rrx)", k)[mk] * 1e3, lab, k)
    ax[0].set_ylabel("ECU local ground [V]"); ax[0].set_ylim(-2, 52)
    ax[0].text(5.3, 20, "spike at 5 ms: ideal switch interrupting the 1 uH harness (clipped)", color=INK2, fontsize=8)
    ax[2].set_ylim(-20, 500)
    ax[1].axhline(1.5, color=INK2, ls="--", lw=0.8); ax[1].text(3.1, 1.7, "receiver threshold 1.5 V", color=INK2, fontsize=8)
    ax[1].set_ylabel("receiver input [V]")
    ax[2].set_ylabel("signal-line current [mA]")
    finish(fig, ax, "time [ms]", "tb30_ground_fault.png")


def tb31():
    r = raw("tb31_retry"); t = r["time"]
    m = meas_log(os.path.join(TB, "tb31_retry.log"))
    fig, ax = panels(4, "tb31 - retries: A = permanent short (back-off 1/2/4 ms), B = persistent 35 A overload",
                     sharex=False)
    mk = win(t, 1.8e-3, 11e-3); tm = t[mk] * 1e3
    plot(ax[0], tm, (r["V(vba)"][mk] - r["V(xa:drn)"][mk]) * 1e3, "A: FET current", 0)
    ax[0].set_ylabel("A: FET current [A]"); ax[0].set_xlabel("time [ms]")
    ax[0].set_title(f"first trip {m['ea1'][0] * 1e3:.0f} mJ; each retry {m['ea2'][0] * 1e3:.0f} mJ "
                    "(the FET slews up into the short)", loc="left", fontsize=9, fontweight="normal")
    plot(ax[1], tm, r["V(tfeta)"][mk], "A: FET junction", 1); ax[1].set_ylabel("A: junction [C]")
    ax[1].set_xlabel("time [ms]")
    tm = t * 1e3
    plot(ax[2], tm, r["I(Lhb)"], "B: current", 0); ax[2].set_ylabel("B: current [A]"); ax[2].set_xlabel("time [ms]")
    plot(ax[3], tm, r["V(xb:xu:fd)"], "B: fuse state fd", 1); ax[3].set_ylabel("B: fd")
    for x, lab in [(56.6, "retry 5 ms after trip"), (162.1, "retry 100 ms after trip")]:
        for a in ax[2:]:
            a.axvline(x, color=INK2, lw=0.8, ls=":")
        ax[3].text(x + 1.5, 0.5, lab, color=INK2, fontsize=8)
    finish(fig, ax, "time [ms]", "tb31_retry.png")


def tb32():
    r = raw("tb32_hw_vs_fw")
    m = meas_log(os.path.join(TB, "tb32_hw_vs_fw.log"))
    labs = ["hardware HSC", "VDS monitor only", "firmware only (1 ms)"]
    fig, ax = panels(3, "tb32 - the same short handled by HSC hardware, by the VDS monitor, by firmware")
    for k, lab in enumerate(labs):
        t = r.get("time", k); mk = win(t, 2.99e-3, 4.3e-3); tm = (t[mk] - 3e-3) * 1e3
        plot(ax[0], tm, ifet(r, k)[mk], f"{lab}: {m['ipk'][k]:.0f} A, {m['e_fet'][k]:.2g} J", k)
        plot(ax[1], tm, r.get("V(vbat)", k)[mk], lab, k)
        plot(ax[2], tm, r.get("V(tfet)", k)[mk], f"{lab}: {m['tjpk'][k]:.0f} C", k)
    ax[0].set_ylabel("FET current [A]"); ax[1].set_ylabel("VBAT [V]"); ax[2].set_ylabel("FET junction [C]")
    ax[2].axhline(175, color=C[7], ls="--", lw=0.8)
    finish(fig, ax, "time after the short [ms]", "tb32_hw_vs_fw.png")


def tb33():
    r = raw("tb33_design_exercise")
    m = meas_log(os.path.join(TB, "tb33_design_exercise.log"))
    fig, ax = panels(4, "tb33 - design exercise: 1 kW DC/DC, 2.64 mF (C max), 3 m of 2.5 mm2", sharex=False)
    for k, lab in [(0, "dV/dt, C_SLEW 68 nF -> HSC trip"), (1, "dV/dt, C_SLEW 220 nF -> VDS trip")]:
        t = r.get("time", k); mk = win(t, 0.9e-3, 2.5e-3); tm = t[mk] * 1e3
        plot(ax[0], tm, r.get("V(load)", k)[mk], lab, k)
        plot(ax[1], tm, ifet(r, k)[mk], lab, k)
    ax[0].set_ylabel("V(DC/DC in) [V]"); ax[0].set_xlabel("time [ms]")
    ax[0].axvspan(1.0, 1.96, color=GRID, alpha=0.5, lw=0); ax[0].text(1.02, 17, "VDS blanking", color=INK2, fontsize=8)
    ax[1].set_ylabel("FET current [A]"); ax[1].set_xlabel("time [ms]")
    ax[1].axhline(105.6, color=INK2, ls="--", lw=0.8)
    k = 2; t = r.get("time", k); mk = t < 105e-3; tm = t[mk] * 1e3
    plot(ax[2], tm, r.get("V(load)", k)[mk], "V(DC/DC in)", 0)
    plot(ax[2], tm, r.get("V(dcen)", k)[mk] * 40, "DC/DC running (x40)", 2)
    ax[2].axvline(m["t_pg"][k] * 1e3, color=INK2, lw=0.8, ls=":")
    ax[2].text(m["t_pg"][k] * 1e3 - 1, 20, "hand-over at 95 %", color=INK2, fontsize=8, ha="right")
    ax[2].set_ylabel("V"); ax[2].set_xlabel("time [ms]")
    ax[2].set_title(f"10 Ohm pre-charge: {m['e_pre'][k]:.1f} J and {m['p_pre'][k]:.0f} W peak in the resistor",
                    loc="left", fontsize=9, fontweight="normal")
    k = 3; t = r.get("time", k); mk = win(t, 109.99e-3, 110.06e-3); tu = (t[mk] - 110e-3) * 1e6
    plot(ax[3], tu, ifet(r, k)[mk], "FET current", 1)
    ax[3].set_ylabel("FET current [A]")
    ax[3].set_title(f"then a short at the DC/DC input: {m['isc'][k]:.0f} A peak, HSC latch after "
                    f"{m['dt_sc'][k] * 1e6:.1f} us", loc="left", fontsize=9, fontweight="normal")
    finish(fig, ax, "time after the short [us]", "tb33_design_exercise.png")


def tb34():
    r = raw("tb34_cold_start")
    labs = ["25 C typical", "-40 C: Vth +0.4 V, C -20 %, ESR x5, Rbat x4", "-40 C + gate drive at spec min (12 V)"]
    fig, ax = panels(3, "tb34 - debug J1: dV/dt start-up into a 1 kW DC/DC, warm vs cold")
    for k, lab in enumerate(labs):
        t = r.get("time", k); mk = win(t, 0.4e-3, 2.5e-3); tm = t[mk] * 1e3
        plot(ax[0], tm, r.get("V(out)", k)[mk], lab, k)
        plot(ax[1], tm, r.get("V(drn)", k)[mk] - r.get("V(out)", k)[mk], lab, k)
        plot(ax[2], tm, r.get("V(xu:vdsmax)", k)[mk] * (1 - 0.05 * k), f"VDS_MAX, {lab}", k)
        plot(ax[2], tm, r.get("V(xu:hsht)", k)[mk] * 0.5, f"HSHT (x0.5), {lab}", k, ls="--")
    ax[0].set_ylabel("OUT [V]"); ax[1].set_ylabel("VDS [V]"); ax[1].set_ylim(-1, 20)
    ax[1].axhline(1.0, color=INK2, lw=0.8, ls="--")
    for a in ax[:2]:
        a.axvspan(0.5, 1.46, color=GRID, alpha=0.5, lw=0)
    ax[1].text(0.55, 17, "VDS blanking 960 us", color=INK2, fontsize=8)
    ax[2].set_ylabel("latched fault")
    finish(fig, ax, "time [ms]", "tb34_cold_start.png")


def tb35():
    r = raw("tb35_field_return")
    m = meas_log(os.path.join(TB, "tb35_field_return.log"))
    labs = ["healthy", "cracked Kelvin sense (reads 50 %)", "FET shorted at 1 s", "pre-charge path stuck on"]
    fig, ax = panels(3, "tb35 - debug J5: overload from 2 s, MCU switches off at 6 s")
    for k, lab in enumerate(labs):
        t = r.get("time", k)
        plot(ax[0], t, r.get("V(tw)", k), f"{lab}: {m['twmax'][k]:.0f} C max", k)
        plot(ax[1], t, r.get("I(Lh)", k), lab, k)
        plot(ax[2], t, r.get("V(xu:fusel)", k) * (1 - 0.04 * k), f"FUSE_LATCH, {lab}", k)
        plot(ax[2], t, -0.2 - r.get("V(pl)", k) * (1 - 0.04 * k), f"plausibility flag, {lab}", k, ls="--")
    ax[0].axhline(125, color=C[7], ls="--", lw=0.8); ax[0].set_ylabel("branch wire [C]")
    ax[1].set_ylabel("branch current [A]")
    ax[2].set_yticks([-1.2, 0, 1]); ax[2].set_yticklabels(["plausibility flag", "0", "FUSE_LATCH"])
    ax[2].set_ylabel("logic")
    for a in ax:
        a.axvline(2, color=INK2, lw=0.8, ls=":"); a.axvline(6, color=INK2, lw=0.8, ls=":")
    finish(fig, ax, "time [s]", "tb35_field_return.png")


def tb36():
    r = raw("tb36_dcdc_hiccup_vs_efuse")
    m = meas_log(os.path.join(TB, "tb36_dcdc_hiccup_vs_efuse.log"))
    labs = ["DC/DC EN gated by pre-charge PG", "DC/DC EN at key-on (own UVLO only)",
            "EN gated + 12 V load above ILIM (0.1 Ohm)"]
    fig, ax = panels(4, "tb36 - debug J4: pre-charge (4.7 Ohm, 4.67 mF) into the DCDC48_12, 12 V rail without battery")
    for k, lab in enumerate(labs):
        t = r.get("time", k) * 1e3
        run = r.get("V(xdc:run)", k)
        n = int(np.sum((run[1:] > 0.5) & (run[:-1] <= 0.5)))
        z = 3 if k == 0 else 2  # case 0 on top where the traces coincide
        plot(ax[0], t, r.get("V(load)", k), lab, k, zorder=z)
        plot(ax[1], t, r.get("V(v12)", k), f"{lab}: {n} start(s)", k, zorder=z)
        plot(ax[2], t, r.get("I(Lh)", k) + r.get("I(Rpre)", k), lab, k, zorder=z)
        plot(ax[3], t, run * (1 - 0.05 * k), f"DC/DC running, {lab}", k, zorder=z)
    for y in (26, 30):
        ax[0].axhline(y, color=INK2, ls="--", lw=0.8)
    ax[0].text(130, 31.5, "DC/DC UVLO 30 / 26 V", color=INK2, fontsize=8)
    for a in ax:
        a.axvline(101, color=INK2, lw=0.8, ls=":")
    ax[0].text(102, 8, "pre-charge timeout", color=INK2, fontsize=8)
    nflt = sum(1 for v in m["fltmax"] if v > 0.5)
    ax[3].text(110, 0.45, f"eFuse latched faults: {nflt} of 3 cases", color=INK2, fontsize=8)
    ax[0].set_ylabel("DC/DC input [V]"); ax[1].set_ylabel("12 V rail [V]")
    ax[2].set_ylabel("48 V feed (eFuse +\npre-charge) [A]"); ax[2].set_ylim(-1, 20)
    ax[3].set_ylabel("logic"); ax[3].set_yticks([0, 1]); ax[3].set_yticklabels(["off", "run"])
    finish(fig, ax, "time [ms]", "tb36_dcdc_hiccup_vs_efuse.png")


def iv_b2():
    """Time scales of the protection layers: datasheet ranges and simulated trips."""
    g = lambda tb, key, k=0: meas_log(os.path.join(TB, tb + ".log"))[key][k]
    t3 = meas_log(os.path.join(TB, "tb03_i2t_curve.log"))["ttrip"][0::2]
    rows = [  # label, range lo, hi, simulated value, source
        ("hard short (HSC)", 5e-6, 10e-6, g("tb02_hard_short", "dt_trip"), "tb02"),
        ("gate under-voltage (VGS_LOW)", 8e-6, 20e-6, None, ""),
        ("supply under-voltage", 33e-6, 50e-6, None, ""),
        ("VDS desaturation", 10e-6, 970e-6, g("tb05_vds_desat", "dt_vds", 1), "tb05 (at turn-on)"),
        ("I2t (tNOM = 1 s ... 511 s)", 61e-6, 511, None, ""),
        ("FET over-temperature (NTC)", 0.3, 30, g("tb07_ntc_overtemp", "t_ot"), "tb07"),
    ]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.set_title("Protection layers and their time scales (VNF1048F model)", loc="left")
    for i, (lab, lo, hi, sim, src) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot([lo, hi], [y, y], color=C[0], lw=6, solid_capstyle="butt")
        if sim:
            ax.plot(sim, y, "o", color=C[1], ms=8, mec=SURF, mew=2)
            ax.text(sim * 1.4, y + 0.25, f"{src}: {sim * 1e6:.0f} us" if sim < 1e-2 else f"{src}: {sim:.1f} s",
                    fontsize=8, color=INK2)
    yi = rows.index(rows[4]); y = len(rows) - 1 - yi
    ax.plot(min(t3), y, "o", color=C[1], ms=8, mec=SURF, mew=2)
    ax.plot(max(t3), y, "o", color=C[1], ms=8, mec=SURF, mew=2)
    ax.text(2e-4, y + 0.25, f"tb03 (tNOM 1 s): {min(t3) * 1e6:.0f} us ... {max(t3):.1f} s", fontsize=8, color=INK2)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r_[0] for r_ in rows][::-1])
    ax.set_xscale("log"); ax.set_xlim(1e-6, 1e3); ax.set_ylim(-0.6, len(rows) - 0.3)
    ax.set_xlabel("time to switch off [s]")
    ax.plot([], [], color=C[0], lw=6, label="datasheet / design range")
    ax.plot([], [], "o", color=C[1], label="simulated")
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout(); fig.savefig(os.path.join(IMG, "iv_b2_timescales.png"), dpi=110); plt.close(fig)
    print("  -> iv_b2_timescales.png")


def iv_h2():
    """Measuring the tb02 short: probe bandwidth, saturation and skew applied to the simulated waveforms."""
    r = raw("tb02_hard_short"); t = r["time"]; i = (r["V(vbat)"] - r["V(x1:drn)"]) * 1e3
    vds = r["V(x1:drn)"] - r["V(out)"]
    mk = win(t, 2.99e-3, 3.06e-3)
    dt = 2e-9; tu = np.arange(t[mk][0], t[mk][-1], dt); iu = np.interp(tu, t, i); vu = np.interp(tu, t, vds)
    fig, ax = panels(2, "Measuring the tb02 short: the same event through different probes and set-ups", h=2.8,
                     sharex=False)
    tus = (tu - 3e-3) * 1e6
    plot(ax[0], tus, iu, f"true (simulated): {iu.max():.0f} A", 0, lw=2.2)
    for k, (bw, lab) in enumerate([(20e6, "20 MHz current probe"), (500e3, "500 kHz clamp"),
                                   (50e3, "50 kHz clamp meter")], start=1):
        a = math.exp(-2 * math.pi * bw * dt); y = np.empty_like(iu); y[0] = iu[0]
        for n in range(1, len(iu)):
            y[n] = a * y[n - 1] + (1 - a) * iu[n]
        plot(ax[0], tus, y, f"{lab}: {y.max():.0f} A", k)
    plot(ax[0], tus, np.minimum(iu, 150), "probe saturating at 150 A", 4, ls="--")
    ax[0].set_ylabel("FET current [A]"); ax[0].set_xlabel("time after the short [us]")
    e0 = np.sum(vu * iu) * dt
    for k, sk in enumerate([0, 0.5e-6, 1e-6, 2e-6]):
        n = int(round(sk / dt)); ish = np.concatenate([np.full(n, iu[0]), iu[:len(iu) - n]])
        p_ = vu * ish; e = np.sum(p_) * dt
        lab = "deskewed" if k == 0 else f"current probe {sk * 1e6:g} us late"
        plot(ax[1], tus, p_ / 1e3, f"{lab}: E = {e * 1e3:.1f} mJ ({100 * (e / e0 - 1):+.0f} %)", k)
    ax[1].set_ylabel("VDS x I [kW]"); ax[1].set_xlim(-2, 30)
    finish(fig, ax, "time after the short [us]", "iv_h2_probes.png")


def iv_h4():
    """Wire damage curve vs eFuse trip curve, with sense tolerance (illustrative wire)."""
    inom = 21.8
    i = np.logspace(np.log10(inom * 1.001), np.log10(105.6), 600)
    x = i / inom
    tau, dt_rated, dt_max = 30.0, 50.0, 55.0                  # wire: +50 K at INOM, 55 K allowed
    dts = dt_rated * x ** 2
    wire = np.where(dts > dt_max, -tau * np.log(1 - dt_max / np.maximum(dts, dt_max + 1e-9)), np.nan)
    def step(xx, tnom):
        mm = np.maximum(0, np.floor(np.log2(32 * (xx ** 2 - 1))))
        return tnom / 2 ** mm
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.set_title("Wire damage curve vs eFuse trip curve (INOM 21.8 A, sense tolerance +-5 %)", loc="left")
    ax.loglog(i, wire, color=C[7], lw=2, label="wire damage (illustrative: tau 30 s, +55 K allowed)")
    for k, tnom in enumerate([31, 511]):
        ax.loglog(i, step(x, tnom), color=C[k], lw=1.6, label=f"eFuse, tNOM = {tnom} s (stepwise)")
        lo, hi = step(x * 1.05, tnom), step(np.maximum(x * 0.95, 1.0001), tnom)
        hi = np.where(x * 0.95 > 1, hi, np.nan)
        ax.fill_between(i, lo, hi, color=C[k], alpha=0.12, lw=0)
    m = meas_log(os.path.join(TB, "tb03_i2t_curve.log"))
    xs, ts = np.array(m["xavg"][0::2]), np.array(m["ttrip"][0::2])
    sel = xs * inom <= 105.6
    ax.loglog(xs[sel] * inom, ts[sel] * 31, "o", color=C[0], ms=6, mfc=SURF, mew=1.5,
              label="tb03 simulated points, scaled to tNOM 31 s")
    ax.axvline(inom * math.sqrt(dt_max / dt_rated), color=INK2, lw=0.8, ls=":")
    ax.text(inom * math.sqrt(dt_max / dt_rated) * 1.02, 2e-3, "wire limit current", color=INK2, fontsize=8, rotation=90)
    ax.set_xlabel("current [A]"); ax.set_ylabel("time [s]"); ax.set_ylim(1e-3, 1e4); ax.set_xlim(20, 110)
    ax.legend(loc="upper right")
    fig.tight_layout(); fig.savefig(os.path.join(IMG, "iv_h4_wire_vs_fuse.png"), dpi=110); plt.close(fig)
    print("  -> iv_h4_wire_vs_fuse.png")


# ---------------------------------------------------------------------------
# battery model benches (models/BATTERY_beh.lib)
BAT = {12: dict(cap=70, v0=11.70, v100=12.90, veoc=15.0, r0=2.0e-3, r1=0.8e-3, r2=0.7e-3, l=0.2e-6),
       48: dict(cap=10, v0=40.0, v100=52.0, veoc=55.0, r0=15e-3, r1=5e-3, r2=5e-3, l=1e-6)}
from bat_ocv import ocv as _bat_ocv  # noqa: E402  (complete OCV curve of the .lib)


def bat_ocv(c, s):
    return np.vectorize(lambda x: _bat_ocv(x, c["v0"], c["v100"], c["veoc"]))(np.asarray(s, dtype=float))


def bat_ft(temp):
    return np.exp(1200 * (1 / (np.asarray(temp) + 273.15) - 1 / 298.15))


def bat01():
    r0 = raw("bat01_capacity_ocv"); tu = np.arange(0, r0["time"][-1], 5.0)
    r = {n: np.interp(tu, r0["time"], r0[n]) for n in r0.names[1:]}    # 5 s resolution
    t = tu / 3600
    fig, ax = panels(4, "bat01 - 1C pulsed OCV test, discharge to cut-off and CC-CV charge (12 V 70 Ah, 48 V 10 Ah)")
    plot(ax[0], t, r["V(p12)"], "terminal", 0); plot(ax[0], t, r["V(x12:ocv)"], "OCV (internal)", 1)
    ax[0].set_ylabel("12 V class [V]"); ax[0].set_ylim(10, 15)
    plot(ax[1], t, r["V(p48)"], "terminal", 0); plot(ax[1], t, r["V(x48:ocv)"], "OCV (internal)", 1)
    ax[1].set_ylabel("48 V class [V]"); ax[1].set_ylim(34, 55)
    plot(ax[2], t, r["V(soc12)"], "SOC pin, 12 V", 0); plot(ax[2], t, r["V(soc48)"], "SOC pin, 48 V", 1, ls="--")
    ax[2].set_ylabel("SOC [-]")
    plot(ax[3], t, r["I(x12:Vi)"] / 70, "12 V (1C = 70 A)", 0)
    plot(ax[3], t, r["I(x48:Vi)"] / 10, "48 V (1C = 10 A)", 1, ls="--")
    ax[3].set_ylabel("I / 1C (+ = discharge)")
    finish(fig, ax, "time [h]", "bat01_capacity_ocv.png")
    m = meas_log(os.path.join(TB, "bat01_capacity_ocv.log"))
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    fig.suptitle("bat01 - OCV(SOC): model curve and simulated rest voltages", x=0.02, ha="left",
                 fontsize=11, fontweight="bold", color=INK)
    sx = np.linspace(-0.02, 1.02, 600)
    for a, v in zip(ax, (12, 48)):
        c = BAT[v]
        a.plot(sx * 100, bat_ocv(c, sx), color=C[0], label="OCV(SOC) of the model")
        a.plot([100 - 10 * k for k in range(1, 10)], [m[f"vr{v}_{k}"][0] for k in range(1, 10)], "o",
               color=C[1], ms=6, mfc=SURF, mew=1.5, label="rest voltage after each 10 % step")
        a.axvspan(-2, 0, color=GRID, alpha=0.6, lw=0); a.axvspan(100, 102, color=GRID, alpha=0.6, lw=0)
        a.set_title(f"{v} V class (defaults)", loc="left"); a.set_xlabel("SOC [%]"); a.set_ylabel("V")
        a.set_ylim(c["v0"] - 0.08 * c["v100"], c["veoc"] * 1.01)
        a.text(1, c["v0"] - 0.06 * c["v100"], "end of\ndischarge", fontsize=7, color=INK2)
        a.text(82, c["veoc"] * 0.985, "end of charge", fontsize=7, color=INK2)
    ax[0].legend(loc="upper left")
    fig.tight_layout(rect=(0, 0, 1, 0.93)); fig.savefig(os.path.join(IMG, "bat01_ocv_curve.png"), dpi=110)
    plt.close(fig); print("  -> bat01_ocv_curve.png")


def bat02():
    r = raw("bat02_pulse_temperature")
    m = meas_log(os.path.join(TB, "bat02_pulse_temperature.log"))
    T = [-30, -18, 0, 25, 45]
    fig, ax = panels(3, "bat02 - 100 A / 10 s pulse at 50 % SOC, -30 ... +45 degC", sharex=False)
    tu = np.arange(0, 71, 0.02)                                         # 20 ms resolution
    for k, temp in enumerate(T):
        tt = r.get("time", k)
        plot(ax[0], tu, np.interp(tu, tt, r.get("V(p12)", k)), f"{temp:+d} degC", k)
        plot(ax[1], tu, np.interp(tu, tt, r.get("V(p48)", k)), f"{temp:+d} degC", k)
    ax[0].set_ylabel("12 V class [V]"); ax[1].set_ylabel("48 V class [V]")
    for a in ax[:2]:
        a.set_xlabel("time [s]")
    tc = np.linspace(-35, 50, 100)
    ax[2].plot(tc, bat_ft(tc), color=INK2, lw=1, ls="--", label="FT(T) = exp(1200 K (1/T - 1/298 K))")
    ax[2].plot(T, np.array(m["r0_12"]) / m["r0_12"][3], "o", color=C[0], ms=6, mfc=SURF, mew=1.5,
               label="R0 measured, 12 V")
    ax[2].plot(T, np.array(m["r0_48"]) / m["r0_48"][3], "s", color=C[1], ms=4, label="R0 measured, 48 V")
    ax[2].plot(T, np.array(m["r10_12"]) / m["r10_12"][3], "^", color=C[2], ms=5, label="R(10 s) measured, 12 V")
    ax[2].set_ylabel("R(T) / R(25 degC)")
    finish(fig, ax, "battery temperature [degC]", "bat02_pulse_temperature.png")


def bat03():
    r = raw("bat03_impedance_ac"); f = r["frequency"].real
    fig, ax = panels(2, "bat03 - output impedance |Z(f)| and phase, 50 % SOC, 25 degC", h=2.6)
    for k, v in enumerate((12, 48)):
        c = BAT[v]; z = r[f"V(p{v})"]
        jw = 2j * np.pi * f
        za = (c["r0"] + c["r1"] / (1 + jw * 20e-3) + c["r2"] / (1 + jw * 20)) * 1.125 + 1 / (1 / (jw * c["l"]) + 1 / 100)
        ax[0].loglog(f, np.abs(z) * 1e3, color=C[k], label=f"{v} V class, simulated")
        ax[0].loglog(f, np.abs(za) * 1e3, color=C[k], ls=":", lw=2.4, label=f"{v} V class, analytic")
        ax[1].semilogx(f, np.degrees(np.angle(z)), color=C[k], label=f"{v} V class")
    for fc, lab in [(1 / (2 * np.pi * 20), "TAU2"), (1 / (2 * np.pi * 20e-3), "TAU1")]:
        for a in ax:
            a.axvline(fc, color=INK2, lw=0.8, ls="--")
        ax[0].text(fc * 1.15, 60, lab, color=INK2, fontsize=8)
    ax[0].set_ylabel("|Z| [mOhm]"); ax[1].set_ylabel("phase [deg]")
    ax[0].text(2e3, 0.3e3, "L_INT", color=INK2, fontsize=8)
    finish(fig, ax, "frequency [Hz]", "bat03_impedance_ac.png")


def bat04():
    r = raw("bat04_cold_crank"); t = r["time"]
    fig, ax = panels(3, "bat04 - engine crank at +25 / -18 / -30 degC (SOC 80 %) and CCA test", sharex=False)
    mk = t <= 1.6
    for k, (n, lab) in enumerate([("b", "+25 degC"), ("c", "-18 degC"), ("d", "-30 degC")]):
        plot(ax[0], t[mk], r[f"V(p{n})"][mk], lab, k)
        plot(ax[1], t[mk], r[f"I(Lc{n.upper()})"][mk], lab, k)
    ax[0].set_ylabel("battery terminal [V]"); ax[1].set_ylabel("starter current [A]"); ax[0].set_ylim(5, 15)
    ax[0].set_xlabel("time [s]")
    plot(ax[2], t, r["V(pa)"], "terminal voltage, 700 A from 1 s, -18 degC", 0)
    ax[2].axhline(7.2, color=INK2, ls="--", lw=0.8); ax[2].text(2, 7.35, "7.2 V at 30 s (SAE J537)", color=INK2,
                                                               fontsize=8)
    ax[2].set_ylabel("CCA test [V]"); ax[2].set_ylim(6, 13.5)
    finish(fig, ax, "time [s]", "bat04_cold_crank.png")


def bat05():
    r = raw("bat05_short_circuit"); t = r["time"] * 1e3
    fig, ax = panels(3, "bat05 - bolted terminal short: 12 V battery (unprotected) and 48 V pack with BMS")
    plot(ax[0], t, r["I(LA)"] / 1e3, "12 V: short current [kA]", 0)
    plot(ax[0], t, r["V(pa)"] / 10, "12 V: terminal voltage / 10 [V]", 1)
    ax[0].set_ylabel("12 V battery")
    plot(ax[1], t, r["I(xb:Vsw)"] / 1e3, "48 V: pack current [kA]", 0)
    plot(ax[1], t, r["I(LB)"] / 1e3, "48 V: current in the short [kA]", 2)
    ax[1].axhline(1.0, color=INK2, ls="--", lw=0.8); ax[1].text(2.5, 1.07, "I_SC 1 kA", color=INK2, fontsize=8)
    ax[1].set_ylabel("kA")
    plot(ax[2], t, r["V(xb:bs)"] - r["V(pb)"], "voltage across the pack switch", 0)
    plot(ax[2], t, r["V(pb)"], "pack terminal", 1); plot(ax[2], t, r["V(fltb)"] * 10, "FLT x 10", 3)
    ax[2].set_ylabel("V")
    for a in ax:
        a.set_xlim(0.9, 3)
    finish(fig, ax, "time [ms]", "bat05_short_circuit.png")


def bat06():
    r = raw("bat06_bms_protection"); t = r["time"]
    fig, ax = panels(4, "bat06 - 48 V pack BMS: pre-charge, overcurrent, under-/over-voltage", sharex=False)
    mk = t <= 0.8
    plot(ax[0], t[mk], r["V(pa)"][mk], "bus, with pre-charge", 0)
    plot(ax[0], t[mk], r["V(pb)"][mk], "bus, without pre-charge (SC trip)", 1)
    plot(ax[0], t[mk], r["V(fltb)"][mk] * 10, "FLT x 10, without pre-charge", 3)
    ax[0].set_ylabel("V"); ax[0].set_xlabel("time [s]")
    mk = win(t, 0.099, 0.1004)
    plot(ax[1], (t[mk] - 0.1) * 1e3, r["I(xb:Vsw)"][mk], "pack current, no pre-charge", 1)
    plot(ax[1], (t[mk] - 0.1) * 1e3, r["I(xa:Vsw)"][mk] * 100, "pack current, with pre-charge x 100", 0)
    ax[1].axhline(1000, color=INK2, ls="--", lw=0.8); ax[1].text(0.3, 1050, "I_SC", color=INK2, fontsize=8)
    ax[1].set_ylabel("A"); ax[1].set_xlabel("time after EN [ms]")
    mk = t <= 5
    plot(ax[2], t[mk], r["I(xc:Vsw)"][mk], "pack current (overload ~400 A)", 0)
    plot(ax[2], t[mk], r["V(fltc)"][mk] * 80, "FLT x 80", 3); plot(ax[2], t[mk], r["V(enc)"][mk] * 100, "EN x 100", 2)
    ax[2].set_ylim(-150, 700)
    ax[2].axhline(350, color=INK2, ls="--", lw=0.8); ax[2].text(0.05, 365, "I_OC", color=INK2, fontsize=8)
    ax[2].set_ylabel("A"); ax[2].set_xlabel("time [s]")
    plot(ax[3], t, r["V(xd:vm)"], "D: BMS voltage, 100 A from SOC 10 %", 0)
    plot(ax[3], t, r["V(xe:vm)"], "E: BMS voltage, faulty 56 V charger", 1)
    plot(ax[3], t, r["V(fltd)"] * 3 + 15, "D: FLT (offset)", 2)
    plot(ax[3], t, r["V(flte)"] * 3 + 15, "E: FLT (offset)", 3, ls="--")
    for y, lab in [(36, "V_UV"), (54, "V_OV")]:
        ax[3].axhline(y, color=INK2, ls="--", lw=0.8); ax[3].text(1, y + 0.4, lab, color=INK2, fontsize=8)
    ax[3].set_ylabel("V")
    finish(fig, ax, "time [s]", "bat06_bms_protection.png")


def bat07():
    r = raw("bat07_pdn_48v"); t = r["time"] * 1e3
    fig, ax = panels(3, "bat07 - 48 V PDU fed by the battery pack: CH2 short 15 ms, BSG 25 ms, pack opens 35 ms")
    plot(ax[0], t, r["V(bus)"], "48 V bus", 0); plot(ax[0], t, r["V(bat)"], "pack terminal", 1)
    plot(ax[0], t, r["V(d1)"], "DC/DC input (CH1)", 2); ax[0].set_ylabel("V"); ax[0].set_ylim(20, 85)
    plot(ax[1], t, r["I(xbat:Vsw)"], "pack current (+ = discharge)", 0)
    plot(ax[1], t, r["I(Lh2)"], "CH2 (motor) current", 2); plot(ax[1], t, -r["I(Dtvs)"], "TVS current", 3)
    ax[1].set_ylabel("A"); ax[1].set_ylim(-60, 120)
    plot(ax[2], t, r["V(diag2)"] / 3.3, "DIAG CH2", 2); plot(ax[2], t, r["V(fltb)"] / 3.3 * 0.95, "pack FLT (x0.95)", 3)
    plot(ax[2], t, r["V(xbat:x)"] * 0.9, "pack switch state (x0.9)", 0); plot(ax[2], t, r["V(greg)"] * 0.85,
                                                                              "BSG regulator (x0.85)", 1)
    ax[2].set_ylabel("logic")
    finish(fig, ax, "time [ms]", "bat07_pdn_48v.png")


# ---------------------------------------------------------------------------
# DC/DC benches (models/DCDC48_12_beh.lib)
def dc01():
    m = meas_log(os.path.join(TB, "dc01_efficiency.log"))
    VI, IL = [36, 48, 54], [2.5, 5, 10, 20, 30, 40, 50]
    fig, ax = panels(2, "dc01 - 700 W 48/12 V DC/DC: efficiency and input current vs load", h=2.6)
    for j, v in enumerate(VI):
        eta = [100 * m["pout"][3 * k + j] / m["pin"][3 * k + j] for k in range(len(IL))]
        iin = [m["iin"][3 * k + j] for k in range(len(IL))]
        pw = [14 * i for i in IL]
        ax[0].plot(pw, eta, "o-", color=C[j], ms=5, label=f"VIN = {v} V")
        ax[1].plot(pw, iin, "o-", color=C[j], ms=5, label=f"VIN = {v} V")
    ax[0].set_ylabel("efficiency [%]"); ax[0].set_ylim(80, 98)
    ax[1].set_ylabel("input current [A]")
    for a in ax:
        a.axvline(700, color=INK2, ls="--", lw=0.8)
    ax[0].text(705, 82, "700 W", color=INK2, fontsize=8)
    finish(fig, ax, "output power [W]", "dc01_efficiency.png")


def dc02():
    r = raw("dc02_load_transient"); t = r["time"] * 1e3
    fig, ax = panels(3, "dc02 - load steps: COUT only (+25 A, +45 A) and with a 12 V battery on the output")
    mk = win(t, 7.5, 12)
    plot(ax[0], t[mk], r["V(oa)"][mk], "COUT only, +25 A", 0); plot(ax[0], t[mk], r["V(ob)"][mk], "COUT only, +45 A", 1)
    plot(ax[0], t[mk], r["V(oc)"][mk], "with 12 V battery, +25 A", 2); ax[0].set_ylabel("VOUT [V]")
    plot(ax[1], t[mk], r["V(xa:il)"][mk], "il, +25 A", 0); plot(ax[1], t[mk], r["V(xb:il)"][mk], "il, +45 A", 1)
    plot(ax[1], t[mk], r["V(xc:il)"][mk], "il, with battery", 2)
    ax[1].axhline(55, color=INK2, ls="--", lw=0.8); ax[1].text(7.55, 56.5, "I_LIM 55 A", color=INK2, fontsize=8)
    ax[1].set_ylabel("DC/DC current [A]")
    plot(ax[2], t[mk], -r["I(Lbc)"][mk], "12 V battery current (+ = charging)", 2); ax[2].set_ylabel("A")
    finish(fig, ax, "time [ms]", "dc02_load_transient.png")


def dc03():
    r = raw("dc03_startup"); t = r["time"] * 1e3
    fig, ax = panels(3, "dc03 - start-up: soft-start, pre-biased 12 V battery, bidirectional sink")
    plot(ax[0], t, r["V(oa)"], "VOUT, 2 Ohm load", 0); plot(ax[0], t, r["V(xa:vref)"], "reference", 1, ls="--")
    plot(ax[0], t, r["V(ob)"], "VOUT, 12 V battery on the output", 2); plot(ax[0], t, r["V(pga)"], "PG (2 Ohm case)", 3)
    ax[0].set_ylabel("V")
    plot(ax[1], t, r["V(xb:il)"], "il, battery on the output", 2); plot(ax[1], t, -r["I(VinB)"] * 10, "input current x 10", 4)
    ax[1].set_ylabel("A")
    plot(ax[2], t, r["V(xc:il)"], "il, BIDIR=1, output pulled to 14.5 V", 5)
    plot(ax[2], t, -r["I(VinC)"], "input current (< 0: power to 48 V)", 6); ax[2].set_ylabel("A")
    finish(fig, ax, "time [ms]", "dc03_startup.png")


def dc04():
    r = raw("dc04_short_overload"); t = r["time"] * 1e3
    fig, ax = panels(3, "dc04 - output short 10..150 ms (hiccup) and a discharged 12 V battery (constant current)")
    plot(ax[0], t, r["V(oa)"], "VOUT, shorted output", 0); plot(ax[0], t, r["V(ob)"], "VOUT, discharged battery", 2)
    ax[0].set_ylabel("V")
    plot(ax[1], t, r["V(xa:il)"], "il, shorted output", 0); plot(ax[1], t, r["V(xb:il)"], "il, discharged battery", 2, ls="--")
    ax[1].set_ylabel("A")
    plot(ax[2], t, r["V(xa:run)"], "running (short case)", 0); plot(ax[2], t, r["V(xa:hic)"] * 0.9, "hiccup off-time (x0.9)", 1)
    ax[2].set_ylabel("logic")
    finish(fig, ax, "time [ms]", "dc04_short_overload.png")


def dc05():
    r = raw("dc05_input_transients"); t = r["time"] * 1e3
    fig, ax = panels(3, "dc05 - input profile: UVLO 26/30 V, OVP 60/58 V, constant-power input current")
    plot(ax[0], t, r["V(vin)"], "VIN", 0); plot(ax[0], t, r["V(out)"], "VOUT", 1); ax[0].set_ylabel("V")
    for y in (26, 30, 58, 60):
        ax[0].axhline(y, color=GRID, lw=0.8)
    plot(ax[1], t, -r["I(Vin)"], "input current (392 W load)", 0); ax[1].set_ylabel("A"); ax[1].set_ylim(-1, 20)
    plot(ax[2], t, r["V(x1:uvok)"], "input above UVLO", 0); plot(ax[2], t, r["V(x1:ovp)"] * 0.9, "OVP (x0.9)", 1)
    plot(ax[2], t, r["V(x1:run)"] * 0.8, "running (x0.8)", 2); ax[2].set_ylabel("logic")
    finish(fig, ax, "time [ms]", "dc05_input_transients.png")


def dc06():
    r = raw("dc06_impedance_ac"); f = r["frequency"].real
    fig, ax = panels(2, "dc06 - output and input impedance (25 A load, VIN 48 V)", h=2.6)
    ax[0].loglog(f, np.abs(r["V(out1)"]) * 1e3, color=C[0], label="|Zout|")
    ax[0].axvline(3e3, color=INK2, ls="--", lw=0.8); ax[0].text(3.3e3, 0.5, "FC 3 kHz", color=INK2, fontsize=8)
    ax[0].set_ylabel("|Zout| [mOhm]")
    zi = r["V(vin2)"]
    ax[1].semilogx(f, np.abs(zi), color=C[1], label="|Zin|")
    ax[1].semilogx(f, zi.real, color=C[2], ls="--", label="Re(Zin) (< 0: negative resistance)")
    ax[1].axhline(0, color=INK2, lw=0.6); ax[1].set_ylabel("Zin [Ohm]"); ax[1].set_ylim(-8, 8)
    finish(fig, ax, "frequency [Hz]", "dc06_impedance_ac.png")


def dc07():
    r = raw("dc07_input_filter_stability"); t = r["time"] * 1e3
    fig, ax = panels(2, "dc07 - input-filter stability: 2 uH + 470 uF (A), 10 uH + 22 uF (B), B + damper (C)")
    plot(ax[0], t, r["V(ia)"], "A: VIN", 0); plot(ax[0], t, r["V(ib)"], "B: VIN (unstable)", 1)
    plot(ax[0], t, r["V(ic)"], "C: VIN (damped)", 2); ax[0].set_ylabel("V")
    plot(ax[1], t, r["V(oa)"], "A: VOUT", 0); plot(ax[1], t, r["V(ob)"], "B: VOUT", 1); plot(ax[1], t, r["V(oc)"], "C: VOUT", 2)
    ax[1].set_ylabel("V")
    finish(fig, ax, "time [ms]", "dc07_input_filter_stability.png")


def dc08():
    r = raw("dc08_pdn_48v_12v"); t = r["time"] * 1e3
    fig, ax = panels(3, "dc08 - 48 V pack -> eFuse -> DC/DC -> 12 V net: start-up, 12 V load step 20 ms, 48 V short 30 ms")
    plot(ax[0], t, r["V(bus)"], "48 V bus", 0); plot(ax[0], t, r["V(d1)"], "DC/DC input (CH1)", 1)
    plot(ax[0], t, r["V(b12)"] * 3, "12 V net x 3", 2); ax[0].set_ylabel("V"); ax[0].set_ylim(0, 60)
    plot(ax[1], t, r["I(Lh1)"], "CH1 (DC/DC input) current", 1); plot(ax[1], t, r["V(xdc:il)"], "DC/DC output current", 2)
    plot(ax[1], t, -r["I(xb12:Vi)"], "12 V battery (+ = charging)", 3); ax[1].set_ylabel("A"); ax[1].set_ylim(-20, 80)
    plot(ax[2], t, r["V(xdc:run)"], "DC/DC running", 2); plot(ax[2], t, r["V(diag2)"] / 3.3 * 0.9, "DIAG CH2 (x0.9)", 0)
    plot(ax[2], t, r["V(pgdc)"] / 3.3 * 0.8, "DC/DC PG (x0.8)", 1); ax[2].set_ylabel("logic")
    finish(fig, ax, "time [ms]", "dc08_pdn_48v_12v.png")


ALL = dict(tb01=tb01, tb02=tb02, tb03=tb03, tb04=tb04, tb05=tb05, tb06=tb06,
           tb07=tb07, tb08=tb08, tb09=tb09, tb10=tb10, tb11=tb11, tb12=tb12,
           tb13=tb13, tb14=tb14, tb15=tb15, tb16=tb16, tb17=tb17, tb18=tb18, tb19=tb19,
           tb20=tb20, tb21=tb21, tb22=tb22, tb23=tb23, tb24=tb24, tb25=tb25, tb26=tb26,
           tb27=tb27, tb28=tb28, tb29=tb29, tb30=tb30, tb31=tb31, tb32=tb32, tb33=tb33,
           tb34=tb34, tb35=tb35, tb36=tb36, iv_b2=iv_b2, iv_h2=iv_h2, iv_h4=iv_h4,
           bat01=bat01, bat02=bat02, bat03=bat03, bat04=bat04, bat05=bat05, bat06=bat06, bat07=bat07,
           dc01=dc01, dc02=dc02, dc03=dc03, dc04=dc04, dc05=dc05, dc06=dc06, dc07=dc07, dc08=dc08)

if __name__ == "__main__":
    sel = sys.argv[1:] or list(ALL)
    bad = []
    for k in sel:
        print(k)
        try:
            ALL[k]()
        except Exception as e:  # noqa: BLE001  (one broken bench must not stop the others)
            print(f"!! {k}: {type(e).__name__}: {e}")
            bad.append(k)
        plt.close("all")
    if bad:
        print(f"!! {len(bad)} plot(s) failed: {' '.join(bad)}")
    sys.exit(1 if bad else 0)
