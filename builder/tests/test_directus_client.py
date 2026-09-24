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


def test_sync_files_prunes_files_no_longer_referenced(tmp_path):
    """Un original borrado del CMS no puede seguir vivo en images/cms/ (ni arrastrado a cada release)."""
    def handler(req):
        return httpx.Response(200, content=b"12345")

    f = {"id": "abc", "filename_download": "a.jpg", "filesize": 5}
    raw = {"models": [{"hero_image": f}]}
    D.sync_files(make(handler), raw, tmp_path, log=lambda m: None)
    viejo = tmp_path / "images/cms/zzz.jpg"                      # de una corrida anterior, ya no referenciado
    viejo.write_bytes(b"viejo")
    (tmp_path / "images/cms/sub").mkdir()                        # una carpeta no es un original suelto: no se toca
    msgs = []
    assert D.sync_files(make(handler), raw, tmp_path, log=msgs.append) == 0
    assert (tmp_path / "images/cms/abc.jpg").exists() and not viejo.exists()
    assert (tmp_path / "images/cms/sub").is_dir()
    assert any("zzz.jpg" in m for m in msgs)


def test_sync_files_without_images_cms_dir_does_not_fail(tmp_path):
    assert D.sync_files(make(lambda req: httpx.Response(200, content=b"")), {"models": []}, tmp_path, log=lambda m: None) == 0


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


# ---- límite de pedidos de Directus (RATE_LIMITER_*: en producción 50 pedidos por segundo por IP) ----
# El builder habla con Directus por la red interna: bajar ~75 originales seguidos supera el límite y Directus
# responde 429. Eso no puede tumbar el build (ni dejar la fila de `builds` en `running` porque el PATCH final
# también rebotó): se espera lo que pide `Retry-After` (o un backoff) y se reintenta.

def limited(ok, fails=2, retry_after="1"):
    """Handler que responde 429 las primeras `fails` veces para cada (método, ruta) y después delega en `ok`."""
    seen = {}

    def handler(req):
        k = (req.method, req.url.path)
        seen[k] = seen.get(k, 0) + 1
        if seen[k] <= fails:
            return httpx.Response(429, headers={"Retry-After": retry_after} if retry_after is not None else {},
                                  json={"errors": [{"message": "Too many requests"}]})
        return ok(req)
    return handler, seen


def make_limited(handler, sleeps):
    return D.Directus("https://cms.test", "tok", transport=httpx.MockTransport(handler), sleep=sleeps.append)


def test_429_on_get_create_update_is_retried_honoring_retry_after():
    def ok(req):
        return httpx.Response(200, json={"data": {"id": 1}})
    handler, seen = limited(ok, fails=2, retry_after="1")
    sleeps = []
    dx = make_limited(handler, sleeps)
    assert dx.get("/items/sites/1") == {"id": 1}
    assert dx.create("builds", {"mode": "publish"}) == {"id": 1}
    assert dx.update("builds", 1, {"status": "error"}) == {"id": 1}
    assert seen == {("GET", "/items/sites/1"): 3, ("POST", "/items/builds"): 3, ("PATCH", "/items/builds/1"): 3}
    assert len(sleeps) == 6 and all(s >= 1 for s in sleeps)


def test_429_on_download_is_retried_and_writes_the_file(tmp_path):
    handler, seen = limited(lambda req: httpx.Response(200, content=b"12345"), fails=3, retry_after=None)
    sleeps = []
    f = {"id": "abc", "filename_download": "a.jpg", "filesize": 5}
    assert D.sync_files(make_limited(handler, sleeps), {"models": [{"hero_image": f}]}, tmp_path, log=lambda m: None) == 1
    assert (tmp_path / "images/cms/abc.jpg").read_bytes() == b"12345"
    assert not (tmp_path / "images/cms/abc.jpg.part").exists()
    assert seen[("GET", "/assets/abc")] == 4
    assert len(sleeps) == 3 and all(s > 0 for s in sleeps)          # sin Retry-After: backoff creciente, nunca 0
    assert sleeps == sorted(sleeps)


def test_429_forever_ends_in_http_error_without_sleeping_forever():
    handler, seen = limited(lambda req: httpx.Response(200, json={"data": {}}), fails=10**6, retry_after="0")
    sleeps = []
    with pytest.raises(httpx.HTTPStatusError) as e:
        make_limited(handler, sleeps).get("/items/sites/1")
    assert e.value.response.status_code == 429
    assert seen[("GET", "/items/sites/1")] == D.MAX_RETRIES + 1
    assert sum(sleeps) <= 60                                          # acotado: un Directus caído no cuelga el build
