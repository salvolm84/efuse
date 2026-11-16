Version 4
SymbolType CELL
RECTANGLE Normal -48 -48 48 48
CIRCLE Normal -32 -32 32 32
TEXT 0 0 Center 1 ISO 7637
TEXT 8 -40 Left 1 +
WINDOW 0 -48 -56 Left 2
WINDOW 3 -48 56 Left 2
WINDOW 39 -48 88 Left 1
SYMATTR Value TP_ISO7637
SYMATTR Prefix X
SYMATTR SpiceLine US=-150 RI=10 TRISE=1u TDUR=2m DISC=1
SYMATTR Description Test-pulse source: ISO 7637-2 pulse (1, 2a, 3a, 3b); Value may be set to a preset of PULSES_beh.lib with the same pins. Needs .include PULSES_beh.lib
LINE Normal 0 -64 0 -48
PIN 0 -64 TOP 12
PINATTR PinName P
PINATTR SpiceOrder 1
LINE Normal 0 64 0 48
PIN 0 64 BOTTOM 12
PINATTR PinName N
PINATTR SpiceOrder 2
