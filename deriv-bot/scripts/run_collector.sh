#!/usr/bin/env bash
set -euo pipefail
python collector/stream_ticks.py &
python collector/build_ohlc.py
