# cms/setup_flows.py — Flows: bloqueo de dominio + botones de publicación. Idempotente por nombre.
# Uso: DIRECTUS_ADMIN_TOKEN=... [BUILDER_URL=http://zeekr-builder:8000] python3 cms/setup_flows.py
import os
from urllib.parse import quote
from common import api

BUILDER_URL = os.environ.get("BUILDER_URL")
DOMAIN_JS = r"""module.exports = async function(data) {
  const p = data.$trigger.payload || {};
  if (p.email && !/@santarosa\.com\.py$/i.test(String(p.email).trim())) {
    throw new Error('Solo se permiten correos @santarosa.com.py');
  }
  return p;
}"""


def upsert_flow(name, trigger, options, ops, icon, description):
    """Crea el flow con su cadena de operaciones; si existe, re-sincroniza sus campos, actualiza las
    operaciones ya presentes (por key) y crea + encadena las que falten, preservando el orden de `ops`."""
    found = api("GET", f"/flows?filter[name][_eq]={quote(name)}&fields=id,operation,operations.id,operations.key&limit=1")
    if found:
        flow_id = found[0]["id"]
        # re-sincroniza los campos del flow (antes solo se tocaban al crearlo)
        api("PATCH", f"/flows/{flow_id}", {"icon": icon, "description": description, "status": "active",
                                            "trigger": trigger, "accountability": "all", "options": options})
        keys = {o["key"]: o["id"] for o in found[0].get("operations", [])}
        prev = None
        for key, typ, opts in ops:
            if key in keys:
                api("PATCH", f"/operations/{keys[key]}", {"options": opts})
                cur = keys[key]
            else:
                # falta esta operación (ej.: se agregó una nueva al final de `ops`) — crearla y encadenarla
                cur = api("POST", "/operations", {"flow": flow_id, "key": key, "type": typ, "options": opts,
                                                   "position_x": 19 + len(keys) * 20, "position_y": 1})["id"]
                keys[key] = cur
                if prev:
                    api("PATCH", f"/operations/{prev}", {"resolve": cur})
                else:
                    api("PATCH", f"/flows/{flow_id}", {"operation": cur})
            prev = cur
        print("  =", name)
        return
    flow = api("POST", "/flows", {"name": name, "icon": icon, "description": description, "status": "active", "trigger": trigger, "accountability": "all", "options": options})
    prev = None
    for i, (key, typ, opts) in enumerate(ops):
        op = api("POST", "/operations", {"flow": flow["id"], "key": key, "type": typ, "options": opts, "position_x": 19 + i * 20, "position_y": 1})
        if prev:
            api("PATCH", f"/operations/{prev}", {"resolve": op["id"]})
        else:
            api("PATCH", f"/flows/{flow['id']}", {"operation": op["id"]})
        prev = op["id"]
    print("  +", name)


upsert_flow("Solo correos @santarosa.com.py", "event", {"type": "filter", "scope": ["items.create", "items.update"], "collections": ["directus_users"]},
            [("check", "exec", {"code": DOMAIN_JS})], "verified_user", "Rechaza altas/ediciones de usuarios con otro dominio")

if BUILDER_URL:
    def request_op(path, mode):
        return ("call_builder", "request", {
            "method": "POST", "url": f"{BUILDER_URL.rstrip('/')}{path}",
            "headers": [{"header": "Content-Type", "value": "application/json"}, {"header": "X-Builder-Token", "value": "{{$env.BUILDER_TOKEN}}"}],
            "body": '{"site_settings_id": {{$trigger.body.keys[0]}}, "mode": "' + mode + '", "user": "{{$accountability.user}}"}'})

    for name, mode, path, icon, desc, confirm in [
        ("Vista previa", "preview", "/build", "visibility", "Genera el sitio con borradores en el host de vista previa",
         "Se generará la vista previa con TODO (borradores incluidos). Tarda ~1 minuto; el resultado queda en Builds."),
        ("Publicar", "publish", "/build", "rocket_launch", "Publica en producción solo lo marcado como Publicado",
         "Se publicará en el sitio público lo que esté en estado Publicado. ¿Continuar?"),
        ("Volver a la versión anterior", "rollback", "/rollback", "history", "Restaura la release publicada anterior",
         "Se restaurará la versión publicada anterior. ¿Continuar?")]:
        upsert_flow(name, "manual", {"collections": ["site_settings"], "async": False, "requireSelection": True, "requireConfirmation": True,
                                     "confirmationDescription": confirm, "location": "item"}, [request_op(path, mode)], icon, desc)
else:
    print("  (sin BUILDER_URL: no se crean los botones; correr de nuevo en Task 11)")
print("OK flows")
