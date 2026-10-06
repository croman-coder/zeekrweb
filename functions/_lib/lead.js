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
 *      Sucursal Ciudad del Este: si el formulario manda sucursal="cde", el lead va a los asesores de CDE
 *      (ZEEKR no tiene equipo propio en CDE: en producción CDE_ADVISOR_IDS="16001" = Mathias Acosta, del departamento 155
 *      "NUEVAS ENERGÍAS (LEAP, ZEEKR, XPENG, JMEV)", vendedor de Leap / Zeekr / JMEV / Xpeng en la sucursal multimarca y que ya está
 *      en la cola de ZEEKR de Bitrix. El 03/10/2026 se pasó de "todo al jefe" a "16001,19827" (con Pedro Ocampos); el 06/10/2026
 *      Bruno Capossela dejó a Pedro como vendedor exclusivo de Renault, así que quedó solo Mathias)
 *        CDE_ADVISOR_IDS="16001"        (opcional) pool explícito de CDE; sin esto: departamento CDE_DEPARTMENT_ID + cargo ASESOR
 *        CDE_DEPARTMENT_ID=133          "MULTIMARCAS CDE"
 *        CDE_FALLBACK_ASSIGNEE_ID=21707 Walter Bavera, Jefe de Ventas Multimarcas CDE: recibe el lead si ese equipo no tiene asesores activos
 *
 * Estadísticas: handle() recibe opcionalmente { stats } (functions/_lib/stats.js, solo en el servidor Node)
 * y cuenta un "lead" por cada lead creado en Bitrix. Sin stats (Cloudflare Pages) todo sigue igual.
 */
const SITE = "zeekrlife.com.py";
const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"];

const idList = (v) => String(v || "").split(",").map((s) => s.trim()).filter((s) => /^\d+$/.test(s)).map(Number);

/**
 * Zonas entre las que elige el visitante (formulario y WhatsApp): Asunción, Ciudad del Este y otras zonas. Sin dato → se trata como
 * Asunción (el comportamiento de siempre). Solo CDE tiene equipo propio: "otras" se reparte como Asunción (mismo equipo y misma cola),
 * igual que "resto del país" hasta el 06/10/2026 (pedido de Marketing, el mismo que en santarosa.com.py).
 */
const SUCURSALES = { asuncion: "Asunción", cde: "Ciudad del Este", otras: "Otras zonas" };
const CDE_ALIAS = new Set(["cde", "ciudad del este", "ciudad-del-este", "ciudad_del_este"]);
const OTRAS_ALIAS = new Set(["otras", "otras zonas", "otras-zonas", "otras_zonas"]);
function parseSucursal(v) {
  const s = String(v == null ? "" : v).trim().toLowerCase();
  if (!s) return null;
  if (CDE_ALIAS.has(s)) return "cde";
  if (OTRAS_ALIAS.has(s)) return "otras";
  return "asuncion"; // también lo que mandaba el sitio antes del 06/10/2026 ("asuncion" con el rótulo "Asunción y resto del país")
}

function cfg(env) {
  const webhook = String(env.BITRIX_WEBHOOK_URL || "").replace(/\/+$/, "") + "/";
  return {
    webhook,
    departmentId: Number(env.ZEEKR_DEPARTMENT_ID || 29),
    sourceId: env.LEAD_SOURCE_ID || "WEB_SR_ZEEKR",
    brandField: env.BRAND_FIELD || "UF_CRM_1775591500778",
    brandValue: Number(env.BRAND_VALUE || 301),
    fallbackAssignee: Number(env.FALLBACK_ASSIGNEE_ID || 73),
    advisorIds: idList(env.ADVISOR_IDS),
    cdeAdvisorIds: idList(env.CDE_ADVISOR_IDS),
    cdeDepartmentId: Number(env.CDE_DEPARTMENT_ID || 133),
    cdeFallbackAssignee: Number(env.CDE_FALLBACK_ASSIGNEE_ID || 21707),
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

/** Equipo que recibe los leads de una sucursal: ids explícitos o, sin ids, departamento + cargo "ASESOR". */
function poolOf(c, sucursal) {
  if (sucursal === "cde") {
    return {
      key: c.cdeAdvisorIds.length ? `cde-ids:${c.cdeAdvisorIds.join(",")}` : `cde-dep:${c.cdeDepartmentId}`,
      ids: c.cdeAdvisorIds, dep: c.cdeDepartmentId, fallback: c.cdeFallbackAssignee,
    };
  }
  return {
    key: c.advisorIds.length ? `ids:${c.advisorIds.join(",")}` : `dep:${c.departmentId}`,
    ids: c.advisorIds, dep: c.departmentId, fallback: c.fallbackAssignee,
  };
}

/* ---- asesores (cache 10 min por instancia y por equipo) ---- */
const advisorsCache = new Map(); // clave del pool → { at, list }
async function advisors(c, pool) {
  const hit = advisorsCache.get(pool.key);
  if (hit && hit.list.length && Date.now() - hit.at < 600000) return hit.list;
  let users;
  if (pool.ids.length) users = await b24(c, "user.get", { filter: { ID: pool.ids, ACTIVE: true } });
  else {
    users = await b24(c, "user.get", { filter: { UF_DEPARTMENT: pool.dep, ACTIVE: true } });
    users = users.filter((u) => String(u.WORK_POSITION || "").toUpperCase().includes("ASESOR"));
  }
  const list = users.map((u) => ({ id: Number(u.ID), name: `${u.NAME || ""} ${u.LAST_NAME || ""}`.trim() }));
  if (list.length) advisorsCache.set(pool.key, { at: Date.now(), list });
  return list;
}

/**
 * El asesor cuyo último lead web es el más antiguo (o que nunca recibió).
 * sucursal "cde" → equipo multimarca de Ciudad del Este; cualquier otra cosa → el de siempre (Asunción).
 */
export async function nextAdvisor(env, sucursal = null) {
  const c = cfg(env);
  const pool = poolOf(c, sucursal);
  const team = await advisors(c, pool);
  if (!team.length) return { id: pool.fallback, name: "" };
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
    sucursal: parseSucursal(str(b.sucursal, 40)), // "cde" | "asuncion" | "otras" | null (el formulario viejo no lo manda)
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

/** Solo para los tests: vacía el estado en memoria de la instancia (equipos cacheados y límite por IP). */
export function resetState() { advisorsCache.clear(); hits.clear(); }
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
  const cde = lead.sucursal === "cde";
  const advisor = await nextAdvisor(env, lead.sucursal);
  const parts = lead.nombre.split(/\s+/);
  const [first, last] = parts.length > 1 ? [parts[0], parts.slice(1).join(" ")] : [lead.nombre, ""];
  const notes = [`Solicitud: ${lead.tipo}`, `Modelo de interés: ${lead.modelo}`];
  if (lead.sucursal) notes.push(`Sucursal elegida: ${SUCURSALES[lead.sucursal]}`);
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
    STATUS_ID: "NEW", SOURCE_ID: c.sourceId, SOURCE_DESCRIPTION: `${SITE} · ${lead.tipo}${cde ? " · " + SUCURSALES.cde : ""}`,
    ASSIGNED_BY_ID: advisor.id, OPENED: "Y",
    PHONE: [{ VALUE: normalizePhone(lead.telefono), VALUE_TYPE: "MOBILE" }],
    COMMENTS: notes.join("\n"),
    [c.brandField]: c.brandValue,
  };
  if (cde) fields.ADDRESS_CITY = SUCURSALES.cde; // campo "Ciudad" del Prospecto: el equipo de CDE lo filtra en Bitrix
  if (lead.email) fields.EMAIL = [{ VALUE: lead.email, VALUE_TYPE: "WORK" }];
  for (const k of utms) fields[k.toUpperCase()] = lead[k];
  const leadId = await b24(c, "crm.lead.add", { fields, params: { REGISTER_SONET_EVENT: "Y" } });
  return { ok: true, leadId, asesor: advisor.name ? advisor.name.split(" ")[0].replace(/^(.)(.*)$/, (m, a, b) => a + b.toLowerCase()) : null, sucursal: lead.sucursal };
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
      console.log(`lead ${result.leadId} → ${result.asesor}${result.sucursal ? ` sucursal=${result.sucursal}` : ""} ip=${ip}`);
      try { if (stats) stats.lead(body); } catch (e) { console.error("estadísticas (lead):", e.message); }
    }
    return json(200, result);
  } catch (e) {
    console.error("lead error:", e.message);
    return json(e.status || 500, { ok: false, detail: e.status === 422 ? e.message : "No se pudo registrar el lead" });
  }
}
