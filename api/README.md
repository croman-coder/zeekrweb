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

## Meta: píxel y API de conversiones

Dataset **"Zeekr Paraguay"** (`1384147742910671`, cuenta publicitaria Zeekr Paraguay). El ID está en `js/head.js`
(navegador) y en `functions/_lib/meta-capi.js` (servidor); `api/meta-capi.test.mjs` verifica que coincidan.

- **Píxel** (`js/head.js`, todas las páginas): se carga solo si el visitante aceptó las cookies opcionales del banner
  (la misma categoría que Google Analytics, "Analíticas y publicidad") y solo en **zeekrlife.com.py**: el alias, la
  vista previa y localhost no mandan nada. Si acepta más tarde, se carga en ese momento. Eventos (`js/main.js`):
  `PageView` en cada página; `Contact` al tocar un enlace de WhatsApp a un número (`content_name`: `header`, `footer`,
  `contact_modal`, `contact_strip`, `form_success` o `page`; compartir una noticia no cuenta) y cuando el formulario cae
  al respaldo de WhatsApp (`whatsapp_fallback`); `Lead` cuando `/api/lead` crea el prospecto (`content_name`: el tipo,
  `Prueba de manejo` o `Consulta`; no con el honeypot).
- **API de conversiones** (`functions/_lib/meta-capi.js`, desde `lead.js`): cuando Bitrix crea el lead, manda el mismo
  `Lead` a `graph.facebook.com/v21.0/<píxel>/events` con el `event_id` del navegador (Meta cuenta uno solo),
  teléfono, nombre, apellido, email (si hay) y país en SHA-256, IP, user-agent y las cookies `_fbp`/`_fbc`. El
  formulario manda `meta: {event_id, fbp, fbc, event_source_url, consentimiento}`; con `consentimiento: "rechazado"`
  (rechazó las cookies o todavía no eligió) no se manda nada. Tampoco para bots, honeypot, leads que no se crean o
  formularios enviados desde otro host. Tope de 3 s; nunca cambia la respuesta. En Coolify corre en segundo plano; en
  Cloudflare Pages la función lo espera.

Variables (app 17 en Coolify; en Cloudflare Pages, las del proyecto):

| Variable | |
|---|---|
| `META_CAPI_TOKEN` | **Obligatoria** para la API de conversiones: token de acceso del dataset (Administrador de eventos → dataset → Configuración → API de conversiones → Generar token de acceso). Sin ella no se manda nada. Al arrancar, el log dice `meta capi: activada (píxel …)` o `meta capi: desactivada (falta META_CAPI_TOKEN)`. |
| `META_PIXEL_ID` | Opcional: pisa el ID del código. |
| `META_TEST_EVENT_CODE` | Opcional: código de **Probar eventos** del Administrador de eventos; los eventos del servidor caen ahí. Sacarlo al terminar la prueba. |

Log (sin datos personales): `meta capi (lead 123): Lead enviado a Meta`, o `Meta respondió HTTP 400 (…)` / `Meta no
respondió en 3 s` si algo falla.

Tests (sin dependencias): `node --test api/` (Node 20) o `node --test api/*.test.mjs` (Node ≥ 22).
