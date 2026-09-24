# Panel de contenido (Directus)

## Dónde está

- **Panel:** https://zeekrlife.com.py/cms/admin/ — atajo para los editores: https://zeekrlife.com.py/admin
  (302 a `/cms/admin/`, conserva la subruta: `/admin/content/news` → `/cms/admin/content/news`).
- **API:** https://zeekrlife.com.py/cms (p. ej. `/cms/server/health` → `{"status":"ok"}`).
- **Camino:** Cloudflare (túnel) → Traefik → app Coolify 16 `zeekr-web` (nginx: `location ^~ /cms/` en
  `nginx.conf` de `main` quita el prefijo) → app Coolify 18 `directus` por el alias de red `directus:8055`.
  nginx resuelve `directus` en cada pedido: si el panel está caído o redesplegando, el sitio sigue y solo
  `/cms/` da 502.
- **Por qué `/cms` y no `/admin` directo:** Directus arma la URL de su API cortando la ruta del navegador en
  `/admin`. Servido en `zeekrlife.com.py/admin`, la API quedaría en la raíz del sitio y chocaría con las
  páginas. En `/cms/admin/` la API queda en `/cms/`.
- `/cms/` lleva su propia CSP (la de Directus; la del sitio le rompería el panel), `X-Robots-Tag: noindex`, y
  `robots.txt` excluye `/cms/` y `/admin`.
- `admin.santarosa.lat` sigue apuntando a la misma app (fqdn en Coolify), pero con `PUBLIC_URL` en `/cms` la
  interfaz ahí **no carga** (pide sus archivos en `/cms/admin/…`); solo responde la API. No usarlo.

## App en Coolify

- App 18 `directus` (uuid `wx2hkkgxqsuavlc7t4yjgvlk`): imagen `directus/directus:11` (11.17.4), SQLite en
  `/directus/database/data.db`, alias de red `directus`.
- Volúmenes docker: `directus_database`, `directus_uploads`, `directus_extensions`.
- Variables: ver `directus.env.example` (los valores reales viven solo en Coolify). Se cambian con tinker
  pasando los valores por archivo temporal (nunca en la línea de comando) y se redespliega la app 18.
- **Sin SMTP todavía** (`EMAIL_*` sin cargar): el panel no manda mails de recuperar contraseña ni invitaciones.

## Credenciales (nunca en git)

| Archivo (notebook, modo 600) | Qué tiene |
|---|---|
| `~/.zeekr-cms-secrets.env` | `KEY`, `SECRET`, `ADMIN_PASSWORD` (inicial de croman@santarosa.com.py), `BUILDER_TOKEN` (el `X-Builder-Token` que mandan los Flows al builder; también cargado en Coolify) |
| `~/.zeekr-cms-prod.env` | `DIRECTUS_URL=https://zeekrlife.com.py/cms`, `DIRECTUS_ADMIN_TOKEN` (token estático de croman@), `DIRECTUS_BUILDER_TOKEN` (token estático de builder@santarosa.com.py = `DIRECTUS_TOKEN` del builder) |

El token estático del admin se fijó directo en `directus_users.token` (Directus 11 lo compara en texto plano),
pasando el valor por stdin a un script de Node dentro del contenedor, sin usar la contraseña. También se puede
regenerar desde el panel: Perfil → Token.

## Scripts (idempotentes, desde la notebook)

```bash
set -a; . ~/.zeekr-cms-prod.env; set +a
cd cms
python3 setup_schema.py                                   # colecciones, campos, carpetas, sitio zeekr
python3 setup_roles.py                                    # 1ª vez: BUILDER_STATIC_TOKEN="$DIRECTUS_BUILDER_TOKEN" python3 setup_roles.py
BUILDER_URL=http://zeekr-builder:8000 python3 setup_flows.py   # flow de dominio + botones Vista previa/Publicar/Volver
cd ..
builder/.venv/bin/python -m builder.seed_from_code        # contenido actual → Directus (2ª corrida: 0 subidas)
DIRECTUS_TOKEN="$DIRECTUS_BUILDER_TOKEN" SITES_ROOT=/tmp/zk-parity bash scripts/check_parity_cms.sh   # → PARIDAD CMS OK
```

- `setup_roles.py` no toca el token del builder en las corridas siguientes; para rotarlo:
  `ROTATE_BUILDER_TOKEN=1 BUILDER_STATIC_TOKEN=<nuevo>` (y actualizar el builder).
- Cloudflare bloquea el User-Agent `Python-urllib` (403, error 1010): `common.py` manda uno propio.
- `seed_map.json` guarda ruta del repo → id de archivo **de producción**. Si se corre el seed contra otra
  instancia, detecta que los ids no existen allí, resube y reescribe el mapa (no commitear ese mapa).
- Snapshot del esquema: `cms/schema.yaml`. Para comparar o reproducir en otro servidor:
  `curl -X POST "$DIRECTUS_URL/schema/diff?force=true" -H "Authorization: Bearer $DIRECTUS_ADMIN_TOKEN" -F file=@cms/schema.yaml`
  (204 = mismo esquema; si no, `POST /schema/apply` con el diff devuelto).

## Backup

- Cron del servidor (usuario `santarosa`), 03:30: `~/.local/bin/backup-directus.sh` (fuente versionada:
  `cms/backup-directus.sh`).
- Copia consistente de la SQLite con `VACUUM INTO` (la imagen no trae el CLI `sqlite3`) → `~/backups/directus/data-<fecha>.db`
  (se guardan 14 días) + espejo de `uploads/` en `~/backups/directus/uploads/`. Log en `~/backups/directus/backup.log`;
  si falla avisa por ntfy (`NTFY_TOPIC` de `~/.config/botika/healthcheck.env`).
- Restaurar: parar la app 18 en Coolify, `docker cp` del `.db` elegido a `/directus/database/data.db` y de
  `uploads/` a `/directus/uploads/` en el contenedor, redesplegar.

## Pendiente

- SMTP (Google Workspace) para recuperar contraseña e invitaciones.
- Primer ingreso de Croman: Directus pide completar el "project owner" y aceptar su licencia (BSL 1.1).
- App `zeekr-builder` en Coolify (los botones ya apuntan a `http://zeekr-builder:8000`) y host de vista previa.
