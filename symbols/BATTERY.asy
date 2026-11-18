Version 4
SymbolType CELL
RECTANGLE Normal -64 -64 64 64
LINE Normal -32 -24 32 -24
LINE Normal -16 -8 16 -8
LINE Normal -32 8 32 8
LINE Normal -16 24 16 24
TEXT 40 -40 Left 1 +
TEXT 0 44 Center 1 BATTERY
TEXT 56 0 Right 1 SOC
WINDOW 0 -28 84 Right 2
WINDOW 3 -28 112 Right 2
WINDOW 39 -28 136 Right 1
SYMATTR Value BATTERY
SYMATTR Prefix X
SYMATTR SpiceLine VNOM=12 SOC0=0.8 TBAT=25
SYMATTR Description Behavioral automotive battery (12/24/48 V class): OCV(SOC), R0 + 2 RC + L, charge counting. Needs .include BATTERY_beh.lib
LINE Normal 0 -80 0 -64
PIN 0 -80 NONE 0
PINATTR PinName P
PINATTR SpiceOrder 1
LINE Normal 0 80 0 64
PIN 0 80 NONE 0
PINATTR PinName N
PINATTR SpiceOrder 2
LINE Normal 80 0 64 0
PIN 80 0 NONE 0
PINATTR PinName SOC
PINATTR SpiceOrder 3
