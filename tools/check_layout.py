"""Check the generated LTspice symbols and schematics for overlapping text.

    python3 tools/check_layout.py                 # report overlaps, exit 1 if any
    python3 tools/check_layout.py --png DIR       # also render every file to DIR/*.png

Every text that LTspice draws is turned into an estimated bounding box: the
attribute windows of each symbol instance (instance name, value, SpiceLine;
symbol defaults or the WINDOW overrides of the .asc, rotated and mirrored
with the instance), the pin names and TEXT of the symbols, net labels
(FLAG) and the comments and directives of the schematic. The boxes are
checked against each other, against wires, symbol graphics and pins, and
against the ground symbols.

The text size is an estimate of LTspice's font (Arial): line height
16 x the size factor (size 1 = 1.0, 2 = 1.5, ...) and 0.58 of the height
per character; boxes are shrunk by 2 units before the test so that touching
does not count. Built-in symbols (res, cap, voltage, ...) are read from the
local LTspice installation; without it they count as their pins only.
"""
import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMDIRS = [os.path.expanduser("~/Library/Application Support/LTspice/Bottles/ltspice/drive_c/users/crossover/"
                              "AppData/Local/LTspice/lib/sym"),
           os.path.expanduser("~/AppData/Local/LTspice/lib/sym"),
           os.path.expanduser("~/Documents/LTspice/lib/sym")]
SCALE = {0: 0.625, 1: 1.0, 2: 1.5, 3: 2.0, 4: 2.5, 5: 3.5, 6: 5.0, 7: 7.0}
LINE_H, CHAR_W, SHRINK = 16.0, 0.58, 2.0

ROT = {"R0": lambda x, y: (x, y), "R90": lambda x, y: (-y, x), "R180": lambda x, y: (-x, -y),
       "R270": lambda x, y: (y, -x), "M0": lambda x, y: (-x, y), "M90": lambda x, y: (-y, -x),
       "M180": lambda x, y: (x, -y), "M270": lambda x, y: (y, x)}


def text_box(x, y, just, size, s, vertical=False):
    """Corners of a text in its own frame (screen y down). Left/Right/Center:
    anchored at the vertical middle; Top: anchor above the text; Bottom: below."""
    h = LINE_H * SCALE.get(size, 1.5)
    w = max(len(s), 1) * CHAR_W * h
    j = just.lstrip("V")
    if j == "Left":
        a, b, c, d = 0, w, -h / 2, h / 2
    elif j == "Right":
        a, b, c, d = -w, 0, -h / 2, h / 2
    elif j == "Top":
        a, b, c, d = -w / 2, w / 2, 0, h
    elif j == "Bottom":
        a, b, c, d = -w / 2, w / 2, -h, 0
    else:
        a, b, c, d = -w / 2, w / 2, -h / 2, h / 2
    pts = [(a, c), (b, c), (b, d), (a, d)]
    if vertical or just.startswith("V"):       # reads bottom to top: rotate the frame by -90 deg
        pts = [(q, -p) for p, q in pts]
    return [(x + p, y + q) for p, q in pts]


def bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def parse(path):
    """Generic LTspice text-file parser: list of (keyword, tokens, rest-of-line)."""
    raw = open(path, "rb").read()
    txt = raw.decode("utf-16-le") if raw[1:2] == b"\x00" else raw.decode("latin-1")
    out = []
    for ln in txt.replace("\r", "").split("\n"):
        if ln.strip():
            out.append(ln.split(" ", 1)[0])
            out[-1] = (out[-1], ln)
    return out


class Symbol:
    def __init__(self, path):
        self.lines, self.rects, self.circles, self.texts, self.pins = [], [], [], [], []
        self.windows, self.attrs = {}, {}
        for kw, ln in parse(path) if path else []:
            t = ln.split()
            if kw == "LINE":
                self.lines.append(tuple(map(int, t[2:6])))
            elif kw == "RECTANGLE":
                self.rects.append(tuple(map(int, t[2:6])))
            elif kw in ("CIRCLE", "ARC"):
                self.circles.append(tuple(map(int, t[2:6])))
            elif kw == "TEXT":
                m = re.match(r"TEXT (-?\d+) (-?\d+) (\S+) (\d+) (.*)", ln)
                self.texts.append((int(m[1]), int(m[2]), m[3], int(m[4]), m[5]))
            elif kw == "WINDOW":
                self.windows[int(t[1])] = (int(t[2]), int(t[3]), t[4], int(t[5]))
            elif kw == "SYMATTR":
                self.attrs[t[1]] = ln.split(" ", 2)[2] if len(t) > 2 else ""
            elif kw == "PIN":
                self.pins.append([int(t[1]), int(t[2]), t[3], int(t[4]), ""])
            elif kw == "PINATTR" and t[1] == "PinName":
                self.pins[-1][4] = t[2]


def find_symbol(name, here):
    for d in [here] + SYMDIRS:
        p = os.path.join(d, name + ".asy")
        if os.path.isfile(p):
            return p
    return None


class Item:
    """A text box or a graphic segment/box on the sheet (a segment keeps its end points)."""
    def __init__(self, kind, box, label, owner=None, pts=None):
        self.kind, self.box, self.label, self.owner, self.pts = kind, box, label, owner, pts


def pin_text(px, py, orient, off, name):
    if orient == "LEFT":
        return text_box(px + off, py, "Left", 1, name)
    if orient == "RIGHT":
        return text_box(px - off, py, "Right", 1, name)
    if orient == "TOP":
        return text_box(px, py + off, "Top", 1, name)
    if orient == "BOTTOM":
        return text_box(px, py - off, "Bottom", 1, name)
    return None


def symbol_items(sym, tf, owner, label):
    """Graphics and fixed texts of a placed symbol, transformed by tf."""
    texts, graphics = [], []
    for x1, y1, x2, y2 in sym.lines:
        graphics.append(Item("seg", bbox([tf(x1, y1), tf(x2, y2)]), f"{label} line", owner, (tf(x1, y1), tf(x2, y2))))
    for x1, y1, x2, y2 in sym.rects + sym.circles:
        graphics.append(Item("box", bbox([tf(x1, y1), tf(x2, y2)]), f"{label} body", owner))
    for x, y, just, size, s in sym.texts:
        texts.append(Item("text", bbox([tf(*p) for p in text_box(x, y, just, size, s)]), f"{label} text '{s}'",
                          owner))
    for px, py, orient, off, name in sym.pins:
        graphics.append(Item("pin", bbox([tf(px, py), tf(px, py)]), f"{label} pin {name}", owner))
        if orient != "NONE" and name:
            pts = pin_text(px, py, orient, off, name)
            texts.append(Item("text", bbox([tf(*p) for p in pts]), f"{label} pin name {name}", owner))
    return texts, graphics


def items_asy(path):
    sym = Symbol(path)
    name = os.path.splitext(os.path.basename(path))[0]
    texts, graphics = symbol_items(sym, ROT["R0"], name, name)
    for wid, key in ((0, "InstName"), (3, "Value"), (39, "SpiceLine")):
        if wid in sym.windows:
            x, y, just, size = sym.windows[wid]
            s = {"InstName": "X1"}.get(key, sym.attrs.get(key, ""))
            if s and just != "Invisible":
                texts.append(Item("text", bbox(text_box(x, y, just, size, s)), f"{name} window {key}", name))
    return texts, graphics


def items_asc(path):
    here = os.path.dirname(path)
    texts, graphics, wires = [], [], []
    cur = None
    syms = []
    for kw, ln in parse(path):
        t = ln.split()
        if kw == "WIRE":
            x1, y1, x2, y2 = map(int, t[1:5])
            wires.append((x1, y1, x2, y2))
            graphics.append(Item("seg", bbox([(x1, y1), (x2, y2)]), f"wire {x1},{y1}-{x2},{y2}"))
        elif kw == "FLAG":
            x, y, net = int(t[1]), int(t[2]), t[3]
            if net == "0":
                graphics.append(Item("box", (x - 16, y, x + 16, y + 16), "ground", f"gnd{x},{y}"))
            else:
                texts.append(Item("flag", (x, y, net), f"net label '{net}'", f"flag{x},{y}"))
        elif kw == "TEXT":
            m = re.match(r"TEXT (-?\d+) (-?\d+) (\S+) (\d+) [;!](.*)", ln)
            texts.append(Item("text", bbox(text_box(int(m[1]), int(m[2]), m[3], int(m[4]), m[5])),
                              f"text '{m[5][:40]}'"))
        elif kw == "RECTANGLE":
            pass                                   # dashed frames: drawing only
        elif kw == "SYMBOL":
            cur = {"name": t[1], "x": int(t[2]), "y": int(t[3]), "rot": t[4], "win": {}, "attr": {}}
            syms.append(cur)
        elif kw == "WINDOW" and cur is not None:
            cur["win"][int(t[1])] = (int(t[2]), int(t[3]), t[4], int(t[5]) if len(t) > 5 else 2)
        elif kw == "SYMATTR" and cur is not None:
            cur["attr"][t[1]] = ln.split(" ", 2)[2] if len(t) > 2 else ""
    for c in syms:
        sp = find_symbol(c["name"], here)
        sym = Symbol(sp)
        rot = ROT[c["rot"]]
        tf = (lambda r, x0, y0: (lambda x, y: (x0 + r(x, y)[0], y0 + r(x, y)[1])))(rot, c["x"], c["y"])
        inst = c["attr"].get("InstName", c["name"])
        st, sg = symbol_items(sym, tf, inst, inst)
        texts += st
        graphics += sg
        wins = dict(sym.windows)
        wins.update(c["win"])
        attrs = dict(sym.attrs)
        attrs.update(c["attr"])
        for wid, key in ((0, "InstName"), (3, "Value"), (39, "SpiceLine"), (123, "Value2"), (40, "SpiceLine2")):
            if wid not in wins or not attrs.get(key):
                continue
            x, y, just, size = wins[wid]
            if just == "Invisible":
                continue
            s = attrs[key]
            if key == "SpiceLine" and wid not in c["win"] and wid not in sym.windows:
                continue
            # the box in the symbol frame (V* = reads upwards), turned with the
            # instance: a V-justified window on a 90/270 deg instance is horizontal
            pts = [rot(p, q) for p, q in text_box(0, 0, just, size, s)]
            ax, ay = tf(x, y)
            box = bbox([(ax + p, ay + q) for p, q in pts])
            # LTspice's own default window of a built-in symbol may touch the
            # symbol's artwork (e.g. a circle's bounding box): only other items count
            builtin = sp is not None and os.path.dirname(sp) != here and wid not in c["win"]
            texts.append(Item("text", box, f"{inst} {key} '{s[:40]}'", inst + ("#own" if builtin else "")))
    # net labels: LTspice puts the text beside the wire end, away from the wire
    for it in [i for i in texts if i.kind == "flag"]:
        x, y, net = it.box
        dirs = set()
        for x1, y1, x2, y2 in wires:
            for (ax, ay), (bx, by) in (((x1, y1), (x2, y2)), ((x2, y2), (x1, y1))):
                if (ax, ay) == (x, y):
                    dirs.add((0 if bx == ax else (1 if bx > ax else -1), 0 if by == ay else (1 if by > ay else -1)))
        h = LINE_H * 1.5
        w = len(net) * CHAR_W * h
        if dirs and all(d[1] == 0 for d in dirs):        # horizontal wire: text above
            it.box = (x - w / 2, y - h - 4, x + w / 2, y - 4)
        elif dirs:                                       # vertical wire: text to the side
            it.box = (x + 4, y - h / 2, x + 4 + w, y + h / 2) if (0, 1) in dirs or (0, -1) in dirs and (1, 0) not in dirs \
                else (x - 4 - w, y - h / 2, x - 4, y + h / 2)
        else:                                            # on a pin: text above
            it.box = (x - w / 2, y - h - 4, x + w / 2, y - 4)
        it.kind = "text"
    return texts, graphics


def hit(a, b, m=SHRINK):
    return a[0] + m < b[2] - m and b[0] + m < a[2] - m and a[1] + m < b[3] - m and b[1] + m < a[3] - m


def seg_hit(box, seg, m=SHRINK, pts=None):
    """A text box against a segment (exact for diagonal lines), a point or a box."""
    x0, y0, x1, y1 = box[0] + m, box[1] + m, box[2] - m, box[3] - m
    if not (seg[0] <= x1 and seg[2] >= x0 and seg[1] <= y1 and seg[3] >= y0):
        return False
    if pts is None or pts[0][0] == pts[1][0] or pts[0][1] == pts[1][1]:
        return True
    (ax, ay), (bx, by) = pts                     # Liang-Barsky clipping
    t0, t1, dx, dy = 0.0, 1.0, bx - ax, by - ay
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    return t0 <= t1


def overlaps(texts, graphics):
    out = []
    for i, a in enumerate(texts):
        own = a.owner[:-4] if a.owner and a.owner.endswith("#own") else None
        for b in texts[i + 1:]:
            if hit(a.box, b.box):
                out.append((a.label, b.label))
        for g in graphics:
            if own is not None and g.owner == own:
                continue
            if g.kind == "pin" and g.owner == a.owner:
                continue
            if g.kind == "box" and g.owner == a.owner and "body" in g.label:
                # text drawn inside its own symbol body is intended
                bx = g.box
                if a.box[0] >= bx[0] - 1 and a.box[2] <= bx[2] + 1 and a.box[1] >= bx[1] - 1 and a.box[3] <= bx[3] + 1:
                    continue
            if g.kind == "box" and g.owner == a.owner and ("text" in a.label or "pin name" in a.label):
                continue
            if seg_hit(a.box, g.box, pts=g.pts):
                out.append((a.label, g.label))
    return out


def render(path, texts, graphics, png, bad):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    boxes = [t.box for t in texts] + [g.box for g in graphics]
    x0 = min(b[0] for b in boxes) - 32; x1 = max(b[2] for b in boxes) + 32
    y0 = min(b[1] for b in boxes) - 32; y1 = max(b[3] for b in boxes) + 32
    sc = min(1.0, 3000 / max(x1 - x0, y1 - y0))
    fig = plt.figure(figsize=((x1 - x0) * sc / 100, (y1 - y0) * sc / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.axis("off")
    names = {n for pair in bad for n in pair}
    for g in graphics:
        b = g.box
        if g.kind == "seg":
            ax.plot([b[0], b[2]], [b[1], b[3]], color="#1d4ed8", lw=1)
        elif g.kind == "box":
            ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, color="#1d4ed8", lw=0.8))
        else:
            ax.plot([b[0]], [b[1]], "s", color="#b91c1c", ms=2)
    for t in texts:
        b = t.box
        col = "#dc2626" if t.label in names else "#6b7280"
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=t.label in names, alpha=0.25 if
                               t.label in names else 1, color=col, lw=0.6))
        s = t.label.split("'")[1] if "'" in t.label else t.label.split()[-1]
        ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, s[:60], ha="center", va="center", fontsize=4,
                rotation=90 if (b[3] - b[1]) > 2 * (b[2] - b[0]) else 0)
    fig.savefig(png)
    plt.close(fig)


def files():
    out = sorted(glob.glob(os.path.join(ROOT, "symbols", "*.asy")))
    out += sorted(glob.glob(os.path.join(ROOT, "schematics", "*.asc")))
    out += sorted(glob.glob(os.path.join(ROOT, "examples", "*.asc")))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--png", help="render each file with its text boxes into this folder")
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args()
    if not any(os.path.isdir(d) for d in SYMDIRS):
        print("note: LTspice built-in symbols not found, built-in parts are checked by their pins only")
    total = 0
    for p in a.paths or files():
        texts, graphics = (items_asy if p.endswith(".asy") else items_asc)(p)
        bad = overlaps(texts, graphics)
        total += len(bad)
        rel = os.path.relpath(p, ROOT)
        print(f"{rel}: {len(bad)} overlap(s)")
        for x, y in bad:
            print(f"    {x}  <->  {y}")
        if a.png:
            os.makedirs(a.png, exist_ok=True)
            render(p, texts, graphics, os.path.join(a.png, os.path.basename(p) + ".png"), bad)
    print(f"{total} overlap(s)")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
