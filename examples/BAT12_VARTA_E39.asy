Version 4
SymbolType CELL
RECTANGLE Normal -64 -64 64 64
LINE Normal -32 -24 32 -24
LINE Normal -16 -8 16 -8
LINE Normal -32 8 32 8
LINE Normal -16 24 16 24
TEXT 40 -40 Left 1 +
TEXT 0 44 Center 1 VARTA E39
WINDOW 0 -64 -72 Left 2
WINDOW 3 -64 72 Left 2
WINDOW 39 -64 104 Left 1
SYMATTR Value BAT12_VARTA_E39
SYMATTR Prefix X
SYMATTR SpiceLine SOC0=0.8 TBAT=25
SYMATTR Description 12 V 70 Ah AGM, Varta Silver Dynamic AGM E39 (fitted to public data). Needs .include BATTERY_beh.lib, DCDC48_12_beh.lib (as used) and REFERENCE_SETS_beh.lib
LINE Normal 0 -80 0 -64
PIN 0 -80 TOP 12
PINATTR PinName P
PINATTR SpiceOrder 1
LINE Normal 0 80 0 64
PIN 0 80 BOTTOM 12
PINATTR PinName N
PINATTR SpiceOrder 2
LINE Normal 80 0 64 0
PIN 80 0 RIGHT 20
PINATTR PinName SOC
PINATTR SpiceOrder 3
