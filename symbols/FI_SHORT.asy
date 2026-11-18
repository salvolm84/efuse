Version 4
SymbolType CELL
RECTANGLE Normal -48 -48 48 48
LINE Normal -16 -32 8 -4
LINE Normal 8 -4 -8 4
LINE Normal -8 4 16 32
TEXT 0 40 Center 1 FIU short
WINDOW 0 60 -24 Left 2
WINDOW 3 60 4 Left 2
WINDOW 39 60 28 Left 1
SYMATTR Value FI_SHORT
SYMATTR Prefix X
SYMATTR SpiceLine ID=1 FID=1 RF=10m TF=1m TTR=1u
SYMATTR Description Fault injection: short / leakage RF between A and B, active from TF when FID = ID (or ID2, ID3). Needs .include FAULTS_beh.lib
LINE Normal 0 -64 0 -48
PIN 0 -64 NONE 0
PINATTR PinName A
PINATTR SpiceOrder 1
LINE Normal 0 64 0 48
PIN 0 64 NONE 0
PINATTR PinName B
PINATTR SpiceOrder 2
