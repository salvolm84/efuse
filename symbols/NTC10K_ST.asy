Version 4
SymbolType CELL
RECTANGLE Normal -48 -32 48 32
TEXT -20 -12 Center 1 NTC
TEXT 22 12 Center 1 10k
LINE Normal -40 24 40 -24
TEXT 8 -40 Left 1 T
WINDOW 0 -28 52 Right 2
WINDOW 3 -28 80 Right 2
WINDOW 39 -28 104 Right 1
SYMATTR Value NTC10K_ST
SYMATTR Prefix X
SYMATTR Description 10k NTC thermistor (fit to VNF1048F NTC thresholds); T = temperature node [degC]
LINE Normal -64 0 -48 0
PIN -64 0 NONE 0
PINATTR PinName A
PINATTR SpiceOrder 1
LINE Normal 64 0 48 0
PIN 64 0 NONE 0
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
