# builder/app.py — API del builder (la llaman los Flows de Directus). Auth por X-Builder-Token.
import hmac
import traceback
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import build_runner
from .config import Settings
from .directus_client import Directus

settings = Settings()
LAST = {}


@asynccontextmanager
async def lifespan(_app):
    try:
        build_runner.reap_stale_builds(Directus(settings.directus_url, settings.directus_token))
    except Exception as e:  # noqa: BLE001 — si Directus todavía no está arriba, arrancar igual
        print(f"⚠ no se pudieron cerrar los builds colgados al arrancar ({e!r}); se reintenta en el próximo arranque", flush=True)
    yield


app = FastAPI(title="zeekr-builder", docs_url=None, redoc_url=None, lifespan=lifespan)


class Job(BaseModel):
    site_settings_id: int
    mode: str = "publish"
    user: str | None = None


def check(token):
    # lee el `settings` del módulo en cada llamada (Settings es frozen: los tests reemplazan el objeto entero).
    # La comparación va en bytes: compare_digest sobre str revienta con TypeError si el token no es ASCII.
    if not settings.builder_token or not hmac.compare_digest((token or "").encode(), settings.builder_token.encode()):
        raise HTTPException(401, "token inválido")


def _run(job):
    """El build corre en background: el Flow de Directus recibe el 202 al instante y no espera los minutos que tarde."""
    try:
        row = build_runner.run(job, settings) or {}
    except Exception as e:  # noqa: BLE001 — un build roto no puede tumbar el worker
        traceback.print_exc()
        row = {"status": "error", "mode": job.get("mode"), "log": str(e)}
    LAST.clear()             # sin esto un build con error mostraría la `release` del build exitoso anterior
    LAST.update(row)


@app.get("/health")
def health():
    return {"status": "ok", "last": {k: LAST.get(k) for k in ("id", "mode", "status", "release", "finished_at")}}


@app.post("/build", status_code=202)
def build(job: Job, tasks: BackgroundTasks, x_builder_token: str | None = Header(default=None)):
    check(x_builder_token)
    if job.mode not in ("preview", "publish"):
        raise HTTPException(400, "mode debe ser preview o publish")
    tasks.add_task(_run, job.model_dump())
    return {"queued": True, "mode": job.mode}


@app.post("/rollback", status_code=202)
def rollback(job: Job, tasks: BackgroundTasks, x_builder_token: str | None = Header(default=None)):
    check(x_builder_token)
    tasks.add_task(_run, {**job.model_dump(), "mode": "rollback"})
    return {"queued": True, "mode": "rollback"}
