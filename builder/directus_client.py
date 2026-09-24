# builder/directus_client.py — acceso a Directus (REST): contenido, archivos, builds y traducciones.
import json
import time
from pathlib import Path

import httpx

from .transform import file_path

# Directus limita los pedidos por IP (RATE_LIMITER_*; en producción 50 por segundo). Por la red interna el
# builder los supera fácil —bajar ~75 originales seguidos— y recibe 429. En vez de fallar el build se espera
# lo que pide `Retry-After` (o un backoff creciente si no viene o viene en 0) y se reintenta, con tope.
MAX_RETRIES = 8
MAX_WAIT = 10.0

MODEL_FIELDS = ("*,translations.*,hero_image.*,hero_image_mobile.*,card_image.*,menu_image.*,pdf.*,versions.*,versions.translations.*,"
                "sections.*,sections.translations.*,sections.image.*,sections.video.*,sections.gallery.*,sections.gallery.file.*")


class Directus:
    def __init__(self, url, token, timeout=120, transport=None, sleep=time.sleep):
        self.http = httpx.Client(base_url=url.rstrip("/"), headers={"Authorization": f"Bearer {token}"}, timeout=timeout, transport=transport)
        self.sleep = sleep                   # inyectable: los tests no esperan de verdad

    @staticmethod
    def _wait(r, attempt):
        """Segundos a esperar tras un 429: Retry-After si es útil; si no, 0.5, 1, 2, 4… (tope MAX_WAIT)."""
        try:
            retry_after = float(r.headers.get("retry-after") or 0)
        except ValueError:                   # Retry-After también puede venir como fecha HTTP: se ignora
            retry_after = 0
        return min(max(retry_after, 0.5 * 2 ** attempt), MAX_WAIT)

    def _request(self, method, path, **kw):
        for attempt in range(MAX_RETRIES + 1):
            r = self.http.request(method, path, **kw)
            if r.status_code != 429 or attempt == MAX_RETRIES:
                r.raise_for_status()
                return r
            self.sleep(self._wait(r, attempt))

    def get(self, path, **params):
        return self._request("GET", path, params=params).json().get("data")

    def items(self, coll, **params):
        return self.get(f"/items/{coll}", limit=-1, **params) or []

    def create(self, coll, data):
        return self._request("POST", f"/items/{coll}", json=data).json()["data"]

    def update(self, coll, id_, data):
        return self._request("PATCH", f"/items/{coll}/{id_}", json=data).json()["data"]

    def download(self, file_id, dest):
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        for attempt in range(MAX_RETRIES + 1):
            with self.http.stream("GET", f"/assets/{file_id}", params={"download": ""}) as r:
                if r.status_code == 429 and attempt < MAX_RETRIES:
                    wait = self._wait(r, attempt)
                else:
                    r.raise_for_status()
                    with open(tmp, "wb") as fh:
                        for chunk in r.iter_bytes(1 << 20):
                            fh.write(chunk)
                    break
            self.sleep(wait)                 # fuera del `with`: la conexión ya se devolvió al pool
        tmp.replace(dest)


def status_filter(drafts):
    return {"status": {"_in": ["draft", "published"]}} if drafts else {"status": {"_eq": "published"}}


def fetch_site(dx, site_settings_id):
    st = dx.get(f"/items/site_settings/{site_settings_id}", fields="*,site.*")
    if not st:
        raise LookupError(f"site_settings {site_settings_id} no existe")
    site = st.pop("site")
    return site, st


def fetch_content(dx, site_id, drafts):
    def f(extra):
        return json.dumps({"_and": [{"site": {"_eq": site_id}}, extra]})

    site = dx.get(f"/items/sites/{site_id}")
    st = dx.items("site_settings", fields="*,translations.*", filter=f(status_filter(drafts)), sort="id")
    if not st:
        any_st = dx.items("site_settings", fields="id", filter=json.dumps({"site": {"_eq": site_id}}))
        if any_st:
            raise LookupError("La configuración del sitio está en borrador: publicala (estado = Publicado) para poder publicar el sitio")
        raise LookupError("el sitio no tiene site_settings")
    if len(st) > 1:
        print(f"⚠ hay {len(st)} filas de configuración para este sitio; se usó la de id {st[0]['id']}")
    return {"site": site, "settings": st[0],
            "hero_slides": dx.items("hero_slides", fields="*,translations.*,image_desktop.*,image_mobile.*", filter=f(status_filter(drafts)), sort="sort"),
            "models": dx.items("models", fields=MODEL_FIELDS, filter=f(status_filter(drafts)), sort="sort"),
            "news": dx.items("news", fields="*,translations.*,cover.*,gallery.*,gallery.file.*", filter=f(status_filter(drafts)), sort="-date")}


def iter_files(obj):
    """Recorre el árbol y devuelve los dicts de archivo (tienen id + filename_download)."""
    if isinstance(obj, dict):
        if obj.get("id") and "filename_download" in obj:
            yield obj
        for v in obj.values():
            yield from iter_files(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_files(v)


def sync_files(dx, raw, workspace, log=print):
    """Baja a <workspace>/images/cms/ los originales que faltan (o cambiaron de tamaño) y borra los que el
    contenido de esta corrida ya no referencia. Devuelve cuántos bajó."""
    n, seen = 0, set()
    for f in iter_files(raw):
        rel = file_path(f)
        if rel in seen:
            continue
        seen.add(rel)
        dest = Path(workspace) / rel
        size = int(f.get("filesize") or 0)
        if size and dest.exists() and dest.stat().st_size == size:
            continue
        dx.download(f["id"], dest)
        n += 1
        log(f"  ↓ {f.get('filename_download')} → {rel}")
    prune_files(workspace, seen, log)
    return n


def prune_files(workspace, keep, log=print):
    """Borra de images/cms/ los originales que ya no están en el contenido: si no, un archivo borrado del
    CMS sigue descargable en el dominio y se arrastra a todas las releases siguientes."""
    cms = Path(workspace) / "images" / "cms"
    if not cms.is_dir():
        return []
    removed = []
    for p in sorted(cms.iterdir()):
        if p.is_file() and p.suffix != ".part" and f"images/cms/{p.name}" not in keep:
            p.unlink()
            removed.append(p.name)
            log(f"  ✗ ya no está en el CMS: images/cms/{p.name}")
    return removed
