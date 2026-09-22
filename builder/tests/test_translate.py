import json

import httpx
import pytest

from builder import translate as TR


def make_claude(handler, **kw):
    """Como `make` de test_directus_client.py: un Claude real con transport mockeado (sin red)."""
    return TR.Claude("fake-key", transport=httpx.MockTransport(handler), **kw)


def text_response(text):
    return httpx.Response(200, json={"content": [{"type": "text", "text": text}]})


class FakeClaude:
    def __init__(self):
        self.calls = []

    def translate(self, texts, lang):
        self.calls.append((lang, list(texts)))
        return [f"[{lang}] {t}" for t in texts]


class FakeDx:
    def __init__(self, meta=None):
        self.meta = meta or []
        self.created, self.updated = [], []
        self.n = 100

    def items(self, coll, **params):
        assert coll == "translation_meta"
        return self.meta

    def create(self, coll, data):
        self.n += 1
        self.created.append((coll, data))
        return {"id": self.n, **data}

    def update(self, coll, id_, data):
        self.updated.append((coll, id_, data))
        return {"id": id_, **data}


def test_flatten_unflatten_roundtrip():
    items = [{"title": "A", "text": "B", "extra": 1}, {"title": "C", "text": ""}]
    flat = TR.flatten("items", items)
    assert flat == ["A", "B", "C"]
    assert TR.unflatten("items", items, iter(["a", "b", "c"])) == [{"title": "a", "text": "b", "extra": 1}, {"title": "c", "text": ""}]
    assert TR.flatten("body", "<p>Uno</p><p>Dos</p>") == ["Uno", "Dos"]
    assert TR.unflatten("body", "<p>Uno</p><p>Dos</p>", iter(["One", "Two"])) == "<p>One</p>\n<p>Two</p>"
    assert TR.flatten("title", "Hola") == ["Hola"] and TR.unflatten("title", "Hola", iter(["Hi"])) == "Hi"


def test_sync_creates_missing_and_respects_human(raw):
    raw["models"] = []
    raw["news"] = []
    raw["hero_slides"] = raw["hero_slides"][:1]
    dx, cl = FakeDx(), FakeClaude()
    stats = TR.sync_translations(dx, raw, cl, log=lambda m: None)
    # site_settings: en existe (creada por humano sin meta) → se completa lo que falta; pt/zh se crean enteras; hero: en/pt/zh nuevas
    langs = sorted(c[1]["languages_code"] for c in dx.created if c[0] == "site_settings_translations")
    assert langs == ["pt-BR", "zh-Hans"]
    en_patch = next(u for u in dx.updated if u[0] == "site_settings_translations")[2]
    assert "statement_title" not in en_patch and en_patch["statement_text"] == "[en] Texto"      # el título en inglés ya estaba (humano) y no se pisa
    assert "home_faq" not in en_patch and "header_menu" not in en_patch                        # ya tenían inglés
    hero_rows = [c[1] for c in dx.created if c[0] == "hero_slides_translations"]
    assert len(hero_rows) == 3 and hero_rows[0]["title"] == "[en] ZEEKR 7X" and hero_rows[0]["hero_slides_id"] == 1
    metas = [c[1] for c in dx.created if c[0] == "translation_meta"]
    assert all(m["translated_by"] == "ai" and len(m["source_hash"]) == 16 for m in metas)
    assert any(t["languages_code"] == "pt-BR" for t in raw["hero_slides"][0]["translations"])   # raw queda actualizado para el transform
    assert stats["errors"] == 0 and stats["translated"] > 0


def test_sync_skips_unchanged_and_retranslates_changed(raw):
    raw["models"] = []
    raw["news"] = []
    raw["hero_slides"] = raw["hero_slides"][:1]
    h = raw["hero_slides"][0]
    h["translations"].append({"id": 9, "languages_code": "en", "eyebrow": "SUV en", "title": "ZEEKR 7X", "claim": "Claim en", "cta_primary_label": "Discover the {model}"})
    meta = [{"id": 1, "collection": "hero_slides", "item": "1", "field": f, "lang": "en", "source_hash": TR.h(TR.tr(h)[f]), "translated_by": "ai"} for f in ("eyebrow", "title", "claim", "cta_primary_label")]
    meta[0]["source_hash"] = "stale"                       # el español del eyebrow cambió
    dx, cl = FakeDx(meta), FakeClaude()
    TR.sync_translations(dx, {**raw, "settings": {"translations": []}}, cl, log=lambda m: None)
    en_calls = [c for c in cl.calls if c[0] == "en"]
    assert en_calls == [("en", ["SUV"])]                   # solo el campo con hash viejo
    assert dx.updated[0][:2] == ("hero_slides_translations", 9) and dx.updated[0][2] == {"eyebrow": "[en] SUV"}
    assert any(u[0] == "translation_meta" and u[2]["source_hash"] == TR.h("SUV") for u in dx.updated)


def test_gallery_alts(raw):
    raw["hero_slides"] = []
    raw["news"] = raw["news"][:1]
    dx, cl = FakeDx(), FakeClaude()
    TR.sync_translations(dx, {**raw, "settings": {"translations": []}, "models": []}, cl, log=lambda m: None)
    g = next(u for u in dx.updated if u[0] == "news_gallery")
    assert g[1] == 9 and g[2] == {"alt_pt": "[pt-BR] Foto evento", "alt_zh": "[zh-Hans] Foto evento"}   # alt_en ya estaba


def test_error_in_claude_does_not_raise(raw):
    class Boom:
        def translate(self, texts, lang):
            raise RuntimeError("api caída")

    stats = TR.sync_translations(FakeDx(), raw, Boom(), log=lambda m: None)
    assert stats["errors"] > 0 and stats["translated"] == 0


# ---------------------------------------------------------------- Claude.translate: validación de la respuesta (fix round 1)

def test_claude_translate_rejects_fewer_elements_than_requested():
    c = make_claude(lambda req: text_response(json.dumps(["solo uno"])))
    with pytest.raises(ValueError):
        c.translate(["a", "b", "c"], "en")


def test_claude_translate_rejects_more_elements_than_requested():
    c = make_claude(lambda req: text_response(json.dumps(["a", "b", "c", "de más"])))
    with pytest.raises(ValueError):
        c.translate(["a", "b", "c"], "en")


def test_claude_translate_rejects_non_string_elements():
    c = make_claude(lambda req: text_response(json.dumps(["ok", 2])))
    with pytest.raises(ValueError):
        c.translate(["a", "b"], "en")


def test_claude_translate_extracts_json_from_surrounding_prose():
    c = make_claude(lambda req: text_response('Acá está la traducción:\n["One", "Two"]\nEspero que sirva.'))
    assert c.translate(["Uno", "Dos"], "en") == ["One", "Two"]


def test_claude_translate_raises_without_brackets():
    c = make_claude(lambda req: text_response("lo siento, no puedo ayudar con eso"))
    with pytest.raises(ValueError):
        c.translate(["a"], "en")


# ---------------------------------------------------------------- sync_translations ante respuestas malas de Claude (fix round 1)

def test_sync_counts_error_and_writes_nothing_on_wrong_length_response(raw):
    raw["models"] = []
    raw["news"] = []
    raw["hero_slides"] = raw["hero_slides"][:1]
    client = make_claude(lambda req: text_response(json.dumps(["solo un texto"])))   # hero pide 4 campos por idioma
    dx = FakeDx()
    stats = TR.sync_translations(dx, {**raw, "settings": {"translations": []}}, client, log=lambda m: None)
    assert stats["errors"] >= 1 and stats["translated"] == 0
    assert dx.created == [] and dx.updated == []
    assert len(raw["hero_slides"][0]["translations"]) == 1   # solo sigue la fila es-PY original; nada parcial


def test_sync_counts_error_and_does_not_raise_when_response_has_no_brackets(raw):
    raw["models"] = []
    raw["news"] = []
    raw["hero_slides"] = raw["hero_slides"][:1]
    client = make_claude(lambda req: text_response("no puedo ayudar con esta traducción"))
    stats = TR.sync_translations(FakeDx(), {**raw, "settings": {"translations": []}}, client, log=lambda m: None)   # no debe lanzar
    assert stats["errors"] >= 1 and stats["translated"] == 0


def test_batch_over_BATCH_size_keeps_patch_aligned(monkeypatch, raw):
    monkeypatch.setattr(TR, "BATCH", 2)
    raw["models"] = []
    raw["news"] = []
    raw["hero_slides"] = raw["hero_slides"][:1]
    dx, cl = FakeDx(), FakeClaude()
    TR.sync_translations(dx, {**raw, "settings": {"translations": []}}, cl, log=lambda m: None)
    en_calls = [c for c in cl.calls if c[0] == "en"]
    assert len(en_calls) == 2 and sum(len(t) for _, t in en_calls) == 4          # 4 strings / BATCH=2 → 2 llamadas
    hero_en = next(t for t in raw["hero_slides"][0]["translations"] if t["languages_code"] == "en")
    assert (hero_en["eyebrow"], hero_en["title"], hero_en["claim"], hero_en["cta_primary_label"]) == ("[en] SUV", "[en] ZEEKR 7X", "[en] Claim", "[en] Conocé el {model}")


def test_second_batch_failure_writes_nothing_for_that_item_lang(monkeypatch, raw):
    monkeypatch.setattr(TR, "BATCH", 2)
    raw["models"] = []
    raw["news"] = []
    raw["hero_slides"] = raw["hero_slides"][:1]

    class FailSecondCall:
        def __init__(self):
            self.calls = []

        def translate(self, texts, lang):
            self.calls.append((lang, list(texts)))
            if len(self.calls) == 2:            # "en" se procesa primero (orden de LANG_NAME): esta es su segunda tanda
                raise RuntimeError("api caída a mitad de lote")
            return [f"[{lang}] {t}" for t in texts]

    dx, cl = FakeDx(), FailSecondCall()
    stats = TR.sync_translations(dx, {**raw, "settings": {"translations": []}}, cl, log=lambda m: None)
    assert stats["errors"] >= 1
    # nada se escribió para hero/en: ni fila de traducción ni meta → queda consistente para reintentar en el próximo build
    assert not any(c[0] == "hero_slides_translations" and c[1].get("languages_code") == "en" for c in dx.created)
    assert not any(c[0] == "translation_meta" and c[1].get("lang") == "en" for c in dx.created)
    assert not any(t.get("languages_code") == "en" for t in raw["hero_slides"][0]["translations"])
    # pt-BR y zh-Hans sí se tradujeron (aislamiento de errores: una tanda rota no frena a los demás idiomas)
    assert any(c[0] == "hero_slides_translations" and c[1].get("languages_code") == "pt-BR" for c in dx.created)
    assert any(c[0] == "hero_slides_translations" and c[1].get("languages_code") == "zh-Hans" for c in dx.created)


# ---------------------------------------------------------------- alts de galería loteados por idioma (fix round 1)

def test_gallery_alts_batched_per_language(raw):
    raw["hero_slides"] = []
    raw["models"] = []
    raw["news"] = raw["news"][:1]
    n = raw["news"][0]
    n["gallery"] = [
        {"id": 20, "sort": 1, "file": {"id": "f1"}, "alt_es": "Foto uno", "alt_pt": "Foto um", "alt_zh": "照片一"},
        {"id": 21, "sort": 2, "file": {"id": "f2"}, "alt_es": "Foto dos", "alt_pt": "Foto dois", "alt_zh": "照片二"},
        {"id": 22, "sort": 3, "file": {"id": "f3"}, "alt_es": "Foto tres", "alt_pt": "Foto três", "alt_zh": "照片三"},
    ]  # a las tres les falta alt_en; alt_pt/alt_zh ya están y no deben pisarse
    dx, cl = FakeDx(), FakeClaude()
    TR.sync_translations(dx, {**raw, "settings": {"translations": []}}, cl, log=lambda m: None)
    # la fila "news" en sí también dispara sus propias llamadas ("en" para kicker/title/lead/...); lo que nos importa
    # es que los 3 alts pendientes vinieron juntos en UNA sola llamada, no una por foto.
    en_gallery_calls = [c for c in cl.calls if c == ("en", ["Foto uno", "Foto dos", "Foto tres"])]
    assert en_gallery_calls == [("en", ["Foto uno", "Foto dos", "Foto tres"])]
    updates = {u[1]: u[2] for u in dx.updated if u[0] == "news_gallery"}
    assert updates == {20: {"alt_en": "[en] Foto uno"}, 21: {"alt_en": "[en] Foto dos"}, 22: {"alt_en": "[en] Foto tres"}}


def test_gallery_alts_batch_error_isolated_per_language(raw):
    raw["hero_slides"] = []
    raw["models"] = []
    raw["news"] = raw["news"][:1]
    n = raw["news"][0]
    n["gallery"] = [
        {"id": 30, "sort": 1, "file": {"id": "f1"}, "alt_es": "Foto uno"},   # falta alt_en, alt_pt y alt_zh
    ]

    class FailEnOnly:
        def translate(self, texts, lang):
            if lang == "en":
                raise RuntimeError("api caída")
            return [f"[{lang}] {t}" for t in texts]

    dx = FakeDx()
    stats = TR.sync_translations(dx, {**raw, "settings": {"translations": []}}, FailEnOnly(), log=lambda m: None)
    assert stats["errors"] >= 1
    updates = {u[1]: u[2] for u in dx.updated if u[0] == "news_gallery"}
    assert updates == {30: {"alt_pt": "[pt-BR] Foto uno", "alt_zh": "[zh-Hans] Foto uno"}}   # pt/zh sí se guardaron pese a que "en" falló
