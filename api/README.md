# API de leads — zeekrlife.com.py → Bitrix24

`POST /api/lead` crea un Prospecto en Bitrix24 (origen `WEB_SR_ZEEKR`, marca Zeekr) y lo asigna
al asesor de ventas del departamento **05. ZEEKR** que hace más tiempo no recibe un lead web
(cola justa, sin estado: se calcula leyendo los últimos leads del origen).

Un solo código, dos despliegues:
- **Cloudflare Pages** (`functions/api/lead.js`) — edge global, mismo dominio del sitio.
- **Coolify** (`api/server.mjs` + `api/Dockerfile`, contexto = raíz del repo) — publicado bajo `/api`.

Variables de entorno: ver cabecera de `functions/_lib/lead.js`. Local:
```bash
BITRIX_WEBHOOK_URL=... PORT=8801 node api/server.mjs
```

## Estadísticas (`POST /api/hit`, solo en Coolify)

`js/main.js` manda con `navigator.sendBeacon` una visita por página (`{k:"view", p:location.pathname, t:document.title}`)
y un clic por enlace a WhatsApp (`k:"whatsapp"`), **solo desde zeekrlife.com.py** (el alias y la vista previa no
cuentan). `api/server.mjs` atiende `/hit` con `functions/_lib/stats.js`: responde siempre 204, descarta bots
(`bot|crawl|spider|slurp|headless|lighthouse|preview`), hosts que no sean zeekrlife.com.py y más de 300 hits por IP
cada 10 min; acumula en memoria `(día de Asunción, tipo, ruta sin idioma, idioma)` y cada 60 s (y al recibir
SIGTERM) hace upsert en la colección `site_stats` de Directus. `lead.js` suma `lead` cuando Bitrix crea el lead.
Sin cookies, sin IDs, sin IP guardada. Si Directus falla, conserva los contadores (tope 5.000 claves) y reintenta.

Variables (app 17): `DIRECTUS_URL=http://directus:8055`, `DIRECTUS_STATS_TOKEN` (usuario `stats@santarosa.com.py`,
solo `site_stats`). Opcionales: `STATS_SITE=zeekr`, `STATS_HOSTS=zeekrlife.com.py`, `STATS_FLUSH_MS=60000`.
Sin `DIRECTUS_URL`/`DIRECTUS_STATS_TOKEN`, `/hit` responde 204 y no hace nada.

Tests (sin dependencias): `node --test api/` (Node 20) o `node --test api/*.test.mjs` (Node ≥ 22).
