"""Static consistency checks of the model library (no simulation needed).

    python3 tools/lint_models.py

- every .subckt and .model name is defined once across models/*.lib
- every symbol (symbols/*.asy) names an existing subckt, its pins in SpiceOrder
  match the subckt pins, its SpiceLine parameters exist in the subckt, and the
  copy in schematics/ is identical
- the pin coordinates in tools/make_schematics.py (PINS) match the symbols
- every X instance in the libraries and test benches calls a subckt that is
  defined in the file or the files it includes, with the right number of
  nodes and only parameters the subckt declares
- every .include path exists

Exits non-zero on any problem.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_schematics  # noqa: E402  (PINS only; generation runs under __main__)
from validate import bench_inputs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errs = []


def lines(path):
    """Netlist lines with '+' continuations joined and comments dropped."""
    out = []
    for raw in open(path, encoding="latin-1").read().splitlines():
        s = raw.split(";")[0].rstrip()
        if not s.strip() or s.lstrip().startswith("*"):
            continue
        if s.lstrip().startswith("+") and out:
            out[-1] += " " + s.lstrip()[1:]
        else:
            out.append(s.strip())
    return out


def tokens(line):
    # keep {expr} and name={expr with spaces} together
    return re.findall(r"\S+=\{[^}]*\}|\{[^}]*\}|\S+=\S+|\S+", line)


def split_params(tok):
    nodes, params = [], {}
    for t in tok:
        if t.lower() == "params:":
            continue
        if "=" in t:
            k, v = t.split("=", 1)
            params[k.lower()] = v
        else:
            nodes.append(t)
    return nodes, params


def subckts(path):
    """{NAME: (pins, params)} defined in one file, and the X instances in it
    as (file, line, name, nodes, params)."""
    defs, inst, models = {}, [], []
    for ln in lines(path):
        tok = tokens(ln)
        head = tok[0].lower()
        if head == ".subckt":
            pins, params = split_params(tok[2:])
            if tok[1].upper() in defs:
                errs.append(f"{rel(path)}: .subckt {tok[1]} defined twice")
            defs[tok[1].upper()] = ([p.upper() for p in pins], set(params))
        elif head == ".model":
            models.append(tok[1].upper())
        elif head.startswith("x"):
            nodes, params = split_params(tok[1:])
            inst.append((path, tok[0], nodes[-1].upper(), nodes[:-1], params))
    return defs, inst, models


def rel(p):
    return os.path.relpath(p, ROOT)


# ---- library: unique subckt / model names -----------------------------------------
LIB = {}
where = {}
for lib in sorted(glob.glob(os.path.join(ROOT, "models", "*.lib"))):
    d, _, models = subckts(lib)
    for n in list(d) + [f".model {x}" for x in models]:
        if n in where:
            errs.append(f"{n} defined in both {where[n]} and {rel(lib)}")
        where[n] = rel(lib)
    LIB.update(d)

# ---- symbols -------------------------------------------------------------------
for asy in sorted(glob.glob(os.path.join(ROOT, "symbols", "*.asy"))):
    txt = open(asy, encoding="latin-1").read()
    name = os.path.splitext(os.path.basename(asy))[0]
    twin = os.path.join(ROOT, "schematics", os.path.basename(asy))
    if not os.path.isfile(twin) or open(twin, "rb").read() != open(asy, "rb").read():
        errs.append(f"{rel(asy)}: copy in schematics/ missing or different")
    value = re.search(r"^SYMATTR Value (\S+)", txt, re.M).group(1).upper()
    if value not in LIB:
        errs.append(f"{rel(asy)}: no subckt {value} in models/*.lib")
        continue
    pins = re.findall(r"^PIN (-?\d+) (-?\d+) \S+ \d+\nPINATTR PinName (\S+)\nPINATTR SpiceOrder (\d+)", txt, re.M)
    pins = sorted(pins, key=lambda p: int(p[3]))
    names = [p[2].upper() for p in pins]
    if names != LIB[value][0]:
        errs.append(f"{rel(asy)}: pins {names} != .subckt {value} {LIB[value][0]}")
    line = re.search(r"^SYMATTR SpiceLine (.*)$", txt, re.M)
    for k in split_params(tokens(line.group(1)))[1] if line else {}:
        if k not in LIB[value][1]:
            errs.append(f"{rel(asy)}: SpiceLine parameter {k} not declared by {value}")
    coords = [(int(p[0]), int(p[1])) for p in pins]
    if make_schematics.PINS.get(name) != coords:
        errs.append(f"tools/make_schematics.py: PINS[{name}] {make_schematics.PINS.get(name)} != {rel(asy)} {coords}")

# ---- instances in libraries and benches -----------------------------------------
files = sorted(glob.glob(os.path.join(ROOT, "models", "*.lib")) + glob.glob(os.path.join(ROOT, "testbenches", "*.cir")))
for f in files:
    for inc in re.findall(r"^\s*\.include\s+(\S+)", open(f, encoding="latin-1").read(), re.M | re.I):
        if not os.path.isfile(os.path.join(os.path.dirname(f), inc)):
            errs.append(f"{rel(f)}: .include {inc} not found")
    # a library may call subckts of the other libraries (they are included
    # together); a bench must include what it calls
    known = dict(LIB) if f.endswith(".lib") else {}
    for g in bench_inputs(f):
        if not g.endswith(".asc"):
            known.update(subckts(g)[0])
    for path, inst, sub, nodes, params in subckts(f)[1]:
        if sub not in known:
            errs.append(f"{rel(path)}: {inst} calls {sub}, not defined in the file or its includes")
            continue
        pins, declared = known[sub]
        if len(nodes) != len(pins):
            errs.append(f"{rel(path)}: {inst} has {len(nodes)} nodes, {sub} has {len(pins)} pins")
        for k in params:
            if k not in declared:
                errs.append(f"{rel(path)}: {inst} passes {k}, not a parameter of {sub}")

for e in errs:
    print("LINT", e)
print(f"lint: {len(LIB)} subckts, {len(files)} files, {len(errs)} problems")
sys.exit(1 if errs else 0)
