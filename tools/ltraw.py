"""Minimal reader for LTspice .raw files (binary or ASCII, incl. .step runs).

    from ltraw import LTRaw
    r = LTRaw("tb01_startup_inrush.raw")
    t = r["time"]; v = r["V(out)"]            # first step
    for k in range(r.nsteps): r.get("V(out)", k)
"""
import numpy as np


class LTRaw:
    def __init__(self, path):
        data = open(path, "rb").read()
        enc = "utf-16-le" if data[1:2] == b"\x00" else "latin-1"
        key_b = "Binary:\n".encode(enc)
        key_a = "Values:\n".encode(enc)
        ib, ia = data.find(key_b), data.find(key_a)
        binary = ib >= 0
        i = ib if binary else ia
        hdr = data[:i].decode(enc)
        body = data[i + len(key_b if binary else key_a):]
        self.header = hdr
        lines = hdr.splitlines()
        nvar = int(next(l for l in lines if l.startswith("No. Variables")).split(":")[1])
        npts = int(next(l for l in lines if l.startswith("No. Points")).split(":")[1])
        flags = next((l for l in lines if l.startswith("Flags")), "")
        k = lines.index("Variables:")
        self.names = [lines[k + 1 + j].split("\t")[2] for j in range(nvar)]
        self.idx = {n.lower(): j for j, n in enumerate(self.names)}
        if binary and "complex" in flags:  # .ac: every variable is complex double
            arr = np.frombuffer(body[: npts * nvar * 16], dtype="<c16").reshape(npts, nvar).copy()
            arr[:, 0] = arr[:, 0].real
            self.data = arr
            self.bounds = [(0, npts)]
            self.nsteps = 1
            return
        if binary:
            if "double" in flags:
                arr = np.frombuffer(body[: npts * nvar * 8], dtype="<f8").reshape(npts, nvar)
            else:  # time double, others float32
                rec = np.dtype([("t", "<f8")] + [(f"v{j}", "<f4") for j in range(1, nvar)])
                a = np.frombuffer(body[: npts * rec.itemsize], dtype=rec)
                arr = np.empty((npts, nvar))
                arr[:, 0] = a["t"]
                for j in range(1, nvar):
                    arr[:, j] = a[f"v{j}"]
        else:
            vals = body.decode(enc).split()
            arr = np.zeros((npts, nvar))
            p = 0
            for n in range(npts):
                p += 1  # point index
                for j in range(nvar):
                    arr[n, j] = float(vals[p].split(",")[0]); p += 1
        arr[:, 0] = np.abs(arr[:, 0])  # LTspice marks some time points negative
        self.data = arr
        t = arr[:, 0]
        starts = [0] + [n for n in range(1, len(t)) if t[n] < t[n - 1]]
        self.bounds = list(zip(starts, starts[1:] + [len(t)]))
        self.nsteps = len(self.bounds)

    def get(self, name, step=0):
        a, b = self.bounds[step]
        return self.data[a:b, self.idx[name.lower()]]

    def __getitem__(self, name):
        return self.get(name, 0)


def meas_log(path):
    """Parse '.meas' results of an LTspice .log into {name: [values per step]}."""
    import re
    out = {}
    txt = open(path, "rb").read()
    txt = txt.decode("utf-16-le") if txt[1:2] == b"\x00" else txt.decode("latin-1")
    for line in txt.splitlines():
        # .ac results are printed as "=(<mag>dB,<phase>°)": stored as the signed
        # real value |x|*cos(phase) (= |x| for mag(), sign kept for re())
        m = re.match(r"^\s*([A-Za-z_]\w*):\s.*?=\(([-+0-9.eE]+)dB,([-+0-9.eE]+)", line)
        if m:
            import math
            val = 10 ** (float(m.group(2)) / 20) * math.cos(math.radians(float(m.group(3))))
            out.setdefault(m.group(1).lower(), []).append(val)
            continue
        m = re.match(r"^\s*([A-Za-z_]\w*):\s.*?=\s*([-+0-9.eE]+)", line)
        if m:
            out.setdefault(m.group(1).lower(), []).append(float(m.group(2)))
            continue
        # trig/targ results: "name=<value> FROM <t1> TO <t2>" (no colon)
        m = re.match(r"^\s*([A-Za-z_]\w*)=([-+0-9.eE]+)\s+FROM\s", line)
        if m:
            out.setdefault(m.group(1).lower(), []).append(float(m.group(2)))
    # stepped .meas tables
    blk = None
    for line in txt.splitlines():
        m = re.match(r"^Measurement:\s*(\w+)", line)
        if m:
            blk = m.group(1).lower(); out[blk] = []; continue
        if blk:
            f = line.split()
            if len(f) >= 2 and f[0].isdigit():
                try:
                    out[blk].append(float(f[1]))
                except ValueError:
                    out[blk].append(float("nan"))
            elif not f or not f[0].strip().startswith("step"):
                if f and not f[0].isdigit():
                    blk = None
    # 'Measurement "x" FAIL'ed': failed in every step (stepped runs print no
    # table then), stored as NaN for each step
    nsteps = max([len(v) for v in out.values()] + [1])
    for name in re.findall(r'^Measurement "(\w+)" FAIL\'ed', txt, re.M):
        out[name.lower()] = [float("nan")] * nsteps
    return out
