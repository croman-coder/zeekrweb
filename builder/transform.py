# builder/transform.py — Directus → content.json del generador. Funciones puras (sin red ni disco).
import re

SRC = "es-PY"
LANG_KEY = {"en": "en", "pt-BR": "pt", "zh-Hans": "zh"}            # código Directus → clave del generador
FAQ_TITLE = {"en": "{name} frequently asked questions", "pt": "Perguntas frequentes sobre o {name}", "zh": "{name} 常见问题"}
TEXT_KEYS = ("title", "text", "q", "a", "k", "v", "value", "label", "name", "subtitle")   # claves de texto dentro de repeaters
TRANSLATABLE = {
    "site_settings": ["statement_title", "statement_text", "footer_tagline", "cookie_text", "legal_disclaimer", "org_description", "seo_title", "seo_description", "header_menu", "tech_items", "home_faq"],
    "hero_slides": ["eyebrow", "title", "claim", "cta_primary_label"],
    "models": ["eyebrow", "tagline", "claim", "seo_title", "seo_description", "schema_description", "stats", "faq", "dimensions", "warranty", "versions_title"],
    "model_versions": ["subtitle", "rows"],
    "model_sections": ["kicker", "title", "text", "image_alt", "items"],
    "news": ["kicker", "title", "lead", "meta_description", "body", "quote_text", "quote_org"],
}
REQUIRED = {"features": ("items",), "stats": ("items",), "split": ("image",), "band": ("image",), "video": ("video", "image"), "gallery": ("gallery",)}


def file_path(f):
    """Ruta local (relativa al workspace) de un archivo de Directus; None si no hay archivo."""
    if not f or not f.get("id"):
        return None
    name = f.get("filename_download") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "bin"
    return f"images/cms/{f['id']}.{ext}"


def focal(f, default="50% 50%"):
    """Punto focal del archivo → object-position ("60% 50%")."""
    if not f or f.get("focal_point_x") is None or f.get("focal_point_y") is None or not f.get("width") or not f.get("height"):
        return default
    return f"{round(100 * f['focal_point_x'] / f['width'])}% {round(100 * f['focal_point_y'] / f['height'])}%"


def tr(row, lang=SRC):
    for t in row.get("translations") or []:
        if t.get("languages_code") == lang:
            return t
    return {}


def html_to_paragraphs(s):
    if not s:
        return []
    out = []
    for p in re.split(r"</p\s*>", s, flags=re.I):
        p = re.sub(r"<p\b[^>]*>", "", p, flags=re.I)
        p = re.sub(r"\s+", " ", p.replace("\n", " ")).strip()
        if p and p != "&nbsp;":
            out.append(p)
    return out


def sort_rows(rows):
    return sorted(rows or [], key=lambda r: (r.get("sort") is None, r.get("sort") or 0, r.get("id") or 0))


def model_key(m):
    return re.sub(r"[^a-z0-9]+", "", (m.get("short") or m.get("slug") or "").lower())


def _id(v):
    return v.get("id") if isinstance(v, dict) else v


def _pairs(items, ka, kb):
    return [{ka: i.get(ka) or "", kb: i.get(kb) or ""} for i in (items or []) if isinstance(i, dict)]


def gallery(rows):
    return [{"file": file_path(g["file"]), "alt": g.get("alt_es") or ""} for g in sort_rows(rows) if g.get("file")]


def section(s, warnings, owner):
    t = tr(s)
    d = {"type": s.get("type"), "kicker": t.get("kicker") or "", "title": t.get("title") or "", "text": t.get("text") or "",
         "dark": bool(s.get("dark")), "reverse": bool(s.get("reverse")), "items": _pairs(t.get("items"), "title", "text")}
    if s.get("image"):
        d["image"], d["image_alt"], d["position"] = file_path(s["image"]), t.get("image_alt") or d["title"], focal(s["image"])
    if s.get("video"):
        d["video"] = file_path(s["video"])
    if d["type"] == "gallery":
        d["gallery"] = gallery(s.get("gallery"))
    missing = [k for k in REQUIRED.get(d["type"], ("tipo válido",)) if not d.get(k)]
    if missing:
        warnings.append(f"{owner}: sección {d['type']!r} #{s.get('id')} omitida (falta {', '.join(missing)})")
        return None
    return d


def version(v):
    t = tr(v)
    return {"name": v.get("name") or "", "subtitle": t.get("subtitle") or "", "rows": _pairs(t.get("rows"), "k", "v")}


def model(m, warnings):
    t = tr(m)
    name = m.get("name") or ""
    secs = [d for d in (section(s, warnings, name) for s in sort_rows(m.get("sections"))) if d]
    return {"key": model_key(m), "slug": m["slug"], "name": name, "short": m.get("short") or name,
            "eyebrow": t.get("eyebrow") or "", "tagline": t.get("tagline") or "", "claim": t.get("claim") or "",
            "hero_image": file_path(m.get("hero_image")) or file_path(m.get("card_image")), "hero_image_mobile": file_path(m.get("hero_image_mobile")),
            "hero_position": focal(m.get("hero_image")), "og_position": m.get("og_position") or "50% 50%",
            "card_image": file_path(m.get("card_image")), "card_position": focal(m.get("card_image")),
            "card_position_mobile": m.get("card_position_mobile") or focal(m.get("card_image")),
            "menu_image": file_path(m.get("menu_image")), "pdf": file_path(m.get("pdf")),
            "stats": _pairs(t.get("stats"), "value", "label"),
            "seo_title": t.get("seo_title") or name, "seo_description": t.get("seo_description") or t.get("claim") or "",
            "schema_description": t.get("schema_description") or t.get("claim") or "",
            "faq": _pairs(t.get("faq"), "q", "a"), "dimensions": _pairs(t.get("dimensions"), "k", "v"), "warranty": _pairs(t.get("warranty"), "k", "v"),
            "versions_title": t.get("versions_title") or "Versiones", "versions": [version(v) for v in sort_rows(m.get("versions"))], "sections": secs}


def hero_slide(h, by_id):
    t = tr(h)
    return {"model": by_id.get(_id(h.get("model")), ""), "image_desktop": file_path(h.get("image_desktop")), "image_mobile": file_path(h.get("image_mobile")),
            "eyebrow": t.get("eyebrow") or "", "title": t.get("title") or "", "claim": t.get("claim") or "",
            "cta_primary_label": t.get("cta_primary_label") or "Conocé el {model}", "cta_primary_url": t.get("cta_primary_url") or "",
            "cta_secondary_intent": h.get("cta_secondary_intent") or "test-drive"}


def news(n, by_id):
    t = tr(n)
    q = t.get("quote_text") or ""
    return {"slug": n.get("slug") or "", "date": n["date"], "kicker": t.get("kicker") or "", "title": t.get("title") or "", "lead": t.get("lead") or "",
            "meta_description": t.get("meta_description") or "", "body": html_to_paragraphs(t.get("body")),
            "quote": {"text": q, "who": t.get("quote_who") or "", "org": t.get("quote_org") or ""} if q else None,
            "quote_pos": 2 if n.get("quote_pos") is None else n["quote_pos"],
            "place": n.get("place") or "", "place_locality": n.get("place_locality") or "", "cover": file_path(n.get("cover")), "cover_position": focal(n.get("cover")),
            "gallery": gallery(n.get("gallery")), "cta_model": by_id.get(_id(n.get("cta_model")), "")}


def build_content(raw):
    """raw = {"site", "settings", "hero_slides", "models", "news"} (fetch_content). Devuelve content.json + "_warnings"."""
    warnings = []
    site, st = raw["site"], raw["settings"]
    ts = tr(st)
    by_id = {m["id"]: model_key(m) for m in raw["models"]}
    models = [model(m, warnings) for m in sort_rows(raw["models"])]
    if not models:
        # home_hero() del generador hace MODEL_ORDER[0]: sin modelos revienta con IndexError en vez de avisar.
        raise ValueError("No hay ningún modelo publicado: publicá al menos uno antes de generar el sitio.")
    for m in models:
        if not m["menu_image"]:
            # sin menu_image el generador cae al literal images/menu/zeekr_<key>.png, que solo existe
            # para los tres modelos actuales: un modelo nuevo revienta el build con FileNotFoundError.
            raise ValueError(f"El modelo «{m['name']}» no tiene imagen de menú (menu_image): subila en Directus antes de publicar.")
    slides = []
    for h in sort_rows(raw["hero_slides"]):
        d = hero_slide(h, by_id)
        if d["image_desktop"] and (d["model"] or d["cta_primary_url"]):
            slides.append(d)
        else:
            warnings.append(f"hero #{h.get('id')} omitido (falta imagen de escritorio o modelo/URL)")
    news_out = []
    for n in raw["news"]:
        d = news(n, by_id)
        if d["cover"] and d["title"]:
            news_out.append(d)
        else:
            warnings.append(f"noticia #{n.get('id')} omitida (falta portada o título)")
    phones = [p for p in (st.get("phones") or []) if isinstance(p, dict) and p.get("e164") and p.get("display")]
    if not phones:
        raise ValueError("Configuración del sitio: faltan teléfonos (phones)")
    return {
        "site": {"name": site["name"], "slug": site["slug"], "domain": site["domain"].rstrip("/"), "ga_id": site.get("ga_id") or "",
                 "whatsapp": site.get("whatsapp") or "", "languages": ["es", "en", "pt", "zh"]},
        "settings": {
            "phones": [{"kind": p.get("kind") or "Ventas", "display": p["display"], "e164": p["e164"]} for p in phones],
            "social": [{"network": s.get("network") or "", "url": s["url"]} for s in (st.get("social") or []) if isinstance(s, dict) and s.get("url")],
            "header_menu": [{"label": i.get("label") or "", "target": i.get("target") or "url", "url": i.get("url") or ""} for i in (ts.get("header_menu") or []) if isinstance(i, dict)],
            **{k: ts.get(k) or "" for k in ("statement_title", "statement_text", "footer_tagline", "cookie_text", "legal_disclaimer", "org_description", "seo_title", "seo_description")},
            "tech_items": _pairs(ts.get("tech_items"), "title", "text"), "home_faq": _pairs(ts.get("home_faq"), "q", "a"),
        },
        "hero_slides": slides, "models": models, "news": news_out, "translations": translations(raw), "_warnings": warnings,
    }


# ---------------------------------------------------------------- traducciones (español → idioma) para `_()` del generador
def _pair(a, b, field, out):
    if isinstance(a, str) and isinstance(b, str):
        if field == "body":
            for pa, pb in zip(html_to_paragraphs(a), html_to_paragraphs(b)):
                out[pa] = pb
        elif a.strip() and b.strip():
            out[a] = b
    elif isinstance(a, list) and isinstance(b, list):
        for ia, ib in zip(a, b):
            if isinstance(ia, dict) and isinstance(ib, dict):
                for k in TEXT_KEYS:
                    va, vb = ia.get(k), ib.get(k)
                    if isinstance(va, str) and isinstance(vb, str) and va.strip() and vb.strip():
                        out[va] = vb


def walk(raw):
    """(colección, fila) de todo lo que tiene traducciones."""
    yield "site_settings", raw["settings"]
    for h in raw["hero_slides"]:
        yield "hero_slides", h
    for m in raw["models"]:
        yield "models", m
        for v in m.get("versions") or []:
            yield "model_versions", v
        for s in m.get("sections") or []:
            yield "model_sections", s
    for n in raw["news"]:
        yield "news", n


def galleries(raw):
    for m in raw["models"]:
        for s in m.get("sections") or []:
            for g in s.get("gallery") or []:
                yield "section_gallery", g
    for n in raw["news"]:
        for g in n.get("gallery") or []:
            yield "news_gallery", g


def translations(raw):
    out = {k: {} for k in LANG_KEY.values()}
    for coll, row in walk(raw):
        es = tr(row)
        for code, key in LANG_KEY.items():
            other = tr(row, code)
            for f in TRANSLATABLE[coll]:
                _pair(es.get(f), other.get(f), f, out[key])
    for _coll, g in galleries(raw):
        for code, key in LANG_KEY.items():
            if g.get("alt_es") and g.get(f"alt_{key}"):
                out[key][g["alt_es"]] = g[f"alt_{key}"]
    for m in raw["models"]:
        name = m.get("name") or ""
        for key, tpl in FAQ_TITLE.items():
            out[key].setdefault("Preguntas frecuentes sobre el " + name, tpl.format(name=name))
    return out
