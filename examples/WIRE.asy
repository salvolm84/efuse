Version 4
SymbolType CELL
RECTANGLE Normal -64 -32 64 32
LINE Normal -48 0 48 0
TEXT 0 -16 Center 1 WIRE
TEXT 24 -40 Left 1 T
TEXT 0 16 Center 1 R(T), L
WINDOW 0 -64 -40 Left 2
WINDOW 3 -64 40 Left 2
WINDOW 39 -64 72 Left 1
SYMATTR Value WIRE
SYMATTR Prefix X
SYMATTR SpiceLine LEN=1 CSA=2.5 TAMB=25
SYMATTR Description Wiring-harness wire segment: R(T) + contact R + loop L, conductor temperature T [degC] ref. to GND. Needs .include HARNESS_beh.lib
LINE Normal -80 0 -64 0
PIN -80 0 LEFT 20
PINATTR PinName A
PINATTR SpiceOrder 1
LINE Normal 80 0 64 0
PIN 80 0 RIGHT 20
PINATTR PinName B
PINATTR SpiceOrder 2
LINE Normal 0 -48 0 -32
PIN 0 -48 TOP 12
PINATTR PinName T
PINATTR SpiceOrder 3
LINE Normal 0 48 0 32
PIN 0 48 BOTTOM 12
PINATTR PinName GND
PINATTR SpiceOrder 4
