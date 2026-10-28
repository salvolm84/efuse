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
