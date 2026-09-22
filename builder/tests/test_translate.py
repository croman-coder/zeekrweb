from builder import translate as TR


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
