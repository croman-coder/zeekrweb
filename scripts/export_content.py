# scripts/export_content.py — vuelca los literales actuales de build_site.py a un content.json (seed y paridad).
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ap = argparse.ArgumentParser(description="Exporta los literales de build_site.py a un content.json")
_ap.add_argument("--out", default=os.path.join(ROOT, "content", "zeekr.json"), help="destino del JSON (default: content/zeekr.json)")
ARGS = _ap.parse_args()
ARGS.out = os.path.abspath(ARGS.out)   # build_site hace chdir(ROOT) al importarse

sys.path.insert(0, ROOT)
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
        "social": b.SOCIAL_DEFAULT,
        "header_menu": b.HEADER_MENU_DEFAULT,
        "statement_title": b.STATEMENT_TITLE,
        "statement_text": b.STATEMENT_TEXT,
        "footer_tagline": b.FOOTER_TAGLINE,
        "cookie_text": b.COOKIE_TEXT,
        "legal_disclaimer": b.LEGAL_DISCLAIMER,
        "org_description": b.ORG_DESCRIPTION,
        "seo_title": b.SEO_TITLE,
        "seo_description": b.SEO_DESCRIPTION,
        "tech_items": [{"title": t, "text": x} for t, x in b.TECH_ITEMS],
        "home_faq": [{"q": q, "a": a} for q, a in b.HOME_FAQ],
    },
    "hero_slides": [{"model": k, "image_desktop": b.MODELS[k]["hero_desktop"], "image_mobile": b.MODELS[k]["hero_mobile"], "eyebrow": b.MODELS[k]["eyebrow"], "title": b.MODELS[k]["name"],
                     "claim": b.MODELS[k]["claim"], "cta_primary_label": "Conocé el {model}", "cta_primary_url": "", "cta_secondary_intent": "test-drive"} for k in b.MODEL_ORDER],
    "models": [model(k) for k in b.MODEL_ORDER],
    "news": [news(n) for n in b.NEWS],
    "translations": {lang: dict(TRANSLATIONS[lang]) for lang in ("en", "pt", "zh")},
}
os.makedirs(os.path.dirname(ARGS.out), exist_ok=True)
json.dump(content, open(ARGS.out, "w"), ensure_ascii=False, indent=1)
print(ARGS.out, ":", len(content["models"]), "modelos,", len(content["news"]), "noticias")
