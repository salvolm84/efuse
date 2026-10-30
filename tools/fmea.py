"""FMEA simulation: evaluate a fault-injection bench against its FMEA table.

The table (CSV, docs/fmea/<bench>.csv; template docs/fmea/FMEA_TEMPLATE.csv)
has one row per scenario FID of the bench (.step param FID):

    FID, Item, Function, Failure mode, Failure cause, Injection,
    Expected effect, S, Expected detection, Max detection time [ms],
    Expected safe state, Criteria

* Expected detection: the mechanisms that must react, comma-separated, each
  a detection .meas "t_<name>" of the bench (time of the first reaction after
  the fault), e.g. "DIAG2, FLTB"; "none" = no mechanism may react (the fault
  is undetected, as expected). Each listed mechanism must react within
  "Max detection time" after the fault onset TF (.param TF in the bench).
* Criteria: semicolon-separated conditions on the bench's .meas names (SI
  units) at that scenario, e.g. "v12_max < 16; ipack_end < 1". They encode
  the expected effect and safe state as numbers.

    python3 tools/fmea_report.py                  # writes docs/fmea/<bench>.md
"""
import csv
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FMEA_DIR = os.path.join(ROOT, "docs", "fmea")
MECHS = {"DIAG1": "t_diag1", "DIAG2": "t_diag2", "FLTB": "t_fltb", "PG": "t_pg"}


def tables():
    """FMEA tables that belong to a bench: {bench name: csv path}."""
    out = {}
    for f in sorted(os.listdir(FMEA_DIR)):
        b = os.path.splitext(f)[0]
        if f.endswith(".csv") and os.path.isfile(os.path.join(ROOT, "testbenches", b + ".cir")):
            out[b] = os.path.join(FMEA_DIR, f)
    return out


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fault_onset(bench):
    txt = open(os.path.join(ROOT, "testbenches", bench + ".cir"), encoding="latin-1").read()
    m = re.search(r"^\.param\s+TF\s*=\s*([0-9.eE+-]+)(m|u)?\s*$", txt, re.M | re.I)
    scale = {"m": 1e-3, "u": 1e-6, None: 1.0}[m.group(2) and m.group(2).lower()]
    return float(m.group(1)) * scale


def mechanisms(text):
    t = text.strip()
    return [] if t.lower() in ("none", "") else [x.strip().upper() for x in t.split(",")]


def evaluate(res, bench, row):
    """Checks of one FMEA row: [(what, value, lo, hi, unit, ref)], and the
    simulated detection {mechanism: delay [s] or NaN}. res(key, k) returns
    the k-th value of a .meas of the bench."""
    k = int(row["FID"])
    tf = fault_onset(bench)
    det = {}
    for mech, key in MECHS.items():
        t = res(key, k)
        det[mech] = t - tf if not math.isnan(t) else float("nan")
    want = mechanisms(row["Expected detection"])
    out = []
    if want:
        tmax = float(row["Max detection time [ms]"]) * 1e-3
        n_ok = sum(1 for mch in want if not math.isnan(det[mch]) and det[mch] <= tmax)
        out.append((f"FID {k}: detected by {', '.join(want)} within {tmax * 1e3:g} ms", n_ok, len(want), len(want),
                    "", row["Failure mode"]))
    else:
        n_det = sum(1 for v in det.values() if not math.isnan(v))
        out.append((f"FID {k}: no detection (as expected)", n_det, 0, 0, "", row["Failure mode"]))
    names = {}
    for crit in [c.strip() for c in row["Criteria"].split(";") if c.strip()]:
        for name in re.findall(r"[A-Za-z_]\w*", crit):
            names[name] = res(name, k)
        ok = eval(crit, {"__builtins__": {}}, dict(names))  # noqa: S307 (expressions from the repo's table)
        out.append((f"FID {k}: {crit}", 1.0 if ok else 0.0, 1, 1, "", row["Expected effect"]))
    return out, det
