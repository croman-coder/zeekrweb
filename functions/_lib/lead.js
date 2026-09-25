/**
 * Lead web → Bitrix24 (ZEEKR Paraguay). Código compartido por:
 *   - functions/api/lead.js  (Cloudflare Pages Function, edge)
 *   - api/server.mjs         (Node en Coolify)
 *
 * Crea un Prospecto con origen "ZEEKR Web Santa Rosa" y lo asigna al asesor de ventas del
 * departamento 05. ZEEKR que hace más tiempo no recibe un lead web (cola justa, sin estado).
 *
 * env: BITRIX_WEBHOOK_URL (obligatoria) · ZEEKR_DEPARTMENT_ID=29 · LEAD_SOURCE_ID=WEB_SR_ZEEKR
 *      BRAND_FIELD=UF_CRM_1775591500778 · BRAND_VALUE=301 · FALLBACK_ASSIGNEE_ID=73 · ADVISOR_IDS="139,2171"
 *
 * Estadísticas: handle() recibe opcionalmente { stats } (functions/_lib/stats.js, solo en el servidor Node)
 * y cuenta un "lead" por cada lead creado en Bitrix. Sin stats (Cloudflare Pages) todo sigue igual.
 */
const SITE = "zeekrlife.com.py";
const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"];

function cfg(env) {
  const webhook = String(env.BITRIX_WEBHOOK_URL || "").replace(/\/+$/, "") + "/";
  return {
    webhook,
    departmentId: Number(env.ZEEKR_DEPARTMENT_ID || 29),
    sourceId: env.LEAD_SOURCE_ID || "WEB_SR_ZEEKR",
    brandField: env.BRAND_FIELD || "UF_CRM_1775591500778",
    brandValue: Number(env.BRAND_VALUE || 301),
    fallbackAssignee: Number(env.FALLBACK_ASSIGNEE_ID || 73),
    advisorIds: String(env.ADVISOR_IDS || "").split(",").map((s) => s.trim()).filter((s) => /^\d+$/.test(s)).map(Number),
  };
}

export class LeadError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

async function b24(c, method, params) {
  if (!c.webhook.startsWith("http")) throw new LeadError(503, "Bitrix no configurado");
  const res = await fetch(`${c.webhook}${method}.json`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params || {}),
  });
  const data = await res.json();
  if (data.error) throw new LeadError(502, `Bitrix ${method}: ${data.error} ${data.error_description || ""}`);
  return data.result;
}

/* ---- asesores (cache 10 min por instancia) ---- */
let advisorsCache = { at: 0, list: [] };
async function advisors(c) {
  if (advisorsCache.list.length && Date.now() - advisorsCache.at < 600000) return advisorsCache.list;
  let users;
  if (c.advisorIds.length) users = await b24(c, "user.get", { filter: { ID: c.advisorIds, ACTIVE: true } });
  else {
    users = await b24(c, "user.get", { filter: { UF_DEPARTMENT: c.departmentId, ACTIVE: true } });
    users = users.filter((u) => String(u.WORK_POSITION || "").toUpperCase().includes("ASESOR"));
  }
  const list = users.map((u) => ({ id: Number(u.ID), name: `${u.NAME || ""} ${u.LAST_NAME || ""}`.trim() }));
  if (list.length) advisorsCache = { at: Date.now(), list };
  return list;
}

/** El asesor cuyo último lead web es el más antiguo (o que nunca recibió). */
export async function nextAdvisor(env) {
  const c = cfg(env);
  const team = await advisors(c);
  if (!team.length) return { id: c.fallbackAssignee, name: "" };
  const ids = new Set(team.map((a) => a.id));
  const recent = await b24(c, "crm.lead.list", {
    filter: { SOURCE_ID: c.sourceId }, order: { ID: "DESC" }, select: ["ID", "ASSIGNED_BY_ID"], start: 0,
  });
  const lastSeen = new Map(); // id → posición (0 = más reciente)
  recent.forEach((l, pos) => { const uid = Number(l.ASSIGNED_BY_ID || 0); if (ids.has(uid) && !lastSeen.has(uid)) lastSeen.set(uid, pos); });
  const never = team.filter((a) => !lastSeen.has(a.id)).sort((a, b) => a.id - b.id);
  if (never.length) return never[0];
  return team.reduce((best, a) => (lastSeen.get(a.id) > lastSeen.get(best.id) ? a : best), team[0]);
}

/* ---- validación / normalización ---- */
export function normalizePhone(raw) {
  const s = String(raw || "").trim();
  const digits = s.replace(/\D/g, "");
  if (s.startsWith("+")) return "+" + digits;
  if (digits.startsWith("595")) return "+" + digits;
  if (digits.startsWith("0") && (digits.length === 10 || digits.length === 9)) return "+595" + digits.slice(1);
  return s;
}

export function validate(body) {
  const b = body && typeof body === "object" ? body : {};
  const str = (v, max) => (v == null ? "" : String(v)).trim().slice(0, max);
  const lead = {
    nombre: str(b.nombre, 120), telefono: str(b.telefono, 40), email: str(b.email, 120) || null,
    modelo: str(b.modelo, 60) || "Aún no lo sé", mensaje: str(b.mensaje, 1500) || null, pagina: str(b.pagina, 300) || null,
    tipo: ["Consulta", "Prueba de manejo"].includes(str(b.tipo, 40)) ? str(b.tipo, 40) : "Prueba de manejo",
    idioma: str(b.idioma, 10).toLowerCase().slice(0, 2) || "es",
    website: str(b.website, 200),
  };
  for (const k of UTM_KEYS) { const v = str(b[k], 160); if (v) lead[k] = v; }
  const errors = [];
  if (lead.nombre.length < 2) errors.push("nombre");
  if (lead.telefono.replace(/\D/g, "").length < 6) errors.push("telefono");
  if (lead.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(lead.email)) errors.push("email");
  if (errors.length) throw new LeadError(422, "Datos inválidos: " + errors.join(", "));
  return lead;
}

/* ---- rate limit simple en memoria (por instancia) ---- */
const hits = new Map();
export function rateLimited(ip, limit = 8, windowMs = 600000) {
  const now = Date.now();
  const q = (hits.get(ip) || []).filter((t) => now - t < windowMs);
  if (q.length >= limit) { hits.set(ip, q); return true; }
  q.push(now); hits.set(ip, q);
  return false;
}

/** Crea el lead. Devuelve {ok, leadId, asesor}. */
export async function createLead(body, env) {
  const c = cfg(env);
  const lead = validate(body);
  if (lead.website) return { ok: true, leadId: null }; // honeypot
  const advisor = await nextAdvisor(env);
  const parts = lead.nombre.split(/\s+/);
  const [first, last] = parts.length > 1 ? [parts[0], parts.slice(1).join(" ")] : [lead.nombre, ""];
  const notes = [`Solicitud: ${lead.tipo}`, `Modelo de interés: ${lead.modelo}`];
  if (lead.mensaje) notes.push(`Mensaje: ${lead.mensaje}`);
  if (lead.pagina) notes.push(`Página: ${lead.pagina}`);
  const LANG_NAMES = { es: "Español", en: "English", pt: "Português", zh: "中文" };
  if (lead.idioma && lead.idioma !== "es") notes.push(`Idioma del cliente: ${LANG_NAMES[lead.idioma] || lead.idioma}`);
  const utms = UTM_KEYS.filter((k) => lead[k]);
  if (utms.length) notes.push("UTM: " + utms.map((k) => `${k.slice(4)}=${lead[k]}`).join(", "));
  notes.push(`Origen: ${SITE} · ${new Date().toLocaleString("es-PY", { timeZone: "America/Asuncion" })}`);
  const fields = {
    TITLE: `${lead.nombre} - ${lead.modelo} - ${lead.tipo} - ZEEKR Web Santa Rosa`,
    NAME: first, LAST_NAME: last,
    STATUS_ID: "NEW", SOURCE_ID: c.sourceId, SOURCE_DESCRIPTION: `${SITE} · ${lead.tipo}`,
    ASSIGNED_BY_ID: advisor.id, OPENED: "Y",
    PHONE: [{ VALUE: normalizePhone(lead.telefono), VALUE_TYPE: "MOBILE" }],
    COMMENTS: notes.join("\n"),
    [c.brandField]: c.brandValue,
  };
  if (lead.email) fields.EMAIL = [{ VALUE: lead.email, VALUE_TYPE: "WORK" }];
  for (const k of utms) fields[k.toUpperCase()] = lead[k];
  const leadId = await b24(c, "crm.lead.add", { fields, params: { REGISTER_SONET_EVENT: "Y" } });
  return { ok: true, leadId, asesor: advisor.name ? advisor.name.split(" ")[0].replace(/^(.)(.*)$/, (m, a, b) => a + b.toLowerCase()) : null };
}

/** Manejador HTTP común (Request → Response, estándar Fetch). ctx.stats: contador opcional (stats.js). */
export async function handle(request, env, { stats } = {}) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "");
  const json = (status, obj) => new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
  if (request.method === "GET" && /\/health$/.test(path)) return json(200, { ok: true, source: cfg(env).sourceId, configured: cfg(env).webhook.startsWith("http") });
  if (request.method !== "POST") return json(405, { ok: false, detail: "Método no permitido" });
  const ip = request.headers.get("cf-connecting-ip") || (request.headers.get("x-forwarded-for") || "").split(",")[0].trim() || "?";
  if (rateLimited(ip)) return json(429, { ok: false, detail: "Demasiados envíos. Probá de nuevo en unos minutos." });
  let body;
  try { body = await request.json(); } catch { return json(400, { ok: false, detail: "JSON inválido" }); }
  try {
    const result = await createLead(body, env);
    if (result.leadId) {
      console.log(`lead ${result.leadId} → ${result.asesor} ip=${ip}`);
      try { if (stats) stats.lead(body); } catch (e) { console.error("estadísticas (lead):", e.message); }
    }
    return json(200, result);
  } catch (e) {
    console.error("lead error:", e.message);
    return json(e.status || 500, { ok: false, detail: e.status === 422 ? e.message : "No se pudo registrar el lead" });
  }
}
