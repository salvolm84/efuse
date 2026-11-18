Version 4
SymbolType CELL
RECTANGLE Normal -80 -48 80 48
LINE Normal -48 -16 -16 -16
LINE Normal -16 -16 16 -32
LINE Normal 24 -16 48 -16
TEXT 0 16 Center 1 OC SWITCH
WINDOW 0 -80 -56 Left 2
WINDOW 3 -80 56 Left 2
WINDOW 39 -80 88 Left 1
SYMATTR Value OCSW
SYMATTR Prefix X
SYMATTR SpiceLine IMAX=10 TOC=1m RON=1m TRETRY=0 VCLAMP=80
SYMATTR Description Overcurrent switch: opens when |I| > IMAX for TOC, latched (EN low resets) or auto-retry; RON, active clamp, FLT output. Needs .include OCSW_beh.lib
LINE Normal -96 -16 -80 -16
PIN -96 -16 LEFT 20
PINATTR PinName IN
PINATTR SpiceOrder 1
LINE Normal 96 -16 80 -16
PIN 96 -16 RIGHT 20
PINATTR PinName OUT
PINATTR SpiceOrder 2
LINE Normal 0 64 0 48
PIN 0 64 BOTTOM 12
PINATTR PinName GND
PINATTR SpiceOrder 3
LINE Normal -96 16 -80 16
PIN -96 16 LEFT 20
PINATTR PinName EN
PINATTR SpiceOrder 4
LINE Normal 96 16 80 16
PIN 96 16 RIGHT 20
PINATTR PinName FLT
PINATTR SpiceOrder 5
