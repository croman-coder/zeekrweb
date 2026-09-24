# scripts/normalize_cms_paths.py — reemplaza en el HTML generado desde Directus las rutas images/cms/<id> por las rutas originales del repo (cms/seed_map.json)
import json
import os
import sys

ws, map_path = sys.argv[1], sys.argv[2]
seed_map = json.load(open(map_path))
subs = []
for orig, fid in seed_map.items():
    rel = orig[len("images/"):] if orig.startswith("images/") else orig
    base, ext = os.path.splitext(rel)
    subs.append((f"/images/_opt/cms/{fid}-", f"/images/_opt/{base}-"))
    subs.append((f"/images/cms/{fid}{ext}", f"/{orig}"))
n = 0
for root, _d, files in os.walk(ws):
    if "/images" in root or "/css" in root or "/js" in root or "/fonts" in root:
        continue
    for f in files:
        if not f.endswith((".html", ".xml", ".txt", ".webmanifest")):
            continue
        p = os.path.join(root, f)
        s = open(p, encoding="utf-8").read()
        t = s
        for a, b in subs:
            t = t.replace(a, b)
        if t != s:
            open(p, "w", encoding="utf-8").write(t)
            n += 1
print("normalizados:", n)
