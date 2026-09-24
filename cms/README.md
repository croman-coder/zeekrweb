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
- La app 18 **no tiene dominio propio** en Coolify (fqdn vacío, sin etiquetas de Traefik): solo se llega por
  `zeekrlife.com.py/cms` o, dentro de la red `coolify`, por `http://directus:8055` (el builder).
- `admin.santarosa.lat` (primer dominio del panel) está en el fqdn de la app 16 y su nginx responde **302 a
  https://zeekrlife.com.py/admin** en cualquier ruta (server block propio al final de `nginx.conf`).

## App en Coolify

- App 18 `directus` (uuid `wx2hkkgxqsuavlc7t4yjgvlk`): imagen `directus/directus:11` (11.17.4), SQLite en
  `/directus/database/data.db`, alias de red `directus`.
- Volúmenes docker: `directus_database`, `directus_uploads`, `directus_extensions`.
- Variables: ver `directus.env.example` (los valores reales viven solo en Coolify). Se cambian con tinker
  pasando los valores por archivo temporal (nunca en la línea de comando) y se redespliega la app 18.
- **Sin SMTP todavía** (`EMAIL_*` sin cargar): el panel no manda mails de recuperar contraseña ni invitaciones.
- Cookies de sesión y refresh con `Secure` y `SameSite=Lax` (`SESSION_COOKIE_SECURE`, `REFRESH_TOKEN_COOKIE_SECURE`,
  `*_SAME_SITE`). Si alguna vez se prueba por http plano, el navegador no las guarda.
- Idioma: Directus **no lee** `DEFAULT_LANGUAGE`; el idioma del login y de los usuarios sin idioma propio es
  `default_language` de `/settings` (Configuración → Proyecto), fijado en `es-ES`.

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

## Builder (botones Vista previa / Publicar / Volver)

> **Hoy el sitio público todavía NO sale de acá.** zeekrlife.com.py lo sigue sirviendo la app 16 con el HTML
> del repo (`main`). El builder ya publica en el volumen `zeekr_sites`, pero el cambio del sitio a ese volumen
> es la Task 12. Hasta entonces, "Publicar" en el panel no cambia lo que ve el público.

### App en Coolify

- App 20 `zeekr-builder` (uuid `pymlwpcftohfpayqbwhobu9b`): `build_pack=dockerfile`, `/builder/Dockerfile`
  (contexto: raíz del repo), repo `croman-coder/zeekrweb` rama **`worktree-admin-cms`** (el código del builder
  todavía no está en `main`; al mergear, cambiar `git_branch` a `main`). Fuente "Public GitHub": no necesita
  credenciales porque el repo es público.
- **Sin dominio** (fqdn vacío, cero etiquetas de Traefik, sin puertos publicados): solo se llega desde la red
  `coolify` por el alias **`http://zeekr-builder:8000`** (`custom_network_aliases`). Corre como uid 10001.
- Volumen docker **`zeekr_sites`** → `/srv/sites`. Sobrevive a los redespliegues (el workspace, las releases y
  los symlinks quedan).
- Auto-deploy **apagado**: un push a la rama no redespliega. Para desplegar:
  ```bash
  ssh srpy-servidor "docker exec coolify php artisan tinker --execute='
  \$app=\App\Models\Application::where(\"name\",\"zeekr-builder\")->firstOrFail();
  echo queue_application_deployment(application:\$app, deployment_uuid:new_public_id(), force_rebuild:false)[\"deployment_uuid\"];'"
  ```
  Tarda ~35–45 s. Un build en curso se corta; al arrancar, el builder cierra como `error` las filas de
  `builds` que quedaron en `queued`/`running` ("el builder se reinició…").
- Variables (valores solo en Coolify; se cargan por archivo temporal + tinker, igual que las de Directus):

  | Variable | Valor |
  |---|---|
  | `DIRECTUS_URL` | `http://directus:8055` (red interna, sin pasar por Cloudflare) |
  | `DIRECTUS_TOKEN` | `DIRECTUS_BUILDER_TOKEN` de `~/.zeekr-cms-prod.env` (usuario builder@, rol Builder) |
  | `BUILDER_TOKEN` | el mismo `BUILDER_TOKEN` de Directus (`~/.zeekr-cms-secrets.env`): lo mandan los Flows en `X-Builder-Token` |
  | `SITES_ROOT` / `KEEP_RELEASES` | `/srv/sites` / `10` |
  | `ANTHROPIC_API_KEY` | **sin cargar todavía**. Sin clave el build no traduce: deja en el log "⚠ sin ANTHROPIC_API_KEY: no se traduce (donde falte se usa español)" y lo que no tenga traducción sale en español |

### Cómo se usa

- Panel → Contenido → **Configuración del sitio** → abrir el ítem → barra derecha: **Vista previa**,
  **Publicar**, **Volver a la versión anterior** (piden confirmación). Cada clic crea una fila en **Builds**
  (`queued` → `running` → `success`/`error`, con el log completo, la release y quién lo pidió).
- Vista previa incluye los borradores; Publicar solo lo que está en estado Publicado.
- Volver a la versión anterior repunta `current` a la release publicada **anterior a la actual** (necesita al
  menos dos publicaciones; si no, la fila queda en `error` con "No hay una versión anterior…" y no cambia
  nada). Para volver a lo último, Publicar de nuevo (genera una release nueva).
- Mismo disparo desde la terminal (lo que hace el botón):
  ```bash
  set -a; . ~/.zeekr-cms-prod.env; set +a
  H() { printf 'Authorization: Bearer %s\n' "$DIRECTUS_ADMIN_TOKEN"; }     # el token no queda en la línea de comando
  FLOW=$(curl -sg -A zeekr-cms-setup/1.0 -H @<(H) "$DIRECTUS_URL/flows?filter[name][_eq]=Publicar&fields=id" | python3 -c "import sys,json;print(json.load(sys.stdin)['data'][0]['id'])")
  curl -s -A zeekr-cms-setup/1.0 -H @<(H) -H 'Content-Type: application/json' -X POST "$DIRECTUS_URL/flows/trigger/$FLOW" -d '{"collection":"site_settings","keys":[1]}'
  curl -s -A zeekr-cms-setup/1.0 -H @<(H) "$DIRECTUS_URL/items/builds?sort=-id&limit=1&fields=id,mode,status,release,started_at,finished_at"
  ```
  (`-A`: Cloudflare rechaza algunos User-Agent por defecto; `-g`: que curl no tome los `[ ]` del filtro como rango.)

### Qué hay en el volumen

```
/srv/sites/zeekr/
├── current -> /srv/sites/zeekr/releases/<ts>            # lo publicado (symlink absoluto: montar el volumen
├── preview -> /srv/sites/zeekr/releases/<ts>-preview    #   en /srv/sites también en el contenedor que sirva)
├── releases/<ts>[-preview]/  + <ts>.content.json          # releases inmutables + el contenido con que se generó
└── workspace/{publish,preview}/                           # árbol de trabajo acumulativo (originales y _opt cacheados)
```

- Se guardan 10 releases publicadas y 2 de vista previa (nunca se borran las apuntadas por `current`/`preview`).
- Los archivos iguales a `current` se hardlinkean. Después de redesplegar el builder, los assets del repo
  cambian de mtime y la primera release nueva ocupa ~65 MB más (el volumen ronda 0,6–1,5 GB).

### Tiempos medidos (24 sep 2026, servidor SRPY186)

| Build | Duración |
|---|---|
| Publicar completo (workspace vacío: baja los 74 originales, genera todos los WebP y los 4 idiomas) | 27 s |
| Vista previa primera vez | 26 s |
| Publicar / Vista previa incremental (sin cambios de archivos) | 2–3 s |
| Volver a la versión anterior | < 1 s |

Objetivo del spec: completo ≤ 90 s, incremental ≤ 30 s.

### Problemas conocidos

- Directus limita a 50 pedidos por segundo por IP (`RATE_LIMITER_*`). El builder los supera al bajar los
  originales por la red interna: el cliente reintenta los 429 respetando `Retry-After` (backoff 0,5→10 s, 8
  intentos). Sin eso el primer build falló con 429.
- Logs: `ssh srpy-servidor 'docker logs --tail 100 $(docker ps -q -f label=coolify.resourceName=zeekr-builder)'`.
- Salud desde la red interna: `docker exec $(docker ps -q -f label=coolify.resourceName=directus) wget -qO- http://zeekr-builder:8000/health`.

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
- `ANTHROPIC_API_KEY` en la app 20 para que el builder traduzca lo nuevo (hoy lo que falte sale en español).
- Task 12: servir zeekrlife.com.py desde `zeekr_sites/zeekr/current` y el host de vista previa desde `preview`.
- 14 fotos sueltas `*.jpg.jpeg` en la raíz de `main` se sirven hoy pero no están en las releases del builder
  (nada del sitio las usa); tampoco las `images/_opt/{hero,menu,zeekr7x,…}` viejas, que pasan a `images/_opt/cms/`.
