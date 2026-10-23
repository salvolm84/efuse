#!/bin/zsh
# Run LTspice netlists/schematics in batch mode (-b) and print warnings/.meas.
# Works with native LTspice and with the macOS CrossOver-wrapped LTspice 24/26
# (which needs its bundled wine + bottle).
#   usage: tools/run_ltspice.sh [-t timeout_s] testbenches/tb01_startup_inrush.cir [...]
WINE=/Applications/LTspice.app/Contents/SharedSupport/ltspice/LTspice/wine
BOTTLE="$HOME/Library/Application Support/LTspice/Bottles/ltspice"
EXE='C:\Program Files\ADI\LTspice\LTspice.exe'
TMO=900
if [[ "$1" == "-t" ]]; then TMO=$2; shift 2; fi
for f in "$@"; do
  abs="${f:A}"
  if [[ -x "$WINE" ]]; then
    WINEPREFIX="$BOTTLE" WINEDEBUG=-all "$WINE" "$EXE" -b "Z:${abs//\//\\}" >/dev/null 2>&1 &
  else
    LTspice -b "$abs" >/dev/null 2>&1 &
  fi
  pid=$!; n=0
  while kill -0 $pid 2>/dev/null; do
    sleep 1; n=$((n+1))
    if (( n > TMO )); then pkill -f "${abs:t}"; kill $pid 2>/dev/null; echo "!! timeout ${f:t}"; break; fi
  done
  log="${abs:r}.log"
  echo "== ${f:t}  (${n}s)"
  grep -iE "error|fail|singular|time step too small|not found|unknown|^[a-z_0-9]+:" "$log" \
    | grep -v "Direct Newton iteration failed" || true
done
