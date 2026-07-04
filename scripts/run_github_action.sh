#!/usr/bin/env bash
set -uo pipefail

status=0
svgap check "$SVGAP_MANIFEST" || status=$?

if [[ -f "$SVGAP_REPORT" ]]; then
  svgap export "$SVGAP_REPORT" --sarif "$SVGAP_SARIF" --html "$SVGAP_HTML"
else
  echo "SV-Gap report was not written at $SVGAP_REPORT" >&2
  exit 2
fi

exit "$status"
