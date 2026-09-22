import json

import httpx
import pytest

from builder import directus_client as D


def make(handler):
    return D.Directus("https://cms.test", "tok", transport=httpx.MockTransport(handler))


def test_fetch_content_filters_and_shapes():
    seen = {}

    def handler(req):
        seen[req.url.path] = dict(req.url.params)
        assert req.headers["authorization"] == "Bearer tok"
        data = {"/items/sites/1": {"id": 1, "slug": "zeekr"}, "/items/site_settings": [{"id": 1, "translations": []}],
                "/items/models": [{"id": 10}], "/items/hero_slides": [], "/items/news": []}[req.url.path]
        return httpx.Response(200, json={"data": data})

    raw = D.fetch_content(make(handler), 1, drafts=False)
    assert raw["site"]["slug"] == "zeekr" and raw["settings"]["id"] == 1 and raw["models"] == [{"id": 10}]
    f = json.loads(seen["/items/models"]["filter"])
    assert f == {"_and": [{"site": {"_eq": 1}}, {"status": {"_eq": "published"}}]}
    assert seen["/items/models"]["limit"] == "-1" and "sections.gallery.file.*" in seen["/items/models"]["fields"]
    raw = D.fetch_content(make(handler), 1, drafts=True)
    assert json.loads(seen["/items/news"]["filter"])["_and"][1] == {"status": {"_in": ["draft", "published"]}}


def test_fetch_site():
    def handler(req):
        assert req.url.path == "/items/site_settings/7"
        return httpx.Response(200, json={"data": {"id": 7, "site": {"id": 1, "slug": "zeekr"}, "phones": []}})

    site, st = D.fetch_site(make(handler), 7)
    assert site["slug"] == "zeekr" and st == {"id": 7, "phones": []}


def test_fetch_content_site_settings_filtered_and_sorted():
    seen = {}

    def handler(req):
        seen[req.url.path] = dict(req.url.params)
        data = {"/items/sites/1": {"id": 1, "slug": "zeekr"}, "/items/site_settings": [{"id": 1, "translations": []}],
                "/items/models": [], "/items/hero_slides": [], "/items/news": []}[req.url.path]
        return httpx.Response(200, json={"data": data})

    D.fetch_content(make(handler), 1, drafts=False)
    f = json.loads(seen["/items/site_settings"]["filter"])
    assert f == {"_and": [{"site": {"_eq": 1}}, {"status": {"_eq": "published"}}]}
    assert seen["/items/site_settings"]["sort"] == "id"


def test_fetch_content_site_settings_draft_only_raises_actionable_error():
    def handler(req):
        if req.url.path == "/items/sites/1":
            return httpx.Response(200, json={"data": {"id": 1, "slug": "zeekr"}})
        assert req.url.path == "/items/site_settings"
        filt = json.loads(req.url.params["filter"])
        if "_and" in filt:                                            # filtrada por status (published) → vacía
            return httpx.Response(200, json={"data": []})
        return httpx.Response(200, json={"data": [{"id": 5}]})         # solo por site → existe (draft)

    with pytest.raises(LookupError, match="borrador"):
        D.fetch_content(make(handler), 1, drafts=False)


def test_fetch_content_site_settings_none_at_all_raises_original_error():
    def handler(req):
        if req.url.path == "/items/sites/1":
            return httpx.Response(200, json={"data": {"id": 1, "slug": "zeekr"}})
        assert req.url.path == "/items/site_settings"
        return httpx.Response(200, json={"data": []})                 # ninguna fila, con o sin filtro de status

    with pytest.raises(LookupError, match="el sitio no tiene site_settings"):
        D.fetch_content(make(handler), 1, drafts=False)


def test_fetch_content_site_settings_multiple_warns_and_uses_first(capsys):
    def handler(req):
        data = {"/items/sites/1": {"id": 1, "slug": "zeekr"},
                "/items/site_settings": [{"id": 3, "translations": []}, {"id": 9, "translations": []}],
                "/items/models": [], "/items/hero_slides": [], "/items/news": []}[req.url.path]
        return httpx.Response(200, json={"data": data})

    raw = D.fetch_content(make(handler), 1, drafts=False)
    assert raw["settings"]["id"] == 3
    out = capsys.readouterr().out
    assert "2" in out and "id 3" in out


def test_sync_files_downloads_once_and_skips_same_size(tmp_path):
    calls = []

    def handler(req):
        calls.append(req.url.path)
        return httpx.Response(200, content=b"12345")

    f = {"id": "abc", "filename_download": "a.jpg", "filesize": 5}
    raw = {"models": [{"hero_image": f, "sections": [{"image": f}]}], "news": [{"cover": {"id": "def", "filename_download": "b.png", "filesize": 5}}]}
    assert D.sync_files(make(handler), raw, tmp_path, log=lambda m: None) == 2
    assert (tmp_path / "images/cms/abc.jpg").read_bytes() == b"12345" and (tmp_path / "images/cms/def.png").exists()
    assert calls == ["/assets/abc", "/assets/def"]
    assert D.sync_files(make(handler), raw, tmp_path, log=lambda m: None) == 0      # ya están, mismo tamaño
    (tmp_path / "images/cms/abc.jpg").write_bytes(b"x")                              # tamaño distinto → se vuelve a bajar
    assert D.sync_files(make(handler), raw, tmp_path, log=lambda m: None) == 1


def test_sync_files_redownloads_when_filesize_falsy(tmp_path):
    calls = []

    def handler(req):
        calls.append(req.url.path)
        return httpx.Response(200, content=b"xxxxx")

    f = {"id": "ghi", "filename_download": "c.jpg", "filesize": 0}    # Directus todavía no completó filesize
    raw = {"models": [{"hero_image": f}]}
    assert D.sync_files(make(handler), raw, tmp_path, log=lambda m: None) == 1
    assert calls == ["/assets/ghi"]
    # sin un filesize confiable no hay forma segura de detectar "sin cambios" -> se vuelve a bajar siempre
    assert D.sync_files(make(handler), raw, tmp_path, log=lambda m: None) == 1
    assert calls == ["/assets/ghi", "/assets/ghi"]


def test_create_update():
    def handler(req):
        body = json.loads(req.content)
        if req.method == "POST":
            assert req.url.path == "/items/builds"
            assert body == {"mode": "publish"}
            return httpx.Response(200, json={"data": {"id": 3, **body}})
        assert req.method == "PATCH"
        assert req.url.path == "/items/builds/3"
        assert body == {"status": "success"}
        return httpx.Response(200, json={"data": {"id": 3, **body}})

    dx = make(handler)
    assert dx.create("builds", {"mode": "publish"})["id"] == 3
    assert dx.update("builds", 3, {"status": "success"})["status"] == "success"
