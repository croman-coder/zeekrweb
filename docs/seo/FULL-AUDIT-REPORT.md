# Auditoría SEO — zeekrlife.com.py (build servido en zeekr.santarosa.lat)

**Fecha:** 19 sep 2026 · **Alcance:** 36 páginas HTML (9 × 4 idiomas) + 3 redirecciones legacy · **Método:** crawler propio (títulos, metas, h1, canonical, hreflang recíproco, JSON-LD, imágenes, enlaces internos/externos, cabeceras), Lighthouse 13 móvil + desktop (4 páginas), validación nginx en Docker.

## Resumen ejecutivo

**SEO Health Score: 87 / 100** · Tipo de negocio: concesionario automotor (AutoDealer, marca única) con contenido editorial.

| Categoría | Peso | Puntaje | Estado |
|---|---|---|---|
| Técnico | 22 % | 85 | ✅ salvo **DNS pendiente** del dominio real |
| Calidad de contenido | 23 % | 82 | ✅ fichas ricas; faltan página de contacto y precio |
| On-page | 20 % | 95 | ✅ títulos ≤60, metas ≤160, 1 h1, hreflang recíproco |
| Schema | 10 % | 80 | ⚠️ AutoDealer sin dirección/horarios/geo |
| Rendimiento (CWV lab) | 10 % | 95 | ✅ perf 95–100, CLS 0, TTFB 81 ms |
| AI readiness | 10 % | 85 | ✅ llms.txt, FAQPage, JSON-LD |
| Imágenes | 5 % | 98 | ✅ WebP responsive, alt y dimensiones en el 100 % |

### Top 5 críticos / altos
1. **CRÍTICO — El dominio canónico no sirve el sitio.** Todas las páginas declaran `canonical` y `hreflang` hacia `https://zeekrlife.com.py/…`, pero ese dominio (NS DreamHost) sigue sirviendo el sitio viejo (Apache). Hasta cambiar los NS a Cloudflare, Google no puede indexar el sitio nuevo. El alias `zeekr.santarosa.lat` se sirve con `X-Robots-Tag: noindex` a propósito.
2. **ALTO — `AutoDealer` sin `address`, `openingHoursSpecification` ni `geo`** (36/36 páginas). Falta la dirección del showroom.
3. **ALTO — Sin Google Business Profile enlazado** (`sameAs`) ni página de contacto indexable con NAP (nombre, dirección, teléfono).
4. **ALTO — Sin Search Console / Bing Webmaster** (no se puede verificar hasta que el dominio real apunte al sitio).
5. **MEDIO — Sin contenido de precio/financiación**: la intención "ZEEKR 7X precio Paraguay" no tiene respuesta en el sitio.

### Top 5 quick wins (ya aplicados en esta auditoría)
- Metas descripción 163–203 → ≤160 caracteres en las 36 páginas; 3 títulos >60 → ≤60.
- `Content-Type` con `charset=utf-8` (antes sin charset), **HSTS**, **CSP estricta** (sin `unsafe-inline` en scripts: el JS del `<head>` pasó a `js/head.js` y los textos i18n a un bloque JSON).
- `X-Robots-Tag: noindex` para cualquier host que no sea `zeekrlife.com.py` (evita indexar el alias/staging).
- `llms.txt` (resumen, datos clave, enlaces por idioma) para motores de respuesta.
- `_headers` de Cloudflare Pages alineado con nginx (HSTS + CSP).

## 1. Técnico

| Chequeo | Resultado |
|---|---|
| Rastreo | 39 URLs, **100 % HTTP 200**, 0 enlaces rotos, 0 assets rotos, 19 enlaces externos accesibles |
| Sitemap | 36 URLs = 36 rastreadas; `lastmod`; `xhtml:link` hreflang por URL; referenciado en robots.txt |
| robots.txt | `Allow: /`, sin bloqueos a GPTBot/ClaudeBot/PerplexityBot; `Disallow: /404.html` |
| Canonical | autorreferente en todas (al dominio real) |
| hreflang | es-PY / en / pt-BR / zh-Hans + x-default, **recíproco en 36/36** |
| Redirecciones | `.html` legacy → 301 a URLs limpias; `www` → apex 301; sin cadenas |
| 404 | real (sin soft-404), página por idioma (`/en/404.html`, `/pt/`, `/zh/`) |
| HTTPS / TLS | Cloudflare (TLS 1.3), HSTS 1 año en origen; falta **HSTS a nivel Cloudflare + Always Use HTTPS** (panel) |
| Cabeceras | nosniff, SAMEORIGIN, Referrer-Policy, Permissions-Policy, **CSP**, charset |
| Compresión | Brotli (Cloudflare) |
| Caché | estáticos `immutable` 30 d; HTML `no-cache` (CF `DYNAMIC`) |
| TTFB | promedio **81 ms**, 1 outlier 2,1 s (arranque en frío) |

## 2. Contenido (E-E-A-T)

- **Experiencia/Autoridad:** página Nosotros (Geely, Gotemburgo, Santa Rosa), noticias con fecha y `NewsArticle`, cita atribuida (Manuel Antelo · Grupo Antelo), evento con vocero (Agustín Varela). ✅
- **Confianza:** teléfonos de ventas/postventa visibles, WhatsApp, distribuidor oficial, disclaimer WLTP. ⚠️ Falta **dirección física**, **horarios**, **política de privacidad/cookies** (el banner la menciona) y **GBP**.
- **Profundidad:** fichas 700–1.200 palabras con versiones, dimensiones, garantía, FAQ; ninguna página <200 palabras.
- **Duplicados:** 0 títulos duplicados; idiomas con URL propia (no duplicado).
- **Gaps de intención:** precio/financiación, página de contacto, test drive como landing, comparativa entre modelos, servicio/postventa.
- **Chino:** metas de 49–65 caracteres CJK (equivalen a ~100–130 latinos) — correcto para SERP zh.

## 3. On-page

- Títulos: 36/36 ≤60 caracteres, únicos, marca al final.
- Metas: 36/36 entre 70 y 160 (zh más cortas por densidad CJK).
- Encabezados: 1 h1 por página, jerarquía sin saltos.
- Enlazado interno: header (modelos, nosotros, noticias), footer (todo), tarjetas de modelo, CTA cruzados noticia→modelo. ⚠️ Faltan breadcrumbs visibles en fichas y enlaces "otros modelos" en el cuerpo.

## 4. Schema

| Tipo | Páginas | Estado |
|---|---|---|
| WebSite + AutoDealer/Organization (`@id`) | todas | ⚠️ sin `address`, `openingHoursSpecification`, `geo`; `sameAs` sin GBP |
| Car/Product | 3 fichas × 4 | ✅ name, brand, model, fuelType, image, description (sin `offers`: no hay precio público) |
| BreadcrumbList | fichas, listados, artículos | ✅ |
| FAQPage | home + fichas | ✅ traducido |
| NewsArticle | 2 artículos × 4 | ✅ headline, image[], datePublished, author/publisher, contentLocation |
| CollectionPage / AboutPage | listados / nosotros | ✅ |

## 5. Rendimiento (Lighthouse 13, producción vía Cloudflare)

| Página | Perf móvil | Perf desktop | LCP móvil | CLS | TBT |
|---|---|---|---|---|---|
| Home | 97–99 | 100 | 1,8 s | 0 | 0 ms |
| /modelos/zeekr-7x/ | 95 | 100 | 2,8 s | 0 | 0 ms |
| Noticia CDE | 95 | 100 | 2,9 s | 0 | 0 ms |
| /en/ | 96 | 99 | 2,6 s | 0 | 0 ms |

Accesibilidad **100**, Best Practices **100**. SEO Lighthouse = 69 en el alias por el `noindex` intencional; en el dominio real (sin `X-Robots-Tag`, `meta robots index,follow`) = **100** (verificado con `Host: zeekrlife.com.py` contra el nginx del build).

## 6. Imágenes

- 100 % con `alt` y `width/height` (CLS 0). WebP responsive (`srcset`/`sizes`, mobile art-direction en heroes), fallback JPEG único, lazy salvo LCP, `fetchpriority=high` + preload del LCP (desktop y móvil).
- Ningún derivado servido >300 KB. Originales pesados (`images/*.png`) no se sirven.

## 7. AI readiness (GEO)

- `llms.txt` con resumen, datos clave (autonomías, garantía, contacto) y enlaces por idioma.
- FAQPage con respuestas fácticas y autocontenidas; JSON-LD con `@id` de organización reutilizado.
- robots.txt no bloquea rastreadores de IA.
- ⚠️ Mejorable: autores/personas con `Person` (voceros), referencias externas (prensa), GBP y reseñas.

## 8. Local SEO

- NAP: nombre ✅, teléfonos ✅ (formato internacional en schema), **dirección ✗**, horarios ✗, mapa ✗, GBP ✗.
- Menciones geográficas: Asunción y Ciudad del Este en noticias ✅; falta página de showroom/sucursales.

---

### Corregido durante la auditoría (commits `78c865d` y `b8f8036`)
metas/títulos · charset · HSTS · CSP · noindex alias · llms.txt · `_headers` Pages · CSP compatible con GA4 y Cloudflare Web Analytics.

### Pendiente (requiere datos o accesos de Croman)
Ver `ACTION-PLAN.md`.
