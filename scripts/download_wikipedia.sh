#!/usr/bin/env bash
set -euo pipefail

LANGUAGE="$1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_DIR="$(dirname "$SCRIPT_DIR")"

OUTPUT_DIR="$MAIN_DIR/data/xml/$LANGUAGE"
mkdir -p "$OUTPUT_DIR"

WIKI="${LANGUAGE}wiki"
BASE_URL="https://dumps.wikimedia.org/${WIKI}/latest/"
PATTERN="${WIKI}-latest-pages-articles[0-9]*.xml-p*.bz2"

wget -r -l1 -nd \
  -A "$PATTERN" \
  --reject '*multistream*' \
  -P "$OUTPUT_DIR" \
  "$BASE_URL"
