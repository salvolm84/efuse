"""Keep the simulated numbers quoted in the documentation in sync with the
simulation results.

A quoted number is tagged with an HTML comment (invisible on GitHub) that
holds a Python format expression, followed by the number and a closing tag:

    the latch fires after <!--v {m('tb02_hard_short','dt_trip')*1e6:.1f}-->8.1<!--/v--> us

The tag must be on one line and the expression must start with "{".

`m(bench, meas, k=0)` returns the k-th value of a .meas result of a bench
(testbenches/ or schematics/, looked up by name); m('summary', 'checks_total')
and m('summary', 'checks_<group>') give the check counts of tools/validate.py. The expression is formatted
with str.format-like f-string rules, so any arithmetic is allowed.

    python3 tools/sync_docs.py                    # rewrite the tagged numbers from the .log files
    python3 tools/sync_docs.py --check            # only report stale numbers (exit 1 if any)
    python3 tools/sync_docs.py --json docs/results.json --check   # from stored results (CI)
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate  # noqa: E402  (result loading)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = ["README.md", "interview/pdn_48v_12v_interview_guide.md"]
# one tag = one line; the expression must start with "{". A tag can never span
# lines, so a stray or unbalanced tag cannot swallow text.
TAG = re.compile(r"<!--v (\{[^\n]*?)-->([^\n]*?)<!--/v-->")
OPEN = re.compile(r"<!--v \{")


def make_m(results):
    def m(bench, key, k=0):
        for folder in ("testbenches", "schematics", "validation"):
            r = results.get(f"{folder}/{bench}")
            if r is not None:
                v = r.get(key.lower(), [])
                if len(v) > k:
                    return v[k]
                raise KeyError(f"{bench}: no value {key}[{k}]")
        raise KeyError(f"no results for {bench}")
    return m


def u(x, fmt):
    """Format x with a typographic minus sign, as used in the docs."""
    return format(x, fmt).replace("-", "\u2212")


def render(expr, m):
    return eval("f" + repr(expr), {"m": m, "u": u, "abs": abs, "min": min, "max": max})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="report stale numbers, do not rewrite")
    ap.add_argument("--json", help="read the results from this JSON file instead of the .log files")
    a = ap.parse_args()
    if a.json:
        results = json.load(open(a.json))
    else:  # parse the logs and run the checks once, for the check counts
        results = validate.load_logs()
        validate.RESULTS = results
        counts = {}
        for g, fn in validate.GROUPS.items():
            n0 = len(validate.rows)
            try:
                fn()
            except validate.MissingResults:
                pass
            counts[f"checks_{g}"] = [len(validate.rows) - n0]
        counts["benches"] = [len(results)]
        counts["checks_total"] = [len(validate.rows)]
        counts["checks_passed"] = [len(validate.rows) - validate.fails]
        results["validation/summary"] = counts
    m = make_m(results)
    stale, errors, n = [], [], 0
    for doc in DOCS:
        path = os.path.join(ROOT, doc)
        text = open(path).read()

        def sub(mo):
            nonlocal n
            n += 1
            expr, old = mo.group(1), mo.group(2)
            try:
                new = render(expr, m)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{doc}: {expr}: {e}")
                return mo.group(0)
            if new != old:
                line = text.count("\n", 0, mo.start()) + 1
                stale.append(f"{doc}:{line}: {old!r} -> {new!r}   ({expr})")
            return f"<!--v {expr}-->{new}<!--/v-->"
        new_text = TAG.sub(sub, text)
        # every opener must belong to a complete tag on the same line
        for ln, line in enumerate(text.split("\n"), 1):
            if len(OPEN.findall(line)) != len(TAG.findall(line)):
                errors.append(f"{doc}:{ln}: unbalanced <!--v tag")
        if not a.check and new_text != text:
            open(path, "w").write(new_text)
    for e in errors:
        print("ERROR", e)
    for s in stale:
        print(("STALE " if a.check else "updated ") + s)
    print(f"{n} tagged numbers, {len(stale)} {'stale' if a.check else 'updated'}, {len(errors)} errors")
    sys.exit(1 if errors or (a.check and stale) else 0)


if __name__ == "__main__":
    main()
