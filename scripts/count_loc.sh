#!/usr/bin/env bash
# Prints the current line count of the actual bot (src/ventanita/*.py).
# The README quotes a number from this; it goes stale the moment someone
# adds a line, so re-run it rather than trusting the README's copy.
set -euo pipefail
cd "$(dirname "$0")/.."
wc -l src/ventanita/*.py | tail -1 | awk '{print $1}'
