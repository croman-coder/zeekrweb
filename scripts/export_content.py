# scripts/export_content.py — vuelca los literales actuales de build_site.py a content/zeekr.json (seed y paridad).
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_site as b  # noqa: E402
from i18n import TRANSLATIONS  # noqa: E402


def model(key):
    m = b.MODELS[key]
    hero, hero_m, og_pos = b.PAGE_HERO[key]
    vt, versions = b.VERSIONS[key]
    return {"key": key, "slug": m["slug"], "name": m["name"], "short": m["short"], "eyebrow": m["eyebrow"], "tagline": m["tagline"], "claim": m["claim"],
            "hero_image": hero, "hero_image_mobile": hero_m, "hero_position": m.get("hero_pos", "50% 50%"), "og_position": og_pos,
            "card_image": m["card"], "card_position": m["card_pos"], "card_position_mobile": m.get("card_pos_m", m["card_pos"]),
            "menu_image": f"images/menu/zeekr_{key}.png", "pdf": m.get("pdf"),
            "stats": [{"value": v, "label": l} for v, l in m["stats"]],
            "seo_title": m["meta_title"], "seo_description": m["meta_desc"], "schema_description": m["schema_desc"],
            "faq": [{"q": q, "a": a} for q, a in m["faq"]], "dimensions": b.DIMENSIONS[key], "warranty": b.WARRANTY[key],
            "versions_title": vt, "versions": versions, "sections": b.SECTIONS[key]}


def news(n):
    q = n.get("quote")
    return {"slug": n.get("slug", ""), "date": n["date"], "kicker": n.get("kicker", ""), "title": n["title"], "lead": n.get("lead", ""), "meta_description": n.get("meta_desc", ""),
            "body": n.get("body") or [], "quote": {"text": q[0], "who": q[1] or "", "org": q[2] or ""} if q else None, "quote_pos": n.get("quote_pos", 2),
            "place": n.get("place", ""), "place_locality": n.get("place_locality", ""), "cover": n["img"], "cover_position": n.get("img_pos", "50% 50%"),
            "gallery": [{"file": f, "alt": a} for f, a in n.get("gallery", [])], "cta_model": n.get("cta_model", "")}


content = {
    "site": {"name": b.SITE_NAME, "slug": "zeekr", "domain": b.DOMAIN, "ga_id": b.GA_ID, "whatsapp": b.WA_NUMBER, "languages": list(b.LANGS)},
    "settings": {
        "phones": [{"kind": k, "display": d, "e164": e} for k, d, e in b.PHONES],
        "social": [{"network": "instagram", "url": "https://www.instagram.com/zeekrparaguay/"}, {"network": "linkedin", "url": "https://www.linkedin.com/company/zeekr"}],
        "header_menu": [{"label": "Modelos", "target": "modelos", "url": ""}, {"label": "Nosotros", "target": "nosotros", "url": ""}, {"label": "Noticias", "target": "noticias", "url": ""}],
        "statement_title": "Vehículos eléctricos premium que reimaginan la forma de moverse.",
        "statement_text": "Diseño escandinavo, tecnología de vanguardia y el respaldo del Grupo Geely. ZEEKR llega a Paraguay de la mano de Santa Rosa Paraguay, con los modelos 001, X y 7X.",
        "footer_tagline": "Distribuidor oficial ZEEKR en Paraguay.",
        "cookie_text": "Cuando visitás nuestro sitio web (“Plataformas ZEEKR”), utilizamos cookies y otras tecnologías de seguimiento similares para mejorar la funcionalidad de las Plataformas ZEEKR, el rendimiento, medir el tráfico del sitio web, analizar el comportamiento del usuario y ajustar nuestro contenido y servicios. Si hacés clic en “Aceptar todo” nos autorizás a procesar tus datos personales para tales fines. Si hacés clic en “Rechazar todo” solo utilizaremos cookies y tecnologías estrictamente necesarias para la funcionalidad de la Plataforma ZEEKR. Para más información o para consentir cookies específicas, hacé clic en “Configuración de cookies”.",
        "legal_disclaimer": "Toda la información contenida en este material está basada en datos disponibles al momento de su publicación. Las fotos y pantallas son de carácter ilustrativo y de referencia. Los datos de autonomía y prestaciones se basan en ciclos de prueba (WLTP / pruebas de ingeniería) y pueden variar según clima, camino, carga, batería y configuración del vehículo.",
        "org_description": "Distribuidor oficial de ZEEKR en Paraguay: vehículos eléctricos premium ZEEKR 001, ZEEKR X y ZEEKR 7X.",
        "seo_title": "ZEEKR Paraguay | Vehículos eléctricos premium: 7X, X y 001",
        "seo_description": "Vehículos eléctricos premium ZEEKR en Paraguay: ZEEKR 7X, X y 001. Diseño escandinavo, tecnología líder y autonomía real. Agendá tu prueba de manejo.",
        "tech_items": [{"title": t, "text": x} for t, x in b.TECH_ITEMS],
        "home_faq": [{"q": q, "a": a} for q, a in b.HOME_FAQ],
    },
    "hero_slides": [{"model": k, "image_desktop": b.MODELS[k]["hero_desktop"], "image_mobile": b.MODELS[k]["hero_mobile"], "eyebrow": b.MODELS[k]["eyebrow"], "title": b.MODELS[k]["name"],
                     "claim": b.MODELS[k]["claim"], "cta_primary_label": "Conocé el {model}", "cta_primary_url": "", "cta_secondary_intent": "test-drive"} for k in b.MODEL_ORDER],
    "models": [model(k) for k in b.MODEL_ORDER],
    "news": [news(n) for n in b.NEWS],
    "translations": {lang: dict(TRANSLATIONS[lang]) for lang in ("en", "pt", "zh")},
}
os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content"), exist_ok=True)
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "zeekr.json")
json.dump(content, open(out, "w"), ensure_ascii=False, indent=1)
print(out, ":", len(content["models"]), "modelos,", len(content["news"]), "noticias")
