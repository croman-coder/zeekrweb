#!/usr/bin/env bash
# Backup diario del panel Directus (app Coolify "directus": SQLite + archivos subidos).
#
# Por qué así (24/09/2026):
#   - La imagen directus/directus:11 no trae el CLI sqlite3, así que la copia consistente
#     se hace con `VACUUM INTO` usando el módulo sqlite3 de Node que ya viene en la imagen
#     (vale con Directus escribiendo al mismo tiempo).
#   - /var/lib/docker no es legible por este usuario: la copia sale del contenedor con
#     `docker cp` y queda en ~/backups/directus (fuera del volumen: sobrevive si se borra).
#   - El contenedor se DESCUBRE por la etiqueta de Coolify (el nombre cambia en cada deploy).
#   - uploads/ se espeja entero (los archivos de Directus no cambian una vez subidos); sin
#     ellos la base restaurada apuntaría a imágenes que no existen.
# Restaurar: parar la app en Coolify, copiar data-<fecha>.db como /directus/database/data.db
# (y uploads/ a /directus/uploads) con `docker cp`, y volver a desplegar.
set -euo pipefail

CONF="${BACKUP_CONF:-$HOME/.config/botika/healthcheck.env}"   # solo para NTFY_TOPIC (aviso al celular)
# shellcheck disable=SC1090
[ -r "$CONF" ] && . "$CONF"

DEST="${BACKUP_DIR:-$HOME/backups/directus}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
STAMP="$(date +%F_%H%M)"
LOG="$DEST/backup.log"
mkdir -p "$DEST/uploads"
log() { echo "$(date +%FT%T) $*" >> "$LOG"; }

avisar() {
  [ -z "${NTFY_TOPIC:-}" ] && { log "  (sin NTFY_TOPIC en $CONF: no se pudo avisar)"; return 0; }
  curl -sS -m 15 -H "Title: $1" -H "Priority: urgent" -H "Tags: floppy_disk" -d "$2" \
    "https://ntfy.sh/${NTFY_TOPIC}" >/dev/null 2>&1 && log "  push enviado" || log "  push FALLO"
}
fallo() { log "ERROR: $1"; avisar "Backup Directus FALLÓ" "$1"; exit 1; }

C="$(docker ps -q -f label=coolify.resourceName=directus | head -1)"
[ -n "$C" ] || fallo "no hay contenedor corriendo con label coolify.resourceName=directus"

TMP="/directus/database/.backup-$STAMP.db"
docker exec -i -e TMP="$TMP" "$C" node - <<'JS' || fallo "VACUUM INTO falló (ver docker logs)"
const sqlite3 = require('/directus/node_modules/.pnpm/sqlite3@5.1.7/node_modules/sqlite3');
const db = new sqlite3.Database('/directus/database/data.db');
db.configure('busyTimeout', 30000);
db.run('VACUUM INTO ?', [process.env.TMP], (e) => { if (e) { console.error(e.message); process.exit(1); } db.close(); });
JS

OUT="$DEST/data-$STAMP.db"
docker cp "$C:$TMP" "$OUT" >/dev/null 2>&1 || { docker exec "$C" rm -f "$TMP"; fallo "docker cp de la base falló"; }
docker exec "$C" rm -f "$TMP"
head -c 15 "$OUT" | grep -q "SQLite format 3" || fallo "$OUT no es una base SQLite válida"
docker cp "$C:/directus/uploads/." "$DEST/uploads/" >/dev/null 2>&1 || fallo "docker cp de uploads falló"

find "$DEST" -maxdepth 1 -name 'data-*.db' -mtime +"$KEEP_DAYS" -delete
log "OK $(basename "$OUT") $(du -h "$OUT" | cut -f1), uploads $(du -sh "$DEST/uploads" | cut -f1)"
