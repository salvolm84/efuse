Version 4
SymbolType CELL
RECTANGLE Normal -48 -48 48 48
CIRCLE Normal -32 -32 32 32
TEXT 0 0 Center 1 STEP
TEXT 8 -40 Left 1 +
WINDOW 0 -48 -56 Left 2
WINDOW 3 -48 56 Left 2
WINDOW 39 -48 88 Left 1
SYMATTR Value TP_STEP
SYMATTR Prefix X
SYMATTR SpiceLine UB=13.5 U1=24 TD=10m T1=60
SYMATTR Description Test-pulse source: level change UB -> U1 -> UB (jump start, over-voltage, drop, LV 148); Value may be set to a preset of PULSES_beh.lib with the same pins. Needs .include PULSES_beh.lib
LINE Normal 0 -64 0 -48
PIN 0 -64 TOP 12
PINATTR PinName P
PINATTR SpiceOrder 1
LINE Normal 0 64 0 48
PIN 0 64 BOTTOM 12
PINATTR PinName N
PINATTR SpiceOrder 2
