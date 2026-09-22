#!/usr/bin/env bash
# Generador con literales vs. con content.json: el HTML debe ser idéntico. Imprime "PARIDAD OK" o el diff.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/export_content.py
A=$(mktemp -d); B=$(mktemp -d)
for d in css js fonts icons images; do ln -s "$PWD/$d" "$A/$d"; ln -s "$PWD/$d" "$B/$d"; done
cp build_site.py i18n.py "$A/"; cp build_site.py i18n.py "$B/"; cp content/zeekr.json "$B/content.json"
(cd "$A" && python3 build_site.py >/dev/null)
(cd "$B" && python3 build_site.py --content content.json >/dev/null)
if diff -r -x images -x css -x js -x fonts -x icons -x build_site.py -x i18n.py -x content.json -x __pycache__ "$A" "$B" >/tmp/parity.diff; then
  echo "PARIDAD OK"; rm -rf "$A" "$B"
else
  head -60 /tmp/parity.diff; echo "PARIDAD FALLÓ (diff completo en /tmp/parity.diff)"; exit 1
fi
