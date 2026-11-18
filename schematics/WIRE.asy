Version 4
SymbolType CELL
RECTANGLE Normal -64 -32 64 32
LINE Normal -48 0 48 0
TEXT 0 -16 Center 1 WIRE
TEXT 8 -40 Left 1 T
TEXT 0 16 Center 1 R(T), L
WINDOW 0 -28 52 Right 2
WINDOW 3 -28 80 Right 2
WINDOW 39 -28 104 Right 1
SYMATTR Value WIRE
SYMATTR Prefix X
SYMATTR SpiceLine LEN=1 CSA=2.5 TAMB=25
SYMATTR Description Wiring-harness wire segment: R(T) + contact R + loop L, conductor temperature T [degC] ref. to GND. Needs .include HARNESS_beh.lib
LINE Normal -80 0 -64 0
PIN -80 0 NONE 0
PINATTR PinName A
PINATTR SpiceOrder 1
LINE Normal 80 0 64 0
PIN 80 0 NONE 0
PINATTR PinName B
PINATTR SpiceOrder 2
LINE Normal 0 -48 0 -32
PIN 0 -48 NONE 0
PINATTR PinName T
PINATTR SpiceOrder 3
LINE Normal 0 48 0 32
PIN 0 48 NONE 0
PINATTR PinName GND
PINATTR SpiceOrder 4
