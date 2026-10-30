"""Generate the LTspice symbols (.asy) for the behavioral models (eFuse, battery, DC/DC)
and the reference parameter sets.
Writes identical copies to symbols/ (canonical) and schematics/ (so the demo
schematics find them next to the .asc files)."""
import os

from make_schematics import write_if_changed

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

bat_pins = [("P", 0, -80, "TOP"), ("N", 0, 80, "BOTTOM"), ("SOC", 80, 0, "RIGHT")]
bat = asy("BATTERY",
          "Behavioral automotive battery (12/24/48 V class): OCV(SOC), R0 + 2 RC + L, charge counting. Needs .include BATTERY_beh.lib",
          (-64, -64, 64, 64), bat_pins, "VNOM=12 SOC0=0.8 TBAT=25",
          ["LINE Normal -32 -24 32 -24", "LINE Normal -16 -8 16 -8", "LINE Normal -32 8 32 8",
           "LINE Normal -16 24 16 24", "TEXT 40 -40 Left 1 +", "TEXT 0 44 Center 1 BATTERY"])

bms_pins = [("P", 0, -96, "TOP"), ("N", 0, 96, "BOTTOM"), ("SOC", 112, -32, "RIGHT"),
            ("EN", -112, 0, "LEFT"), ("FLT", 112, 32, "RIGHT")]
bms = asy("BATTERY_BMS",
          "Battery pack with BMS: BATTERY + disconnect switch, OV/UV/OC/SC protection, pre-charge. Needs .include BATTERY_beh.lib",
          (-96, -80, 96, 80), bms_pins, "VNOM=48 SOC0=0.8 TBAT=25 T_PRE=0",
          ["LINE Normal -32 -40 32 -40", "LINE Normal -16 -24 16 -24", "LINE Normal -32 -8 32 -8",
           "LINE Normal -16 8 16 8", "TEXT 0 36 Center 2 Battery + BMS"])

dc_pins = [("VIN", -128, -32, "LEFT"), ("VOUT", 128, -32, "RIGHT"), ("GND", 0, 96, "BOTTOM"),
           ("EN", -128, 32, "LEFT"), ("PG", 128, 32, "RIGHT")]
dcdc = asy("DCDC48_12",
           "700 W 48/12 V buck converter, averaged behavioral model (regulation, current limit, hiccup, UVLO/OVP, losses). Needs .include DCDC48_12_beh.lib",
           (-112, -80, 112, 80), dc_pins, "VSET=14 PRATED=700 DCRUN=0",
           ["TEXT 0 -24 Center 2 48V -> 12V", "TEXT 0 8 Center 1 DC/DC 700 W", "LINE Normal -64 40 64 -40"])

# reference parameter sets (models/REFERENCE_SETS_beh.lib): base-model pins
REF_INC = "Needs .include BATTERY_beh.lib, DCDC48_12_beh.lib (as used) and REFERENCE_SETS_beh.lib"
varta = asy("BAT12_VARTA_E39", "12 V 70 Ah AGM, Varta Silver Dynamic AGM E39 (fitted to public data). " + REF_INC,
            (-64, -64, 64, 64), bat_pins, "SOC0=0.8 TBAT=25",
            ["LINE Normal -32 -24 32 -24", "LINE Normal -16 -8 16 -8", "LINE Normal -32 8 32 8",
             "LINE Normal -16 24 16 24", "TEXT 40 -40 Left 1 +", "TEXT 0 44 Center 1 VARTA E39"])
a123 = asy("BAT48_A123_8AH", "48 V 8 Ah LiFePO4 pack with BMS, A123 (SAE 2018-01-0433, fitted). " + REF_INC,
           (-96, -80, 96, 80), bms_pins, "SOC0=0.5 TBAT=25 T_PRE=0",
           ["LINE Normal -32 -40 32 -40", "LINE Normal -16 -24 16 -24", "LINE Normal -32 -8 32 -8",
            "LINE Normal -16 8 16 8", "TEXT 0 36 Center 2 A123 48V 8Ah"])
rd210 = asy("DCDC_TOSHIBA_RD210", "3 kW 48/12 V converter, Toshiba RD210 reference design (fitted). " + REF_INC,
            (-112, -80, 112, 80), dc_pins, "VSET=12 DCRUN=0",
            ["TEXT 0 -24 Center 2 48V -> 12V", "TEXT 0 8 Center 1 RD210 3 kW", "LINE Normal -64 40 64 -40"])

for d in ("symbols", "schematics"):
    os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    write_if_changed(os.path.join(ROOT, d, "VNF1048F.asy"), vnf)
    write_if_changed(os.path.join(ROOT, d, "EFUSE48_MOD.asy"), mod)
    write_if_changed(os.path.join(ROOT, d, "NTC10K_ST.asy"), ntc)
    write_if_changed(os.path.join(ROOT, d, "BATTERY.asy"), bat)
    write_if_changed(os.path.join(ROOT, d, "BATTERY_BMS.asy"), bms)
    write_if_changed(os.path.join(ROOT, d, "DCDC48_12.asy"), dcdc)
    write_if_changed(os.path.join(ROOT, d, "BAT12_VARTA_E39.asy"), varta)
    write_if_changed(os.path.join(ROOT, d, "BAT48_A123_8AH.asy"), a123)
    write_if_changed(os.path.join(ROOT, d, "DCDC_TOSHIBA_RD210.asy"), rd210)
print("symbols written")
