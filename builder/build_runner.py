# builder/build_runner.py — un build de punta a punta (bajar → traducir → transformar → generar → publicar), con lock por sitio.
import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import httpx

from . import publish
from .config import Settings
from .directus_client import Directus, fetch_content, fetch_site, sync_files
from .transform import build_content
from .translate import Claude, sync_translations

MODES = ("preview", "publish", "rollback")
SOURCE_DIRS = ("css", "js", "fonts", "icons", "images")
SOURCE_FILES = ("build_site.py", "i18n.py")

# Un lock por slug, no por modo: preview y publish del mismo sitio comparten el workspace y, además,
# new_release() borra al empezar los stagings `.tmp-*` huérfanos de ESE sitio — dos builds del mismo
# sitio en paralelo se pisarían el workspace y el staging del otro. Sitios distintos sí corren a la vez.
_LOCKS, _LOCKS_GUARD = {}, threading.Lock()


def site_lock(slug):
    with _LOCKS_GUARD:                       # crear el lock también tiene que ser atómico entre hilos
        return _LOCKS.setdefault(slug, threading.Lock())


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Log:
    def __init__(self):
        self.lines = []

    def __call__(self, msg):
        self.lines.append(f"{time.strftime('%H:%M:%S')} {msg}")
        print(msg, flush=True)

    def text(self):
        return "\n".join(self.lines)[-60000:]


def prepare_workspace(repo_dir, ws):
    """Copia generador y assets del repo al workspace sin borrar lo propio del workspace (images/cms, images/_opt, HTML)."""
    ws = Path(ws)
    ws.mkdir(parents=True, exist_ok=True)
    for name in SOURCE_FILES:
        shutil.copy2(Path(repo_dir) / name, ws / name)
    for d in SOURCE_DIRS:
        src = Path(repo_dir) / d
        if src.exists():
            subprocess.run(["rsync", "-a", "--exclude=_opt/", "--exclude=cms/", f"{src}/", f"{ws / d}/"], check=True)


def generate(ws, content, log):
    ws = Path(ws)
    (ws / "content.json").write_text(json.dumps(content, ensure_ascii=False, indent=1))
    p = subprocess.run([sys.executable, "build_site.py", "--content", "content.json"], cwd=ws, capture_output=True, text=True, timeout=900)
    if p.stdout.strip():
        log(p.stdout.strip()[-4000:])
    if p.returncode != 0:
        raise RuntimeError("build_site.py falló:\n" + (p.stderr or "")[-4000:])


def _build(settings, dx, site, mode, claude, log):
    # Un workspace por modo: el árbol es acumulativo (el generador no borra lo que ya no genera salvo en
    # su cleanup), así que con un workspace compartido una página en borrador previsualizada terminaba
    # rsyncheada dentro de la siguiente publicación. `rollback` no usa workspace.
    ws = Path(settings.sites_root) / site["slug"] / "workspace" / mode
    log(f"preparando workspace ({mode})")
    prepare_workspace(settings.repo_dir, ws)
    log("bajando contenido")
    raw = fetch_content(dx, site["id"], drafts=(mode == "preview"))
    log(f"archivos nuevos: {sync_files(dx, raw, ws, log)}")
    if claude or settings.anthropic_api_key:
        sync_translations(dx, raw, claude or Claude(settings.anthropic_api_key), log)
    else:
        log("⚠ sin ANTHROPIC_API_KEY: no se traduce (donde falte se usa español)")
    content = build_content(raw)
    for w in content.get("_warnings", []):
        log("⚠ " + w)
    log("generando sitio")
    generate(ws, content, log)
    return ws, content


def _snapshot(rel, content):
    """Guarda al lado de la release el content.json con el que se generó (para depurar qué se publicó)."""
    (rel.parent / f"{rel.name}.content.json").write_text(json.dumps(content, ensure_ascii=False))


def _prune(settings, slug):
    removed = publish.prune(settings.sites_root, slug, keep=settings.keep_releases)
    for p in removed:                        # el snapshot vive fuera del directorio de la release: hay que borrarlo aparte
        (p.parent / f"{p.name}.content.json").unlink(missing_ok=True)
    return removed


def run(job, settings, dx=None, claude=None, log=None):
    """job = {"site_settings_id": int, "mode": "preview"|"publish"|"rollback", "user": str|None}. Devuelve la fila `builds` final."""
    log = log or Log()
    dx = dx or Directus(settings.directus_url, settings.directus_token)
    mode, user, sid = job.get("mode"), job.get("user") or "", job["site_settings_id"]
    try:
        site, _st = fetch_site(dx, sid)
        slug = site["slug"]      # si el m2o `site` vino en null, site es None: también es un error de build
    except (LookupError, httpx.HTTPError, TypeError, KeyError) as e:
        # Directus 11 responde 403 (no 404) cuando el id no existe o el token no lo alcanza → puede ser HTTPStatusError.
        log(f"ERROR no se pudo leer la configuración del sitio #{sid}: {e!r}")
        return dx.create("builds", {"site": None, "mode": mode, "status": "error", "requested_by": user,
                                    "started_at": now(), "finished_at": now(), "log": log.text()})
    build = dx.create("builds", {"site": site["id"], "mode": mode, "status": "queued", "requested_by": user, "started_at": now()})
    with site_lock(slug):
        dx.update("builds", build["id"], {"status": "running"})
        try:
            if mode not in MODES:
                raise ValueError(f"modo desconocido: {mode!r}")
            if mode == "rollback":
                prev = publish.previous_release(settings.sites_root, slug)
                if not prev:
                    raise RuntimeError("No hay una versión anterior a la que volver")
                publish.switch(settings.sites_root, slug, "current", prev)
                log(f"current → {prev.name}")
                result = {"release": prev.name, "preview_url": site.get("domain")}
            else:
                ws, content = _build(settings, dx, site, mode, claude, log)
                rel = publish.new_release(settings.sites_root, slug, ws, kind=mode)
                _snapshot(rel, content)
                link = "current" if mode == "publish" else "preview"
                publish.switch(settings.sites_root, slug, link, rel)
                log(f"{link} → {rel.name}; releases limpiadas: {len(_prune(settings, slug))}")
                result = {"release": rel.name, "preview_url": site.get("preview_host") if mode == "preview" else site.get("domain")}
            return dx.update("builds", build["id"], {"status": "success", "finished_at": now(), "log": log.text(), **result})
        except Exception as e:  # noqa: BLE001 — cualquier error deja la release anterior intacta
            log("ERROR " + "".join(traceback.format_exception_only(type(e), e)).strip())
            return dx.update("builds", build["id"], {"status": "error", "finished_at": now(), "log": log.text()})


STALE_MSG = ("El builder se reinició mientras este build estaba en curso, así que quedó a medias y no se "
             "publicó nada. El sitio sigue en la versión anterior: volvé a intentar.")


def reap_stale_builds(dx, log=print):
    """Al arrancar: una fila en `queued`/`running` es de un proceso que murió (deploy, reinicio, OOM).
    Nadie la va a terminar nunca, así que se cierra como error para que el editor no vea un spinner eterno."""
    stale = dx.items("builds", fields="id,mode", filter=json.dumps({"status": {"_in": ["queued", "running"]}}))
    for b in stale:
        dx.update("builds", b["id"], {"status": "error", "finished_at": now(), "log": STALE_MSG})
    if stale:
        log(f"builds que quedaron colgados de un reinicio y se cerraron como error: {[b['id'] for b in stale]}")
    return len(stale)


def dry_run(settings, site_settings_id, mode):
    """Genera en el workspace sin traducir, publicar ni registrar (paridad y depuración local)."""
    log = Log()
    dx = Directus(settings.directus_url, settings.directus_token)
    site, _st = fetch_site(dx, site_settings_id)
    ws, content = _build(settings, dx, site, mode, None, log)
    log(f"OK dry-run en {ws}")
    return ws, content


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-settings", type=int, default=1)
    ap.add_argument("--mode", choices=list(MODES), default="publish")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    s = Settings()
    if a.dry_run:
        dry_run(s, a.site_settings, a.mode)
    else:
        print(json.dumps(run({"site_settings_id": a.site_settings, "mode": a.mode, "user": "cli"}, s), ensure_ascii=False, indent=1))
