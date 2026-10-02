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

## Sucursal Ciudad del Este (desde el 02/10/2026)

Pedido de Gerencia Comercial (mail de Bruno Capossela del 01/10/2026, "Filtros WEB Sucursal CDE - Todas las marcas"): los
contactos de Ciudad del Este (CDE) van directo al equipo comercial de esa zona. **ZEEKR no tiene equipo propio en CDE**
(en Bitrix los equipos de CDE son 135 Soueast+Jetour, 137 GWM, 139 Mitsubishi y 141 JAC+Renault+Leapmotor), así que sus
contactos de CDE van al **equipo multimarca de CDE** (departamento 133): `+595 991 702 176` por WhatsApp/teléfono y, en
Bitrix, el Jefe de Ventas Multimarcas CDE. Es el mismo criterio que Croman fijó para JMEV; el número y la persona son un
supuesto razonable, no confirmado por escrito.

- **Formulario** (modal de prueba de manejo / contacto): campo obligatorio "Sucursal más cercana", sin valor por defecto.
  El POST lleva `sucursal: "asuncion" | "cde"`. Un cliente viejo que no lo manda se trata como Asunción (reparto de siempre).
- **WhatsApp**: todos los enlaces de ventas (encabezado, pie, franja de contacto, modal) llevan `data-sucursal-wa` y abren el
  diálogo `#waChooser` ("¿Con qué sucursal querés hablar?") con los dos números: Asunción `WA_NUMBER` (`595971370006`) y CDE
  `WA_CDE` (`595991702176`). "Continuar por WhatsApp" y el respaldo del formulario usan el número de la sucursal elegida.
  Abrir el diálogo no cuenta como clic a WhatsApp; el clic cuenta al elegir (`click_whatsapp` con `sucursal`).
- **Teléfonos**: "Ventas Ciudad del Este 0991 702 176" (`PHONE_CDE` en `build_site.py`; se suma a los del CMS justo después del
  último "Ventas": pie, franja de contacto, tarjetas del modal, JSON-LD y `llms.txt`).
- **API**: `sucursal="cde"` → el lead va a `CDE_ADVISOR_IDS` (cola justa propia, no cuenta la de Asunción), con `ADDRESS_CITY`
  = Ciudad del Este, "Sucursal elegida" en los comentarios y en la descripción del origen. Sin asesores → `CDE_FALLBACK_ASSIGNEE_ID`
  (nunca el responsable de Asunción). Variables (app 17): `CDE_ADVISOR_IDS=21707` · `CDE_DEPARTMENT_ID=133` ·
  `CDE_FALLBACK_ASSIGNEE_ID=21707`. Para sumar a alguien al reparto de CDE: agregar su ID a `CDE_ADVISOR_IDS` y redesplegar la app 17.
- **Qué NO está en el código**: las preguntas frecuentes ("Escribinos por WhatsApp al 0971 370 006…") y la lista de teléfonos del CMS
  viven en Directus; si se quiere nombrar el número de CDE en las FAQ se edita ahí.
- **Pruebas**: `node --test api/*.test.mjs` (la API) y `node scripts/qa-sucursal.mjs <base>` (Chromium real: selector, formulario en
  los 4 idiomas, respaldo, móvil; no toca el CRM: intercepta `/api/lead` y `wa.me`). Local: `python3 -m http.server 8812` en la raíz del repo.

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
