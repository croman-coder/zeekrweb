# builder/directus_client.py — acceso a Directus (REST): contenido, archivos, builds y traducciones.
import json
from pathlib import Path

import httpx

from .transform import file_path

MODEL_FIELDS = ("*,translations.*,hero_image.*,hero_image_mobile.*,card_image.*,menu_image.*,pdf.*,versions.*,versions.translations.*,"
                "sections.*,sections.translations.*,sections.image.*,sections.video.*,sections.gallery.*,sections.gallery.file.*")


class Directus:
    def __init__(self, url, token, timeout=120, transport=None):
        self.http = httpx.Client(base_url=url.rstrip("/"), headers={"Authorization": f"Bearer {token}"}, timeout=timeout, transport=transport)

    def get(self, path, **params):
        r = self.http.get(path, params=params)
        r.raise_for_status()
        return r.json().get("data")

    def items(self, coll, **params):
        return self.get(f"/items/{coll}", limit=-1, **params) or []

    def create(self, coll, data):
        r = self.http.post(f"/items/{coll}", json=data)
        r.raise_for_status()
        return r.json()["data"]

    def update(self, coll, id_, data):
        r = self.http.patch(f"/items/{coll}/{id_}", json=data)
        r.raise_for_status()
        return r.json()["data"]

    def download(self, file_id, dest):
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        with self.http.stream("GET", f"/assets/{file_id}", params={"download": ""}) as r:
            r.raise_for_status()
            with open(tmp, "wb") as fh:
                for chunk in r.iter_bytes(1 << 20):
                    fh.write(chunk)
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
    st = dx.items("site_settings", fields="*,translations.*", filter=json.dumps({"site": {"_eq": site_id}}))
    if not st:
        raise LookupError("el sitio no tiene site_settings")
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
    """Baja a <workspace>/images/cms/ los originales que faltan (o cambiaron de tamaño). Devuelve cuántos bajó."""
    n, seen = 0, set()
    for f in iter_files(raw):
        rel = file_path(f)
        if rel in seen:
            continue
        seen.add(rel)
        dest = Path(workspace) / rel
        size = int(f.get("filesize") or 0)
        if dest.exists() and (size == 0 or dest.stat().st_size == size):
            continue
        dx.download(f["id"], dest)
        n += 1
        log(f"  ↓ {f.get('filename_download')} → {rel}")
    return n
