/**
 * Estadísticas propias del sitio → colección `site_stats` de Directus (se ven en el panel, Insights).
 *
 * Sin cookies, sin IDs y sin datos personales: cada visita suma 1 a un contador
 * (sitio, día de Asunción, tipo, ruta, idioma). La IP solo se usa en memoria para el tope por IP y
 * nunca se guarda. Los contadores se acumulan en memoria y se mandan a Directus cada 60 s (y al
 * apagar el proceso): perder ≤ 60 s de conteo en un reinicio es aceptable.
 *
 * Tipos: view (visita de página) y whatsapp (clic a wa.me) llegan por POST /hit desde js/main.js;
 *        lead lo suma lead.js cuando Bitrix crea el lead.
 *
 * env: DIRECTUS_URL (interno: http://directus:8055) · DIRECTUS_STATS_TOKEN (usuario stats@, solo site_stats)
 *      STATS_SITE=zeekr (slug en `sites`) · STATS_HOSTS=zeekrlife.com.py (hosts que cuentan)
 *      STATS_FLUSH_MS=60000
 * Si falta DIRECTUS_URL o DIRECTUS_STATS_TOKEN, /hit responde 204 y no hace nada.
 */
const HIT_KINDS = new Set(["view", "whatsapp"]);
const BOT_RE = /bot|crawl|spider|slurp|headless|lighthouse|preview/i;
const LANG_PREFIX = new Set(["en", "pt", "zh"]);
// Secciones con nombre traducido en la URL → nombre en español, para agrupar la misma página en los 4 idiomas.
const SECTION_ES = { models: "modelos", news: "noticias", about: "nosotros", sobre: "nosotros" };
const PATH_OK = /^\/[a-z0-9\-._~%/]*$/;
const MAX_BODY = 2048;
const NO_CONTENT = () => new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });

/** Ruta del navegador → {path, lang}: sin query ni hash, sin prefijo de idioma, secciones en español. */
export function normalizePath(raw) {
  if (typeof raw !== "string" || !raw.startsWith("/") || raw.length > 255) return null;
  let p = raw.split(/[?#]/)[0].toLowerCase().replace(/\/{2,}/g, "/");
  if (!PATH_OK.test(p)) return null;
  p = p.replace(/\/index\.html$/, "/");
  const segs = p.split("/").filter(Boolean);
  let lang = "es";
  if (segs.length && LANG_PREFIX.has(segs[0])) {
    lang = segs.shift();
    if (segs.length && SECTION_ES[segs[0]]) segs[0] = SECTION_ES[segs[0]];
  }
  let path = "/" + segs.join("/");
  if (segs.length && !/\.[a-z0-9]+$/.test(segs[segs.length - 1])) path += "/";
  return { path, lang };
}

const DAY_FMT = new Intl.DateTimeFormat("en-US", { timeZone: "America/Asuncion", year: "numeric", month: "2-digit", day: "2-digit" });
/** Día local de Paraguay, YYYY-MM-DD (formatToParts: no depende de los datos de locale del ICU). */
export function localDay(date) {
  const parts = Object.fromEntries(DAY_FMT.formatToParts(date).map((x) => [x.type, x.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function cleanLabel(t) {
  if (typeof t !== "string") return null;
  const s = t.replace(/\s+/g, " ").trim().slice(0, 120);
  return s || null;
}

function requestHost(request) {
  const h = request.headers.get("x-forwarded-host") || request.headers.get("host") || "";
  return h.split(",")[0].trim().toLowerCase().replace(/:\d+$/, "");
}

export function createStats(env = {}, {
  fetch: fetchImpl = (...a) => globalThis.fetch(...a), now = () => new Date(), log = console,
  maxKeys = 5000, rateLimit = 300, rateWindowMs = 600000, chunk = 500, timeoutMs = 10000,
} = {}) {
  const base = String(env.DIRECTUS_URL || "").replace(/\/+$/, "");
  const token = String(env.DIRECTUS_STATS_TOKEN || "");
  const siteSlug = env.STATS_SITE || "zeekr";
  const hosts = new Set(String(env.STATS_HOSTS || "zeekrlife.com.py").split(",").map((s) => s.trim().toLowerCase()).filter(Boolean));
  const enabled = Boolean(base && token);
  let pending = new Map(); // clave → {day, kind, path, lang, label, n} (orden de inserción = antigüedad)
  let dropped = 0;
  let siteId = null;
  let flushing = null;
  let timer = null;
  const perIp = new Map(); // ip → {n, t0}; solo en memoria, se poda en cada envío

  function trim(map) {
    while (map.size > maxKeys) { map.delete(map.keys().next().value); dropped++; }
  }

  function record({ kind, path, lang, label = null, n = 1 }) {
    if (!enabled) return;
    const day = localDay(now());
    const key = `${day}\u0000${kind}\u0000${path}\u0000${lang}`;
    const e = pending.get(key);
    if (e) { e.n += n; if (!e.label && label) e.label = label; return; }
    pending.set(key, { day, kind, path, lang, label: label || null, n });
    trim(pending);
  }

  function limited(ip) {
    const t = now().getTime();
    const q = perIp.get(ip);
    if (!q || t - q.t0 > rateWindowMs) { perIp.set(ip, { n: 1, t0: t }); return false; }
    q.n++;
    return q.n > rateLimit;
  }

  /** POST /hit desde el navegador. Siempre 204: nunca romper la página. */
  async function hit(request) {
    try {
      if (!enabled || request.method !== "POST") return NO_CONTENT();
      if (!hosts.has(requestHost(request))) return NO_CONTENT();
      const ua = request.headers.get("user-agent") || "";
      if (!ua || BOT_RE.test(ua)) return NO_CONTENT();
      const text = await request.text();
      if (text.length > MAX_BODY) return NO_CONTENT();
      const b = JSON.parse(text);
      if (!b || typeof b !== "object" || !HIT_KINDS.has(b.k)) return NO_CONTENT();
      const norm = normalizePath(b.p);
      if (!norm) return NO_CONTENT();
      const ip = request.headers.get("cf-connecting-ip") || (request.headers.get("x-forwarded-for") || "").split(",")[0].trim() || "?";
      if (limited(ip)) return NO_CONTENT();
      record({ kind: b.k, ...norm, label: cleanLabel(b.t) });
    } catch { /* cuerpo inválido: se ignora */ }
    return NO_CONTENT();
  }

  /** Lead creado en Bitrix: cuenta en la ruta de origen (pagina) o en "/". */
  function lead(body) {
    if (!enabled) return;
    const b = body && typeof body === "object" ? body : {};
    let norm = null;
    try {
      const u = b.pagina ? new URL(String(b.pagina)) : null; // el formulario manda location.href (absoluta)
      if (u && /^https?:$/.test(u.protocol)) norm = normalizePath(u.pathname);
    } catch { norm = null; }
    if (!norm) {
      const idioma = String(b.idioma || "").toLowerCase().slice(0, 2);
      norm = { path: "/", lang: LANG_PREFIX.has(idioma) ? idioma : "es" };
    }
    record({ kind: "lead", ...norm, label: null });
  }

  async function api(method, path, body) {
    const res = await fetchImpl(`${base}${path}`, {
      method, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(timeoutMs),
    });
    if (!res.ok) throw new Error(`${method} ${path.split("?")[0]} → HTTP ${res.status}`);
    const txt = await res.text();
    return txt ? JSON.parse(txt).data : null;
  }

  async function resolveSite() {
    if (siteId != null) return siteId;
    const q = new URLSearchParams({ filter: JSON.stringify({ slug: { _eq: siteSlug } }), fields: "id", limit: "1" });
    const rows = await api("GET", `/items/sites?${q}`);
    if (!rows || !rows.length) throw new Error(`sitio "${siteSlug}" no encontrado en Directus`);
    siteId = rows[0].id;
    return siteId;
  }

  /** Devuelve los no confirmados a lo pendiente (primero, por ser los más viejos) respetando el tope. */
  function restore(todo) {
    const merged = new Map(todo);
    for (const [k, e] of pending) {
      const m = merged.get(k);
      if (m) { m.n += e.n; if (!m.label && e.label) m.label = e.label; } else merged.set(k, e);
    }
    trim(merged);
    pending = merged;
  }

  async function doFlush() {
    const t = now().getTime();
    for (const [ip, q] of perIp) if (t - q.t0 > rateWindowMs) perIp.delete(ip);
    if (dropped) { log.warn(`estadísticas: se superó el tope de ${maxKeys} claves en memoria; se descartaron ${dropped} (las más viejas)`); dropped = 0; }
    if (!pending.size) return { ok: true, sent: 0 };
    const batch = pending;
    pending = new Map();
    const todo = new Map(batch);
    try {
      const site = await resolveSite();
      const days = [...new Set([...batch.values()].map((e) => e.day))];
      const q = new URLSearchParams({ filter: JSON.stringify({ _and: [{ site: { _eq: site } }, { day: { _in: days } }] }),
        fields: "id,day,kind,path,lang,count", limit: "-1" });
      const existing = new Map();
      for (const r of (await api("GET", `/items/site_stats?${q}`)) || []) {
        existing.set(`${String(r.day).slice(0, 10)}\u0000${r.kind}\u0000${r.path}\u0000${r.lang}`, r);
      }
      const creates = [], updates = [];
      for (const [k, e] of batch) {
        const row = existing.get(k);
        if (row) updates.push([k, { id: row.id, count: Number(row.count || 0) + e.n }]);
        else creates.push([k, { site, day: e.day, kind: e.kind, path: e.path, lang: e.lang, label: e.label, count: e.n }]);
      }
      for (const [method, list] of [["POST", creates], ["PATCH", updates]]) {
        for (let i = 0; i < list.length; i += chunk) {
          const part = list.slice(i, i + chunk);
          await api(method, "/items/site_stats", part.map(([, row]) => row));
          for (const [k] of part) todo.delete(k);
        }
      }
      return { ok: true, sent: batch.size };
    } catch (err) {
      restore(todo);
      log.error(`estadísticas: no se pudo guardar en Directus (${err.message}); se reintenta en el próximo envío (${pending.size} claves pendientes)`);
      return { ok: false, error: err.message };
    }
  }

  /** Manda lo acumulado a Directus (upsert por clave). Un solo envío a la vez. */
  function flush() {
    if (!enabled) return Promise.resolve({ ok: true, sent: 0 });
    if (!flushing) flushing = doFlush().finally(() => { flushing = null; });
    return flushing;
  }

  function start(intervalMs = Number(env.STATS_FLUSH_MS) || 60000) {
    if (!enabled || timer) return;
    timer = setInterval(() => { flush(); }, intervalMs);
    if (timer.unref) timer.unref();
  }
  function stop() { if (timer) clearInterval(timer); timer = null; }

  return {
    enabled, hit, lead, record, flush, start, stop,
    snapshot: () => [...pending.values()].map((e) => ({ ...e })),
  };
}
