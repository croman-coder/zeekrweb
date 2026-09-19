# Panel /admin (CMS) para los sitios de marca — Diseño

**Fecha:** 19 sep 2026 · **Estado:** aprobado por Croman (dirección) · **Alcance fase 1:** Zeekr; diseñado multi-sitio.

## 1. Objetivo

Que los equipos de cada marca (@santarosa.com.py) editen su sitio sin tocar código: textos, fotos, hero, banners, menú, footer, teléfonos, FAQ, noticias/eventos y modelos, subiendo imágenes desde su computadora, con vista previa y botón **Publicar**. Croman (super admin) crea usuarios y administra la configuración. Traducciones EN/PT/ZH automáticas con IA.

## 2. Decisiones tomadas

| Tema | Decisión |
|---|---|
| Alcance | Zeekr ahora; modelo multi-sitio desde el día 1 (`sites`) |
| Publicación | Borrador → vista previa privada → **Publicar** (regenera y publica ~1 min); historial y rollback |
| Crean los editores | Noticias/eventos y modelos nuevos (no traducciones) |
| Traducciones | IA (Claude) al publicar, solo lo nuevo/cambiado, con glosario; editor puede corregir |
| Email saliente | Google Workspace SMTP con contraseña de aplicación (reset e invitaciones) |
| Arquitectura | **Directus** (CMS headless self-hosted en Coolify) + servicio **builder** (Python) que corre `build_site.py` y publica en un volumen que sirve nginx |

## 3. Arquitectura

```
Editores ──► https://admin.santarosa.lat  (Directus 11 + Postgres 16, Coolify)
                 │ uploads en volumen /directus/uploads
                 │ Flow "Vista previa" / "Publicar" / "Volver atrás" → webhook (token)
                 ▼
            builder (FastAPI, Python, Coolify)
              1. GET contenido + traducciones + archivos (Directus REST, token de servicio)
              2. traducir lo nuevo/cambiado (Claude) y guardar en Directus
              3. transformar → content.json → build_site.py → derivados WebP (caché)
              4. /srv/sites/<sitio>/releases/<ts> + symlink current|preview (atómico)
              5. PATCH builds/<id> (estado, log) · opcional: push rama dist (espejo Pages)
                 ▼
            nginx zeekr-web  root /srv/sites/zeekr/current  (volumen compartido, solo lectura)
            nginx preview     root /srv/sites/zeekr/preview (host preview-zeekr.santarosa.lat, noindex, Cloudflare Access)
```

- Git queda para **código** (generador, CSS, JS, builder, schema de Directus). El **contenido** vive en Directus; cada publicación exporta un snapshot `content/<sitio>.json` al repo (historial + plan B).
- El sitio público no depende de Directus en runtime: nginx sirve archivos estáticos. Si Directus cae, el sitio sigue.

## 4. Modelo de contenido (Directus)

Todas las colecciones con texto usan el patrón nativo de Directus `*_translations` (idiomas `es-PY`, `en`, `pt-BR`, `zh-Hans`; español es la fuente).

| Colección | Campos clave | Filtro por sitio |
|---|---|---|
| `languages` | code, name, direction | — |
| `sites` | name, slug, domain, preview_host, languages (M2M), logo, ga_id, whatsapp, theme (json), status | — (solo admin) |
| `site_settings` (1 por sitio) | header_menu (json ordenable: label_translations, url), footer_columns (json), phones (repeater: kind, display, e164), social (json), cookie_text (tr.), statement_title/statement_text (tr.), tech_items (repeater tr.), home_faq (repeater tr.), seo_title/seo_description (tr.), legal_disclaimer (tr.) | ✔ |
| `hero_slides` | site, sort, status, image_desktop (file), image_mobile (file), eyebrow/title/claim (tr.), cta_primary_label/url (tr.), cta_secondary_intent (test-drive/contacto), model (rel) | ✔ |
| `models` | site, sort, status, name, slug, short, eyebrow/tagline/claim (tr.), hero_image (file, focal), hero_image_mobile, card_image (file, focal), stats (repeater: value, label tr.), pdf (file), seo_title/seo_description (tr.), schema_desc (tr.), faq (repeater tr.), versions (repeater: name, sub tr., rows[k tr., v tr.]), dimensions (repeater), warranty (repeater) | ✔ |
| `model_sections` | model, sort, type (features/split/band/stats/video/gallery/compare), kicker/title/text (tr.), items (repeater tr.), image (file), video (file), gallery (files M2M con alt tr.), dark, reverse, position | ✔ |
| `news` | site, status, date, slug, kicker/title/lead/meta_desc (tr.), body (WYSIWYG tr.), quote_text/quote_who/quote_org (tr.), quote_pos, place, place_locality, cover (file, focal), gallery (files M2M con alt tr.), cta_model (rel) | ✔ |
| `builds` | site, mode (preview/publish/rollback), status (queued/running/success/error), requested_by, started_at, finished_at, log, release, preview_url | ✔ (lectura) |
| `translation_meta` | collection, item, field, lang, source_hash, translated_by (ai/human), translated_at | interno |
| Directus Files | carpetas por sitio: `zeekr/hero`, `zeekr/modelos`, `zeekr/noticias`, `zeekr/varios`; focal point → `object-position` | ✔ |

Reglas de negocio: `status` en draft/published/archived; la vista previa incluye draft+published, Publicar solo published. Slugs autogenerados desde el título (editable, únicos por sitio). Campos con notas de tamaño recomendado (hero 2200×1238 y 780×1688, card 1920×1080, noticias 1600 lado largo).

## 5. Usuarios, roles y acceso

- **Administrator** (Directus): croman@santarosa.com.py. Crea usuarios, sitios, configura todo.
- **Editor**: campo `site` en el usuario; permisos de lectura/escritura solo sobre ítems con `site = $CURRENT_USER.site` (filtros de permisos por fila); lectura de `builds` propios; sin acceso a `sites`, usuarios ni settings de Directus.
- Sin registro público. Alta solo por admin (invitación por email → link para definir contraseña). **Flow bloqueante en `users.create/update`** rechaza emails que no terminen en `@santarosa.com.py`.
- Reset de contraseña: nativo de Directus por SMTP (Google Workspace, contraseña de aplicación). Enlaces solo a `admin.santarosa.lat` (allow-lists).
- 2FA (TOTP) obligatorio para administradores, opcional para editores.
- Capa extra: **Cloudflare Access** sobre `admin.santarosa.lat` y el host de preview, política "email termina en @santarosa.com.py" (Zero Trust, gratis hasta 50 usuarios). Fase 1 opcional, recomendado.
- Fase 2 opcional: Google SSO restringido al dominio (`hd=santarosa.com.py`), sin registro automático.

## 6. Publicación, vista previa y versiones

- Botones en el panel (Flows manuales sobre `sites`): **Vista previa**, **Publicar**, **Volver a la versión anterior**. Cada uno crea un registro en `builds` y llama al builder con token compartido.
- Preview: build con drafts a `/srv/sites/<sitio>/preview` → `https://preview-zeekr.santarosa.lat` (noindex, Cloudflare Access).
- Publicar: build solo con published → `releases/<timestamp>` y cambio atómico del symlink `current`; se conservan las últimas 10 releases; rollback = repuntar symlink.
- Historial de ítems: Revisions nativas de Directus (restaurar versión de un texto/foto).
- Snapshot de contenido en git por publicación (`content/<sitio>.json`) y, opcional, push de la salida a la rama `dist` (espejo Cloudflare Pages sin build).
- Un build a la vez por sitio (lock); los demás quedan en cola.

## 7. Builder (servicio Python)

- `builder/` en este repo: FastAPI + httpx. Endpoints: `POST /build {site, build_id, mode}`, `POST /rollback {site, build_id}`, `GET /health`. Auth: `X-Builder-Token`.
- Pasos: fetch (paginado, `fields=*.*`), sincronizar archivos a caché local por `uuid+modified_on`, traducir (ver §8), transformar a `content.json`, ejecutar `build_site.py --content content.json --out <dir>`, derivados WebP cacheados por `uuid+ancho`, publicar, reportar.
- Refactor del generador: `build_site.py` pasa a leer `content.json` (misma estructura que hoy tienen `MODELS/NEWS/HOME_FAQ/PHONES/header/footer` + traducciones). Los literales actuales se convierten en el **seed de migración**; `i18n_src.py` deja de ser fuente.
- Tiempo objetivo: primera build ≤ 90 s, incrementales ≤ 30 s.
- Errores: el build falla → `builds.status=error` con log y notificación en Directus al usuario; la release anterior sigue publicada. Texto sin traducción → se publica en español y se registra en el log (el sitio nunca se rompe).

## 8. Traducción con IA

- Para cada campo traducible: si `source_hash(es)` cambió o falta `en/pt/zh`, se traduce con Claude (`claude-sonnet-5`) usando un glosario fijo (ZEEKR, nombres de modelos, WLTP, Smart/Performance, unidades y formato numérico por idioma) e instrucciones de tono (voseo es → EN neutral, PT-BR, ZH simplificado; tipografía correcta). Se guarda en Directus con `translated_by=ai`.
- Si un editor corrige manualmente (`translated_by=human`), no se sobreescribe salvo que cambie el español.
- Costo estimado: < US$ 0,05 por publicación típica. Sin `ANTHROPIC_API_KEY` el paso se salta con aviso.

## 9. Medios

- Subida desde la computadora en Directus (drag & drop, multi), tipos jpg/png/webp/mp4/pdf, máximo 25 MB por archivo, recorte y **punto focal** (se usa para `object-position`). Almacenamiento local en volumen `/directus/uploads` (backup nocturno).
- El builder descarga originales y genera derivados estáticos (WebP responsive) como hoy; Directus no sirve imágenes al público.

## 10. Multi-marca

- Nuevo sitio = fila en `sites` + carpetas de medios + usuario(s) editor con ese `site` + app nginx en Coolify + ingress. El builder es agnóstico (parámetros de sitio: dominio, idiomas, theme). Fase 1: tema Zeekr fijo; `theme` json reservado para colores/fuentes/logo por marca.

## 11. Migración (Zeekr)

- Script `builder/seed_from_code.py`: carga en Directus el contenido actual (modelos, secciones, noticias, settings, hero, FAQ), sube imágenes a carpetas, crea traducciones desde `i18n_src.py`.
- Verificación de paridad: build desde Directus vs `git HEAD` → diff de HTML ignorando hashes de assets; debe ser 0 antes del switch de nginx al volumen.

## 12. Infraestructura (Coolify, SRPY186)

| App | Stack | Notas |
|---|---|---|
| `directus` | Docker Compose: `directus/directus:11`, `postgres:16-alpine` | volúmenes `directus_uploads`, `directus_db`; env `KEY`, `SECRET`, `PUBLIC_URL`, `ADMIN_EMAIL/PASSWORD` (inicial), `EMAIL_TRANSPORT=smtp` (smtp.gmail.com:465, app password), `PASSWORD_RESET_URL_ALLOW_LIST`, `USER_INVITE_URL_ALLOW_LIST`, `RATE_LIMITER_ENABLED=true`, `CORS_ORIGIN` |
| `zeekr-builder` | Dockerfile Python 3.12 (Pillow, FastAPI, httpx, git) | env `DIRECTUS_URL`, `DIRECTUS_TOKEN`, `BUILDER_TOKEN`, `ANTHROPIC_API_KEY`, `SITES_ROOT=/srv/sites`; volumen `sites` |
| `zeekr-web` | nginx (existente) | `root /srv/sites/zeekr/current` (volumen `sites`, ro); bloque `server_name preview-zeekr.santarosa.lat` → `/srv/sites/zeekr/preview` + noindex |
| Cloudflared | ingress | `admin.santarosa.lat`, `preview-zeekr.santarosa.lat` → `coolify-proxy:80` |
| Backups | cron en servidor | `pg_dump` nocturno + rsync de uploads a la rutina de backup existente |

Esquema de Directus versionado en el repo (`cms/schema.yaml`, `directus schema apply`) y Flows exportados (`cms/flows.json`) para reproducir el panel en otro servidor (plan B).

## 13. Seguridad

- Sin registro público; dominio forzado; 2FA admins; rate limiting; tokens de servicio con rol mínimo (builder: lectura de contenido, escritura solo en `builds` y traducciones); secreto de webhook; Cloudflare Access; HTTPS; backups.
- Validaciones de subida (tipo/tamaño); nombres de archivo sanitizados por Directus; el builder nunca ejecuta contenido.

## 14. Pruebas

- Unitarias: transformación CMS→`content.json`, slugs, hash de traducción, glosario.
- Golden: seed + build == HTML actual (paridad).
- Integración: Flow → builder → `builds.success` → preview responde 200 y contiene el cambio.
- E2E (Playwright): login editor, editar teléfono, subir foto de hero, vista previa, publicar, verificar en producción; permisos (editor de otro sitio no ve Zeekr).

## 15. Fases de implementación

1. Directus en Coolify + SMTP + admin + roles + Flow de dominio + schema (colecciones) + Cloudflare ingress/Access.
2. Refactor del generador a `content.json` + seed desde el código actual + paridad.
3. Builder (build/preview/rollback) + volumen + nginx al volumen + Flows y `builds`.
4. Traducción IA + glosario.
5. Go-live: usuarios reales, guía de uso (1 página con capturas), snapshot de contenido en git.
6. Opcional: Google SSO, rama `dist` para Pages, tema por marca (segunda marca).

## 16. Fuera de alcance (por ahora)

Flujo de aprobación, editor visual/page builder libre, comentarios, edición de traducciones como tarea obligatoria, temas por marca configurables en UI, analítica dentro del panel.

## 17. Necesito de Croman

1. Contraseña de aplicación de Google Workspace para la casilla que enviará emails (recomendado `noreply@santarosa.com.py` o `marketing@`).
2. `ANTHROPIC_API_KEY` para traducciones (cargarla en Coolify).
3. Confirmar subdominios `admin.santarosa.lat` y `preview-zeekr.santarosa.lat`.
4. Lista inicial de usuarios (nombre, email, marca).
