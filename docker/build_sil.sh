#!/usr/bin/env bash
# Build every sil/*_main.cpp against the portable firmware core. New hardware
# backends only need a new SIL main; this script discovers them automatically.
set -euo pipefail
cd /app
shopt -s nullglob

core=(firmware/src/vg_core/*.cpp)

for src in sil/*_main.cpp; do
  [ -e "$src" ] || continue
  base=$(basename "$src" _main.cpp)
  echo "building SIL: $base"
  g++ -O2 -std=c++17 -I firmware/src -I firmware/src/vg_core \
    "$src" "${core[@]}" -o "/usr/local/bin/vg-sil-$base"
done
