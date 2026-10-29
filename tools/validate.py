"""Check the simulation results against the datasheet (DS13084 Rev 6), the
battery and DC/DC model equations (README.md, sections 14-15) and the
expected application behaviour. Writes docs/VALIDATION.md (full runs only)
and exits non-zero if any check fails.

    tools/run_ltspice.sh testbenches/*.cir schematics/*.asc
    python3 tools/validate.py                     # all groups, from the .log files
    python3 tools/validate.py battery dcdc        # selected groups only
    python3 tools/validate.py --export docs/results.json   # also store the results
    python3 tools/validate.py --json docs/results.json     # check stored results (CI)

Groups: efuse (tb01..tb35), battery (bat01..bat07), dcdc (dc01..dc08),
reference (ref01..ref02, public product data), schematics (demo/app .asc).
"""
import argparse
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ltraw import meas_log  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TB = os.path.join(ROOT, "testbenches")
S = os.path.join(ROOT, "schematics")
rows, fails = [], 0
RESULTS = {}          # "testbenches/tb01_startup_inrush" -> {meas: [values per step]}


class MissingResults(Exception):
    pass


def load_logs():
    out = {}
    for folder in ("testbenches", "schematics"):
        for f in sorted(glob.glob(os.path.join(ROOT, folder, "*.log"))):
            name = os.path.splitext(os.path.basename(f))[0]
            out[f"{folder}/{name}"] = meas_log(f)
    return out


def res(tb, folder=TB):
    key = f"{os.path.relpath(folder, ROOT)}/{tb}"
    if key not in RESULTS:
        raise MissingResults(key)
    return RESULTS[key]


def m(tb, key, k=0, folder=TB):
    try:
        v = res(tb, folder).get(key.lower(), [])
    except MissingResults:
        return float("nan")
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



def efuse():
    """eFuse benches tb01..tb35 (DS13084 and hand calculations)."""
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
    lg = res(t)
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
    # ---- interview companion benches (tb15..tb35) ---------------------------------
    t = "tb15_12v_vs_48v"
    check(t, "12 V / 2.5 mm2: wire current", m(t, "iw", 0), 115, 140, "A", "P = V*I with the wire drop")
    check(t, "48 V / 2.5 mm2: wire current", m(t, "iw", 2), 20, 23, "A", "1 kW / 47 V")
    check(t, "wire loss ratio 12 V / 48 V (2.5 mm2)", m(t, "pwire", 0) / m(t, "pwire", 2), 16, 60, "",
          ">= (48/12)^2 = 16")
    check(t, "prospective short current 48 V / 12 V", m(t, "isc", 2) / m(t, "isc", 0), 3.5, 4.2, "", "~VBAT ratio")
    t = "tb16_thermal_memory"
    check(t, "pulse train with memory: trip time", m(t, "t_fl", 0), 0.22, 0.26, "s", "3rd pulse")
    check(t, "pulse train without memory: no trip", 1.0 if failed(t, "t_fl", 1) else 0.0, 1, 1, "", "counter resets")
    check(t, "DC at the train's RMS: trip time", m(t, "t_fl", 2), 0.215, 0.235, "s", "0.1 s + tNOM/2^3")
    check(t, "no memory: wire temperature", m(t, "twend", 1), 125, 140, "degC", "70 + 50*(I_RMS/INOM)^2")
    t = "tb17_latch_vs_limit"
    check(t, "latch-off: FET energy", m(t, "ea") * 1e3, 5, 50, "mJ", "~10 us at 100s of A")
    check(t, "current limit: FET power", m(t, "pb") / 1e3, 4.5, 6, "kW", "48 V x ~110 A")
    check(t, "current limit: time to 175 degC", m(t, "dt175") * 1e3, 0.3, 1.0, "ms", "P / CTHJ")
    t = "tb18_short_di_dt"
    check(t, "LH 0.5 uH: peak current", m(t, "ipk", 0), 380, 520, "A", "IHSC + VBAT/L x delay")
    check(t, "LH 5 uH: peak current", m(t, "ipk", 3), 140, 210, "A", "IHSC + VBAT/L x delay")
    check(t, "LH 1 uH: latch delay", m(t, "dt_trip", 1) * 1e6, 7, 9, "us", "= tb02")
    check(t, "LH 5 uH: latch delay", m(t, "dt_trip", 3) * 1e6, 14, 20, "us", "slower di/dt -> later")
    t = "tb19_turnoff_speed"
    check(t, "fast path (10 Ohm): FET energy", m(t, "e_fet", 0) * 1e3, 5, 40, "mJ", "= tb02")
    check(t, "no fast path: FET energy", m(t, "e_fet", 3), 3, 20, "J", "gate held by C_SLEW")
    check(t, "no fast path: turn-off after latch", m(t, "dt_off", 3) * 1e6, 200, 800, "us", "RG_ON x C_SLEW")
    t = "tb20_sense_error"
    check(t, "nominal: trip time at 40 A", m(t, "ttrip", 1) * 1e3, 12.5, 15.5, "ms", "(1/32)/(x^2-1) = 13.2 ms")
    check(t, "-10 % sensed: trip time", m(t, "ttrip", 0) * 1e3, 17.5, 21.5, "ms", "x = 1.62 -> 19.2 ms")
    check(t, "+20 % sensed: trip time", m(t, "ttrip", 3) * 1e3, 7.5, 9.5, "ms", "x = 2.16 -> 8.5 ms")
    t = "tb21_inductive_clamp"
    check(t, "zener clamp: OUT minimum", m(t, "vout_min", 2), -38, -33, "V", "-(33 V + diode)")
    check(t, "zener clamp: VDS below BV", m(t, "vds_max", 2), 75, 95, "V", "48 V + 34 V")
    check(t, "zener clamp: decay to 1 A", m(t, "dt_decay", 2) * 1e3, 0.25, 0.45, "ms", "faster than freewheel")
    check(t, "zener clamp: energy in the zener", m(t, "e_zen", 2) * 1e3, 30, 80, "mJ", "most of L*I^2/2")
    t = "tb22_parallel_fets"
    check(t, "linear mode: energy ratio M1/M2", m(t, "e1") / m(t, "e2"), 4, 15, "", "(VGS-Vth)^2 at common VGS")
    check(t, "fully on: current ratio M1/M2", m(t, "i1on") / m(t, "i2on"), 0.95, 1.05, "", "equal RDS(on)")
    t = "tb23_linear_soa"
    check(t, "1 mF: FET energy / (1/2 C dV^2)", m(t, "e_fet", 2) / (0.5 * 1e-3 * (48 - m(t, "v0", 2)) ** 2),
          0.8, 1.0, "", "half-energy rule")
    check(t, "1 mF: junction rise", m(t, "tjpk", 2) - 85, 20, 60, "K", "E / CTHJ, Zth")
    check(t, "1 mF: pad (NTC) rise", m(t, "tcpk", 2) - 85, 0, 1, "K", "NTC blind to the pulse")
    t = "tb24_back_to_back"
    check(t, "single FET off: reverse current", -m(t, "ia_off2"), 15, 25, "A", "body diode conducts")
    check(t, "back-to-back off: reverse current", abs(m(t, "ib_off2")), 0, 0.01, "A", "second diode blocks")
    check(t, "reverse current on: CS readback", m(t, "csa_on") * 1e3, 0, 0.1, "mV", "unidirectional sense")
    t = "tb25_supply_clamp"
    check(t, "100 uF + TVS: VBAT peak", m(t, "vbatpk", 0), 55, 70, "V", "= tb02, < VS abs. max")
    check(t, "22 uF, no TVS: VBAT peak", m(t, "vbatpk", 2), 85, 110, "V", "I*sqrt(L/C)")
    check(t, "22 uF + TVS: clamp works but > 70 V", m(t, "vbatpk", 3), 70, 90, "V", "TVS dynamic R at ~110 A")
    check(t, "remote TVS adds overshoot", m(t, "vbatpk", 4) - m(t, "vbatpk", 3), 1, 10, "V", "L*di/dt of the loop")
    check(t, "no freewheel: OUT minimum", m(t, "voutmin", 5), -70, -40, "V", "FET avalanche")
    t = "tb26_hard_turn_on"
    check(t, "hard switch, no protection: inrush", m(t, "ipk", 0), 300, 1000, "A", "V / R_loop, L-limited")
    check(t, "hard switch, protections on: HSC trip", (m(t, "t_hsc", 1) - 0.5e-3) * 1e6, 3, 20, "us", "looks like a short")
    check(t, "dV/dt: no fault", m(t, "fltmax", 2), -0.01, 0.01, "", "= tb11 68 nF")
    t = "tb27_half_energy"
    for k, rr in enumerate([1, 4.7, 22, 100]):
        check(t, f"R = {rr:g} Ohm: resistor energy", m(t, "e_r", k), 5.2, 5.5, "J", "1/2 C V^2 = 5.41 J")
    check(t, "R = 1 Ohm: peak power", m(t, "ppk", 0), 2000, 2400, "W", "V^2/R")
    t = "tb28_bypass_precharge"
    check(t, "AUTO-ON after bypass on", m(t, "dt_auto", 0) * 1e6, 4, 20, "us", "BYPASS_SAT 5 us")
    check(t, "0.1 mF: charged by the main FET", m(t, "vend", 0), 47, 49, "V", "slew-controlled")
    check(t, "1 mF: HSC trip", 1.0 if not failed(t, "t_hsc", 1) else 0.0, 1, 1, "", "as tb11 47 nF")
    t = "tb29_cross_short"
    check(t, "to 12 V battery: HSC trip", m(t, "dt_hsc", 0) * 1e6, 5, 30, "us", "(48-12)/R_loop")
    check(t, "to DC/DC branch: 12 V node", m(t, "v12end", 1), 45, 49, "V", "no sink on the 12 V side")
    check(t, "to DC/DC branch: eFuse current < INOM", m(t, "ifuse", 1), 15, 21.8, "A", "no eFuse trip")
    check(t, "12 V OV monitor: channel off", m(t, "v12end", 2), 11, 13, "V", "12 V restored")
    t = "tb30_ground_fault"
    check(t, "0.2 Ohm ground: offset", m(t, "vlg_on", 1), 1.5, 2.5, "V", "10 A x 0.2 Ohm")
    check(t, "0.2 Ohm ground: receiver low level", m(t, "vrx_low", 1), 1.5, 2.5, "V", "> 1.5 V threshold")
    check(t, "ground lost: signal-line current", m(t, "irx_max", 2) * 1e3, 200, 600, "mA", "(48 - 6 V)/~105 Ohm")
    check(t, "ground lost: eFuse current", m(t, "ifuse", 2), 0, 1, "A", "eFuse sees an under-current only")
    t = "tb31_retry"
    check(t, "retry into short: energy per retry / first trip", m(t, "ea2") / m(t, "ea1"), 3, 12, "",
          "linear-mode turn-on into the short")
    check(t, "overload: first trip", m(t, "dtb1") * 1e3, 29, 34, "ms", "tNOM/2^5 = 31 ms")
    check(t, "overload: retry 5 ms after trip", m(t, "dtb2") * 1e3, 4, 8, "ms", "fd still ~0.84")
    check(t, "overload: retry after cooling", m(t, "dtb3") * 1e3, 29, 34, "ms", "fd back to 0")
    t = "tb32_hw_vs_fw"
    check(t, "HSC: FET energy", m(t, "e_fet", 0) * 1e3, 5, 40, "mJ", "hardware, us")
    check(t, "VDS only: FET energy", m(t, "e_fet", 1) * 1e3, 30, 200, "mJ", "second hardware layer")
    check(t, "firmware only: FET energy", m(t, "e_fet", 2), 3, 10, "J", "~1 kA for 1 ms")
    t = "tb33_design_exercise"
    check(t, "dV/dt 68 nF on 2.64 mF: HSC trip", 1.0 if not failed(t, "t_hsc", 0) else 0.0, 1, 1, "", "C*dV/dt > IHSC")
    check(t, "dV/dt 220 nF on 2.64 mF: VDS trip", (m(t, "t_vds", 1) - 1e-3) * 1e6, 950, 1000, "us", "ramp > blanking")
    check(t, "pre-charge: hand-over time", (m(t, "t_pg", 2) - 1e-3) * 1e3, 70, 85, "ms", "~3 tau = 79 ms")
    check(t, "pre-charge: resistor energy", m(t, "e_pre", 2), 2.0, 2.6, "J", "1/2 C dV^2 = 2.3 J")
    check(t, "pre-charge: DC/DC running", m(t, "idc", 2), 20, 23, "A", "1 kW / 47 V")
    check(t, "short at the end of the feed: HSC", m(t, "dt_sc", 3) * 1e6, 5, 25, "us", "2.5 uH feed")
    t = "tb34_cold_start"
    check(t, "25 degC: no fault", 1.0 if failed(t, "t_vds", 0) and failed(t, "t_hsc", 0) else 0.0, 1, 1, "",
          "ramp inside the blanking")
    check(t, "-40 degC (Vth only): no fault", 1.0 if failed(t, "t_vds", 1) else 0.0, 1, 1, "", "margin absorbs it")
    check(t, "-40 degC + gate drive min: VDS trip", (m(t, "t_vds", 2) - 0.5e-3) * 1e6, 950, 1000, "us",
          "ramp > blanking")
    t = "tb35_field_return"
    check(t, "healthy: I2t trip", m(t, "t_fl", 0), 2.04, 2.09, "s", "tNOM/2^4 after 2 s")
    check(t, "cracked Kelvin: no trip", 1.0 if failed(t, "t_fl", 1) else 0.0, 1, 1, "", "reads 50 %")
    check(t, "cracked Kelvin: wire overheats", m(t, "twmax", 1), 125, 170, "degC", "undetected overload")
    check(t, "stuck-on FET: current after MCU off", m(t, "i_end", 2), 25, 32, "A", "FET cannot open")
    check(t, "stuck-on FET: plausibility flag", m(t, "t_pl", 2), 2.06, 2.1, "s", "OUT high with gate off")
    check(t, "sneak path: resistor power", m(t, "p_pre", 3), 200, 330, "W", "48 V through 4.7 Ohm")


def battery():
    """Battery benches bat01..bat07 (model equations, hand calculations)."""
    # ---- battery models (models/BATTERY_beh.lib), analytic references ---------------
    BAT = {12: dict(cap=70, v0=11.70, v100=12.90, veoc=15.0, r0=2.0e-3, r1=0.8e-3, r2=0.7e-3, l=0.2e-6),
           48: dict(cap=10, v0=40.0, v100=52.0, veoc=55.0, r0=15e-3, r1=5e-3, r2=5e-3, l=1e-6)}
    from bat_ocv import g as bat_g  # noqa: E402  (PCHIP curve used in the .lib)


    def bat_ocv(c, soc):
        return c["v0"] + (c["v100"] - c["v0"]) * bat_g(soc)


    def bat_ft(temp):
        return math.exp(1200 * (1 / (temp + 273.15) - 1 / 298.15))


    def bat_fs(soc):
        return 1 + 0.5 * (1 - min(max(soc, 0), 1)) ** 2


    t = "bat01_capacity_ocv"
    for v in (12, 48):
        c = BAT[v]
        err = max(abs(m(t, f"vr{v}_{k}") - bat_ocv(c, 1 - 0.1 * k)) for k in range(1, 10))
        check(t, f"{v} V: rest voltage vs OCV table (9 points)", err * 1e3, 0, 2, "mV", "OCV(SOC) curve points")
        check(t, f"{v} V: delivered capacity to cut-off / rated", m(t, f"ah{v}") / 3600 / c["cap"], 0.99, 1.01, "",
              "charge counting, CAP_AH")
        s_eoc = 1 + 0.02 * ((14.4 if v == 12 else 53) - c["v100"]) / (c["veoc"] - c["v100"])
        check(t, f"{v} V: CV charge, final raw SOC", m(t, f"s{v}_end"), s_eoc - 5e-4, s_eoc + 5e-4, "",
              f"OCV = V_CV -> {s_eoc:.4f}")
        check(t, f"{v} V: CV charge, final current", m(t, f"ich{v}_end"), -0.01, 0.01, "A", "taper to 0")
    check(t, "12 V: SOC after 9 x 10 % pulses", m(t, "sr12_9"), 0.0999, 0.1001, "", "1 - 9 x 0.1")
    t = "bat02_pulse_temperature"
    lg = res(t)
    for v in (12, 48):
        c = BAT[v]
        e0, e10 = [], []
        for k, temp in enumerate([-30, -18, 0, 25, 45]):
            ft = bat_ft(temp)
            fs10 = bat_fs(0.5 - 100 * 5 / (c["cap"] * 3600))
            r0 = ft * bat_fs(0.5) * (c["r0"] + c["r1"] * (1 - math.exp(-0.49e-3 / 20e-3)))
            docv = (c["v100"] - c["v0"]) * 0.5 * (100 * 10 / (c["cap"] * 3600))
            r10 = ft * fs10 * (c["r0"] + c["r1"] + c["r2"] * (1 - math.exp(-0.5))) + docv / 100
            e0.append(abs(lg[f"r0_{v}"][k] / r0 - 1)); e10.append(abs(lg[f"r10_{v}"][k] / r10 - 1))
        check(t, f"{v} V: R0 (0.5 ms), max error -30..45 degC", 100 * max(e0), 0, 1, "%", "R0 x FT(T) x fs(SOC)")
        check(t, f"{v} V: R(10 s), max error -30..45 degC", 100 * max(e10), 0, 2, "%", "R0' + R1' + R2'(1-e^-0.5) + dOCV")
    check(t, "R0(-30 degC) / R0(25 degC)", lg["r0_12"][0] / lg["r0_12"][3], 0.99 * bat_ft(-30), 1.01 * bat_ft(-30), "",
          f"FT(-30) = {bat_ft(-30):.3f}")
    t = "bat03_impedance_ac"
    for v in (12, 48):
        c = BAT[v]; err = []
        for f, key in [(0.1, "100m"), (1, "1"), (10, "10"), (100, "100"), (1e3, "1k"), (1e4, "10k"),
                       (1e5, "100k"), (1e6, "1meg")]:
            jw = 2j * math.pi * f
            z = (c["r0"] + c["r1"] / (1 + jw * 20e-3) + c["r2"] / (1 + jw * 20)) * bat_fs(0.5) \
                + 1 / (1 / (jw * c["l"]) + 1 / 100)
            err.append(abs(m(t, f"z{v}_{key}") / abs(z) - 1))
        check(t, f"{v} V: |Z| 0.1 Hz .. 1 MHz, max error", 100 * max(err), 0, 1, "%", "R0 + 2 RC + L_INT")
        check(t, f"{v} V: |Z(100 Hz)| (ohmic plateau)", m(t, f"z{v}_100") * 1e3, 0.99e3 * c["r0"] * bat_fs(0.5),
              1.02e3 * c["r0"] * bat_fs(0.5), "mOhm", "R0 x fs(50 %)")
    t = "bat04_cold_crank"
    c = BAT[12]; ft18 = bat_ft(-18)
    s30 = 1 - 700 * 30 / (c["cap"] * 3600); fsm = bat_fs((1 + s30) / 2)
    v30 = bat_ocv(c, s30) - 700 * ft18 * fsm * (c["r0"] + c["r1"] + c["r2"] * (1 - math.exp(-1.5)))
    check(t, "CCA 700 A, 30 s, -18 degC: voltage", m(t, "vcca"), 0.98 * v30, 1.02 * v30, "V", f"hand calc {v30:.2f} V")
    check(t, "CCA 700 A: pass criterion", m(t, "vcca"), 7.2, math.inf, "V", "SAE J537 >= 7.2 V at 30 s")
    for k, temp in zip("bcd", (25, -18, -30)):
        ocv = m(t, f"ocv_{k}"); r0 = c["r0"] * bat_ft(temp) * bat_fs(0.8)
        ipk = ocv / (r0 + 7.6e-3); vmin = ocv - ipk * r0
        check(t, f"crank {temp:+d} degC: minimum voltage", m(t, f"vmin_{k}"), 0.97 * vmin, 1.01 * vmin, "V",
              f"divider R0'/(R0'+7.6 mOhm) = {vmin:.2f} V")
        check(t, f"crank {temp:+d} degC: inrush peak", m(t, f"ipk_{k}"), 0.95 * ipk, 1.0 * ipk, "A",
              f"OCV/(R0'+7.6 mOhm) = {ipk:.0f} A")
    t = "bat05_short_circuit"
    c = BAT[12]
    tt = 2.05e-6; i2 = 12.9 / (c["l"] + 0.5e-6) * tt * (1 - tt / (2 * (c["l"] + 0.5e-6) / 3e-3))
    check(t, "12 V short: current 2 us after closing", m(t, "ia_2us"), 0.98 * i2, 1.02 * i2, "A", "OCV/L x t (18.4 A/us)")
    i3 = 12.9 / (c["r0"] + 1e-3 + c["r1"] * (1 - math.exp(-0.1)))
    check(t, "12 V short: current after 2 ms", m(t, "ia_3ms"), 0.98 * i3, 1.02 * i3, "A",
          "OCV/(R0 + 1 mOhm + R1(1-e^-t/TAU1))")
    check(t, "48 V pack short: I_SC -> FLT delay", m(t, "dt_sc") * 1e6, 99, 102, "us", "T_SC = 100 us")
    check(t, "48 V pack short: switch voltage (clamp)", m(t, "vsw_max"), 80, 85, "V", "V_CLAMP 80 V + I x 1 mOhm")
    check(t, "48 V pack short: current after opening", abs(m(t, "ib_end")), 0, 0.01, "A", "switch off")
    check(t, "48 V pack short: FLT output", m(t, "fltb_end"), 3.2, 3.4, "V", "latched, 3.3 V")
    t = "bat06_bms_protection"
    check(t, "pre-charge: peak current", m(t, "ipre_pk"), 0.98 * m(t, "ocva") / 10, 1.0 * m(t, "ocva") / 10, "A",
          "OCV / R_PRE")
    check(t, "pre-charge: step at main-switch closing", m(t, "iclose_pk"), 0, 50, "A", "bus within ~1 V of OCV")
    check(t, "pre-charge: no fault", m(t, "flta_max"), -0.01, 0.01, "V", "")
    check(t, "no pre-charge, 10 mF: SC trip at closing", (m(t, "tb_flt") - 0.1) * 1e6, 100, 300, "us",
          "inrush > I_SC for > T_SC")
    check(t, "overcurrent ~400 A: trip delay", m(t, "dt_oc"), 0.99, 1.01, "s", "T_OC = 1 s")
    check(t, "EN toggle re-arms, pack re-closes", m(t, "vc_rearm"), 48, 50, "V", "fault cleared")
    check(t, "overload 0.8 s < T_OC: no trip", m(t, "fltc_end"), -0.01, 0.01, "V", f"I = {m(t, 'ic_ol2'):.0f} A")
    check(t, "under-voltage: delay after V < V_UV", m(t, "td_flt") - m(t, "td_uv"), 0.99, 1.01, "s", "T_UV = 1 s")
    check(t, "under-voltage: SOC at trip", m(t, "sd_flt"), -0.01, 0.02, "", "near empty")
    check(t, "over-voltage: delay after V > V_OV", m(t, "te_flt") - m(t, "te_ov"), 0.099, 0.101, "s", "T_OV = 0.1 s")
    check(t, "over-voltage: SOC at trip", m(t, "se_flt"), 1.0, 1.01, "", "just past full charge")
    t = "bat07_pdn_48v"
    check(t, "short on CH2: eFuse isolation time", m(t, "dt_trip2") * 1e6, 5, 10, "us", "HSC 5 us (= tb10)")
    check(t, "short on CH2: pack current peak", m(t, "ibat_pk"), 0, 1000, "A", "< I_SC: selectivity")
    check(t, "short on CH2: BMS does not trip", m(t, "fltb_max"), -0.01, 0.01, "V", "selectivity")
    check(t, "short on CH2: DC/DC stays enabled", m(t, "dcen_min"), 0.99, 1.01, "", "ride-through (= tb10)")
    check(t, "BSG generating: pack absorbs the excess", -m(t, "ibat_chg"), 30, 45, "A", "60 A - loads")
    check(t, "pack disconnect: bus peak (load dump)", m(t, "vbus_ld"), 64, 72, "V", "TVS 64 V + Rs x I")


def dcdc():
    """DC/DC benches dc01..dc08 (loss model, linear loop, impedances, eigenvalues)."""
    # ---- DC/DC 48/12 V (models/DCDC48_12_beh.lib), analytic references ------------
    DC = dict(vset=14.0, ilim=1.1 * 700 / 14.0, p0=6.0, rloss=4e-3, ksw=5e-3, rpre=100.0, cout=2.2e-3,
              esr=3e-3, cin=470e-6, esrin=15e-3, fc=3e3, fci=30e3, tss=5e-3)
    DC["kp"] = 2 * math.pi * DC["fc"] * DC["cout"]
    DC["ki"] = DC["kp"] * 2 * math.pi * DC["fc"] / 4
    DC["taui"] = 1 / (2 * math.pi * DC["fci"])


    def dc_pin(vin, il):
        return DC["vset"] * il + DC["p0"] + DC["rloss"] * il ** 2 + DC["ksw"] * vin * math.sqrt(il ** 2 + 1e-4)


    def dc_step(rload, di, trise, t_end=2e-3, dt=2e-8):
        """Exact simulation of the linear loop (PI + current loop + COUT/ESR + R) for a
        load step di (ramp trise) from steady state; returns (vmin, vmax)."""
        c = DC; rt = 1 / (1 / rload + 1 / c["rpre"]); il = c["vset"] / rt; xi = il; vc = c["vset"]
        vmin, vmax = c["vset"], c["vset"]
        n = int(t_end / dt)
        for k in range(n):
            t = k * dt
            iload = di * min(t / trise, 1.0)
            vo = (il - iload + vc / c["esr"]) / (1 / rt + 1 / c["esr"])
            e = c["vset"] - vo
            icr = c["kp"] * e + xi
            xi += c["ki"] * e * dt
            il += (icr - il) / c["taui"] * dt
            vc += (vo - vc) / c["esr"] / c["cout"] * dt
            vmin, vmax = min(vmin, vo), max(vmax, vo)
        return vmin, vmax


    t = "dc01_efficiency"
    lg = res(t)
    VIs, ILs = [36, 48, 54], [2.5, 5, 10, 20, 30, 40, 50]
    err_eta, err_v = [], []
    for k in range(21):
        vi, il_out = VIs[k % 3], ILs[k // 3]
        il = il_out + DC["vset"] / DC["rpre"]
        eta_m = DC["vset"] * il_out / dc_pin(vi, il)
        err_eta.append(abs(lg["pout"][k] / lg["pin"][k] - eta_m)); err_v.append(abs(lg["vout"][k] - DC["vset"]))
    check(t, "efficiency vs loss model, max error (21 points)", 100 * max(err_eta), 0, 0.05, "pp",
          "P0 + RLOSS I^2 + KSW VIN I")
    check(t, "output regulation, max error", 1e3 * max(err_v), 0, 1, "mV", "integrating loop: VOUT = VSET")
    k = 3 * 6 + 1
    check(t, "efficiency at 700 W, 48 V", 100 * lg["pout"][k] / lg["pin"][k], 95, 97, "%", "[EST] 95..97 % class")
    t = "dc02_load_transient"
    vmin_a, vmax_a = dc_step(2.8, 25, 25e-6)
    check(t, "+25 A step, COUT only: minimum", m(t, "va_min"), vmin_a - 0.02, vmin_a + 0.02, "V",
          f"linear loop {vmin_a:.3f} V")
    check(t, "-25 A step, COUT only: maximum", m(t, "va_max"), (2 * DC["vset"] - vmin_a) - 0.02,
          (2 * DC["vset"] - vmin_a) + 0.02, "V", "symmetric (linear)")
    check(t, "+45 A step: current limit reached", m(t, "ilb_max"), DC["ilim"] - 0.01, DC["ilim"] + 0.01, "A",
          "I_LIM = 1.1 x 700 W / 14 V")
    check(t, "with 12 V battery: converter stays in limit", m(t, "ilc1"), DC["ilim"] - 0.01, DC["ilim"] + 0.01, "A",
          "OCV 12.6 V < VSET")
    dv = 25 * (2e-3 * 1.02 + 0.8e-3 * 1.02 * (1 - math.exp(-0.1)) + 1e-3)
    check(t, "with 12 V battery: 12 V net change for +25 A", (m(t, "vc0") - m(t, "vc1")) * 1e3, 0.9e3 * dv,
          1.1e3 * dv, "mV", "dI x (R0' + R1'(1-e^-t/TAU1) + cable)")
    t = "dc03_startup"
    check(t, "soft-start: VOUT half-way through T_SS", m(t, "va_half"), 6.9, 7.1, "V", "VSET/2 at T_SS/2")
    check(t, "PG after EN", (m(t, "tpga") - 1e-3) * 1e3, 4.95, 5.1, "ms", "T_SS = 5 ms")
    check(t, "pre-biased start: minimum inductor current", m(t, "ilb_min"), -1e-3, 1e-3, "A", "no reverse current")
    check(t, "pre-biased start: minimum input current", m(t, "iinb_min"), 0, math.inf, "A", "no power back to 48 V")
    tb = 1e-3 + DC["tss"] * 12.44 / DC["vset"]
    check(t, "pre-biased start: delivery begins", m(t, "tb_on") * 1e3, (tb - 3e-4) * 1e3, (tb + 3e-4) * 1e3, "ms",
          "vref = V_battery")
    ilc = -(0.5 / 0.05 - DC["vset"] / DC["rpre"])
    check(t, "BIDIR: sunk current", m(t, "ilc_end"), ilc - 0.05, ilc + 0.05, "A", "(14.5 - 14) V / 50 mOhm - pre-load")
    iinc = (DC["vset"] * ilc + DC["p0"] + DC["rloss"] * ilc ** 2 + DC["ksw"] * 48 * abs(ilc)) / 48
    check(t, "BIDIR: power fed back to the 48 V input", m(t, "iinc_end"), iinc - 0.02, iinc + 0.02, "A",
          "P_in / VIN < 0")
    check(t, "disabled, 12 V battery on the output: drain", m(t, "ibd_off") * 1e3, 0.09, 0.11, "mA",
          "IOUT_OFF = 0.1 mA (key-off)")
    t = "dc04_short_overload"
    check(t, "short: current limit", m(t, "ia_sc"), DC["ilim"] - 0.01, DC["ilim"] + 0.01, "A", "I_LIM 55 A")
    check(t, "short: hiccup detection delay", m(t, "dt_off1") * 1e3, 0.95, 1.1, "ms", "T_HIC_DET = 1 ms")
    check(t, "hiccup off time", m(t, "dt_offtime") * 1e3, 49.5, 50.5, "ms", "T_HIC_OFF = 50 ms")
    check(t, "hiccup period", m(t, "dt_period") * 1e3, 50.5, 53, "ms", "off + soft-start to limit + 1 ms")
    check(t, "short removed: output back", m(t, "va_end"), 13.99, 14.01, "V", "restart with soft-start")
    check(t, "discharged 12 V battery: no hiccup", m(t, "hicb_max"), -0.01, 0.01, "", "VOUT > 50 % of VSET")
    check(t, "discharged 12 V battery: charging current", m(t, "ib_avg"), DC["ilim"] - 0.01, DC["ilim"] + 0.01, "A",
          "constant current at I_LIM")
    t = "dc05_input_transients"
    check(t, "UVLO off threshold", m(t, "v_uvoff"), 25.9, 26.1, "V", "VIN_OFF 26 V")
    check(t, "UVLO on threshold", m(t, "v_uvon"), 29.9, 30.1, "V", "VIN_ON 30 V")
    check(t, "OVP threshold", m(t, "v_ovp"), 59.9, 60.1, "V", "VIN_OVP 60 V")
    check(t, "OVP restart threshold", m(t, "v_ovr"), 57.9, 58.1, "V", "VIN_OVP - VOVP_HYS")
    il5 = 14 / 0.5 + 14 / 100
    for v, key in [(36, "iin36"), (54, "iin54")]:
        ii = dc_pin(v, il5) / v
        check(t, f"input current at {v} V (392 W out)", m(t, key), 0.995 * ii, 1.005 * ii, "A",
              f"P_in/VIN = {ii:.2f} A")
    check(t, "restart after UVLO and OVP", m(t, "vout_end"), 13.99, 14.01, "V", "soft-start")
    t = "dc06_impedance_ac"
    il6 = 14 / 0.56 + 14 / 100; rt6 = 1 / (1 / 0.56 + 1 / 100)
    pin6 = dc_pin(48, il6); gcpl = -pin6 / 48 ** 2 + DC["ksw"] * math.sqrt(il6 ** 2 + 1e-4) / 48
    ezo, ezi = [], []
    for f, key in [(10, "10"), (100, "100"), (1e3, "1k"), (3e3, "3k"), (1e4, "10k"), (1e5, "100k")]:
        s_ = 2j * math.pi * f
        yc = 1 / (DC["esr"] + 1 / (s_ * DC["cout"]))
        zo = 1 / (yc + 1 / rt6 + (DC["kp"] + DC["ki"] / s_) / (1 + s_ * DC["taui"]))
        ezo.append(abs(m(t, f"zo_{key}") / abs(zo) - 1))
        if key in ("10", "100", "1k", "10k"):
            zi = 1 / (gcpl + 1 / (DC["esrin"] + 1 / (s_ * DC["cin"])) + 1 / (s_ * 1e3))
            ezi.append(abs(m(t, f"zi_{key}") / abs(zi) - 1))
    check(t, "|Zout| 10 Hz .. 100 kHz, max error", 100 * max(ezo), 0, 2, "%", "PI + current loop + COUT")
    check(t, "|Zin| 10 Hz .. 10 kHz, max error", 100 * max(ezi), 0, 2, "%", "CPL + CIN")
    s_ = 2j * math.pi * 10
    zr = (1 / (gcpl + 1 / (DC["esrin"] + 1 / (s_ * DC["cin"])) + 1 / (s_ * 1e3))).real
    check(t, "Re(Zin) at 10 Hz: negative resistance", m(t, "zr_10"), 1.02 * zr, 0.98 * zr, "Ohm",
          f"CPL -VIN^2/P_in = {1 / gcpl:.2f} Ohm, with CIN: {zr:.2f} Ohm")
    t = "dc07_input_filter_stability"
    import numpy as np  # noqa: E402


    def filt_eig(ls, rs, cin, rc, cd=0.0, rd=1.0, vs=48.0, iout=14 / 0.56 + 14 / 100):
        """Eigenvalues of feed (Rs, Ls) + CIN/ESR (+ Cd/Rd damper) + linearized CPL."""
        v = vs
        for _ in range(20):
            v = vs - rs * dc_pin(v, iout) / v
        g = -dc_pin(v, iout) / v ** 2 + DC["ksw"] * iout / v

        def f(x):
            il, vc, vd = x
            # node voltage v from KCL: il = (v-vc)/rc + g v + (v-vd)/rd*[cd>0]
            yd = 1 / rd if cd > 0 else 0.0
            vn = (il + vc / rc + vd * yd) / (1 / rc + g + yd)
            return np.array([(-rs * il - vn) / ls, (vn - vc) / rc / cin,
                             ((vn - vd) * yd / cd) if cd > 0 else 0.0])
        a = np.zeros((3, 3)); h = 1e-6
        for j in range(3):
            e = np.zeros(3); e[j] = h
            a[:, j] = (f(e) - f(-e)) / (2 * h)
        lam = np.linalg.eigvals(a if cd > 0 else a[:2, :2])
        return lam[np.argmax(lam.real)]


    la = filt_eig(2e-6, 10e-3, 470e-6, 15e-3)
    lb = filt_eig(10e-6, 10e-3, 22e-6, 2e-3)
    lc = filt_eig(10e-6, 10e-3, 22e-6, 2e-3, cd=220e-6, rd=0.68)
    check(t, "A (2 uH, 470 uF): settled ripple", m(t, "vpp_a"), 0, 0.05, "V",
          f"stable: max Re(eig) = {la.real:.0f} 1/s")
    check(t, "B (10 uH, 22 uF ceramic): oscillation", m(t, "vpp_b"), 10, math.inf, "V",
          f"unstable: Re = +{lb.real:.0f} 1/s at {abs(lb.imag) / 2 / math.pi / 1e3:.1f} kHz")
    check(t, "B: input peaks trip the OVP, 12 V output collapses", m(t, "vout_b"), 0, 7, "V", "VIN > 60 V")
    check(t, "C (B + 220 uF / 0.68 Ohm damper): settled ripple", m(t, "vpp_c"), 0, 0.05, "V",
          f"stable: max Re(eig) = {lc.real:.0f} 1/s")
    check(t, "eigenvalue sign A / B / C", float(la.real < 0) + float(lb.real > 0) + float(lc.real < 0), 3, 3, "",
          "Middlebrook: damping vs -P/V^2")
    t = "dc08_pdn_48v_12v"
    check(t, "DC/DC starts at its UVLO", m(t, "vin_dcrun"), 30, 31.5, "V", "VIN_ON 30 V (+10 us filter)")
    check(t, "CH1 eFuse: no fault (inrush + 15 A)", m(t, "ch1_flt"), -0.01, 0.01, "", "I < INOM 39 A")
    check(t, "CH1 current with the DC/DC at 55 A", m(t, "ich1_ss"), 14, 17, "A", "(V12 x 55 A + loss) / 48 V")
    check(t, "12 V battery charged at the DC/DC limit", -m(t, "ibat12_ss"), 43, 46, "A", "55 A - 10 A base load")
    check(t, "PTC +40 A: DC/DC still in limit", m(t, "ildc_ph"), DC["ilim"] - 0.01, DC["ilim"] + 0.01, "A",
          "battery charging current drops instead")
    check(t, "48 V branch short: CH2 isolation", m(t, "dt_trip2") * 1e6, 5, 10, "us", "HSC (= tb10)")
    check(t, "48 V branch short: DC/DC input minimum", m(t, "vdc_min"), 30, 49, "V", "> VIN_OFF 26 V")
    check(t, "48 V branch short: DC/DC keeps running", m(t, "uvdc_min"), 0.99, 1.01, "", "no UVLO")
    check(t, "48 V branch short: 12 V net change", (m(t, "v12_min") - m(t, "v12_pre")) * 1e3, -10, 10, "mV",
          "not noticed on 12 V")
    check(t, "48 V pack: no BMS trip", m(t, "fltb_max"), -0.01, 0.01, "V", "selectivity")


def schematics():
    """Demo and application schematics."""
    # ---- schematics ----------------------------------------------------------------
    check("demo_efuse48_module.asc", "HSC trip (matches tb02)", m("demo_efuse48_module", "t_trip", 0, S) * 1e3,
          3.005, 3.010, "ms", "same circuit as tb02")
    check("app_vnf1048f_discrete.asc", "I2t trip, x = 1.36 (30 A / 21.8 A)", m("app_vnf1048f_discrete", "dt_fuse", 0, S) * 1e3,
          56, 69, "ms", "tNOM/2^4 = 62.5 ms")
    check("app_vnf1048f_discrete.asc", "restart after CLR", m("app_vnf1048f_discrete", "vout_end", 0, S),
          46, 49, "V", "CLR re-arms")

    check("demo_battery.asc", "48 V pack: short -> FLT", m("demo_battery", "dt_flt", 0, S) * 1e6, 100, 300, "us",
          "crossing + T_SC")
    check("demo_battery.asc", "48 V pack: no fault during pre-charge / load", m("demo_battery", "fltpre", 0, S),
          -0.01, 0.01, "V", "")
    check("demo_dcdc.asc", "DC/DC charges the 12 V battery at the limit", m("demo_dcdc", "il_cl", 0, S),
          54.99, 55.01, "A", "I_LIM 55 A")
    check("demo_dcdc.asc", "48 V feed current", m("demo_dcdc", "iin", 0, S), 14, 17, "A", "~770 W / 48 V")



def reference():
    """Reference parameter sets (models/REFERENCE_SETS_beh.lib) against public product data."""
    t = "ref01_reference_sets"
    check(t, "Varta E39: EN cold cranking, 760 A, -18 degC, 10 s", m(t, "va1_10"), 7.5, 7.6, "V",
          "EN 50342-1: >= 7.5 V (760 A EN rating)")
    check(t, "Varta E39: 20 h capacity (3.5 A to 10.5 V)", m(t, "ah_a2") / 3600, 70, 71, "Ah", "datasheet 70 Ah")
    check(t, "A123 48 V: 1C capacity to the 36 V limit", m(t, "ah_b1") / 3600, 7.9, 8.1, "Ah",
          "SAE 2018-01-0433: 8 Ah")
    check(t, "A123 48 V: ohmic resistance at 50 % SOC", m(t, "r0_b2") * 1e3, 8, 10, "mOhm",
          "SAE 2018-01-0433: 8 .. 10 mOhm")
    t = "ref02_reference_dcdc"
    check(t, "Toshiba RD210: efficiency at 3 kW, 48 -> 12 V", 100 * m(t, "eta_c"), 91.1, 91.5, "%",
          "RD210 guide: 91.3 %")
    check(t, "Toshiba RD210: output voltage at 3 kW", m(t, "vo_c"), 11.85, 12.15, "V", "RD210: 11.85 .. 12.15 V")
    check(t, "Toshiba RD210: still regulating at 24 V input", m(t, "vo_24"), 11.85, 12.15, "V",
          "RD210: input 24 .. 54 V")


GROUPS = {"efuse": efuse, "battery": battery, "dcdc": dcdc, "reference": reference, "schematics": schematics}


def main():
    global RESULTS
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("groups", nargs="*", metavar="group", help=f"groups to check, of {list(GROUPS)} (default: all)")
    ap.add_argument("--json", help="read the results from this JSON file instead of the .log files")
    ap.add_argument("--export", help="write the results parsed from the .log files to this JSON file")
    a = ap.parse_args()
    RESULTS = json.load(open(a.json)) if a.json else load_logs()
    bad = [g for g in a.groups if g not in GROUPS]
    if bad:
        ap.error(f"unknown group(s) {bad}; choose from {list(GROUPS)}")
    sel = a.groups or list(GROUPS)
    summary = {}
    for g in sel:
        n0 = len(rows)
        try:
            GROUPS[g]()
        except MissingResults as e:
            check(g, f"results missing ({e}): run the benches first", float("nan"), 0, 0, "", "")
        summary[f"checks_{g}"] = [len(rows) - n0]
    full = not a.groups
    if full:
        summary["benches"] = [len([k for k in RESULTS if not k.startswith("validation/")])]
        summary["checks_total"] = [len(rows)]
        summary["checks_passed"] = [len(rows) - fails]
        RESULTS["validation/summary"] = summary
    if a.export:
        json.dump(RESULTS, open(a.export, "w"), indent=0, sort_keys=True)
    if full:
        hdr = ["# Validation report", "",
               "Generated by `tools/validate.py` from the LTspice `.meas` results "
               "(run `tools/run_ltspice.sh testbenches/*.cir schematics/*.asc` first).", "",
               f"**{len(rows) - fails} / {len(rows)} checks pass.**", "",
               "| Bench | Check | Simulated | Limit | Reference | Result |",
               "|---|---|---|---|---|---|"]
        open(os.path.join(ROOT, "docs", "VALIDATION.md"), "w").write("\n".join(hdr + rows) + "\n")
    print("\n".join(rows))
    print(f"\n{len(rows) - fails}/{len(rows)} checks pass" + ("" if full else f" (groups: {', '.join(sel)})"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
