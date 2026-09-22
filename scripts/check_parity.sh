#!/usr/bin/env bash
# Generador con literales vs. con content.json: el HTML debe ser idéntico. Imprime "PARIDAD OK" o el diff.
# No toca nada trackeado: exporta a un temporal y corre los dos builds con --no-cleanup, para que
# la poda de images/_opt no borre derivados que el otro build (o el sitio publicado) sí usa.
set -euo pipefail
cd "$(dirname "$0")/.."
A=$(mktemp -d); B=$(mktemp -d)
python3 scripts/export_content.py --out "$B/content.json"
for d in css js fonts icons images; do ln -s "$PWD/$d" "$A/$d"; ln -s "$PWD/$d" "$B/$d"; done
cp build_site.py i18n.py "$A/"; cp build_site.py i18n.py "$B/"
(cd "$A" && python3 build_site.py --no-cleanup >/dev/null)
(cd "$B" && python3 build_site.py --no-cleanup --content content.json >/dev/null)
if diff -r -x images -x css -x js -x fonts -x icons -x build_site.py -x i18n.py -x content.json -x __pycache__ "$A" "$B" >/tmp/parity.diff; then
  echo "PARIDAD OK"; rm -rf "$A" "$B"
else
  head -60 /tmp/parity.diff; echo "PARIDAD FALLÓ (diff completo en /tmp/parity.diff)"; exit 1
fi
