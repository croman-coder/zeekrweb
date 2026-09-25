/**
 * API de conversiones de Meta (CAPI): el mismo Lead que manda el píxel del navegador, pero desde el servidor,
 * cuando Bitrix confirma que creó el prospecto. Lo llama lead.js (Node en Coolify y Cloudflare Pages).
 *
 * El formulario (js/main.js) manda en el POST `meta: {event_id, fbp, fbc, event_source_url, consentimiento}`.
 * El event_id es el mismo del Lead del píxel: Meta ve los dos y cuenta uno solo (deduplicación).
 *
 * env: META_CAPI_TOKEN (obligatoria: sin ella no se manda nada) · META_PIXEL_ID (opcional, pisa la constante
 *      de abajo) · META_TEST_EVENT_CODE (opcional: los eventos caen en "Probar eventos" del Administrador de eventos)
 *
 * No manda nada si el visitante no aceptó las cookies (consentimiento "rechazado"), si es un bot, si el formulario
 * se envió desde otro host (alias, vista previa, localhost) o si falta el token o el píxel. Nunca cambia la
 * respuesta del formulario: atrapa todo y deja una línea de log sin datos personales.
 */
// Dataset "Zeekr Paraguay" (cuenta publicitaria Zeekr Paraguay). Mismo ID y mismos hosts que js/head.js
// (api/meta-capi.test.mjs verifica que coincidan).
export const META_PIXEL_ID = "1384147742910671";
export const META_HOSTS = ["zeekrlife.com.py"];
export const GRAPH_VERSION = "v21.0";
const HOME = `https://${META_HOSTS[0]}/`;
const TIMEOUT_MS = 3000;
const EVENT_ID_RE = /^[A-Za-z0-9_.:-]{1,100}$/;
const FB_COOKIE_RE = /^fb\.\d\.\d+\.[A-Za-z0-9_.\-]+$/;
const IP_RE = /^[0-9A-Fa-f:.]{3,45}$/;
const BOT_RE = /bot|crawl|spider|slurp|headless|lighthouse/i;

/** Teléfono para Meta: solo dígitos con código de país (Paraguay por defecto). "" si no queda nada. */
export function normalizarTelefono(raw) {
  let d = String(raw ?? "").replace(/\D/g, "");
  if (d.startsWith("00")) d = d.slice(2);                       // 00595… / 0054… (prefijo internacional)
  if (d.startsWith("595")) return d;
  if (d.startsWith("0")) { d = d.replace(/^0+/, ""); return d ? "595" + d : ""; }   // 0981…, 021…
  if (d.length === 9) return "595" + d;                          // 981123456
  return d;                                                      // otro país, ya con su código
}

/** SHA-256 en hexadecimal (Web Crypto: está en Node ≥ 20 y en Cloudflare). */
export async function sha256(texto) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(texto)));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Lo que manda el navegador se valida; lo que no cumple se descarta sin avisar (null). */
export function eventIdValido(v) {
  return typeof v === "string" && EVENT_ID_RE.test(v) ? v : null;
}
export function cookieFbValida(v) {
  return typeof v === "string" && v.length <= 300 && FB_COOKIE_RE.test(v) ? v : null;
}

function hostDe(raw) {
  if (typeof raw !== "string" || !raw) return null;
  try { return new URL(raw).hostname; } catch { return null; }
}

/** La URL si es https en un host del sitio; si no, null. */
export function urlDelSitio(raw) {
  if (typeof raw !== "string" || raw.length > 2000) return null;
  try {
    const u = new URL(raw);
    return u.protocol === "https:" && META_HOSTS.includes(u.hostname) ? u.href : null;
  } catch { return null; }
}

/** IP del visitante. Detrás de Cloudflare, cf-connecting-ip es la confiable (la misma que usa lead.js). */
export function ipDelCliente(headers) {
  for (const k of ["cf-connecting-ip", "x-forwarded-for", "x-nf-client-connection-ip", "x-real-ip"]) {
    const ip = (headers.get(k) || "").split(",")[0].trim();
    if (IP_RE.test(ip)) return ip;
  }
  return null;
}

/**
 * Evento Lead para la API de conversiones. lead = el lead validado por lead.js (nombre, telefono, email, tipo);
 * meta = el objeto `meta` que manda el navegador. Omite toda clave sin valor (nunca manda hashes de "").
 */
export async function armarEventoLead({ lead, meta, headers, ahora = Date.now(), nuevoId = () => crypto.randomUUID() }) {
  const m = meta && typeof meta === "object" ? meta : {};
  const partes = String(lead.nombre || "").trim().toLowerCase().split(/\s+/).filter(Boolean);
  const email = String(lead.email || "").trim().toLowerCase();
  const tel = normalizarTelefono(lead.telefono);
  const user = {};
  if (email) user.em = [await sha256(email)];
  if (tel) user.ph = [await sha256(tel)];
  if (partes.length) user.fn = [await sha256(partes[0])];                   // solo hay "Nombre y apellido":
  if (partes.length > 1) user.ln = [await sha256(partes.slice(1).join(" "))]; // la 1.ª palabra y el resto
  user.country = [await sha256("py")];
  const ip = ipDelCliente(headers);
  if (ip) user.client_ip_address = ip;
  const ua = headers.get("user-agent");
  if (ua) user.client_user_agent = ua;
  const fbp = cookieFbValida(m.fbp);
  if (fbp) user.fbp = fbp;
  const fbc = cookieFbValida(m.fbc);
  if (fbc) user.fbc = fbc;
  const evento = {
    event_name: "Lead",
    event_time: Math.floor(ahora / 1000),
    event_id: eventIdValido(m.event_id) || nuevoId(),
    action_source: "website",
    event_source_url: urlDelSitio(m.event_source_url) || urlDelSitio(headers.get("referer")) || HOME,
    user_data: user,
  };
  if (lead.tipo) evento.custom_data = { content_name: lead.tipo };
  return evento;
}

/** Por qué no se manda (o null si se manda). */
export function motivoParaNoEnviar({ meta, headers, env = {} }) {
  const token = String(env.META_CAPI_TOKEN || "").trim();
  const pixel = String(env.META_PIXEL_ID || "").trim() || META_PIXEL_ID;
  if (!token || !/^\d+$/.test(pixel)) return "sin configurar";
  const m = meta && typeof meta === "object" ? meta : {};
  if (m.consentimiento === "rechazado") return "sin consentimiento";
  const ua = headers.get("user-agent") || "";
  if (!ua || BOT_RE.test(ua)) return "bot";
  // Página desde la que se mandó el formulario: la que informa el navegador o, si no, el Referer. Si no hay
  // ninguna se manda igual (con la home); si hay y no es del sitio (alias, vista previa, localhost), no.
  const host = hostDe(m.event_source_url) || hostDe(headers.get("referer"));
  if (host && !META_HOSTS.includes(host)) return "fuera del sitio";
  return null;
}

/**
 * Manda el Lead a Meta. Nunca lanza: devuelve {enviado, motivo?, status?}. Espera como mucho timeoutMs (3 s).
 * ref: identificador sin datos personales para el log (el ID del lead en Bitrix).
 */
export async function enviarLeadMeta({ lead, meta, headers, env = {}, ref = "", fetch: fetchImpl = (...a) => globalThis.fetch(...a),
  log = console, timeoutMs = TIMEOUT_MS, ahora, nuevoId } = {}) {
  const tag = ref ? `meta capi (lead ${ref})` : "meta capi";
  try {
    const motivo = motivoParaNoEnviar({ meta, headers, env });
    if (motivo) return { enviado: false, motivo };
    const pixel = String(env.META_PIXEL_ID || "").trim() || META_PIXEL_ID;
    const evento = await armarEventoLead({ lead, meta, headers, ahora, nuevoId });
    const body = { data: [evento], access_token: String(env.META_CAPI_TOKEN).trim() };
    const test = String(env.META_TEST_EVENT_CODE || "").trim();
    if (test) body.test_event_code = test;
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetchImpl(`https://graph.facebook.com/${GRAPH_VERSION}/${pixel}/events`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: ctrl.signal,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        log.error(`${tag}: Meta respondió HTTP ${res.status}${data?.error?.message ? ` (${String(data.error.message).slice(0, 200)})` : ""}`);
        return { enviado: false, motivo: "error", status: res.status };
      }
      log.log(`${tag}: Lead enviado a Meta${test ? " (prueba)" : ""}`);
      return { enviado: true, status: res.status };
    } finally {
      clearTimeout(timer);
    }
  } catch (e) {
    log.error(`${tag}: ${e?.name === "AbortError" ? `Meta no respondió en ${timeoutMs / 1000} s` : "no se pudo enviar"}`);
    return { enviado: false, motivo: "error" };
  }
}
