#!/usr/bin/env bash
# Build desde el código (literales) vs. build desde Directus (dry-run del builder), normalizando rutas de archivos con cms/seed_map.json.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DIRECTUS_URL:=https://admin.santarosa.lat}"; : "${DIRECTUS_TOKEN:?token del builder (o admin)}"
SITES_ROOT="${SITES_ROOT:-$HOME/.cache/zeekr-builder}"; mkdir -p "$SITES_ROOT"
A=$(mktemp -d)
for d in css js fonts icons images; do ln -s "$PWD/$d" "$A/$d"; done
cp build_site.py i18n.py "$A/"; (cd "$A" && python3 build_site.py >/dev/null)
REPO_DIR="$PWD" SITES_ROOT="$SITES_ROOT" DIRECTUS_URL="$DIRECTUS_URL" DIRECTUS_TOKEN="$DIRECTUS_TOKEN" builder/.venv/bin/python -m builder.build_runner --site-settings 1 --mode publish --dry-run
B="$SITES_ROOT/zeekr/workspace/publish"
python3 scripts/normalize_cms_paths.py "$B" cms/seed_map.json
if diff -r -x images -x css -x js -x fonts -x icons -x build_site.py -x i18n.py -x content.json -x __pycache__ -x 'i18n_missing_*' "$A" "$B" >/tmp/parity_cms.diff; then
  echo "PARIDAD CMS OK"; rm -rf "$A"
else
  head -80 /tmp/parity_cms.diff; echo "PARIDAD CMS FALLÓ (/tmp/parity_cms.diff)"; exit 1
fi
