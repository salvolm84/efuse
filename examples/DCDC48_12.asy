Version 4
SymbolType CELL
RECTANGLE Normal -112 -80 112 80
TEXT 0 -40 Center 2 48V -> 12V
TEXT 0 -12 Center 1 DC/DC 700 W
LINE Normal -40 56 40 16
WINDOW 0 -28 100 Right 2
WINDOW 3 -28 128 Right 2
WINDOW 39 -28 152 Right 1
SYMATTR Value DCDC48_12
SYMATTR Prefix X
SYMATTR SpiceLine VSET=14 PRATED=700 DCRUN=0
SYMATTR Description 700 W 48/12 V buck converter, averaged behavioral model (regulation, current limit, hiccup, UVLO/OVP, losses). Needs .include DCDC48_12_beh.lib
LINE Normal -128 -32 -112 -32
PIN -128 -32 LEFT 20
PINATTR PinName VIN
PINATTR SpiceOrder 1
LINE Normal 128 -32 112 -32
PIN 128 -32 RIGHT 20
PINATTR PinName VOUT
PINATTR SpiceOrder 2
LINE Normal 0 96 0 80
PIN 0 96 BOTTOM 24
PINATTR PinName GND
PINATTR SpiceOrder 3
LINE Normal -128 32 -112 32
PIN -128 32 LEFT 20
PINATTR PinName EN
PINATTR SpiceOrder 4
LINE Normal 128 32 112 32
PIN 128 32 RIGHT 20
PINATTR PinName PG
PINATTR SpiceOrder 5
