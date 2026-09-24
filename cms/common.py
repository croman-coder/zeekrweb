# cms/common.py — cliente REST mínimo para los scripts de setup (token de admin por env)
import json
import os
import sys
import urllib.error
import urllib.request

URL = os.environ.get("DIRECTUS_URL", "https://admin.santarosa.lat").rstrip("/")
TOKEN = os.environ.get("DIRECTUS_ADMIN_TOKEN") or sys.exit("falta DIRECTUS_ADMIN_TOKEN")


def api(method, path, body=None, ok404=False, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    # User-Agent propio: el panel de producción (zeekrlife.com.py/cms) está detrás de Cloudflare y su
    # Browser Integrity Check rechaza el "Python-urllib/x" por defecto (HTTP 403, error code 1010).
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "zeekr-cms-setup/1.0"}
    if os.environ.get("CF_ACCESS_CLIENT_ID"):  # si admin.santarosa.lat está detrás de Cloudflare Access (service token)
        headers |= {"CF-Access-Client-Id": os.environ["CF_ACCESS_CLIENT_ID"], "CF-Access-Client-Secret": os.environ["CF_ACCESS_CLIENT_SECRET"]}
    req = urllib.request.Request(f"{URL}{path}", method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = r.read()
            if raw:
                return out
            return json.loads(out)["data"] if out else None
    except urllib.error.HTTPError as e:
        # Directus 11 devuelve 403 (no 404) en /collections|/fields|/relations/<id>
        # cuando el recurso no existe, incluso con token de Administrator: la
        # verificación de existencia por policy corre antes que la de existencia
        # real. Por eso ok404 también absorbe 403 en estos lookups puntuales.
        if e.code in (404, 403) and ok404:
            return None
        raise SystemExit(f"{method} {path} → HTTP {e.code}: {e.read().decode()[:400]}")


def exists(path):
    return api("GET", path, ok404=True) is not None
