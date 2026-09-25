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
| `~/.zeekr-cms-prod.env` | `DIRECTUS_URL=https://zeekrlife.com.py/cms`, `DIRECTUS_ADMIN_TOKEN` (token estático de croman@), `DIRECTUS_BUILDER_TOKEN` (token estático de builder@santarosa.com.py = `DIRECTUS_TOKEN` del builder), `DIRECTUS_STATS_TOKEN` (token estático de stats@santarosa.com.py = `DIRECTUS_STATS_TOKEN` de la API de leads, app 17) |

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
python3 setup_insights.py                                 # tablero "Estadísticas — Zeekr" (Insights)
cd ..
builder/.venv/bin/python -m builder.seed_from_code        # contenido actual → Directus (2ª corrida: 0 subidas)
DIRECTUS_TOKEN="$DIRECTUS_BUILDER_TOKEN" SITES_ROOT=/tmp/zk-parity bash scripts/check_parity_cms.sh   # → PARIDAD CMS OK
```

- `setup_roles.py` no toca el token del builder en las corridas siguientes; para rotarlo:
  `ROTATE_BUILDER_TOKEN=1 BUILDER_STATIC_TOKEN=<nuevo>` (y actualizar el builder). Igual con el usuario de
  estadísticas: la primera vez `STATS_STATIC_TOKEN="$DIRECTUS_STATS_TOKEN"`, para rotar `ROTATE_STATS_TOKEN=1`
  (y actualizar `DIRECTUS_STATS_TOKEN` en la app 17).
- Cloudflare bloquea el User-Agent `Python-urllib` (403, error 1010): `common.py` manda uno propio.
- `seed_map.json` guarda ruta del repo → id de archivo **de producción**. Si se corre el seed contra otra
  instancia, detecta que los ids no existen allí, resube y reescribe el mapa (no commitear ese mapa).
- Snapshot del esquema: `cms/schema.yaml`. Para comparar o reproducir en otro servidor:
  `curl -X POST "$DIRECTUS_URL/schema/diff?force=true" -H "Authorization: Bearer $DIRECTUS_ADMIN_TOKEN" -F file=@cms/schema.yaml`
  (204 = mismo esquema; si no, `POST /schema/apply` con el diff devuelto).

## Builder (botones Vista previa / Publicar / Volver)

> **Desde el 25/09/2026 el sitio público sale de acá:** "Publicar" cambia lo que ve zeekrlife.com.py al
> instante (sin redesplegar nada) y "Vista previa" se ve en https://preview-zeekr.santarosa.lat. Detalle en
> [Cómo se sirve](#cómo-se-sirve-app-16-zeekr-web).

### App en Coolify

- App 20 `zeekr-builder` (uuid `pymlwpcftohfpayqbwhobu9b`): `build_pack=dockerfile`, `/builder/Dockerfile`
  (contexto: raíz del repo), repo `croman-coder/zeekrweb` rama **`main`** (hasta el 25/09/2026 fue
  `worktree-admin-cms`; se cambió al mergearla en `main`). Fuente "Public GitHub": no necesita credenciales
  porque el repo es público.
- **Sin dominio** (fqdn vacío, cero etiquetas de Traefik, sin puertos publicados): solo se llega desde la red
  `coolify` por el alias **`http://zeekr-builder:8000`** (`custom_network_aliases`). Corre como uid 10001.
- Volumen docker **`zeekr_sites`** → `/srv/sites`. Sobrevive a los redespliegues (el workspace, las releases y
  los symlinks quedan).
- Auto-deploy **apagado**: un push a `main` no redespliega el builder. Para desplegar:
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

### Cómo se sirve (app 16 `zeekr-web`)

- La app 16 (nginx, `nginx.conf` de `main`) monta el **mismo volumen `zeekr_sites` en `/srv/sites`** (tiene que
  ser esa ruta: `current`/`preview` son symlinks absolutos). nginx sigue el symlink en cada pedido: publicar o
  volver atrás se ve enseguida, sin reiniciar ni redesplegar.
- `zeekrlife.com.py` (y www → 301, y el alias `zeekr.santarosa.lat`, noindex) → `root /srv/sites/zeekr/current`.
- **Las páginas salen solo de la release** (HTML, directorios, sitemap, robots, llms.txt): lo que se despublica
  en el panel da 404 al publicar, con el 404 de su idioma (probado el 25/09 con una noticia en los 4 idiomas).
- **Red de seguridad, solo para estáticos:** la imagen sigue trayendo la copia del repo en `/usr/share/nginx/html`.
  Una imagen, css, js, fuente, pdf, video o ícono que no esté en la release sale de ahí con las mismas cabeceras
  (`@baked_static`). Por eso siguen andando las URLs viejas de imágenes (`images/_opt/{hero,menu,zeekr7x,…}`, que
  las releases reemplazan por `images/_opt/cms/…`) y las fotos sueltas `*.jpg.jpeg` de la raíz.
- **Si no hay release publicada** (volumen sin montar, `current` inexistente o roto, o sin `index.html`) el sitio
  entero sale de la copia de la imagen (`$site_root` en `nginx.conf`), para que el dominio nunca quede vacío.
- **Archivos internos → 404** en producción, alias y vista previa: dotfiles/dirs (`.git`, `.wrangler`, `.gitignore`,
  `.env`…), `__pycache__/`, `docker-compose*`, `Dockerfile*`, `*.py/.pyc/.sh/.md/.mjs/.yml/.yaml/.toml/.env/.conf/…`,
  `_headers`, `_redirects`, `/functions/`. `/cms/` y `/admin/` (`^~`) y `/api/` (app 17 en Traefik) no pasan por
  esas reglas.
- `https://preview-zeekr.santarosa.lat` → `root /srv/sites/zeekr/preview`, **sin** red de seguridad (lo que no
  está da 404), `X-Robots-Tag: noindex, nofollow`, `Cache-Control: no-store`, misma CSP que producción y un
  `robots.txt` propio con `Disallow: /`. Está en el fqdn de la app 16 (router Traefik `http-4`); el túnel y el
  CNAME ya existían.
- Etiquetas de la app 16: si se regeneran con `generateLabelsApplication()`, volver a poner
  `…-to-non-www.redirectregex.permanent=true` (Coolify lo genera en `false` y el 301 de www es a mano).
- **Volver al sitio de antes** (si algo sale mal con el volumen): redesplegar la app 16 en el commit
  `1cfad53` (imagen `qqq99jyv4ubrstlfwjmaibv3:1cfad53…`, sirve solo la copia del repo), o sacar el volumen de la
  app 16: sin `/srv/sites` el nginx nuevo sirve todo de la copia de la imagen.

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

## Estadísticas (Insights → "Estadísticas — Zeekr")

Contador propio de visitas, como el de Renew: **sin cookies, sin IDs y sin datos personales** (no necesita el
consentimiento de cookies; Google Analytics sigue aparte y solo con permiso).

- **Qué se cuenta:** cada página vista (`view`), cada clic a un enlace de WhatsApp (`whatsapp`) y cada formulario que
  termina en un lead de Bitrix (`lead`). Solo en **zeekrlife.com.py**: el alias `zeekr.santarosa.lat` y la vista
  previa no mandan nada, y las 404 no cuentan. Se descartan bots (`bot|crawl|spider|slurp|headless|lighthouse|preview`
  en el User-Agent) y más de 300 hits por IP cada 10 minutos (la IP se usa en memoria y no se guarda).
- **Camino:** `js/main.js` → `navigator.sendBeacon('/api/hit')` (mismo origen: la CSP no cambia) → Traefik → app 17
  (`zeekr-leads-api`, recibe `/hit`) → `functions/_lib/stats.js` acumula en memoria y **cada 60 s** (y al apagarse)
  hace upsert en `site_stats` por la red interna (`http://directus:8055`, usuario `stats@santarosa.com.py`). Un
  reinicio pierde a lo sumo ese minuto. Si Directus no responde, conserva los contadores (tope 5.000 claves) y
  reintenta en el próximo envío.
- **Colección `site_stats`** (una fila por sitio / día / tipo / ruta / idioma, `count` acumulado): `day` es el día de
  Asunción; `path` va sin query ni idioma y con la sección en español (`/en/models/zeekr-7x/` → `/modelos/zeekr-7x/`,
  `lang=en`); `label` es el título de la página. Sin actividad ni revisiones (`accountability` nulo).
- **Tablero** (`setup_insights.py`, idempotente por nombre): visitas 7 y 30 días, formularios y clics a WhatsApp 30
  días, visitas por día (línea, 30 días), páginas y modelos más vistos (top 10, 30 días) y formularios por día
  (barras). Los rangos cuentan días calendario con hoy; `$NOW` de Directus es UTC, así que de 21:00 a 24:00 de
  Asunción la ventana corre un día. Con un solo día de datos la línea es apenas un punto.
- **Permisos:** stats@ (rol y política "Estadísticas", sin acceso al panel): crear/leer/actualizar `site_stats` y
  leer `id`/`slug` de `sites`. Editor: leer `site_stats` de **su** sitio y los tableros/paneles (solo lectura). Un
  editor de otro sitio ve el tablero en cero.
- **App 17:** variables `DIRECTUS_URL=http://directus:8055` y `DIRECTUS_STATS_TOKEN` (valor en
  `~/.zeekr-cms-prod.env`), cargadas por archivo temporal + tinker como las demás. Sin ellas `/api/hit` responde 204
  y no hace nada. Logs: `docker logs $(docker ps -q -f label=coolify.resourceName=zeekr-leads-api)` (arranque:
  "estadísticas: activadas…"; si Directus falla: "estadísticas: no se pudo guardar…").
- Para empezar de cero: borrar las filas de `site_stats` (Contenido → Site Stats, o `DELETE /items/site_stats`).

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
- 14 fotos sueltas `*.jpg.jpeg` en la raíz de `main` y las `images/_opt/{hero,menu,zeekr7x,…}` viejas no están
  en las releases del builder: hoy salen de la copia de la imagen (red de seguridad). Decidir si se mantienen o
  se pasan a 301/404 a propósito.
- Purgar de la caché de Cloudflare (zona zeekrlife.com.py, que el token del túnel no alcanza)
  `https://zeekrlife.com.py/images/_opt/og/zeekr-7x.jpg`: la edge todavía da la imagen de Open Graph vieja del 7X.
- El sitemap pone `lastmod` = día del build en todas las páginas que no son noticias: cada "Publicar" de un día
  nuevo cambia esas fechas aunque el contenido no cambie.
