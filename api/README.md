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
