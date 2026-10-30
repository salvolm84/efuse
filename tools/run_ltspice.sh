#!/bin/zsh
# Run LTspice netlists/schematics in batch mode (-b) and print warnings/.meas.
# Works with native LTspice and with the macOS CrossOver-wrapped LTspice 24/26
# (which needs its bundled wine + bottle).
#   usage: tools/run_ltspice.sh [-t timeout_s] [-j jobs] testbenches/tb01_startup_inrush.cir [...]
#
# The previous outputs of each bench are deleted before it runs, so a failed
# run can never leave old results behind. Exit status is non-zero if any run
# timed out or did not complete ("Total elapsed time" missing from the .log).
#
# Environment overrides (defaults: the macOS CrossOver install of LTspice):
#   LTSPICE_WINE, LTSPICE_BOTTLE, LTSPICE_EXE   wine binary, bottle, LTspice.exe
#   LTSPICE_CMD                                 native LTspice command (no wine),
#                                               used when LTSPICE_WINE is not executable
WINE=${LTSPICE_WINE:-/Applications/LTspice.app/Contents/SharedSupport/ltspice/LTspice/wine}
BOTTLE=${LTSPICE_BOTTLE:-"$HOME/Library/Application Support/LTspice/Bottles/ltspice"}
EXE=${LTSPICE_EXE:-'C:\Program Files\ADI\LTspice\LTspice.exe'}
CMD=${LTSPICE_CMD:-LTspice}
TMO=900
JOBS=1
while [[ "$1" == -[tj] ]]; do
  if [[ $# -lt 2 || "$2" != <-> ]]; then echo "!! $1 needs a number" >&2; exit 2; fi
  if [[ "$1" == "-t" ]]; then TMO=$2; else JOBS=$2; fi
  shift 2
done
for f in "$@"; do
  if [[ "$f" == -* ]]; then echo "!! options go before the files: $f" >&2; exit 2; fi
done
if (( JOBS > 1 )); then
  # one bench per invocation; xargs exits non-zero if any of them failed
  printf '%s\0' "$@" | xargs -0 -n1 -P "$JOBS" "$0" -t "$TMO"
  exit $?
fi
if [[ ! -x "$WINE" ]] && ! command -v "$CMD" >/dev/null; then
  echo "!! LTspice not found: set LTSPICE_WINE/LTSPICE_BOTTLE or LTSPICE_CMD" >&2
  exit 2
fi
st=0
for f in "$@"; do
  abs="${f:A}"
  base="${abs:r}"
  rm -f "$base.log" "$base.raw" "$base.op.raw" "$base.log.raw" "$base.db" "$base.fail"
  if [[ -x "$WINE" ]]; then
    WINEPREFIX="$BOTTLE" WINEDEBUG=-all "$WINE" "$EXE" -b "Z:${abs//\//\\}" >/dev/null 2>&1 &
  else
    "$CMD" -b "$abs" >/dev/null 2>&1 &
  fi
  pid=$!; n=0
  while kill -0 $pid 2>/dev/null; do
    sleep 1; n=$((n+1))
    if (( n > TMO )); then pkill -f "${abs:t}"; kill $pid 2>/dev/null; echo "!! timeout ${f:t}"; break; fi
  done
  log="$base.log"
  echo "== ${f:t}  (${n}s)"
  if [[ ! -f "$log" ]]; then
    echo "!! no log written: ${f:t}"
    # seen after killing a stalled run: hung winedevice.exe processes block every later run
    if [[ -x "$WINE" ]] && pgrep -f winedevice.exe >/dev/null; then
      echo "   if no bench writes a log any more: pkill -9 -f winedevice.exe; WINEPREFIX=\"$BOTTLE\" ${WINE:h:h}/bin/wineserver -k"
    fi
    st=1; continue
  fi
  # older LTspice versions write UTF-16 logs
  txt=$(if [[ "$(head -c 2 "$log" | od -An -tx1)" == *00* ]]; then iconv -f UTF-16LE -t UTF-8 "$log"; else cat "$log"; fi)
  print -r -- "$txt" | grep -iE "error|fail|singular|time step too small|not found|unknown|^[a-z_0-9]+:" \
    | grep -v "Direct Newton iteration failed" || true
  if ! print -r -- "$txt" | grep -q "Total elapsed time"; then
    echo "!! incomplete run (no 'Total elapsed time' in the log): ${f:t}"; st=1
  fi
done
exit $st
