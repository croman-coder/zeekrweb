# cms/setup_insights.py — tablero "Estadísticas — Zeekr" (módulo Insights) sobre site_stats. Idempotente:
# el tablero se busca por nombre y cada panel por (tablero, nombre); si existe se reescriben tipo, lugar y opciones.
# Los paneles que se agreguen a mano en el panel no se tocan.
# Uso: DIRECTUS_ADMIN_TOKEN=... [STATS_SITE=zeekr] python3 cms/setup_insights.py
#
# Rangos: `day` es tipo date y Directus compara "AAAA-MM-DD" contra $NOW(-N days) ("AAAA-MM-DDThh:mm…") como texto,
# así que day >= $NOW(-7 days) toma los últimos 7 días calendario contando hoy (probado en 11.17.4).
# $NOW es UTC: entre las 21:00 y las 24:00 de Asunción el rango corre un día (irrelevante para tendencias).
import os
from urllib.parse import quote
from common import api

SITE_SLUG = os.environ.get("STATS_SITE", "zeekr")
NAME = "Estadísticas — Zeekr"
sites = api("GET", f"/items/sites?filter[slug][_eq]={quote(SITE_SLUG)}&fields=id&limit=1")
if not sites:
    raise SystemExit(f"no existe el sitio {SITE_SLUG} (correr setup_schema.py)")
SITE = sites[0]["id"]


def where(kind, days=None, *extra):
    """Filtro del panel: sitio + tipo (+ últimos N días calendario, contando hoy). Insights consulta por GraphQL,
    donde un m2o se filtra por el campo del relacionado ({"site": {"id": …}}); {"site": {"_eq": …}} da 400."""
    cond = [{"site": {"id": {"_eq": SITE}}}, {"kind": {"_eq": kind}}]
    if days:
        cond.append({"day": {"_gte": f"$NOW(-{days} days)"}})
    return {"_and": cond + list(extra)}


def metric(kind, days, suffix=""):
    return {"collection": "site_stats", "field": "count", "function": "sum", "filter": where(kind, days),
            "numberStyle": "decimal", "notation": "standard", "maximumFractionDigits": 0, "suffix": suffix, "textAlign": "center"}


def series(kind, color):
    # el panel agrega él mismo day ∈ [$NOW(-30 days), $NOW] (opción range)
    return {"collection": "site_stats", "function": "sum", "valueField": "count", "dateField": "day", "precision": "day",
            "range": "30 days", "filter": where(kind), "missingData": "0", "min": 0, "decimals": 0, "color": color,
            "curveType": "smooth", "fillType": "gradient"}


def bars(kind, color):
    # barras por día: con pocos datos (leads) se ven mejor que una línea, que con un solo día es apenas un punto
    return {"collection": "site_stats", "xAxis": "day", "yAxis": "count", "function": "sum", "filter": where(kind, 30),
            "decimals": 0, "color": color, "showDataLabel": True, "showAxisLabels": "both", "horizontal": False}


def top(kind, *extra):
    return {"collection": "site_stats", "groupByField": "path", "aggregateField": "count", "aggregateFunction": "sum",
            "sortDirection": "desc", "limit": 10, "filter": where(kind, 30, *extra), "maximumFractionDigits": 0}


MODELOS = ({"path": {"_starts_with": "/modelos/"}}, {"path": {"_neq": "/modelos/"}})
# (nombre, tipo, x, y, ancho, alto, ícono, nota, opciones) — grilla de Insights (~20 px por unidad). 40 de ancho: entra
# en una notebook con las dos barras laterales abiertas.
PANELS = [
    ("Visitas · 7 días", "metric", 1, 1, 20, 5, "visibility", "Páginas vistas en zeekrlife.com.py, últimos 7 días (con hoy)", metric("view", 7)),
    ("Visitas · 30 días", "metric", 21, 1, 20, 5, "visibility", "Páginas vistas, últimos 30 días", metric("view", 30)),
    ("Formularios enviados · 30 días", "metric", 1, 6, 20, 5, "contact_mail", "Leads creados en Bitrix desde el formulario del sitio, últimos 30 días", metric("lead", 30)),
    ("Clics a WhatsApp · 30 días", "metric", 21, 6, 20, 5, "chat", "Clics en enlaces a WhatsApp del sitio, últimos 30 días", metric("whatsapp", 30)),
    ("Visitas por día", "time-series", 1, 11, 40, 14, "show_chart", "Páginas vistas por día (hora de Asunción), últimos 30 días", series("view", "#2F80ED")),
    ("Páginas más vistas · 30 días", "metric-list", 1, 25, 20, 34, "leaderboard", "Top 10 por ruta; cada ruta suma sus 4 idiomas (/en/models/… cuenta en /modelos/…)", top("view")),
    ("Modelos más vistos · 30 días", "metric-list", 21, 25, 20, 14, "directions_car", "Fichas de modelo más vistas (4 idiomas juntos)", top("view", *MODELOS)),
    ("Formularios por día", "bar-chart", 21, 39, 20, 20, "bar_chart", "Leads del formulario por día, últimos 30 días (solo los días con leads)", bars("lead", "#27AE60")),
]

found = api("GET", f"/dashboards?filter[name][_eq]={quote(NAME)}&fields=id&limit=1")
dash = found[0]["id"] if found else api("POST", "/dashboards", {
    "name": NAME, "icon": "insights", "color": "#2F80ED",
    "note": "Contador propio de zeekrlife.com.py (sin cookies ni datos personales). Se actualiza cada minuto."})["id"]
print(("=" if found else "+"), NAME, dash)
existing = {p["name"]: p["id"] for p in api("GET", f"/panels?filter[dashboard][_eq]={dash}&fields=id,name&limit=-1")}
for name, typ, x, y, w, h, icon, note, options in PANELS:
    body = {"dashboard": dash, "name": name, "type": typ, "position_x": x, "position_y": y, "width": w, "height": h,
            "icon": icon, "note": note, "show_header": True, "options": options}
    if name in existing:
        api("PATCH", f"/panels/{existing[name]}", body)
        print("  =", name)
    else:
        api("POST", "/panels", body)
        print("  +", name)
extra = sorted(set(existing) - {p[0] for p in PANELS})
if extra:
    print("  (paneles agregados a mano, no se tocan:", ", ".join(extra) + ")")
print("OK insights")
