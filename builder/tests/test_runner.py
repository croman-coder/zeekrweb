import json
import threading
import time
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from builder import build_runner as R
from builder import publish as P
from builder.config import Settings


class FakeDx:
    def __init__(self):
        self.rows = {}
        self.n = 0

    def create(self, coll, data):
        self.n += 1
        self.rows[self.n] = {"id": self.n, **data}
        return dict(self.rows[self.n])

    def update(self, coll, id_, data):
        self.rows[id_].update(data)
        return dict(self.rows[id_])


class LockedDx(FakeDx):
    """FakeDx usable desde varios hilos (el test del lock corre dos run() en paralelo)."""

    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()

    def create(self, coll, data):
        with self.lock:
            return super().create(coll, data)

    def update(self, coll, id_, data):
        with self.lock:
            return super().update(coll, id_, data)


def settings(tmp_path):
    repo = tmp_path / "repo"
    (repo / "css").mkdir(parents=True)
    (repo / "css" / "a.css").write_text("body{}")
    (repo / "build_site.py").write_text("")
    (repo / "i18n.py").write_text("TRANSLATIONS={}")
    return Settings(directus_url="http://x", directus_token="t", builder_token="b", anthropic_api_key="", sites_root=str(tmp_path / "sites"), repo_dir=str(repo), keep_releases=3)


def patch_steps(monkeypatch, fail=False):
    monkeypatch.setattr(R, "fetch_site", lambda dx, i: ({"id": 1, "slug": "zeekr", "domain": "https://zeekrlife.com.py", "preview_host": "https://preview-zeekr.santarosa.lat"}, {"id": i}))
    monkeypatch.setattr(R, "fetch_content", lambda dx, sid, drafts: {"drafts": drafts})
    monkeypatch.setattr(R, "sync_files", lambda dx, raw, ws, log: 0)
    monkeypatch.setattr(R, "build_content", lambda raw: {"site": {"slug": "zeekr"}, "_warnings": ["aviso"], "drafts": raw["drafts"]})

    def generate(ws, content, log):
        if fail:
            raise RuntimeError("build_site.py falló")
        Path(ws, "index.html").write_text("drafts=%s" % content["drafts"])
    monkeypatch.setattr(R, "generate", generate)


def test_publish_then_preview_then_rollback(tmp_path, monkeypatch):
    s, dx = settings(tmp_path), FakeDx()
    patch_steps(monkeypatch)
    row = R.run({"site_settings_id": 1, "mode": "publish", "user": "u1"}, s, dx=dx, log=R.Log())
    assert row["status"] == "success" and row["release"] and "aviso" in row["log"] and row["preview_url"] == "https://zeekrlife.com.py"
    cur = P.target(Path(s.sites_root) / "zeekr" / "current")
    assert (cur / "index.html").read_text() == "drafts=False" and (cur / "css" / "a.css").exists()
    row = R.run({"site_settings_id": 1, "mode": "preview"}, s, dx=dx, log=R.Log())
    assert row["status"] == "success" and row["release"].endswith("-preview") and row["preview_url"] == "https://preview-zeekr.santarosa.lat"
    assert (P.target(Path(s.sites_root) / "zeekr" / "preview") / "index.html").read_text() == "drafts=True"
    assert P.target(Path(s.sites_root) / "zeekr" / "current") == cur                 # preview no toca producción
    R.run({"site_settings_id": 1, "mode": "publish"}, s, dx=dx, log=R.Log())
    row = R.run({"site_settings_id": 1, "mode": "rollback"}, s, dx=dx, log=R.Log())
    assert row["status"] == "success" and P.target(Path(s.sites_root) / "zeekr" / "current") == cur
    assert json.loads((cur.parent / f"{cur.name}.content.json").read_text())["site"]["slug"] == "zeekr"   # snapshot del contenido


def test_error_keeps_previous_release(tmp_path, monkeypatch):
    s, dx = settings(tmp_path), FakeDx()
    patch_steps(monkeypatch)
    R.run({"site_settings_id": 1, "mode": "publish"}, s, dx=dx, log=R.Log())
    cur = P.target(Path(s.sites_root) / "zeekr" / "current")
    patch_steps(monkeypatch, fail=True)
    row = R.run({"site_settings_id": 1, "mode": "publish"}, s, dx=dx, log=R.Log())
    assert row["status"] == "error" and "build_site.py falló" in row["log"]
    assert P.target(Path(s.sites_root) / "zeekr" / "current") == cur


def test_without_anthropic_key_the_build_publishes_in_spanish_with_a_warning(tmp_path, monkeypatch):
    # Producción arranca sin ANTHROPIC_API_KEY: el build no puede fallar ni intentar llamar a Claude;
    # deja el aviso en el log y lo que no esté traducido sale en español (fallback de `_()` del generador).
    s, dx = settings(tmp_path), FakeDx()
    patch_steps(monkeypatch)

    def no_translation(*a, **k):
        raise AssertionError("sin clave no se tiene que traducir")
    monkeypatch.setattr(R, "sync_translations", no_translation)
    monkeypatch.setattr(R, "Claude", no_translation)
    row = R.run({"site_settings_id": 1, "mode": "publish"}, s, dx=dx, log=R.Log())
    assert row["status"] == "success" and row["release"]
    assert "sin ANTHROPIC_API_KEY: no se traduce (donde falte se usa español)" in row["log"]


def test_rollback_without_previous_is_error(tmp_path, monkeypatch):
    s, dx = settings(tmp_path), FakeDx()
    patch_steps(monkeypatch)
    row = R.run({"site_settings_id": 1, "mode": "rollback"}, s, dx=dx, log=R.Log())
    assert row["status"] == "error" and "anterior" in row["log"]


def test_a_previewed_draft_page_never_reaches_the_published_release(tmp_path, monkeypatch):
    """Agujero real: con un workspace único, previsualizar un borrador dejaba su HTML ahí y el siguiente
    publish lo rsynceaba al dominio real. Preview y publish tienen que usar workspaces separados."""
    s, dx = settings(tmp_path), FakeDx()
    patch_steps(monkeypatch)

    def generate(ws, content, log):
        Path(ws, "index.html").write_text("ok")
        if content["drafts"]:                                   # el modelo en borrador solo existe en preview
            Path(ws, "modelos", "zeekr-9x").mkdir(parents=True, exist_ok=True)
            Path(ws, "modelos", "zeekr-9x", "index.html").write_text("BORRADOR 9X")
    monkeypatch.setattr(R, "generate", generate)

    R.run({"site_settings_id": 1, "mode": "preview"}, s, dx=dx, log=R.Log())
    prev = P.target(Path(s.sites_root) / "zeekr" / "preview")
    assert (prev / "modelos" / "zeekr-9x" / "index.html").exists()      # en la preview sí tiene que estar
    row = R.run({"site_settings_id": 1, "mode": "publish"}, s, dx=dx, log=R.Log())
    cur = P.target(Path(s.sites_root) / "zeekr" / "current")
    assert row["status"] == "success"
    assert not (cur / "modelos" / "zeekr-9x").exists(), "el borrador previsualizado se publicó"


def test_preview_and_publish_use_separate_workspaces(tmp_path, monkeypatch):
    s, dx = settings(tmp_path), FakeDx()
    patch_steps(monkeypatch)
    seen = []
    monkeypatch.setattr(R, "generate", lambda ws, content, log: (seen.append(str(ws)), Path(ws, "index.html").write_text("x")))
    R.run({"site_settings_id": 1, "mode": "publish"}, s, dx=dx, log=R.Log())
    R.run({"site_settings_id": 1, "mode": "preview"}, s, dx=dx, log=R.Log())
    base = Path(s.sites_root) / "zeekr" / "workspace"
    assert seen == [str(base / "publish"), str(base / "preview")]


def test_unknown_mode_is_a_failed_build(tmp_path, monkeypatch):
    s, dx = settings(tmp_path), FakeDx()
    patch_steps(monkeypatch)
    row = R.run({"site_settings_id": 1, "mode": "loco"}, s, dx=dx, log=R.Log())
    assert row["status"] == "error" and "loco" in row["log"]
    assert not (Path(s.sites_root) / "zeekr" / "current").exists()


def test_site_without_slug_is_a_failed_build(tmp_path, monkeypatch):
    """Si el m2o `site` viene en null, fetch_site devuelve site=None: tiene que quedar fila, no reventar."""
    s, dx = settings(tmp_path), FakeDx()
    monkeypatch.setattr(R, "fetch_site", lambda dx_, i: (None, {"id": i}))
    row = R.run({"site_settings_id": 1, "mode": "publish"}, s, dx=dx, log=R.Log())
    assert row["status"] == "error" and row["site"] is None and "configuración del sitio" in row["log"]


def test_reap_stale_builds_closes_rows_left_running(tmp_path):
    dx = FakeDx()
    dx.create("builds", {"status": "running", "mode": "publish"})
    dx.create("builds", {"status": "queued", "mode": "preview"})
    dx.create("builds", {"status": "success", "mode": "publish"})
    dx.items = lambda coll, **p: [dict(r) for r in dx.rows.values() if r["status"] in ("queued", "running")]
    assert R.reap_stale_builds(dx, log=lambda m: None) == 2
    assert [r["status"] for r in dx.rows.values()] == ["error", "error", "success"]
    assert "reinició" in dx.rows[1]["log"]


def test_api_auth_and_queue(monkeypatch):
    from builder import app as A
    monkeypatch.setattr(A, "settings", Settings(builder_token="secreto"))
    ran = []
    monkeypatch.setattr(A.build_runner, "run", lambda job, settings: ran.append(job) or {"status": "success"})
    c = TestClient(A.app)
    assert c.get("/health").json()["status"] == "ok"
    assert c.post("/build", json={"site_settings_id": 1, "mode": "publish"}).status_code == 401
    assert c.post("/build", json={"site_settings_id": 1, "mode": "publish"}, headers={"X-Builder-Token": "malo"}).status_code == 401
    assert c.post("/build", json={"site_settings_id": 1, "mode": "loco"}, headers={"X-Builder-Token": "secreto"}).status_code == 400
    r = c.post("/build", json={"site_settings_id": 1, "mode": "preview", "user": "abc"}, headers={"X-Builder-Token": "secreto"})
    assert r.status_code == 202 and ran[-1] == {"site_settings_id": 1, "mode": "preview", "user": "abc"}
    r = c.post("/rollback", json={"site_settings_id": 1}, headers={"X-Builder-Token": "secreto"})
    assert r.status_code == 202 and ran[-1]["mode"] == "rollback"


def test_api_rejects_everything_when_builder_token_is_empty(monkeypatch):
    """Sin BUILDER_TOKEN configurado la API no puede quedar abierta."""
    from builder import app as A
    monkeypatch.setattr(A, "settings", Settings(builder_token=""))
    c = TestClient(A.app)
    assert c.post("/build", json={"site_settings_id": 1, "mode": "publish"}).status_code == 401
    assert c.post("/build", json={"site_settings_id": 1, "mode": "publish"}, headers={"X-Builder-Token": ""}).status_code == 401
    assert c.post("/rollback", json={"site_settings_id": 1}, headers={"X-Builder-Token": "lo-que-sea"}).status_code == 401


def test_non_ascii_builder_token_gives_401_and_not_500(monkeypatch):
    """Si alguien configura BUILDER_TOKEN con acentos, hmac.compare_digest sobre str levanta TypeError y
    la API contesta 500 a todo. Comparando en bytes contesta 401, que es lo correcto."""
    from builder import app as A
    monkeypatch.setattr(A, "settings", Settings(builder_token="contraseña"))
    c = TestClient(A.app)
    assert c.post("/build", json={"site_settings_id": 1, "mode": "publish"}, headers={"X-Builder-Token": "otra"}).status_code == 401
    with pytest.raises(HTTPException):          # nunca TypeError
        A.check("otra")
    A.check("contraseña")                       # el token correcto pasa (los headers HTTP no viajan con no-ASCII)


def test_health_does_not_mix_data_from_the_previous_build(monkeypatch):
    from builder import app as A
    monkeypatch.setattr(A, "settings", Settings(builder_token="secreto"))
    monkeypatch.setattr(A.build_runner, "run", lambda job, settings: {"id": 1, "mode": "publish", "status": "success", "release": "20260101-000000", "finished_at": "x"})
    c = TestClient(A.app)
    c.post("/build", json={"site_settings_id": 1, "mode": "publish"}, headers={"X-Builder-Token": "secreto"})
    assert c.get("/health").json()["last"]["release"] == "20260101-000000"
    monkeypatch.setattr(A.build_runner, "run", lambda job, settings: {"id": 2, "mode": "publish", "status": "error", "finished_at": "y"})
    c.post("/build", json={"site_settings_id": 1, "mode": "publish"}, headers={"X-Builder-Token": "secreto"})
    last = c.get("/health").json()["last"]
    assert last["status"] == "error" and last["release"] is None      # no arrastra la release del build anterior


# ── errores heredados de las tareas 5-6: el runner los deja en la fila `builds`, no revienta ──────────────

@pytest.mark.parametrize("exc", [
    LookupError("site_settings 99 no existe"),
    httpx.HTTPStatusError("403", request=httpx.Request("GET", "http://x/items/site_settings/99"), response=httpx.Response(403)),
])
def test_fetch_site_error_is_a_failed_build(tmp_path, monkeypatch, exc):
    """Directus 11 devuelve 403 (no 404) para un id que no existe: fetch_site puede levantar HTTPStatusError o LookupError."""
    s, dx = settings(tmp_path), FakeDx()

    def boom(_dx, _i):
        raise exc
    monkeypatch.setattr(R, "fetch_site", boom)
    row = R.run({"site_settings_id": 99, "mode": "publish", "user": "u1"}, s, dx=dx, log=R.Log())
    assert row["status"] == "error" and row["site"] is None and row["mode"] == "publish"
    assert "99" in row["log"] and "configuración del sitio" in row["log"]


def test_draft_site_settings_message_reaches_the_build_log(tmp_path, monkeypatch):
    """El mensaje de fetch_content llega tal cual al log: es lo único que ve el editor en el panel."""
    s, dx = settings(tmp_path), FakeDx()
    patch_steps(monkeypatch)
    msg = "La configuración del sitio está en borrador: publicala (estado = Publicado) para poder publicar el sitio"

    def boom(_dx, _sid, drafts):
        raise LookupError(msg)
    monkeypatch.setattr(R, "fetch_content", boom)
    row = R.run({"site_settings_id": 1, "mode": "publish"}, s, dx=dx, log=R.Log())
    assert row["status"] == "error" and msg in row["log"]


def test_missing_phones_value_error_is_a_failed_build(tmp_path, monkeypatch):
    """transform.build_content levanta ValueError si faltan teléfonos."""
    s, dx = settings(tmp_path), FakeDx()
    patch_steps(monkeypatch)

    def boom(_raw):
        raise ValueError("site_settings sin teléfonos")
    monkeypatch.setattr(R, "build_content", boom)
    row = R.run({"site_settings_id": 1, "mode": "publish"}, s, dx=dx, log=R.Log())
    assert row["status"] == "error" and "sin teléfonos" in row["log"]


# ── lock por sitio ────────────────────────────────────────────────────────────────────────────────────────

def _patch_multisite(monkeypatch, generate):
    slugs = {1: "zeekr", 2: "otro"}
    monkeypatch.setattr(R, "fetch_site", lambda dx, i: ({"id": i, "slug": slugs[i], "domain": "https://d", "preview_host": "https://p"}, {"id": i}))
    monkeypatch.setattr(R, "fetch_content", lambda dx, sid, drafts: {"drafts": drafts})
    monkeypatch.setattr(R, "sync_files", lambda dx, raw, ws, log: 0)
    monkeypatch.setattr(R, "build_content", lambda raw: {"site": {}, "_warnings": []})
    monkeypatch.setattr(R, "generate", generate)


def _run_both(jobs, s, dx):
    rows = {}

    def go(i, job):
        rows[i] = R.run(job, s, dx=dx, log=R.Log())
    ts = [threading.Thread(target=go, args=(i, j)) for i, j in enumerate(jobs)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(30)
    assert not any(t.is_alive() for t in ts), "los builds no terminaron (¿deadlock?)"
    return [rows[i] for i in range(len(jobs))]


def test_lock_serializes_preview_and_publish_of_the_same_site(tmp_path, monkeypatch):
    """El lock es por slug y no por modo: new_release borra los stagings .tmp-* del sitio al empezar y
    preview/publish comparten el workspace, así que dos builds del mismo sitio no pueden solaparse."""
    s, dx = settings(tmp_path), LockedDx()
    inside, peak, guard = [], [], threading.Lock()

    def generate(ws, content, log):
        with guard:
            inside.append(ws)
            peak.append(len(inside))
        time.sleep(0.3)
        Path(ws, "index.html").write_text("x")
        with guard:
            inside.remove(ws)
    _patch_multisite(monkeypatch, generate)

    rows = _run_both([{"site_settings_id": 1, "mode": "publish"}, {"site_settings_id": 1, "mode": "preview"}], s, dx)
    assert [r["status"] for r in rows] == ["success", "success"]
    assert max(peak) == 1, f"dos builds del mismo sitio se solaparon (peak={peak})"


def test_lock_does_not_serialize_different_sites(tmp_path, monkeypatch):
    s, dx = settings(tmp_path), LockedDx()
    barrier = threading.Barrier(2, timeout=10)

    def generate(ws, content, log):
        barrier.wait()          # si el lock fuera global, el segundo build nunca llega y esto revienta
        Path(ws, "index.html").write_text("x")
    _patch_multisite(monkeypatch, generate)

    rows = _run_both([{"site_settings_id": 1, "mode": "publish"}, {"site_settings_id": 2, "mode": "publish"}], s, dx)
    assert [r["status"] for r in rows] == ["success", "success"]


def test_prune_also_removes_the_content_snapshots(tmp_path, monkeypatch):
    s, dx = settings(tmp_path), FakeDx()          # keep_releases=3
    patch_steps(monkeypatch)
    for _ in range(4):
        R.run({"site_settings_id": 1, "mode": "publish"}, s, dx=dx, log=R.Log())
    rel = Path(s.sites_root) / "zeekr" / "releases"
    dirs = sorted(p.name for p in rel.iterdir() if p.is_dir())
    snaps = sorted(p.name[: -len(".content.json")] for p in rel.glob("*.content.json"))
    assert len(dirs) == 3 and dirs == snaps       # no quedan snapshots huérfanos de releases borradas
