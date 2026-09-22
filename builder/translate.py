# builder/translate.py — traduce con Claude lo que falta o cambió en español; respeta correcciones humanas.
import hashlib
import json
from datetime import datetime, timezone

import httpx

from .transform import LANG_KEY, TEXT_KEYS, TRANSLATABLE, galleries, html_to_paragraphs, tr, walk

MODEL = "claude-sonnet-5"
LANG_NAME = {"en": "English (neutral, international)", "pt-BR": "Brazilian Portuguese", "zh-Hans": "Simplified Chinese"}
BATCH = 60
GLOSSARY = [
    "ZEEKR siempre en mayúsculas; ZEEKR 7X, ZEEKR X, ZEEKR 001 son nombres: no se traducen",
    "Smart, Performance, Flagship, Premium, Sport son nombres de versión: no se traducen",
    "Santa Rosa Paraguay, Grupo Geely, Qualcomm, Snapdragon, Falcon Eye Vidar, Qilin: no se traducen",
    "WLTP, OTA, ADAS, AWD, RWD, DRL, kWh, km/h, V, HP se mantienen; HP → EN 'hp', PT-BR 'cv', ZH '马力'",
    "Números: EN usa coma de miles y punto decimal (4,787 mm; 3.8 s); PT-BR punto de miles y coma decimal (4.787 mm; 3,8 s); ZH coma de miles y punto decimal (4,787 mm; 3.8 秒)",
    "El español usa voseo (agendá, conocé): usar el registro natural de cada idioma, tono premium y breve",
    "Mantener etiquetas HTML inline (<strong>, <a …>), entidades y marcadores {model} exactamente igual",
]
SYSTEM = ("Sos el traductor oficial del sitio web de ZEEKR Paraguay (vehículos eléctricos premium). Traducís del español al idioma pedido. "
          "Respondé SOLO con un array JSON de strings, en el mismo orden y con la misma cantidad que la entrada, sin comentarios.\nGlosario y reglas:\n- " + "\n- ".join(GLOSSARY))


def h(text):
    return hashlib.sha256(json.dumps(text, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Claude:
    def __init__(self, api_key, model=MODEL, timeout=240, transport=None):
        self.api_key, self.model = api_key, model
        self.http = httpx.Client(base_url="https://api.anthropic.com",
                                  headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                                  timeout=timeout, transport=transport)

    def translate(self, texts, lang):
        r = self.http.post("/v1/messages",
                            json={"model": self.model, "max_tokens": 8000, "system": SYSTEM,
                                  "messages": [{"role": "user", "content": f"Idioma destino: {LANG_NAME[lang]}\nTextos (JSON):\n{json.dumps(list(texts), ensure_ascii=False)}"}]})
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
        out = json.loads(text[text.index("["):text.rindex("]") + 1])
        if len(out) != len(texts) or not all(isinstance(x, str) for x in out):
            raise ValueError("Claude devolvió una cantidad distinta de textos")
        return out


def flatten(field, value):
    if field == "body":
        return html_to_paragraphs(value)
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [i[k] for i in value if isinstance(i, dict) for k in TEXT_KEYS if isinstance(i.get(k), str) and i[k].strip()]
    return []


def unflatten(field, value, it):
    if field == "body":
        return "\n".join(f"<p>{next(it)}</p>" for _ in html_to_paragraphs(value))
    if isinstance(value, str):
        return next(it) if value.strip() else value
    out = []
    for i in value:
        if not isinstance(i, dict):
            out.append(i)
            continue
        j = dict(i)
        for k in TEXT_KEYS:
            if isinstance(i.get(k), str) and i[k].strip():
                j[k] = next(it)
        out.append(j)
    return out


def _chunked(strings, client, lang):
    out = []
    for i in range(0, len(strings), BATCH):
        out += client.translate(strings[i:i + BATCH], lang)
    return out


def sync_translations(dx, raw, client, log=print):
    """Para cada ítem/campo/idioma: traduce si falta o si el español cambió (hash), salvo traducciones humanas. Muta raw."""
    stats = {"translated": 0, "skipped": 0, "errors": 0}
    meta = {(m["collection"], str(m["item"]), m["field"], m["lang"]): m for m in dx.items("translation_meta")}

    def upsert_meta(coll, item, field, lang, sh):
        key = (coll, str(item), field, lang)
        data = {"collection": coll, "item": str(item), "field": field, "lang": lang, "source_hash": sh, "translated_by": "ai", "translated_at": now()}
        if key in meta:
            meta[key] = dx.update("translation_meta", meta[key]["id"], data)
        else:
            meta[key] = dx.create("translation_meta", data)

    for coll, row in walk(raw):
        es = tr(row)
        if not es:
            continue
        for lang in LANG_NAME:
            cur = tr(row, lang)
            todo = []
            for field in TRANSLATABLE[coll]:
                src = es.get(field)
                if not flatten(field, src):
                    continue
                sh = h(src)
                m = meta.get((coll, str(row["id"]), field, lang))
                has = bool(flatten(field, cur.get(field)))
                if has and (m is None or m.get("translated_by") == "human" or m.get("source_hash") == sh):
                    stats["skipped"] += 1
                    continue
                todo.append((field, src, sh))
            if not todo:
                continue
            strings = [s for field, src, _ in todo for s in flatten(field, src)]
            try:
                out = iter(_chunked(strings, client, lang))
            except Exception as e:  # noqa: BLE001 — sin traducción se publica en español
                stats["errors"] += 1
                log(f"⚠ traducción {coll}#{row['id']} {lang}: {e}")
                continue
            patch = {field: unflatten(field, src, out) for field, src, _ in todo}
            if cur.get("id"):
                dx.update(f"{coll}_translations", cur["id"], patch)
                cur.update(patch)
            else:
                new = dx.create(f"{coll}_translations", {f"{coll}_id": row["id"], "languages_code": lang, **patch})
                row.setdefault("translations", []).append({**new, "languages_code": lang, **patch})
            for field, _src, sh in todo:
                upsert_meta(coll, row["id"], field, lang, sh)
            stats["translated"] += len(todo)

    pending = {lang: [] for lang in LANG_NAME}   # lang → [(coll, g, field, es), ...] de todas las galerías, agrupado para lotear por idioma
    for coll, g in galleries(raw):
        es = g.get("alt_es")
        if not es:
            continue
        for lang in LANG_NAME:
            field = f"alt_{LANG_KEY[lang]}"
            if not g.get(field):
                pending[lang].append((coll, g, field, es))

    row_patches = {}   # id(fila) → (coll, g, patch) — junta los campos de varios idiomas de la misma fila en un solo update
    for lang, items in pending.items():
        if not items:
            continue
        try:
            out = _chunked([es for *_, es in items], client, lang)
        except Exception as e:  # noqa: BLE001 — se cuenta el idioma entero como error y se sigue con el resto
            stats["errors"] += len(items)
            log(f"⚠ traducción alt {lang}: {e}")
            continue
        for (coll, g, field, _es), val in zip(items, out):
            row_patches.setdefault(id(g), (coll, g, {}))[2][field] = val

    for coll, g, patch in row_patches.values():
        dx.update(coll, g["id"], patch)
        g.update(patch)
        stats["translated"] += len(patch)
    log(f"traducciones: {stats}")
    return stats
