# cms/setup_roles.py — roles/políticas/permisos + usuario de servicio del builder. Idempotente.
# Uso: DIRECTUS_ADMIN_TOKEN=... BUILDER_STATIC_TOKEN=<openssl rand -hex 32> python3 cms/setup_roles.py
import os
from common import api

SITE = {"site": {"_eq": "$CURRENT_USER.site"}}
CONTENT = ["site_settings", "hero_slides", "models", "news"]                     # colecciones con campo site
CHILD_FILTER = {                                                                 # hijos: filtro vía padre
    "model_sections": {"model": SITE}, "model_versions": {"model": SITE},
    "section_gallery": {"section": {"model": SITE}}, "news_gallery": {"news": SITE},
}
TR_FILTER = {                                                                    # traducciones: filtro vía ítem
    "site_settings_translations": {"site_settings_id": SITE}, "hero_slides_translations": {"hero_slides_id": SITE},
    "models_translations": {"models_id": SITE}, "news_translations": {"news_id": SITE},
    "model_sections_translations": {"model_sections_id": {"model": SITE}}, "model_versions_translations": {"model_versions_id": {"model": SITE}},
}
ACTIONS = ["create", "read", "update", "delete"]


def ensure_policy(name, **kw):
    found = api("GET", f"/policies?filter[name][_eq]={name}&limit=1")
    return found[0] if found else api("POST", "/policies", {"name": name, "icon": "badge", "app_access": True, "admin_access": False, "enforce_tfa": False, **kw})


def ensure_role(name, policy_id, icon):
    found = api("GET", f"/roles?filter[name][_eq]={name}&limit=1")
    role = found[0] if found else api("POST", "/roles", {"name": name, "icon": icon})
    if not api("GET", f"/access?filter[role][_eq]={role['id']}&filter[policy][_eq]={policy_id}&limit=1"):
        api("POST", "/access", {"role": role["id"], "policy": policy_id})
    return role


def perm(policy, collection, action, filt=None, fields="*", presets=None):
    body = {"policy": policy, "collection": collection, "action": action, "permissions": filt or {}, "validation": {}, "presets": presets or {},
            "fields": [fields] if isinstance(fields, str) else fields}
    found = api("GET", f"/permissions?filter[policy][_eq]={policy}&filter[collection][_eq]={collection}&filter[action][_eq]={action}&limit=1")
    if found:
        api("PATCH", f"/permissions/{found[0]['id']}", body)
    else:
        api("POST", "/permissions", body)


# ---- Editor: solo su sitio
ed = ensure_policy("Editor")
ensure_role("Editor", ed["id"], "edit")
for c in CONTENT:
    for a in ACTIONS:
        # create no filtra (el ítem aún no existe): el preset fija site = el del usuario
        perm(ed["id"], c, a, None if a == "create" else SITE, presets={"site": "$CURRENT_USER.site"} if a == "create" else None)
for c, filt in {**CHILD_FILTER, **TR_FILTER}.items():
    for a in ACTIONS:
        perm(ed["id"], c, a, None if a == "create" else filt)
perm(ed["id"], "builds", "read", SITE)
perm(ed["id"], "sites", "read", {"id": {"_eq": "$CURRENT_USER.site"}})
perm(ed["id"], "languages", "read")
perm(ed["id"], "translation_meta", "read")
for a in ["create", "read", "update"]:
    perm(ed["id"], "directus_files", a)
perm(ed["id"], "directus_folders", "read")
perm(ed["id"], "directus_users", "read", {"id": {"_eq": "$CURRENT_USER"}})
perm(ed["id"], "directus_users", "update", {"id": {"_eq": "$CURRENT_USER"}},
     fields=["first_name", "last_name", "avatar", "password", "language", "theme_light", "theme_dark", "tfa_secret", "email_notifications"])
perm(ed["id"], "directus_flows", "read")          # ver los botones
perm(ed["id"], "directus_revisions", "read")      # historial de cambios
perm(ed["id"], "directus_activity", "read")

# ---- Builder (servicio): lee todo el contenido, escribe builds, traducciones y translation_meta
bp = ensure_policy("Builder", app_access=False)
brole = ensure_role("Builder", bp["id"], "smart_toy")
for c in CONTENT + list(CHILD_FILTER) + list(TR_FILTER) + ["builds", "sites", "languages", "directus_files", "directus_folders", "translation_meta"]:
    perm(bp["id"], c, "read")
for c in ["builds", "translation_meta"] + list(TR_FILTER):
    for a in ["create", "update"]:
        perm(bp["id"], c, a)
for c in ["section_gallery", "news_gallery"]:
    perm(bp["id"], c, "update", fields=["alt_en", "alt_pt", "alt_zh"])
tok = os.environ.get("BUILDER_STATIC_TOKEN") or exit("falta BUILDER_STATIC_TOKEN")
u = api("GET", "/users?filter[email][_eq]=builder@santarosa.com.py&limit=1")
if u:
    api("PATCH", f"/users/{u[0]['id']}", {"token": tok, "role": brole["id"], "status": "active"})
else:
    api("POST", "/users", {"email": "builder@santarosa.com.py", "first_name": "Builder", "role": brole["id"], "token": tok, "status": "active"})
print("OK roles: Editor, Builder; usuario builder@santarosa.com.py con token")
