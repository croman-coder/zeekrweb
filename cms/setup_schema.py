# cms/setup_schema.py — crea el modelo de contenido. Idempotente: salta lo que ya existe.
# Uso: DIRECTUS_ADMIN_TOKEN=... python3 cms/setup_schema.py
from common import api, exists

PK = {"field": "id", "type": "integer", "meta": {"hidden": True, "interface": "input", "readonly": True},
      "schema": {"is_primary_key": True, "has_auto_increment": True}}
LANGS = [("es-PY", "Español"), ("en", "English"), ("pt-BR", "Português"), ("zh-Hans", "中文")]
STATUS = {"interface": "select-dropdown", "options": {"choices": [
    {"text": "Borrador", "value": "draft"}, {"text": "Publicado", "value": "published"}, {"text": "Archivado", "value": "archived"}]},
    "display": "labels", "width": "half"}


def F(field, type_, interface=None, options=None, special=None, required=False, note=None, width="full", hidden=False, display=None, default=None):
    meta = {"interface": interface, "options": options, "special": special, "required": required, "note": note, "width": width, "hidden": hidden, "display": display}
    if type_ == "alias":
        return {"field": field, "type": type_, "meta": meta}
    return {"field": field, "type": type_, "meta": meta, "schema": {"default_value": default} if default is not None else {}}


def S(field, length, *a, **kw):
    """F() de tipo string con largo máximo en la base."""
    spec = F(field, "string", *a, **kw)
    spec["schema"]["max_length"] = length
    return spec


def ensure_collection(name, fields, hidden=False, icon="box", note=None, singleton=False, sort_field=None, pk=PK):
    if exists(f"/collections/{name}"):
        print("  =", name)
    else:
        api("POST", "/collections", {"collection": name, "meta": {"hidden": hidden, "icon": icon, "note": note, "singleton": singleton, "sort_field": sort_field},
                                     "schema": {}, "fields": [pk]})
        print("  +", name)
    for spec in fields:
        ensure_field(name, spec)


def ensure_field(coll, spec):
    if exists(f"/fields/{coll}/{spec['field']}"):
        return
    api("POST", f"/fields/{coll}", spec)
    print("    +", coll, spec["field"])


def ensure_relation(coll, field, related, meta=None, on_delete="SET NULL"):
    if api("GET", f"/relations/{coll}/{field}", ok404=True):
        api("PATCH", f"/relations/{coll}/{field}", {"meta": meta or {}})
        return
    api("POST", "/relations", {"collection": coll, "field": field, "related_collection": related, "meta": meta or {}, "schema": {"on_delete": on_delete}})


def m2o(coll, field, related, template="{{name}}", required=False, hidden=False, width="half", one_field=None):
    ftype = "uuid" if related.startswith("directus_") else "integer"
    ensure_field(coll, F(field, ftype, "select-dropdown-m2o", {"template": template}, ["m2o"], required=required, hidden=hidden, width=width))
    ensure_relation(coll, field, related, {"one_field": one_field})


def file_field(coll, field, note=None, width="half", image=True):
    ensure_field(coll, F(field, "uuid", "file-image" if image else "file", None, ["file"], note=note, width=width))
    ensure_relation(coll, field, "directus_files")


def repeater(field, items, note=None, template=None):
    """Repeater JSON: items = [(campo, etiqueta, tipo, interfaz)]."""
    fields = [{"field": f, "name": n, "type": t, "meta": {"interface": i, "width": "half" if t == "string" else "full"}} for f, n, t, i in items]
    return F(field, "json", "list", {"fields": fields, "template": template or "{{" + items[0][0] + "}}", "addLabel": "Agregar"}, note=note)


def translations(coll, fields):
    """Patrón nativo: <coll>_translations (<coll>_id + languages_code) y alias 'translations' en la principal."""
    junction = f"{coll}_translations"
    ensure_collection(junction, [F(f"{coll}_id", "integer", hidden=True), F("languages_code", "string", hidden=True)] + fields, hidden=True, icon="import_export")
    ensure_relation(junction, f"{coll}_id", coll, {"one_field": "translations", "junction_field": "languages_code"}, on_delete="CASCADE")
    ensure_relation(junction, "languages_code", "languages", {"one_field": None, "junction_field": f"{coll}_id"})
    ensure_field(coll, F("translations", "alias", "translations", {"languageField": "name", "defaultLanguage": "es-PY", "userLanguage": True}, ["translations"]))


def o2m(coll, field, related, related_field, template="{{id}}"):
    ensure_field(coll, F(field, "alias", "list-o2m", {"template": template, "enableCreate": True, "enableSelect": False}, ["o2m"]))
    ensure_relation(related, related_field, coll, {"one_field": field, "sort_field": "sort"}, on_delete="CASCADE")


print("languages")
LANG_PK = {"field": "code", "type": "string", "meta": {"interface": "input", "readonly": False, "width": "half"}, "schema": {"is_primary_key": True, "length": 16}}
ensure_collection("languages", [F("name", "string", "input", width="half"), F("direction", "string", "select-dropdown", {"choices": [{"text": "LTR", "value": "ltr"}, {"text": "RTL", "value": "rtl"}]}, default="ltr", width="half")],
                  icon="translate", note="Idiomas del sitio (no editar)", pk=LANG_PK)
for code, name in LANGS:
    if not api("GET", f"/items/languages/{code}", ok404=True):
        api("POST", "/items/languages", {"code": code, "name": name, "direction": "ltr"})

print("sites")
ensure_collection("sites", [F("name", "string", "input", required=True, width="half"), F("slug", "string", "input", required=True, width="half", note="ej. zeekr"),
                            F("domain", "string", "input", required=True, width="half", note="https://zeekrlife.com.py"), F("preview_host", "string", "input", width="half"),
                            F("ga_id", "string", "input", width="half"), F("whatsapp", "string", "input", width="half", note="5959… (sin +)"), F("status", "string", **STATUS),
                            F("theme", "json", "input-code", {"language": "json"}, note="reservado: colores/fuentes/logo por marca")], icon="storefront")
file_field("sites", "logo")

print("directus_users.site")
m2o("directus_users", "site", "sites")

print("site_settings")
ensure_collection("site_settings", [F("status", "string", **STATUS)], icon="settings", note="Configuración del sitio: abrir el ítem y usar los botones Vista previa / Publicar")
m2o("site_settings", "site", "sites", required=True)
ensure_field("site_settings", repeater("phones", [("kind", "Tipo (Ventas / Postventa)", "string", "input"), ("display", "Cómo se muestra (0971 370 006)", "string", "input"), ("e164", "Internacional (+595971370006)", "string", "input")], "Teléfonos del footer, del modal de contacto y de los datos estructurados", "{{kind}} {{display}}"))
ensure_field("site_settings", repeater("social", [("network", "Red (instagram / linkedin / facebook / tiktok / youtube)", "string", "input"), ("url", "URL", "string", "input")], "Redes del footer", "{{network}}"))
translations("site_settings", [
    F("statement_title", "string", "input", note="Título principal (h1) de la portada"), F("statement_text", "text", "input-multiline"),
    F("footer_tagline", "string", "input", note="Debajo del logo en el footer"), F("cookie_text", "text", "input-multiline"), F("legal_disclaimer", "text", "input-multiline"),
    F("org_description", "text", "input-multiline", note="Descripción de la empresa para Google (datos estructurados)"),
    F("seo_title", "string", "input", note="Título de la portada en Google (≤ 60 caracteres)"), F("seo_description", "text", "input-multiline", note="≤ 160 caracteres"),
    repeater("header_menu", [("label", "Texto", "string", "input"), ("target", "Destino (modelos / nosotros / noticias / url)", "string", "input"), ("url", "URL (solo si destino = url)", "string", "input")], "Menú principal", "{{label}}"),
    repeater("tech_items", [("title", "Título", "string", "input"), ("text", "Texto", "text", "input-multiline")], "Franja de tecnología (portada)"),
    repeater("home_faq", [("q", "Pregunta", "string", "input"), ("a", "Respuesta", "text", "input-multiline")], "FAQ de la portada", "{{q}}"),
])

print("models")
ensure_collection("models", [F("status", "string", **STATUS), F("sort", "integer", "input", hidden=True), F("name", "string", "input", required=True, width="half", note="ZEEKR 7X"),
                             F("slug", "string", "input", required=True, width="half", note="zeekr-7x (URL /modelos/zeekr-7x/)"), F("short", "string", "input", required=True, width="half", note="7X"),
                             F("card_position_mobile", "string", "input", width="half", note="Foco de la foto de tarjeta en celular, ej. 50% 28% (vacío = igual que escritorio)"),
                             F("og_position", "string", "input", width="half", default="50% 50%", note="Foco del recorte 1200×630 para redes sociales, ej. 60% 50%")],
                  icon="directions_car", sort_field="sort")
m2o("models", "site", "sites", required=True)
file_field("models", "hero_image", "Portada de la ficha, 2200×1238 (el punto focal define el encuadre)")
file_field("models", "hero_image_mobile", "Portada vertical, 780×1688")
file_field("models", "card_image", "Tarjeta en portada y /modelos/, 1920×1080")
file_field("models", "menu_image", "PNG con fondo transparente para el menú (≈600×300)")
file_field("models", "pdf", "Ficha técnica PDF", image=False)
translations("models", [F("eyebrow", "string", "input"), F("tagline", "string", "input"), F("claim", "text", "input-multiline"),
                        F("seo_title", "string", "input"), F("seo_description", "text", "input-multiline"), F("schema_description", "text", "input-multiline"),
                        repeater("stats", [("value", "Valor (800 V)", "string", "input"), ("label", "Etiqueta", "string", "input")], "3 indicadores"),
                        repeater("faq", [("q", "Pregunta", "string", "input"), ("a", "Respuesta", "text", "input-multiline")], template="{{q}}"),
                        repeater("dimensions", [("k", "Medida", "string", "input"), ("v", "Valor", "string", "input")], template="{{k}}: {{v}}"),
                        repeater("warranty", [("k", "Concepto", "string", "input"), ("v", "Cobertura", "string", "input")], template="{{k}}: {{v}}"),
                        F("versions_title", "string", "input", note="Título del comparador de versiones")])

print("model_versions")
ensure_collection("model_versions", [F("sort", "integer", "input", hidden=True), F("name", "string", "input", required=True, width="half", note="Smart / Performance")], hidden=True, icon="list_alt", sort_field="sort")
m2o("model_versions", "model", "models", hidden=True)
translations("model_versions", [F("subtitle", "string", "input"), repeater("rows", [("k", "Ítem", "string", "input"), ("v", "Valor", "string", "input")], template="{{k}}: {{v}}")])
o2m("models", "versions", "model_versions", "model", "{{name}}")

print("model_sections")
ensure_collection("model_sections", [F("sort", "integer", "input", hidden=True),
                                     F("type", "string", "select-dropdown", {"choices": [{"text": v, "value": v} for v in ["features", "split", "band", "stats", "video", "gallery"]]}, required=True, width="half"),
                                     F("dark", "boolean", "boolean", width="half", default=False), F("reverse", "boolean", "boolean", width="half", default=False)],
                  hidden=True, icon="view_agenda", sort_field="sort", note="features: tarjetas (items); split: texto + foto; band: foto ancha; stats: cifras (items: title=cifra, text=etiqueta); video: video + póster (image); gallery: galería")
m2o("model_sections", "model", "models", hidden=True)
file_field("model_sections", "image", "split / band / póster del video")
file_field("model_sections", "video", "MP4 (solo tipo video)", image=False)
translations("model_sections", [F("kicker", "string", "input"), F("title", "string", "input"), F("text", "text", "input-multiline"), F("image_alt", "string", "input"),
                                repeater("items", [("title", "Título", "string", "input"), ("text", "Texto", "text", "input-multiline")], "features y stats")])
o2m("models", "sections", "model_sections", "model", "{{type}} · {{sort}}")

print("section_gallery")
ensure_collection("section_gallery", [F("sort", "integer", "input", hidden=True), F("alt_es", "string", "input", note="Descripción (español)"), F("alt_en", "string", "input"), F("alt_pt", "string", "input"), F("alt_zh", "string", "input")], hidden=True, icon="photo_library", sort_field="sort")
m2o("section_gallery", "section", "model_sections", hidden=True)
file_field("section_gallery", "file", width="full")
o2m("model_sections", "gallery", "section_gallery", "section", "{{file.title}}")

print("hero_slides")
ensure_collection("hero_slides", [F("status", "string", **STATUS), F("sort", "integer", "input", hidden=True),
                                  F("cta_secondary_intent", "string", "select-dropdown", {"choices": [{"text": "Prueba de manejo", "value": "test-drive"}, {"text": "Contáctanos", "value": "contacto"}]}, default="test-drive", width="half")],
                  icon="view_carousel", sort_field="sort")
m2o("hero_slides", "site", "sites", required=True)
m2o("hero_slides", "model", "models")
file_field("hero_slides", "image_desktop", "2200×1238 recomendado")
file_field("hero_slides", "image_mobile", "780×1688 recomendado")
translations("hero_slides", [F("eyebrow", "string", "input"), F("title", "string", "input"), F("claim", "text", "input-multiline"),
                             F("cta_primary_label", "string", "input", width="half", note="{model} se reemplaza por el nombre"), F("cta_primary_url", "string", "input", width="half", note="vacío = ficha del modelo")])

print("news")
ensure_collection("news", [F("status", "string", **STATUS), F("date", "date", "datetime", required=True, width="half"),
                           F("slug", "string", "input", width="half", note="URL /noticias/<slug>/ — vacío = solo tarjeta (sin página)"),
                           F("place", "string", "input", width="half", note="Alma, Asunción"), F("place_locality", "string", "input", width="half", note="Asunción"),
                           F("quote_pos", "integer", "input", width="half", default=2, note="Después de qué párrafo va la cita (0 = antes del texto)")], icon="newspaper")
m2o("news", "site", "sites", required=True)
m2o("news", "cta_model", "models")
file_field("news", "cover", "Portada, 1600 px lado largo")
translations("news", [F("kicker", "string", "input", width="half"), F("title", "string", "input"), F("lead", "text", "input-multiline"), F("meta_description", "text", "input-multiline", note="≤ 160"),
                      F("body", "text", "input-rich-text-html", {"toolbar": ["bold", "italic", "link", "bullist", "numlist", "blockquote"]}), F("quote_text", "text", "input-multiline"),
                      F("quote_who", "string", "input", width="half"), F("quote_org", "string", "input", width="half")])
ensure_collection("news_gallery", [F("sort", "integer", "input", hidden=True), F("alt_es", "string", "input", note="Descripción (español)"), F("alt_en", "string", "input"), F("alt_pt", "string", "input"), F("alt_zh", "string", "input")], hidden=True, icon="photo_library", sort_field="sort")
m2o("news_gallery", "news", "news", hidden=True)
file_field("news_gallery", "file", width="full")
o2m("news", "gallery", "news_gallery", "news", "{{file.title}}")

print("builds")
ensure_collection("builds", [F("mode", "string", "select-dropdown", {"choices": [{"text": v, "value": v} for v in ["preview", "publish", "rollback"]]}, width="half"),
                             F("status", "string", "select-dropdown", {"choices": [{"text": v, "value": v} for v in ["queued", "running", "success", "error"]]}, width="half", display="labels"),
                             F("requested_by", "string", "input", width="half"), F("started_at", "timestamp", "datetime", width="half"), F("finished_at", "timestamp", "datetime", width="half"),
                             F("release", "string", "input", width="half"), F("preview_url", "string", "input"), F("log", "text", "input-multiline")], icon="rocket_launch")
m2o("builds", "site", "sites")

print("translation_meta")
ensure_collection("translation_meta", [F("collection", "string", "input", width="half"), F("item", "string", "input", width="half"), F("field", "string", "input", width="half"),
                                       F("lang", "string", "input", width="half"), F("source_hash", "string", "input", width="half"),
                                       F("translated_by", "string", "select-dropdown", {"choices": [{"text": "IA", "value": "ai"}, {"text": "Humano", "value": "human"}]}, width="half"),
                                       F("translated_at", "timestamp", "datetime", width="half")], hidden=True, icon="translate")

print("site_stats")
# Contador propio de visitas (sin cookies ni datos personales): una fila por sitio/día/tipo/ruta/idioma. Lo escribe
# la API de leads (usuario stats@, functions/_lib/stats.js) y se ve en Insights → "Estadísticas — Zeekr".
# accountability null: sin actividad ni revisiones por cada suma (serían miles de filas al día en directus_activity).
KINDS = [{"text": "Visita", "value": "view"}, {"text": "Formulario enviado", "value": "lead"}, {"text": "Clic a WhatsApp", "value": "whatsapp"}]
day = F("day", "date", "datetime", required=True, width="half", note="Día de Asunción (America/Asuncion)")
day["schema"]["is_indexed"] = True
ensure_collection("site_stats", [day, S("kind", 16, "select-dropdown", {"choices": KINDS}, required=True, width="half"),
                                 S("path", 255, "input", required=True, width="half", note="Ruta sin idioma ni query: /modelos/zeekr-7x/"),
                                 S("lang", 8, "select-dropdown", {"choices": [{"text": t, "value": v} for v, t in [("es", "Español"), ("en", "English"), ("pt", "Português"), ("zh", "中文")]]}, width="half"),
                                 S("label", 120, "input", width="half", note="Título de la página"),
                                 F("count", "integer", "input", required=True, width="half", default=0)],
                  icon="insights", note="Visitas, formularios y clics a WhatsApp por día (contador propio, sin cookies). Gráficos en Insights → Estadísticas — Zeekr")
m2o("site_stats", "site", "sites", required=True)
api("PATCH", "/collections/site_stats", {"meta": {"accountability": None, "display_template": "{{day}} · {{kind}} · {{path}} ({{lang}}): {{count}}"}})

print("carpetas")
root = api("GET", "/folders?filter[name][_eq]=zeekr&filter[parent][_null]=true&limit=1")
root = root[0] if root else api("POST", "/folders", {"name": "zeekr"})
for sub in ["hero", "modelos", "noticias", "varios"]:
    if not api("GET", f"/folders?filter[name][_eq]={sub}&filter[parent][_eq]={root['id']}&limit=1"):
        api("POST", "/folders", {"name": sub, "parent": root["id"]})

print("sitio zeekr")
if not api("GET", "/items/sites?filter[slug][_eq]=zeekr&limit=1"):
    site = api("POST", "/items/sites", {"name": "ZEEKR Paraguay", "slug": "zeekr", "domain": "https://zeekrlife.com.py", "preview_host": "https://preview-zeekr.santarosa.lat",
                                        "ga_id": "G-E6H9ZC5CG3", "whatsapp": "595971370006", "status": "published"})
    api("POST", "/items/site_settings", {"site": site["id"], "status": "published"})
print("OK esquema")
