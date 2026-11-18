Version 4
SymbolType CELL
RECTANGLE Normal -96 -80 96 80
LINE Normal -32 -40 32 -40
LINE Normal -16 -24 16 -24
LINE Normal -32 -8 32 -8
LINE Normal -16 8 16 8
TEXT -8 44 Center 1 Battery + BMS
WINDOW 0 -28 100 Right 2
WINDOW 3 -28 128 Right 2
WINDOW 39 -28 152 Right 1
SYMATTR Value BATTERY_BMS
SYMATTR Prefix X
SYMATTR SpiceLine VNOM=48 SOC0=0.8 TBAT=25 T_PRE=0
SYMATTR Description Battery pack with BMS: BATTERY + disconnect switch, OV/UV/OC/SC protection, pre-charge. Needs .include BATTERY_beh.lib
LINE Normal 0 -96 0 -80
PIN 0 -96 TOP 24
PINATTR PinName P
PINATTR SpiceOrder 1
LINE Normal 0 96 0 80
PIN 0 96 BOTTOM 24
PINATTR PinName N
PINATTR SpiceOrder 2
LINE Normal 112 -32 96 -32
PIN 112 -32 RIGHT 20
PINATTR PinName SOC
PINATTR SpiceOrder 3
LINE Normal -112 0 -96 0
PIN -112 0 LEFT 20
PINATTR PinName EN
PINATTR SpiceOrder 4
LINE Normal 112 32 96 32
PIN 112 32 RIGHT 20
PINATTR PinName FLT
PINATTR SpiceOrder 5
