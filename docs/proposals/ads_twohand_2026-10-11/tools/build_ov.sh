#!/bin/sh
# build_ov.sh <out.pk3>   the revolver / pistol test overlay from ./stage + the staged rows files (run in ads2h)
cd "$(dirname "$0")"
MKOV_EXTRA="rows_webley_empty.txt;rows_nagant.txt;rows_m10.txt;rows_pistol_empty.txt;rows_cycle.txt" \
MKOV_BLOCK="${MKOV_BLOCK-}" \
python mkov.py "$1" $(cat ovargs_default.txt) $(cat ovargs_idle.txt) | grep -v "^file:\|^row:"
