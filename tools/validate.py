"""Check the simulation results against the datasheet (DS13084 Rev 6) and the
expected application behaviour. Writes docs/VALIDATION.md and exits non-zero
if any check fails.

    tools/run_ltspice.sh testbenches/*.cir schematics/*.asc
    python3 tools/validate.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ltraw import meas_log  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TB = os.path.join(ROOT, "testbenches")
rows, fails = [], 0


def m(tb, key, k=0, folder=TB):
    v = meas_log(os.path.join(folder, tb + ".log")).get(key.lower(), [])
    return v[k] if len(v) > k else float("nan")


def check(tb, what, value, lo, hi, unit, ref):
    global fails
    ok = (not math.isnan(value)) and lo <= value <= hi
    fails += 0 if ok else 1
    rng = f"{lo:g} .. {hi:g}" if hi != float("inf") else f">= {lo:g}"
    if lo == float("-inf"):
        rng = f"<= {hi:g}"
    rows.append(f"| {tb} | {what} | {value:.4g} {unit} | {rng} {unit} | {ref} | {'PASS' if ok else '**FAIL**'} |")


def failed(tb, key, k):
    return math.isnan(m(tb, key, k))


# ---- tb01 start-up -----------------------------------------------------------
t = "tb01_startup_inrush"
check(t, "VCP - VS (VS = 48 V)", m(t, "vcp_ss"), 13.5, 15.5, "V", "Tab.11 VCP_10V")
check(t, "VGS at FET, on", m(t, "vgs_ss"), 12, 15, "V", "Tab.12 VGSON_10V (minus Rg divider)")
check(t, "CS readback @ 10 A x 1 mOhm", m(t, "vcs_ss") * 1e3, 9.5, 10.5, "mV", "Tab.13 +-5 % @ 10 mV")
check(t, "peak inrush (220 uF)", m(t, "ipk"), 10, 105.6, "A", "below IHSC -> no trip")
check(t, "latched faults during start-up", m(t, "fltmax"), -0.01, 0.01, "", "none expected")
# ---- tb02 hard short -----------------------------------------------------------
t = "tb02_hard_short"
check(t, "short -> HSHT latch delay", m(t, "dt_trip") * 1e6, 5, 10, "us", "Tab.15 VHSC_DELAY 5 us + di/dt")
check(t, "VBAT peak (inductive kick)", m(t, "vbatpk"), -math.inf, 70, "V", "Tab.2 VS abs. max 70 V")
check(t, "FET VDS peak", m(t, "vdspk"), -math.inf, 100, "V", "FET BV 100 V")
check(t, "FET VGS peak", m(t, "vgsmax"), -math.inf, 20, "V", "FET VGS rating +-20 V")
check(t, "OUT minimum", m(t, "voutmin"), -10, 0, "V", "Tab.2 VOUT -10 V / 10 us")
check(t, "retry into short trips again", m(t, "t_trip2") * 1e3, 6.0, 6.2, "ms", "latched, MCU retry")
check(t, "restart after short removed", m(t, "vout_end"), 46, 49, "V", "CLR re-arms")
# ---- tb03 I2t curve ------------------------------------------------------------
t = "tb03_i2t_curve"
lg = meas_log(os.path.join(TB, t + ".log"))
tt, xa = lg["ttrip"], lg["xavg"]
err_s, err_i = [], []
for k in range(0, len(tt), 2):
    x = xa[k]
    e = 32 * (x * x - 1)
    ts = 1.0 / 2 ** max(0, math.floor(math.log2(e)))
    ti = min(1.0, (1 / 32) / (x * x - 1))
    if ts >= 2e-3:
        err_s.append(abs(tt[k] / ts - 1))
    if ti >= 2e-3:
        err_i.append(abs(tt[k + 1] / ti - 1))
check(t, "stepwise curve, max error (t >= 2 ms)", 100 * max(err_s), 0, 3, "%", "Fig.4 t = tNOM/2^m")
check(t, "ideal curve, max error (t >= 2 ms)", 100 * max(err_i), 0, 5, "%", "t = (tNOM/32)/(x^2-1)")
check(t, "trip time just above INOM", tt[0], 0.9, 1.1, "s", "tNOM = 1 s (T_NOM = 0)")
check(t, "fastest I-t step (x = 25)", tt[-2] * 1e6, 50, 130, "us", "tNOM/2^14 = 61 us + 1 sample")
# ---- tb04 PWM ------------------------------------------------------------------
t = "tb04_pwm_rms"
check(t, "D = 0.25 (I_RMS < INOM): no trip", 1.0 if failed(t, "ttrip", 0) else 0.0, 1, 1, "", "RMS criterion")
check(t, "D = 0.30 (I_RMS ~ INOM): no trip", 1.0 if failed(t, "ttrip", 1) else 0.0, 1, 1, "", "RMS criterion")
check(t, "D = 0.35 (I_RMS 1.06 INOM): trips", m(t, "ttrip", 2), 0.3, 2.0, "s", "heat balance d*2^m - (1-d)*32")
check(t, "D = 0.50 (I_RMS 1.27 INOM): trip time", m(t, "ttrip", 3), 0.056, 0.069, "s", "1/(0.5*64-0.5*32) = 62.5 ms")
# ---- tb05 VDS ------------------------------------------------------------------
t = "tb05_vds_desat"
check(t, "C_SLEW 47 nF: no VDS trip", 1.0 if failed(t, "t_vds", 0) else 0.0, 1, 1, "", "ramp < VDS_BLK")
check(t, "C_SLEW 470 nF: VDS trip after turn-on", m(t, "dt_vds", 1) * 1e6, 864, 1066, "us",
      "Tab.14 VDS_BLK 960 us +-10 % + 10 us")
check(t, "C_SLEW 47 nF: inrush (680 uF)", m(t, "ipk", 0), 20, 105.6, "A", "< IHSC")
# ---- tb06 supply ---------------------------------------------------------------
t = "tb06_supply_transients"
check(t, "VCP - VS at VS = 6 V", m(t, "vcp_6v"), 7, 11, "V", "Tab.11 VCP_6V")
check(t, "VGS at FET at VS = 6 V", m(t, "vgs_6v"), 6, 15, "V", "Tab.12 VGSON_6V >= 6 V")
check(t, "VGS at FET at VS = 70 V", m(t, "vgs_70v"), 12, 15, "V", "Tab.12 VGSON_10V")
check(t, "UV shutdown threshold (falling)", m(t, "vbat_uv"), 4.3, 4.6, "V", "Tab.4 VS_USD 4.5 V (+33 us filter)")
check(t, "no latched fault over the profile", m(t, "fltmax"), -0.01, 0.01, "", "UV is real-time")
check(t, "automatic restart after UV", m(t, "vout_end"), 46, 49, "V", "sec. 5.1")
# ---- tb07 NTC ------------------------------------------------------------------
t = "tb07_ntc_overtemp"
check(t, "pad temperature at NTC_OVT", m(t, "tc_ot"), 117, 123, "degC", "Tab.17 code 4 = 120 degC")
check(t, "VNTC at trip", m(t, "vntc_ot") * 1e3, 67.38, 73.38, "mV", "70.38 mV +-3 mV")
check(t, "I2t fuse not involved", m(t, "fdmax"), 0, 0.05, "", "I < INOM")
# ---- tb08 standby --------------------------------------------------------------
t = "tb08_standby_autoon"
check(t, "OUT in stand-by via bypass (20 mA)", m(t, "vout_sleep"), 47.5, 48, "V", "Tab.18 RDS(on)_BYP 4..10 Ohm")
check(t, "wake-up -> AUTO-ON delay", m(t, "dt_auto") * 1e6, 5, 300, "us", "VS-VOUT > ~1.3 V for 5 us")
check(t, "OUT droop during wake-up", m(t, "vout_min"), 40, 48, "V", "470 uF hold-up")
check(t, "DIAG low after wake-up event", m(t, "diag_wk"), 0, 0.3, "V", "DIAG = 0 if WAKEUPM")
check(t, "DIAG released after CLR", m(t, "diag_end"), 3.0, 3.4, "V", "BYPASS_SAT cleared")
# ---- tb09 inductive ------------------------------------------------------------
t = "tb09_inductive_turnoff"
check(t, "OUT min with freewheel", m(t, "vout_min", 1), -2, 0, "V", "Tab.2 VOUT >= -2 V DC")
check(t, "OUT min without freewheel", m(t, "vout_min", 0), -60, -40, "V", "FET avalanche (expected)")
check(t, "FET energy without freewheel", m(t, "e_fet", 0) * 1e3, 90, 150, "mJ", "L*I^2/2 = 99 mJ + supply")
# ---- tb10 system ---------------------------------------------------------------
t = "tb10_zonal_system"
check(t, "faulty channel (CH2) isolation time", m(t, "dt_trip2") * 1e6, 5, 10, "us", "HSC 5 us")
check(t, "healthy channel (CH1) faults", m(t, "ch1_flt"), -0.01, 0.01, "", "selectivity")
check(t, "DC/DC input minimum", m(t, "vdc_min"), 30, 49, "V", "stays above DC/DC UVLO")
check(t, "DC/DC stays enabled", m(t, "dcen_min"), 0.99, 1.01, "", "ride-through")
# ---- tb11 dV/dt pre-charge window ---------------------------------------------
t = "tb11_precharge_dvdt"
NCL = 5                                   # inner step C_LOAD, outer step C_SLEW


def k11(i_csl, i_cl):
    return i_csl * NCL + i_cl


def tripped(key, k):
    return not failed(t, key, k)


sr68 = [10 / (m(t, "t20v", k11(2, i)) - m(t, "t10v", k11(2, i))) / 1e3 for i in range(3)]
check(t, "dV/dt independent of C_LOAD (68 nF, 0.22..1 mF)", 100 * (max(sr68) - min(sr68)) / min(sr68),
      0, 10, "%", "source follower: dV/dt set by RG_ON*C_SLEW")
check(t, "1 mF, C_SLEW 22 nF: HSC trip", 1.0 if tripped("t_hsc", k11(0, 2)) else 0.0, 1, 1, "",
      "C*dV/dt > IHSC")
check(t, "1 mF, C_SLEW 68 nF: no fault", 0.0 if tripped("t_hsc", k11(2, 2)) or tripped("t_vds", k11(2, 2)) else 1.0,
      1, 1, "", "inside the window")
check(t, "1 mF, C_SLEW 68 nF: inrush", m(t, "ipk", k11(2, 2)), 50, 105.6, "A", "~C*dV/dt = 65 A, < IHSC")
check(t, "1 mF, C_SLEW 68 nF: FET energy / (1/2 C dV^2)",
      m(t, "e_fet", k11(2, 2)) / (0.5 * 1e-3 * (48 - m(t, "v0", k11(2, 2))) ** 2), 0.85, 1.0, "",
      "rest in the series resistances")
check(t, "1 mF, C_SLEW 220 nF: VDS trip after turn-on", (m(t, "t_vds", k11(4, 2)) - 0.5e-3) * 1e6, 864, 1066, "us",
      "VDS_BLK 960 us + 10 us")
n_ok = sum(1 for j in range(5) for i in (3, 4)
           if not (tripped("t_hsc", k11(j, i)) or tripped("t_vds", k11(j, i))))
check(t, "C_LOAD >= 2.2 mF: passing C_SLEW values", n_ok, 0, 0, "", "C_max ~ IHSC*0.9 ms/VBAT ~ 2 mF")
# ---- tb12 resistor pre-charge ------------------------------------------------
t = "tb12_precharge_resistor"
v0 = 6.13                                  # OUT pre-bias (1.3 mA OUT current x 4.7k)
check(t, "V(load) after 1 tau", m(t, "v_ho", 0), 31.5, 33.5, "V", "V0 + (VBAT-V0)(1-1/e) = 32.6 V")
check(t, "pre-charge resistor peak power", m(t, "ppre", 3), 340, 400, "W", "(VBAT-V0)^2/RPRE = 373 W")
check(t, "pre-charge resistor energy (5 tau)", m(t, "e_pre", 3), 3.9, 4.3, "J", "1/2 C (VBAT-V0)^2 = 4.12 J")
check(t, "hand-over at 1 tau: HSC trip", m(t, "dt_hsc", 0) * 1e6, 50, 200, "us", "dV 16 V -> I >> IHSC")
check(t, "hand-over at 2 tau: HSC trip", m(t, "dt_hsc", 1) * 1e6, 50, 200, "us", "dV 5.9 V / ~50 mOhm > IHSC")
check(t, "hand-over at 3 tau: residual inrush", m(t, "ifet", 2), 20, 105.6, "A", "dV 2.2 V / ~50 mOhm, < IHSC")
check(t, "hand-over at 5 tau: residual inrush", m(t, "ifet", 3), 0, 15, "A", "dV 0.35 V")
check(t, "hand-over at 3 tau: output on", m(t, "vend", 2), 47.5, 48.5, "V", "no fault")
# ---- tb13 pre-charge methods -------------------------------------------------
t = "tb13_precharge_methods"
check(t, "resistor: time to 95 %", m(t, "t_pre", 0) * 1e3, 60, 70, "ms", "tau*ln(41.9/2.4) = 65 ms")
check(t, "constant current: time to 95 %", m(t, "t_pre", 1) * 1e3, 17.5, 19.5, "ms", "C*dV/I = 18.6 ms")
check(t, "switch-mode: time to 95 %", m(t, "t_pre", 2) * 1e3, 17.5, 19.5, "ms", "C*dV/I_avg = 18.6 ms")
check(t, "resistor: energy lost", m(t, "e_loss", 0), 3.9, 4.3, "J", "1/2 C (dV0^2 - dV1^2) = 4.11 J")
check(t, "constant current: energy lost", m(t, "e_loss", 1), 3.9, 4.3, "J", "same as resistor")
check(t, "switch-mode: energy lost", m(t, "e_loss", 2), 0, 0.5, "J", "no resistive drop to dissipate")
check(t, "switch-mode: average battery current", m(t, "iin_av", 2), 2, 5, "A", "P_in ~ P_out: I_in < I_out")
check(t, "faults at hand-over (all methods)", max(m(t, "hsht", k) + m(t, "vdsmax", k) for k in range(3)),
      -0.01, 0.01, "", "dV = 2.4 V at 95 %")
# ---- tb14 supervised pre-charge, faults --------------------------------------
t = "tb14_precharge_faults"
check(t, "normal: hand-over time", (m(t, "t_pg", 0) - 1e-3) * 1e3, 60, 70, "ms", "95 % after ~2.9 tau")
check(t, "normal: DC/DC current after start", m(t, "idc", 0), 20, 22.5, "A", "1 kW / 47.5 V")
check(t, "normal: latched faults", m(t, "fltmax", 0), -0.01, 0.01, "", "none expected")
check(t, "short: abort at the checkpoint", m(t, "dt_ab", 1) * 1e3, 21, 24, "ms", "TCHK = 1 tau = 22 ms")
check(t, "short: eFuse never switched on", m(t, "gcmax", 1), -0.01, 0.01, "", "no hand-over into a short")
check(t, "short: resistor energy", m(t, "e_pre", 1), 9, 12, "J", "~VBAT^2/RPRE x 22 ms")
check(t, "leaky load: abort by the timeout", m(t, "dt_ab", 2) * 1e3, 99, 102, "ms", "TTO = 100 ms")
check(t, "leaky load: V(load) at abort", m(t, "v_ab", 2), 30, 35, "V", "divider 10/(10+4.7) -> 32.7 V")
check(t, "DC/DC not gated: hiccup (3rd start)", m(t, "t_dc3", 3) * 1e3, 20, 40, "ms", "UVLO 30/26 V")
check(t, "DC/DC not gated: abort by the timeout", m(t, "dt_ab", 3) * 1e3, 99, 102, "ms", "never reaches 95 %")
# ---- schematics ----------------------------------------------------------------
S = os.path.join(ROOT, "schematics")
check("demo_efuse48_module.asc", "HSC trip (matches tb02)", m("demo_efuse48_module", "t_trip", 0, S) * 1e3,
      3.005, 3.010, "ms", "same circuit as tb02")
check("app_vnf1048f_discrete.asc", "I2t trip, x = 1.36 (30 A / 21.8 A)", m("app_vnf1048f_discrete", "dt_fuse", 0, S) * 1e3,
      56, 69, "ms", "tNOM/2^4 = 62.5 ms")
check("app_vnf1048f_discrete.asc", "restart after CLR", m("app_vnf1048f_discrete", "vout_end", 0, S),
      46, 49, "V", "CLR re-arms")

hdr = ["# Validation report", "",
       "Generated by `tools/validate.py` from the LTspice `.meas` results "
       "(run `tools/run_ltspice.sh testbenches/*.cir schematics/*.asc` first).", "",
       f"**{len(rows) - fails} / {len(rows)} checks pass.**", "",
       "| Bench | Check | Simulated | Limit | Reference | Result |",
       "|---|---|---|---|---|---|"]
open(os.path.join(ROOT, "docs", "VALIDATION.md"), "w").write("\n".join(hdr + rows) + "\n")
print("\n".join(rows))
print(f"\n{len(rows) - fails}/{len(rows)} checks pass")
sys.exit(1 if fails else 0)
