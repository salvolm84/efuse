Version 4
SymbolType CELL
RECTANGLE Normal -48 -32 48 32
TEXT 0 0 Center 1 NTC 10k
LINE Normal -40 24 40 -24
WINDOW 0 -48 -40 Left 2
WINDOW 3 -48 40 Left 2
WINDOW 39 -48 72 Left 1
SYMATTR Value NTC10K_ST
SYMATTR Prefix X
SYMATTR Description 10k NTC thermistor (fit to VNF1048F NTC thresholds); T = temperature node [degC]
LINE Normal -64 0 -48 0
PIN -64 0 LEFT 20
PINATTR PinName A
PINATTR SpiceOrder 1
LINE Normal 64 0 48 0
PIN 64 0 RIGHT 20
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
