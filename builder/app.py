# builder/app.py — API del builder (la llaman los Flows de Directus). Auth por X-Builder-Token.
import hmac
import traceback

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import build_runner
from .config import Settings

settings = Settings()
app = FastAPI(title="zeekr-builder", docs_url=None, redoc_url=None)
LAST = {}


class Job(BaseModel):
    site_settings_id: int
    mode: str = "publish"
    user: str | None = None


def check(token):
    # lee el `settings` del módulo en cada llamada (Settings es frozen: los tests reemplazan el objeto entero)
    if not settings.builder_token or not hmac.compare_digest(token or "", settings.builder_token):
        raise HTTPException(401, "token inválido")


def _run(job):
    """El build corre en background: el Flow de Directus recibe el 202 al instante y no espera los minutos que tarde."""
    try:
        LAST.update(build_runner.run(job, settings) or {})
    except Exception as e:  # noqa: BLE001 — un build roto no puede tumbar el worker
        traceback.print_exc()
        LAST.update({"status": "error", "mode": job.get("mode"), "release": None, "log": str(e)})


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
