"""Generate the LTspice symbols (.asy) for the behavioral eFuse models.
Writes identical copies to symbols/ (canonical) and schematics/ (so the demo
schematics find them next to the .asc files)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asy(name, desc, box, pins, spiceline, texts=()):
    x0, y0, x1, y1 = box
    L = ["Version 4", "SymbolType CELL",
         f"RECTANGLE Normal {x0} {y0} {x1} {y1}"]
    for t in texts:
        L.append(t)
    L += [f"WINDOW 0 {x0} {y0 - 8} Left 2", f"WINDOW 3 {x0} {y1 + 8} Left 2",
          f"WINDOW 39 {x0} {y1 + 40} Left 1",
          f"SYMATTR Value {name}", "SYMATTR Prefix X",
          f"SYMATTR SpiceLine {spiceline}",
          f"SYMATTR Description {desc}"]
    for k, (pn, x, y, side) in enumerate(pins, 1):
        # short pin stub from the box edge to the connection point
        if side == "LEFT":
            L.append(f"LINE Normal {x} {y} {x + 16} {y}")
        elif side == "RIGHT":
            L.append(f"LINE Normal {x} {y} {x - 16} {y}")
        elif side == "BOTTOM":
            L.append(f"LINE Normal {x} {y} {x} {y - 16}")
        else:
            L.append(f"LINE Normal {x} {y} {x} {y + 16}")
        L += [f"PIN {x} {y} {side} {20 if side in ('LEFT', 'RIGHT') else 12}", f"PINATTR PinName {pn}", f"PINATTR SpiceOrder {k}"]
    return "\n".join(L) + "\n"


# VNF1048F: pin order must match the .subckt line
vnf_pins = [("VS", -144, -128, "LEFT"), ("CP", -144, -96, "LEFT"),
            ("ISNS_P", -144, -48, "LEFT"), ("ISNS_N", -144, -16, "LEFT"),
            ("HS_GATE", 144, -128, "RIGHT"), ("OUT", 144, -96, "RIGHT"),
            ("NTC", 144, -48, "RIGHT"), ("NTC_M", 144, -16, "RIGHT"),
            ("GND", 0, 176, "BOTTOM"), ("DIAG", 144, 48, "RIGHT"),
            ("OUTCTL", -144, 48, "LEFT"), ("BYPCTL", -144, 80, "LEFT"),
            ("CLR", -144, 112, "LEFT"), ("CS", 144, 80, "RIGHT")]
vnf = asy("VNF1048F",
          "Behavioral model of ST VNF1048F-style 48V eFuse controller (unofficial). Needs .include VNF1048F_beh.lib",
          (-128, -160, 128, 160), vnf_pins,
          "OVC_CODE=10 HSC_CODE=10 VDS_CODE=10 NTC_CODE=4 TNOM_CODE=0 FUSE_MODE=0 CPON=1",
          ["TEXT 0 -24 Center 2 VNF1048F", "TEXT 0 8 Center 1 (behavioral)"])

mod_pins = [("VBAT", -144, -96, "LEFT"), ("OUT", 144, -96, "RIGHT"),
            ("GND", 0, 144, "BOTTOM"), ("EN", -144, 0, "LEFT"),
            ("BYP", -144, 32, "LEFT"), ("CLR", -144, 64, "LEFT"),
            ("DIAG", 144, 0, "RIGHT"), ("CS", 144, 32, "RIGHT"),
            ("TFET", 144, 64, "RIGHT")]
mod = asy("EFUSE48_MOD",
          "Complete 48V eFuse channel: VNF1048F behavioral + shunt + 100V MOSFET + NTC + passives. Needs .include VNF1048F_beh.lib",
          (-128, -128, 128, 128), mod_pins,
          "RSENSE=1m OVC_CODE=13 HSC_CODE=12 VDS_CODE=14 NTC_CODE=4 TNOM_CODE=0",
          ["TEXT 0 -40 Center 2 48V eFuse", "TEXT 0 -8 Center 1 VNF1048F + FET"])

ntc_pins = [("A", -64, 0, "LEFT"), ("B", 64, 0, "RIGHT"), ("T", 0, -48, "TOP"), ("GND", 0, 48, "BOTTOM")]
ntc = asy("NTC10K_ST", "10k NTC thermistor (fit to VNF1048F NTC thresholds); T = temperature node [degC]",
          (-48, -32, 48, 32), ntc_pins, "", ["TEXT 0 0 Center 1 NTC 10k", "LINE Normal -40 24 40 -24"])
ntc = ntc.replace("SYMATTR SpiceLine \n", "")

for d in ("symbols", "schematics"):
    os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    open(os.path.join(ROOT, d, "VNF1048F.asy"), "w").write(vnf)
    open(os.path.join(ROOT, d, "EFUSE48_MOD.asy"), "w").write(mod)
    open(os.path.join(ROOT, d, "NTC10K_ST.asy"), "w").write(ntc)
print("symbols written")
