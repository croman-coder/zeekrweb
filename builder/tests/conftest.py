# builder/tests/conftest.py — muestra mínima de lo que devuelve Directus (fetch_content)
import copy
import pytest


def file(id_, name, w=2000, h=1000, fx=None, fy=None, size=1234):
    return {"id": id_, "filename_download": name, "type": "image/jpeg", "filesize": size, "width": w, "height": h, "focal_point_x": fx, "focal_point_y": fy, "modified_on": "2026-09-19T10:00:00"}


def trs(es, **langs):
    out = [{"id": 1, "languages_code": "es-PY", **es}]
    for code, vals in langs.items():
        out.append({"id": len(out) + 1, "languages_code": {"en": "en", "pt": "pt-BR", "zh": "zh-Hans"}[code], **vals})
    return out


RAW = {
    "site": {"id": 1, "name": "ZEEKR Paraguay", "slug": "zeekr", "domain": "https://zeekrlife.com.py/", "preview_host": "https://preview-zeekr.santarosa.lat", "ga_id": "G-1", "whatsapp": "595971370006"},
    "settings": {"id": 1, "site": 1, "status": "published",
                 "phones": [{"kind": "Ventas", "display": "0971 370 006", "e164": "+595971370006"}, {"kind": "Postventa", "display": "0974 772 247", "e164": "+595974772247"}],
                 "social": [{"network": "instagram", "url": "https://www.instagram.com/zeekrparaguay/"}],
                 "translations": trs({"statement_title": "Título", "statement_text": "Texto", "footer_tagline": "Tag", "cookie_text": "Cookies", "legal_disclaimer": "Legal", "org_description": "Org",
                                      "seo_title": "SEO", "seo_description": "Desc", "header_menu": [{"label": "Modelos", "target": "modelos", "url": ""}],
                                      "tech_items": [{"title": "SEA", "text": "Plataforma"}], "home_faq": [{"q": "¿Qué?", "a": "Eso."}]},
                                     en={"statement_title": "Title", "header_menu": [{"label": "Models", "target": "modelos", "url": ""}], "home_faq": [{"q": "What?", "a": "That."}]})},
    "hero_slides": [{"id": 1, "site": 1, "status": "published", "sort": 1, "model": 10, "cta_secondary_intent": "test-drive",
                     "image_desktop": file("h1", "7x-desktop.jpg", fx=1200, fy=500), "image_mobile": file("h2", "7x-mobile.jpg", 780, 1688),
                     "translations": trs({"eyebrow": "SUV", "title": "ZEEKR 7X", "claim": "Claim", "cta_primary_label": "Conocé el {model}", "cta_primary_url": ""})},
                    {"id": 2, "site": 1, "status": "published", "sort": 2, "model": None, "image_desktop": None, "translations": trs({"title": "roto"})}],
    "models": [{"id": 10, "site": 1, "status": "published", "sort": 1, "name": "ZEEKR 7X", "slug": "zeekr-7x", "short": "7X", "card_position_mobile": "50% 28%", "og_position": "60% 50%",
                "hero_image": file("h1", "7x-desktop.jpg", fx=1200, fy=500), "hero_image_mobile": file("h2", "7x-mobile.jpg", 780, 1688),
                "card_image": file("c1", "card.jpg", fx=1000, fy=380), "menu_image": file("m1", "menu.png"), "pdf": file("p1", "ficha.pdf"),
                "translations": trs({"eyebrow": "SUV eléctrico", "tagline": "El SUV", "claim": "Claim 7X", "seo_title": "7X SEO", "seo_description": "7X desc", "schema_description": "7X schema",
                                     "stats": [{"value": "800 V", "label": "Alto voltaje"}], "faq": [{"q": "¿Garantía?", "a": "5 años."}], "dimensions": [{"k": "Longitud", "v": "4.787 mm"}],
                                     "warranty": [{"k": "Vehículo", "v": "5 años"}], "versions_title": "Elegí tu 7X"},
                                    en={"eyebrow": "Electric SUV", "stats": [{"value": "800 V", "label": "High voltage"}], "faq": [{"q": "Warranty?", "a": "5 years."}]}),
                "versions": [{"id": 1, "model": 10, "sort": 1, "name": "Smart", "translations": trs({"subtitle": "Acceso", "rows": [{"k": "Autonomía", "v": "480 km (WLTP)"}]}, en={"subtitle": "Entry", "rows": [{"k": "Range", "v": "480 km (WLTP)"}]})}],
                "sections": [
                    {"id": 1, "model": 10, "sort": 2, "type": "split", "dark": True, "reverse": False, "image": file("s1", "interior.jpg"), "video": None, "gallery": [],
                     "translations": trs({"kicker": "Interior", "title": "Como en casa", "text": "Texto interior", "image_alt": "Alt interior"}, en={"kicker": "Interior", "title": "Like home", "text": "Interior text", "image_alt": "Interior alt"})},
                    {"id": 2, "model": 10, "sort": 1, "type": "features", "dark": False, "reverse": False, "image": None, "video": None, "gallery": [],
                     "translations": trs({"kicker": "Explorá", "title": "Conocé", "items": [{"title": "Diseño", "text": "Líneas"}]}, en={"kicker": "Explore", "title": "Meet", "items": [{"title": "Design", "text": "Lines"}]})},
                    {"id": 3, "model": 10, "sort": 3, "type": "split", "dark": False, "reverse": False, "image": None, "video": None, "gallery": [], "translations": trs({"kicker": "Sin foto", "title": "Inválida", "text": "x"})},
                    {"id": 4, "model": 10, "sort": 4, "type": "gallery", "dark": False, "reverse": False, "image": None, "video": None,
                     "gallery": [{"id": 2, "sort": 2, "file": file("g2", "b.jpg"), "alt_es": "Foto B", "alt_en": "Photo B"}, {"id": 1, "sort": 1, "file": file("g1", "a.jpg"), "alt_es": "Foto A", "alt_en": None}],
                     "translations": trs({"kicker": "Galería", "title": "Detalle"})},
                ]}],
    "news": [{"id": 5, "site": 1, "status": "published", "date": "2026-07-28", "slug": "lanzamiento", "place": "Alma, Asunción", "place_locality": "Asunción", "quote_pos": 2, "cta_model": 10,
              "cover": file("n1", "cover.jpg", fx=1000, fy=550), "gallery": [{"id": 9, "sort": 1, "file": file("n2", "foto.jpg"), "alt_es": "Foto evento", "alt_en": "Event photo"}],
              "translations": trs({"kicker": "Evento", "title": "Lanzamiento", "lead": "Lead", "meta_description": "Meta", "body": "<p>Uno</p>\n<p>Dos <strong>fuerte</strong></p><p></p>", "quote_text": "Cita", "quote_who": "Manuel", "quote_org": "Grupo"},
                                  en={"title": "Launch", "body": "<p>One</p><p>Two <strong>strong</strong></p>"})},
             {"id": 6, "site": 1, "status": "published", "date": "2025-01-08", "slug": "", "cover": file("n3", "ces.png"), "gallery": [], "translations": trs({"kicker": "Global", "title": "CES 2025"})}],
}


@pytest.fixture
def raw():
    return copy.deepcopy(RAW)
