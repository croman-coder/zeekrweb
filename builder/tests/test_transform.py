import pytest

from builder import transform as T


def test_file_path_and_focal():
    f = {"id": "abc", "filename_download": "Foto.JPG", "width": 2000, "height": 1000, "focal_point_x": 1200, "focal_point_y": 500}
    assert T.file_path(f) == "images/cms/abc.jpg"
    assert T.focal(f) == "60% 50%"
    assert T.focal({"id": "x", "filename_download": "a.png", "width": 10, "height": 10}) == "50% 50%"
    assert T.file_path(None) is None


def test_html_to_paragraphs():
    assert T.html_to_paragraphs("<p>Uno</p>\n<p>Dos <strong>fuerte</strong></p><p></p><p>&nbsp;</p>") == ["Uno", "Dos <strong>fuerte</strong>"]
    assert T.html_to_paragraphs(None) == []


def test_build_content_models_sections_and_positions(raw):
    c = T.build_content(raw)
    m = c["models"][0]
    assert m["key"] == "7x" and m["slug"] == "zeekr-7x"
    assert m["hero_image"] == "images/cms/h1.jpg" and m["hero_image_mobile"] == "images/cms/h2.jpg"
    assert m["hero_position"] == "60% 50%" and m["card_position"] == "50% 38%" and m["card_position_mobile"] == "50% 28%" and m["og_position"] == "60% 50%"
    assert m["pdf"] == "images/cms/p1.pdf" and m["menu_image"] == "images/cms/m1.png"
    assert [s["type"] for s in m["sections"]] == ["features", "split", "gallery"]          # ordenadas por sort; la split sin foto se omite
    assert m["sections"][1]["image"] == "images/cms/s1.jpg" and m["sections"][1]["dark"] is True
    assert m["sections"][2]["gallery"] == [{"file": "images/cms/g1.jpg", "alt": "Foto A"}, {"file": "images/cms/g2.jpg", "alt": "Foto B"}]
    assert m["versions"] == [{"name": "Smart", "subtitle": "Acceso", "rows": [{"k": "Autonomía", "v": "480 km (WLTP)"}]}]
    assert any("#3 omitida" in w for w in c["_warnings"])


def test_build_content_settings_hero_news(raw):
    c = T.build_content(raw)
    assert c["site"]["domain"] == "https://zeekrlife.com.py"
    assert c["settings"]["phones"][0]["e164"] == "+595971370006" and c["settings"]["header_menu"][0]["target"] == "modelos"
    assert len(c["hero_slides"]) == 1 and c["hero_slides"][0]["model"] == "7x" and c["hero_slides"][0]["image_mobile"] == "images/cms/h2.jpg"
    assert any("hero #2" in w for w in c["_warnings"])
    n = c["news"][0]
    assert n["body"] == ["Uno", "Dos <strong>fuerte</strong>"] and n["quote"] == {"text": "Cita", "who": "Manuel", "org": "Grupo"}
    assert n["cover_position"] == "50% 55%" and n["cta_model"] == "7x" and n["gallery"][0]["alt"] == "Foto evento"
    assert c["news"][1]["slug"] == "" and c["news"][1]["body"] == []


def test_translations_pairing(raw):
    t = T.translations(raw)
    assert t["en"]["Título"] == "Title"                       # campo simple
    assert t["en"]["Modelos"] == "Models"                     # repeater (header_menu.label)
    assert t["en"]["¿Qué?"] == "What?" and t["en"]["Eso."] == "That."
    assert t["en"]["Alto voltaje"] == "High voltage" and t["en"]["Autonomía"] == "Range"
    assert t["en"]["Dos <strong>fuerte</strong>"] == "Two <strong>strong</strong>"   # body por párrafos
    assert t["en"]["Foto B"] == "Photo B" and "Foto A" not in t["en"]                # alt de galería
    assert t["en"]["Preguntas frecuentes sobre el ZEEKR 7X"] == "ZEEKR 7X frequently asked questions"
    assert t["zh"]["Preguntas frecuentes sobre el ZEEKR 7X"] == "ZEEKR 7X 常见问题"
    assert t["pt"] == {"Preguntas frecuentes sobre el ZEEKR 7X": "Perguntas frequentes sobre o ZEEKR 7X"}


def test_missing_phones_raises(raw):
    raw["settings"]["phones"] = []
    with pytest.raises(ValueError):
        T.build_content(raw)
