Version 4
SymbolType CELL
RECTANGLE Normal -48 -48 48 48
CIRCLE Normal -32 -32 32 32
TEXT 0 0 Center 1 RIPPLE
TEXT 8 -40 Left 1 +
WINDOW 0 -48 -56 Left 2
WINDOW 3 -48 56 Left 2
WINDOW 39 -48 88 Left 1
SYMATTR Value TP_RIPPLE
SYMATTR Prefix X
SYMATTR SpiceLine UB=15.5 UPP=1 FMIN=50 FMAX=25k TSW=60
SYMATTR Description Test-pulse source: ISO 16750-2 superimposed AC, log sweep; Value may be set to a preset of PULSES_beh.lib with the same pins. Needs .include PULSES_beh.lib
LINE Normal 0 -64 0 -48
PIN 0 -64 TOP 12
PINATTR PinName P
PINATTR SpiceOrder 1
LINE Normal 0 64 0 48
PIN 0 64 BOTTOM 12
PINATTR PinName N
PINATTR SpiceOrder 2
