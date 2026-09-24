# builder/seed_from_code.py — migración inicial: content/zeekr.json + i18n.py → Directus (archivos con punto focal, ítems anidados, traducciones).
# Uso: DIRECTUS_ADMIN_TOKEN=... [DIRECTUS_URL=https://admin.santarosa.lat] builder/.venv/bin/python -m builder.seed_from_code
# Idempotente: no vuelve a subir archivos ya mapeados ni a crear modelos/noticias/hero existentes.
import json
import mimetypes
import os
import sys
from pathlib import Path

import httpx

from .transform import LANG_KEY, TEXT_KEYS, TRANSLATABLE, html_to_paragraphs
from .translate import h, now

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from i18n import TRANSLATIONS  # noqa: E402

URL = os.environ.get("DIRECTUS_URL", "https://admin.santarosa.lat").rstrip("/")
TOKEN = os.environ.get("DIRECTUS_ADMIN_TOKEN") or sys.exit("falta DIRECTUS_ADMIN_TOKEN")
http = httpx.Client(base_url=URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=300)
MAP_PATH = ROOT / "cms" / "seed_map.json"
seed_map = json.loads(MAP_PATH.read_text()) if MAP_PATH.exists() else {}
_folders = {}
_verified = None   # ids de seed_map confirmados en ESTA instancia; None = todavía no se chequeó (ver _verified_set)


def api(method, path, **kw):
    r = http.request(method, path, **kw)
    if r.status_code >= 400:
        sys.exit(f"{method} {path} → {r.status_code}: {r.text[:400]}")
    return r.json().get("data") if r.content else None


def folder_id(name):
    if name not in _folders:
        root = api("GET", "/folders", params={"filter": json.dumps({"name": {"_eq": "zeekr"}, "parent": {"_null": True}}), "limit": 1})[0]["id"]
        _folders[name] = api("GET", "/folders", params={"filter": json.dumps({"name": {"_eq": name}, "parent": {"_eq": root}}), "limit": 1})[0]["id"]
    return _folders[name]


def _verified_set():
    """ids de seed_map que existen de verdad en esta instancia de Directus. Un solo GET masivo (no
    uno por archivo): si el mapa se generó corriendo el seed contra otra instancia (típicamente local
    vs. producción — cada Directus tiene su propia base y sus propios ids de /files), esos ids no
    apuntan a nada acá y SQLite no valida la referencia: quedaría una imagen rota en silencio. Se
    calcula una sola vez por corrida (global) y se cachea en memoria."""
    global _verified
    if _verified is None:
        ids = sorted(set(seed_map.values()))
        _verified = set()
        for i in range(0, len(ids), 200):   # por si el mapa creciera mucho; hoy son ~74
            chunk = ids[i:i + 200]
            rows = api("GET", "/files", params={"filter": json.dumps({"id": {"_in": chunk}}), "fields": "id", "limit": -1}) or []
            _verified.update(r["id"] for r in rows)
    return _verified


def upload(path, focal=None):
    """Sube (una sola vez) un archivo del repo y fija su punto focal. Devuelve el id de Directus. Si
    el id mapeado no existe en esta instancia (ver _verified_set) se resube y se pisa la entrada del
    mapa, en vez de confiar ciegamente en un id que puede ser de otro Directus."""
    if not path:
        return None
    fid = seed_map.get(path)
    if fid is not None and fid not in _verified_set():
        print(f"  ⚠ {path}: id {fid} no existe en esta instancia (mapa de otro Directus) — resubiendo")
        fid = None
    if fid is None:
        folder = folder_id("hero" if "/hero/" in path else "noticias" if "/noticias/" in path else "modelos")
        p = ROOT / path
        with open(p, "rb") as fh:
            r = http.post("/files", data={"folder": folder, "title": p.stem}, files={"file": (p.name, fh, mimetypes.guess_type(p.name)[0] or "application/octet-stream")})
        if r.status_code >= 400:
            sys.exit(f"upload {path} → {r.status_code}: {r.text[:300]}")
        fid = seed_map[path] = r.json()["data"]["id"]
        _verified_set().add(fid)   # recién subido a esta instancia: ya cuenta como verificado
        MAP_PATH.write_text(json.dumps(seed_map, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
        print("  ↑", path)
    if focal and focal != "50% 50%":
        f = api("GET", f"/files/{fid}", params={"fields": "width,height,focal_point_x"})
        if f.get("width") and f.get("focal_point_x") is None:
            px, py = (float(v.strip("%")) / 100 for v in focal.split())
            api("PATCH", f"/files/{fid}", json={"focal_point_x": round(px * f["width"]), "focal_point_y": round(py * f["height"])})
    return fid


def translate_value(field, v, d):
    """Traducción de un campo con el diccionario i18n; None si no hay traducción completa."""
    if field == "body":
        ps = html_to_paragraphs(v)
        out = [d.get(p) for p in ps]
        return "\n".join(f"<p>{p}</p>" for p in out) if ps and all(out) else None
    if isinstance(v, str):
        return d.get(v) if v.strip() else None
    if isinstance(v, list):
        keys = [(i, k) for i in v if isinstance(i, dict) for k in TEXT_KEYS if isinstance(i.get(k), str)]
        if not any(d.get(i[k]) for i, k in keys):
            return None
        return [{**i, **{k: d.get(i[k], i[k]) for k in TEXT_KEYS if isinstance(i.get(k), str)}} for i in v if isinstance(i, dict)]
    return None


def tr_rows(coll, fields_es):
    """[fila es-PY, filas en/pt/zh con lo que exista en i18n] y las metas (campo, idioma, hash) para translation_meta."""
    rows, metas = [{"languages_code": "es-PY", **fields_es}], []
    for code, key in LANG_KEY.items():
        d = {}
        for f, v in fields_es.items():
            if f not in TRANSLATABLE.get(coll, []) or not v:
                continue
            t = translate_value(f, v, TRANSLATIONS[key])
            if t is not None:
                d[f] = t
                metas.append((f, code, h(v)))
        if d:
            rows.append({"languages_code": code, **d})
    return rows, metas


def alts(alt):
    return {f"alt_{key}": TRANSLATIONS[key][alt] for key in LANG_KEY.values() if TRANSLATIONS[key].get(alt)}


def add_meta(coll, item_id, metas):
    """Crea sólo las filas de translation_meta que falten para (coll, item_id, campo, idioma). Idempotente
    a propósito: si el proceso murió a mitad de una corrida anterior, el ítem puede ya existir con sus
    traducciones puestas pero con algunas (o todas) las filas de translation_meta sin crear todavía — y
    sync_translations() (builder/translate.py) sólo saltea una traducción existente si hay una fila de
    meta para ese campo/idioma. Sin este chequeo, una traducción "humana" sin marcar nunca se detecta
    como faltante pero tampoco se re-traduce (queda congelada): hay texto pero ninguna fila la explica."""
    if not metas:
        return
    have = {(m["field"], m["lang"]) for m in api("GET", "/items/translation_meta", params={"filter": json.dumps({"collection": {"_eq": coll}, "item": {"_eq": str(item_id)}}), "fields": "field,lang", "limit": -1}) or []}
    for field, lang, sh in metas:
        if (field, lang) in have:
            continue
        api("POST", "/items/translation_meta", json={"collection": coll, "item": str(item_id), "field": field, "lang": lang, "source_hash": sh, "translated_by": "human", "translated_at": now()})


def seed_settings(site_id, c):
    st = api("GET", "/items/site_settings", params={"filter": json.dumps({"site": {"_eq": site_id}}), "fields": "id,translations.id", "limit": 1})[0]
    s = c["settings"]
    rows, metas = tr_rows("site_settings", {k: s[k] for k in TRANSLATABLE["site_settings"]})
    payload = {"phones": s["phones"], "social": s["social"], "status": "published"}
    if not st.get("translations"):
        payload["translations"] = rows
    api("PATCH", f"/items/site_settings/{st['id']}", json=payload)
    add_meta("site_settings", st["id"], metas)   # idempotente: si ya estaban las traducciones pero faltó marcarlas, esto las completa


def model_payload(m, site_id, sort):
    rows, metas = tr_rows("models", {k: m[k] for k in TRANSLATABLE["models"]})
    sections, sec_metas = [], []
    for i, s in enumerate(m["sections"], 1):
        sf = {k: s.get(k) or "" for k in ("kicker", "title", "text", "image_alt")}
        if s.get("items"):
            sf["items"] = s["items"]
        srows, sm = tr_rows("model_sections", sf)
        sections.append({"sort": i, "type": s["type"], "dark": bool(s.get("dark")), "reverse": bool(s.get("reverse")), "translations": srows,
                         "image": upload(s.get("image"), s.get("position")), "video": upload(s.get("video")),
                         "gallery": [{"sort": j, "file": upload(g["file"]), "alt_es": g["alt"], **alts(g["alt"])} for j, g in enumerate(s.get("gallery", []), 1)]})
        sec_metas.append(sm)
    versions, ver_metas = [], []
    for i, v in enumerate(m["versions"], 1):
        vrows, vm = tr_rows("model_versions", {"subtitle": v["subtitle"], "rows": v["rows"]})
        versions.append({"sort": i, "name": v["name"], "translations": vrows})
        ver_metas.append(vm)
    payload = {"site": site_id, "status": "published", "sort": sort, "name": m["name"], "slug": m["slug"], "short": m["short"],
               "card_position_mobile": m["card_position_mobile"], "og_position": m["og_position"],
               "hero_image": upload(m["hero_image"], m["hero_position"]), "hero_image_mobile": upload(m.get("hero_image_mobile")),
               "card_image": upload(m["card_image"], m["card_position"]), "menu_image": upload(m.get("menu_image")), "pdf": upload(m.get("pdf")),
               "translations": rows, "sections": sections, "versions": versions}
    return payload, metas, sec_metas, ver_metas


def seed_hero(site_id, c, model_ids):
    """Cada slide se matchea por su posición (sort) dentro del sitio, no por "¿existe algún hero_slide
    para este sitio?": si el proceso murió a mitad de una corrida anterior con sólo 1 de 3 slides
    creados, esa condición agregada ya daba verdadero y la corrida siguiente saltaba TODO el hero para
    siempre, dejándolo incompleto. Acá sólo se crean los sort que falten."""
    existing = {h["sort"]: h["id"] for h in api("GET", "/items/hero_slides", params={"filter": json.dumps({"site": {"_eq": site_id}}), "fields": "id,sort", "limit": -1}) or []}
    for i, sl in enumerate(c["hero_slides"], 1):
        rows, metas = tr_rows("hero_slides", {k: sl[k] for k in TRANSLATABLE["hero_slides"]})
        if i in existing:
            print("hero slide ya existe:", i)
            add_meta("hero_slides", existing[i], metas)
            continue
        rows[0]["cta_primary_url"] = sl.get("cta_primary_url", "")
        item = api("POST", "/items/hero_slides", json={"site": site_id, "status": "published", "sort": i, "model": model_ids.get(sl["model"]), "cta_secondary_intent": sl["cta_secondary_intent"],
                                                       "image_desktop": upload(sl["image_desktop"]), "image_mobile": upload(sl.get("image_mobile")), "translations": rows})
        add_meta("hero_slides", item["id"], metas)
        print("hero slide:", i)


def news_payload(n, site_id, model_ids):
    q = n.get("quote") or {}
    nf = {"kicker": n["kicker"], "title": n["title"], "lead": n["lead"], "meta_description": n["meta_description"],
          "body": "\n".join(f"<p>{p}</p>" for p in n["body"]) if n["body"] else "", "quote_text": q.get("text", ""), "quote_org": q.get("org", "")}
    rows, metas = tr_rows("news", {k: v for k, v in nf.items() if v})
    rows[0]["quote_who"] = q.get("who", "")
    return {"site": site_id, "status": "published", "date": n["date"], "slug": n["slug"], "place": n["place"], "place_locality": n["place_locality"], "quote_pos": n["quote_pos"],
            "cta_model": model_ids.get(n["cta_model"]), "cover": upload(n["cover"], n["cover_position"]), "translations": rows,
            "gallery": [{"sort": j, "file": upload(g["file"]), "alt_es": g["alt"], **alts(g["alt"])} for j, g in enumerate(n["gallery"], 1)]}, metas


def main():
    c = json.loads((ROOT / "content" / "zeekr.json").read_text())
    sid = api("GET", "/items/sites", params={"filter": json.dumps({"slug": {"_eq": "zeekr"}}), "limit": 1})[0]["id"]
    print("settings")
    seed_settings(sid, c)
    model_ids = {}
    for i, m in enumerate(c["models"], 1):
        # model_payload() siempre se calcula, exista o no el modelo: upload() es idempotente (no
        # resube lo que ya está mapeado y verificado) y así, si el modelo ya existe pero la corrida
        # anterior murió antes de completar su translation_meta, igual tenemos los `metas` para
        # completarlos más abajo — en vez de saltear el modelo entero con un `continue` temprano.
        payload, metas, sec_metas, ver_metas = model_payload(m, sid, i)
        ex = api("GET", "/items/models", params={"filter": json.dumps({"site": {"_eq": sid}, "slug": {"_eq": m["slug"]}}), "fields": "id,sections.id,sections.sort,versions.id,versions.sort", "limit": 1})
        if ex:
            item = ex[0]
            model_ids[m["key"]] = item["id"]
            print("modelo ya existe:", m["slug"])
        else:
            item = api("POST", "/items/models", params={"fields": "id,sections.id,sections.sort,versions.id,versions.sort"}, json=payload)
            model_ids[m["key"]] = item["id"]
            print("modelo:", m["slug"])
        add_meta("models", item["id"], metas)
        for s in item["sections"]:
            add_meta("model_sections", s["id"], sec_metas[s["sort"] - 1])
        for v in item["versions"]:
            add_meta("model_versions", v["id"], ver_metas[v["sort"] - 1])
    print("hero")
    seed_hero(sid, c, model_ids)
    for n in c["news"]:
        payload, metas = news_payload(n, sid, model_ids)   # mismo motivo que en el loop de modelos: hace falta `metas` incluso si la noticia ya existe
        flt = {"site": {"_eq": sid}, "slug": {"_eq": n["slug"]}} if n["slug"] else {"site": {"_eq": sid}, "date": {"_eq": n["date"]}, "translations": {"title": {"_eq": n["title"]}}}
        ex = api("GET", "/items/news", params={"filter": json.dumps(flt), "fields": "id", "limit": 1})
        if ex:
            item_id = ex[0]["id"]
            print("noticia ya existe:", n["slug"] or n["title"][:40])
        else:
            item_id = api("POST", "/items/news", json=payload)["id"]
            print("noticia:", n["slug"] or n["title"][:40])
        add_meta("news", item_id, metas)
    print("OK seed;", len(seed_map), "archivos en cms/seed_map.json")


if __name__ == "__main__":
    main()
