# Plan de acción SEO — zeekrlife.com.py

Prioridad: **Crítico** (bloquea indexación) → **Alto** (impacta ranking, 1 semana) → **Medio** (1 mes) → **Bajo** (backlog).

## Crítico
| # | Acción | Quién | Cómo |
|---|---|---|---|
| 1 | **Apuntar zeekrlife.com.py al sitio nuevo** | Croman | Agregar la zona en Cloudflare → cambiar NS en NIC.py/DreamHost → CNAME `@` y `www` al túnel `505fc6ac-…cfargotunnel.com` (proxied). El servidor ya tiene ingress, Traefik y redirect www→apex listos. Alternativa: Cloudflare Pages como primario (repo listo). |
| 2 | Tras el DNS: **Search Console** (propiedad de dominio) + enviar `sitemap.xml`; **Bing Webmaster** (importa de GSC) | Croman | 15 min. Verificar hreflang en el informe de "Segmentación internacional". |

## Alto
| # | Acción | Quién | Cómo |
|---|---|---|---|
| 3 | **Dirección, horarios y coordenadas del showroom** | Croman → Claude | Pasar dirección/horarios; se agregan `address`, `openingHoursSpecification`, `geo` al `AutoDealer` y al footer en 4 idiomas (5 min). |
| 4 | **Google Business Profile "ZEEKR Paraguay"** (o sucursal de Santa Rosa) | Croman | Crear/reclamar, categoría "Concesionario de automóviles", enlazar al sitio; agregar URL en `sameAs`. Pedir reseñas post-test-drive. |
| 5 | **Página `/contacto/` indexable** (NAP, mapa, horarios, WhatsApp, formulario) | Claude | Nueva página en el generador, 4 idiomas, `ContactPage` schema. Hoy el contacto vive solo en el modal. |
| 6 | **Webhook Bitrix dedicado** para la API de leads (scopes `crm`,`user`) | Croman → Claude | Hoy usa el webhook del MCP (usuario 19). Cambiar la variable en Coolify. |

## Medio
| # | Acción | Quién | Cómo |
|---|---|---|---|
| 7 | **Precio / financiación**: sección "Consultá precio y planes" + FAQ "¿Cuánto cuesta el ZEEKR 7X en Paraguay?" (aunque sea "consultar con un asesor") | Croman decide política → Claude | Captura la intención comercial más buscada. Si hay precio público, `offers` en schema. |
| 8 | **Landing `/test-drive/`** para campañas Meta/Google (UTMs ya se capturan) | Claude | Formulario arriba, prueba social, modelos; `noindex` opcional si es solo para pauta. |
| 9 | **Cloudflare (panel):** Always Use HTTPS, HSTS, Auto Minify off (ya minificado), Cache Rule para HTML (Edge TTL 10 min, `Bypass cache on cookie` no aplica) → menos dependencia del servidor de la oficina | Croman | 10 min. Con Pages como primario, no hace falta. |
| 10 | **Política de privacidad y cookies** (`/privacidad/`) enlazada desde el banner y footer | Croman (texto legal) → Claude | E-E-A-T + cumplimiento Ley 6534/2020. |
| 11 | **Comparativa de modelos** (`/modelos/comparar/`) — tabla 001 vs X vs 7X | Claude | Intención "ZEEKR X vs 7X"; enlazado interno entre fichas. |
| 12 | **Servicio / postventa** (`/servicio/`): garantía, mantenimiento, carga, contacto postventa | Croman (contenido) → Claude | Hoy "Servicio" no existe como página. |

## Bajo
| # | Acción | Cómo |
|---|---|---|
| 13 | Breadcrumbs visibles en fichas y listados (ya están en schema) | 10 min en el generador |
| 14 | Enlaces internos contextuales en fichas ("¿Buscás más espacio? Conocé el 7X") | copy corto por modelo |
| 15 | `Person` schema para voceros (Agustín Varela) y `citation` en noticias con prensa | cuando haya links de prensa |
| 16 | Metas zh algo más largas (hoy 49–65 CJK, válido) | opcional |
| 17 | Subtítulos/transcripción del video del 7X (a11y) | archivo `.vtt` |
| 18 | Monitoreo: cron mensual de este crawler + Lighthouse (registro en Obsidian) | script `audit.py` del scratchpad → repo |

## Ya hecho en esta auditoría
- Metas ≤160 y títulos ≤60 en 36 páginas · charset utf-8 · HSTS · CSP estricta · noindex del alias · `llms.txt` · `_headers` Pages · CSP compatible con GA4 y Cloudflare Web Analytics.
