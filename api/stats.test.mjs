// Tests del contador propio de visitas (functions/_lib/stats.js), de la cuenta de leads en lead.js y de la
// ruta /hit del servidor. Sin dependencias: node --test api/
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { fileURLToPath } from "node:url";
import { createStats, normalizePath, localDay } from "../functions/_lib/stats.js";
import { handle } from "../functions/_lib/lead.js";

const ENV = { DIRECTUS_URL: "http://directus.test:8055", DIRECTUS_STATS_TOKEN: "tok-secreto-de-prueba" };
const CHROME = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36";
const NOW = new Date("2026-09-24T15:00:00Z"); // 12:00 en Asunción

function hitReq(body, { ua = CHROME, host = "zeekrlife.com.py", method = "POST", ip = "1.2.3.4", headers = {} } = {}) {
  const h = { host, "cf-connecting-ip": ip, ...headers };
  if (ua) h["user-agent"] = ua;
  return new Request("http://leads-api/hit", {
    method, headers: h,
    body: method === "GET" ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });
}

/** Directus falso: responde según método + ruta y guarda cada pedido. */
function fakeDirectus({ rows = [], fail = {} } = {}) {
  const calls = [];
  let nextId = 100;
  const state = { calls, fail };
  state.fetch = async (url, init = {}) => {
    const u = new URL(url);
    const method = init.method || "GET";
    const body = init.body ? JSON.parse(init.body) : undefined;
    calls.push({ method, path: u.pathname, query: u.searchParams, body, auth: init.headers?.Authorization });
    const key = `${method} ${u.pathname}`;
    if (state.fail[key]) return new Response(JSON.stringify({ errors: [{ message: "caído" }] }), { status: fail[key] });
    const json = (data) => new Response(JSON.stringify({ data }), { status: 200, headers: { "Content-Type": "application/json" } });
    if (key === "GET /items/sites") return json([{ id: 1 }]);
    if (key === "GET /items/site_stats") return json(rows);
    if (key === "POST /items/site_stats") return json(body.map((r) => ({ id: nextId++, ...r })));
    if (key === "PATCH /items/site_stats") return json(body);
    return new Response("{}", { status: 404 });
  };
  return state;
}

function makeStats(opts = {}) {
  const d = opts.directus || fakeDirectus();
  const logs = { warn: [], error: [] };
  const log = { log() {}, warn: (m) => logs.warn.push(String(m)), error: (m) => logs.error.push(String(m)) };
  const stats = createStats(opts.env || ENV, { fetch: d.fetch, now: () => opts.now || NOW, log, ...opts.extra });
  return { stats, d, logs };
}

describe("normalizePath", () => {
  const cases = [
    ["/", "/", "es"],
    ["/modelos/zeekr-7x/", "/modelos/zeekr-7x/", "es"],
    ["/en/models/zeekr-7x/", "/modelos/zeekr-7x/", "en"],
    ["/zh/news/lanzamiento-zeekr-7x-alma/", "/noticias/lanzamiento-zeekr-7x-alma/", "zh"],
    ["/pt/sobre/", "/nosotros/", "pt"],
    ["/pt/modelos/zeekr-001/", "/modelos/zeekr-001/", "pt"],
    ["/en/about/", "/nosotros/", "en"],
    ["/en/", "/", "en"],
    ["/en", "/", "en"],
    ["/modelos/zeekr-7x/?utm_source=ig&x=1#galeria", "/modelos/zeekr-7x/", "es"],
    ["/modelos/zeekr-7x", "/modelos/zeekr-7x/", "es"],
    ["/modelos/zeekr-7x/index.html", "/modelos/zeekr-7x/", "es"],
    ["//modelos//zeekr-7x/", "/modelos/zeekr-7x/", "es"],
    ["/Modelos/ZEEKR-7X/", "/modelos/zeekr-7x/", "es"],
  ];
  for (const [raw, path, lang] of cases) {
    test(`${raw} → ${lang} ${path}`, () => assert.deepEqual(normalizePath(raw), { path, lang }));
  }
  test("rechaza lo que no es una ruta del sitio", () => {
    for (const bad of ["modelos/", "", null, undefined, 42, "/" + "a".repeat(300), "/<script>/", "/a b/", "http://x.com/"]) {
      assert.equal(normalizePath(bad), null, String(bad));
    }
  });
});

describe("localDay", () => {
  test("usa el día de Asunción (UTC−3), no el de UTC", () => {
    assert.equal(localDay(new Date("2026-09-25T02:30:00Z")), "2026-09-24");
    assert.equal(localDay(new Date("2026-09-25T03:30:00Z")), "2026-09-25");
  });
});

describe("hit", () => {
  test("una visita válida responde 204 y se acumula por sitio/día/tipo/ruta/idioma", async () => {
    const { stats } = makeStats();
    const r1 = await stats.hit(hitReq({ k: "view", p: "/en/models/zeekr-7x/", t: "ZEEKR 7X | Premium 800 V electric SUV — ZEEKR Paraguay" }));
    assert.equal(r1.status, 204);
    await stats.hit(hitReq({ k: "view", p: "/en/models/zeekr-7x/?utm_source=ig", t: "ZEEKR 7X" }));
    await stats.hit(hitReq({ k: "whatsapp", p: "/en/models/zeekr-7x/", t: "ZEEKR 7X" }));
    const snap = stats.snapshot();
    assert.equal(snap.length, 2);
    const view = snap.find((e) => e.kind === "view");
    assert.deepEqual(view, { day: "2026-09-24", kind: "view", path: "/modelos/zeekr-7x/", lang: "en",
      label: "ZEEKR 7X | Premium 800 V electric SUV — ZEEKR Paraguay", n: 2 });
    assert.equal(snap.find((e) => e.kind === "whatsapp").n, 1);
  });

  test("el título se limpia y se corta a 120 caracteres", async () => {
    const { stats } = makeStats();
    await stats.hit(hitReq({ k: "view", p: "/", t: "  Hola \n  mundo " + "x".repeat(200) }));
    const [e] = stats.snapshot();
    assert.equal(e.label.length, 120);
    assert.ok(e.label.startsWith("Hola mundo x"));
  });

  test("descarta bots, navegadores automáticos y pedidos sin user-agent", async () => {
    const { stats } = makeStats();
    const uas = ["Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "Mozilla/5.0 HeadlessChrome/130.0",
      "Mozilla/5.0 (Linux) Chrome/130 Safari/537.36 Chrome-Lighthouse", "Mozilla/5.0 (compatible; bingbot/2.0)",
      "Slackbot-LinkExpanding 1.0", "Mozilla/5.0 (compatible; Yahoo! Slurp)", "AhrefsSpider", "SomeCrawler/1.0",
      "Mozilla/5.0 Google Page Speed Insights / preview", ""];
    for (const ua of uas) {
      const r = await stats.hit(hitReq({ k: "view", p: "/" }, { ua }));
      assert.equal(r.status, 204, ua);
    }
    assert.equal(stats.snapshot().length, 0);
  });

  test("solo acepta view y whatsapp, con ruta que empieza con / y de hasta 255 caracteres", async () => {
    const { stats } = makeStats();
    for (const body of [{ k: "lead", p: "/" }, { k: "click", p: "/" }, { p: "/" }, { k: "view", p: "modelos/" },
      { k: "view", p: "/" + "a".repeat(255) }, { k: "view" }, { k: "view", p: 12 }, "no es json", "[1,2]"]) {
      const r = await stats.hit(hitReq(body));
      assert.equal(r.status, 204);
    }
    assert.equal(stats.snapshot().length, 0);
  });

  test("solo cuenta visitas de zeekrlife.com.py (el alias y la vista previa no)", async () => {
    const { stats } = makeStats();
    await stats.hit(hitReq({ k: "view", p: "/" }, { host: "zeekr.santarosa.lat" }));
    await stats.hit(hitReq({ k: "view", p: "/" }, { host: "preview-zeekr.santarosa.lat" }));
    await stats.hit(hitReq({ k: "view", p: "/" }, { host: "zeekrlife.com.py", headers: { "x-forwarded-host": "zeekr.santarosa.lat" } }));
    assert.equal(stats.snapshot().length, 0);
    await stats.hit(hitReq({ k: "view", p: "/" }, { host: "leads-api:8000", headers: { "x-forwarded-host": "zeekrlife.com.py" } }));
    await stats.hit(hitReq({ k: "view", p: "/" }, { host: "zeekrlife.com.py:443" }));
    assert.equal(stats.snapshot()[0].n, 2);
  });

  test("GET y cuerpos enormes: 204 sin contar", async () => {
    const { stats } = makeStats();
    assert.equal((await stats.hit(hitReq(null, { method: "GET" }))).status, 204);
    await stats.hit(hitReq(JSON.stringify({ k: "view", p: "/", t: "x".repeat(5000) })));
    assert.equal(stats.snapshot().length, 0);
  });

  test("tope por IP: pasado el límite de la ventana responde 204 pero no cuenta", async () => {
    const { stats } = makeStats({ extra: { rateLimit: 3 } });
    for (let i = 0; i < 5; i++) await stats.hit(hitReq({ k: "view", p: "/" }, { ip: "9.9.9.9" }));
    await stats.hit(hitReq({ k: "view", p: "/" }, { ip: "8.8.8.8" }));
    assert.equal(stats.snapshot()[0].n, 4);
  });

  test("sin DIRECTUS_URL/DIRECTUS_STATS_TOKEN responde 204 y no hace nada", async () => {
    for (const env of [{}, { DIRECTUS_URL: ENV.DIRECTUS_URL }, { DIRECTUS_STATS_TOKEN: "x" }]) {
      const { stats, d } = makeStats({ env });
      assert.equal(stats.enabled, false);
      assert.equal((await stats.hit(hitReq({ k: "view", p: "/" }))).status, 204);
      stats.lead({ pagina: "https://zeekrlife.com.py/" });
      assert.equal(stats.snapshot().length, 0);
      await stats.flush();
      assert.equal(d.calls.length, 0);
    }
  });
});

describe("lead (contador)", () => {
  test("usa la ruta de origen del payload, sin query, con el idioma de la ruta", () => {
    const { stats } = makeStats();
    stats.lead({ pagina: "https://zeekrlife.com.py/en/models/zeekr-x/?utm_source=fb", idioma: "en" });
    stats.lead({ pagina: "https://zeekrlife.com.py/en/models/zeekr-x/", idioma: "en" });
    assert.deepEqual(stats.snapshot(), [{ day: "2026-09-24", kind: "lead", path: "/modelos/zeekr-x/", lang: "en", label: null, n: 2 }]);
  });
  test("sin página (o con una inválida) cuenta en / con el idioma del payload", () => {
    const { stats } = makeStats();
    stats.lead({ idioma: "pt" });
    stats.lead({ pagina: "no es una url <x>", idioma: "zz" });
    const snap = stats.snapshot();
    assert.deepEqual(snap.map((e) => [e.path, e.lang, e.n]), [["/", "pt", 1], ["/", "es", 1]]);
  });
});

describe("flush a Directus", () => {
  test("upsert: PATCH count+n si la fila existe, POST si no; luego queda vacío", async () => {
    const d = fakeDirectus({ rows: [{ id: 7, day: "2026-09-24", kind: "view", path: "/", lang: "es", count: 5 }] });
    const { stats } = makeStats({ directus: d });
    for (let i = 0; i < 3; i++) await stats.hit(hitReq({ k: "view", p: "/", t: "Inicio" }));
    await stats.hit(hitReq({ k: "whatsapp", p: "/modelos/zeekr-7x/", t: "ZEEKR 7X" }));
    const res = await stats.flush();
    assert.equal(res.ok, true);
    assert.equal(stats.snapshot().length, 0);

    const get = d.calls.find((c) => c.method === "GET" && c.path === "/items/site_stats");
    const filter = JSON.parse(get.query.get("filter"));
    assert.deepEqual(filter, { _and: [{ site: { _eq: 1 } }, { day: { _in: ["2026-09-24"] } }] });
    assert.equal(get.auth, "Bearer tok-secreto-de-prueba");

    const patch = d.calls.find((c) => c.method === "PATCH");
    assert.deepEqual(patch.body, [{ id: 7, count: 8 }]);
    const post = d.calls.find((c) => c.method === "POST");
    assert.deepEqual(post.body, [{ site: 1, day: "2026-09-24", kind: "whatsapp", path: "/modelos/zeekr-7x/", lang: "es", label: "ZEEKR 7X", count: 1 }]);
  });

  test("el id del sitio se busca una sola vez (por slug, STATS_SITE)", async () => {
    const d = fakeDirectus();
    const { stats } = makeStats({ directus: d, env: { ...ENV, STATS_SITE: "zeekr" } });
    await stats.hit(hitReq({ k: "view", p: "/" }));
    await stats.flush();
    await stats.hit(hitReq({ k: "view", p: "/" }));
    await stats.flush();
    const sites = d.calls.filter((c) => c.path === "/items/sites");
    assert.equal(sites.length, 1);
    assert.equal(JSON.parse(sites[0].query.get("filter")).slug._eq, "zeekr");
  });

  test("sin nada pendiente no llama a Directus", async () => {
    const { stats, d } = makeStats();
    assert.deepEqual(await stats.flush(), { ok: true, sent: 0 });
    assert.equal(d.calls.length, 0);
  });

  test("si Directus falla conserva los contadores y los suma en el próximo envío", async () => {
    const d = fakeDirectus({ fail: { "GET /items/site_stats": 503 } });
    const { stats, logs } = makeStats({ directus: d });
    await stats.hit(hitReq({ k: "view", p: "/" }));
    await stats.hit(hitReq({ k: "view", p: "/" }));
    const res = await stats.flush();
    assert.equal(res.ok, false);
    assert.equal(stats.snapshot()[0].n, 2);
    assert.equal(logs.error.length, 1);
    assert.ok(!logs.error[0].includes("tok-secreto-de-prueba"), "el log no muestra el token");

    await stats.hit(hitReq({ k: "view", p: "/" }));
    delete d.fail["GET /items/site_stats"]; // Directus vuelve
    d.calls.length = 0;
    assert.equal((await stats.flush()).ok, true);
    assert.deepEqual(d.calls.find((c) => c.method === "POST").body.map((r) => r.count), [3]);
    assert.equal(stats.snapshot().length, 0);
  });

  test("falla a mitad: lo creado no se reenvía, lo que faltaba actualizar sí", async () => {
    const d = fakeDirectus({ rows: [{ id: 7, day: "2026-09-24", kind: "view", path: "/", lang: "es", count: 5 }], fail: { "PATCH /items/site_stats": 500 } });
    const { stats } = makeStats({ directus: d });
    await stats.hit(hitReq({ k: "view", p: "/" }));
    await stats.hit(hitReq({ k: "whatsapp", p: "/" }));
    assert.equal((await stats.flush()).ok, false);
    assert.deepEqual(stats.snapshot().map((e) => [e.kind, e.n]), [["view", 1]]);
  });

  test("los hits que llegan durante el envío no se pierden", async () => {
    let release;
    const gate = new Promise((r) => { release = r; });
    const d = fakeDirectus();
    const slow = async (url, init) => { if (String(url).includes("/items/site_stats") && (init?.method || "GET") === "GET") await gate; return d.fetch(url, init); };
    const { stats } = makeStats({ directus: { fetch: slow, calls: d.calls } });
    await stats.hit(hitReq({ k: "view", p: "/" }));
    const p = stats.flush();
    const p2 = stats.flush(); // uno solo a la vez
    await stats.hit(hitReq({ k: "view", p: "/" }));
    release();
    await Promise.all([p, p2]);
    assert.equal(d.calls.filter((c) => c.method === "POST").length, 1);
    assert.equal(stats.snapshot()[0].n, 1);
  });

  test("tope de memoria: pasado maxKeys se descartan las claves más viejas y se avisa en el log", async () => {
    const d = fakeDirectus({ fail: { "GET /items/site_stats": 503 } });
    const { stats, logs } = makeStats({ directus: d, extra: { maxKeys: 3 } });
    for (const p of ["/a/", "/b/", "/c/", "/d/", "/e/"]) await stats.hit(hitReq({ k: "view", p }));
    assert.deepEqual(stats.snapshot().map((e) => e.path), ["/c/", "/d/", "/e/"]);
    await stats.flush();
    assert.ok(logs.warn.some((m) => m.includes("2")), "avisa cuántas claves se descartaron");
    // tras la falla, lo pendiente sigue respetando el tope
    for (const p of ["/f/", "/g/"]) await stats.hit(hitReq({ k: "view", p }));
    assert.equal(stats.snapshot().length, 3);
    assert.deepEqual(stats.snapshot().map((e) => e.path), ["/e/", "/f/", "/g/"]);
  });

  test("los envíos grandes van en tandas", async () => {
    const d = fakeDirectus();
    const { stats } = makeStats({ directus: d, extra: { chunk: 2 } });
    for (const p of ["/a/", "/b/", "/c/", "/d/", "/e/"]) await stats.hit(hitReq({ k: "view", p }));
    assert.equal((await stats.flush()).ok, true);
    assert.deepEqual(d.calls.filter((c) => c.method === "POST").map((c) => c.body.length), [2, 2, 1]);
  });
});

describe("lead.js cuenta los leads creados", () => {
  const BITRIX = "https://bitrix.test/rest/1/abc/";
  function withBitrix(fn, { fail = false } = {}) {
    return async () => {
      const real = globalThis.fetch;
      globalThis.fetch = async (url) => {
        const m = String(url).replace(BITRIX, "").replace(".json", "");
        if (fail && m === "crm.lead.add") return new Response(JSON.stringify({ error: "X", error_description: "caído" }));
        const result = { "user.get": [{ ID: "139", NAME: "ANA", LAST_NAME: "P" }], "crm.lead.list": [], "crm.lead.add": 555 }[m];
        return new Response(JSON.stringify({ result }));
      };
      try { await fn(); } finally { globalThis.fetch = real; }
    };
  }
  const env = { BITRIX_WEBHOOK_URL: BITRIX, ADVISOR_IDS: "139" };
  const leadReq = (body, ip) => new Request("http://leads-api/lead", { method: "POST", headers: { "cf-connecting-ip": ip }, body: JSON.stringify(body) });
  const body = { nombre: "Juan Pérez", telefono: "0981 123 456", pagina: "https://zeekrlife.com.py/modelos/zeekr-7x/", idioma: "es" };

  test("lead creado en Bitrix → stats.lead(body)", withBitrix(async () => {
    const seen = [];
    const res = await handle(leadReq(body, "10.0.0.1"), env, { stats: { lead: (b) => seen.push(b) } });
    assert.equal(res.status, 200);
    assert.equal(seen.length, 1);
    assert.equal(seen[0].pagina, body.pagina);
  }));

  test("si Bitrix falla, o es el honeypot, no se cuenta", withBitrix(async () => {
    const seen = [];
    const stats = { lead: (b) => seen.push(b) };
    await handle(leadReq({ ...body, website: "spam" }, "10.0.0.2"), env, { stats });
    await handle(leadReq({ nombre: "x" }, "10.0.0.3"), env, { stats });
    assert.equal(seen.length, 0);
  }));

  test("Bitrix con error → no cuenta", withBitrix(async () => {
    const seen = [];
    const res = await handle(leadReq(body, "10.0.0.4"), env, { stats: { lead: (b) => seen.push(b) } });
    assert.equal(res.status, 502);
    assert.equal(seen.length, 0);
  }, { fail: true }));

  test("un error del contador nunca rompe la respuesta del lead", withBitrix(async () => {
    const res = await handle(leadReq(body, "10.0.0.5"), env, { stats: { lead: () => { throw new Error("boom"); } } });
    assert.equal(res.status, 200);
  }));

  test("sin contador (Cloudflare Pages) sigue funcionando igual", withBitrix(async () => {
    const res = await handle(leadReq(body, "10.0.0.6"), env);
    assert.equal(res.status, 200);
  }));
});

describe("servidor (api/server.mjs)", () => {
  test("/hit → 204; al recibir SIGTERM guarda lo pendiente en Directus y sale", async () => {
    const got = [];
    const fake = http.createServer(async (req, res) => {
      let raw = ""; for await (const c of req) raw += c;
      got.push({ method: req.method, url: req.url, body: raw ? JSON.parse(raw) : null, auth: req.headers.authorization });
      res.setHeader("Content-Type", "application/json");
      if (req.url.startsWith("/items/sites")) return res.end(JSON.stringify({ data: [{ id: 1 }] }));
      if (req.method === "GET") return res.end(JSON.stringify({ data: [] }));
      res.end(JSON.stringify({ data: JSON.parse(raw) }));
    }).listen(0, "127.0.0.1");
    await once(fake, "listening");
    const port = 20000 + Math.floor(Math.random() * 20000);
    const server = spawn(process.execPath, [fileURLToPath(new URL("./server.mjs", import.meta.url))], {
      env: { ...process.env, PORT: String(port), DIRECTUS_URL: `http://127.0.0.1:${fake.address().port}`, DIRECTUS_STATS_TOKEN: "tok-srv", STATS_FLUSH_MS: "600000" },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let out = "";
    server.stdout.on("data", (c) => { out += c; });
    server.stderr.on("data", (c) => { out += c; });
    for (let i = 0; i < 50 && !out.includes("escuchando"); i++) await new Promise((r) => setTimeout(r, 100));
    try {
      const r = await fetch(`http://127.0.0.1:${port}/hit`, { method: "POST", headers: { "X-Forwarded-Host": "zeekrlife.com.py", "User-Agent": CHROME, "Content-Type": "text/plain" },
        body: JSON.stringify({ k: "view", p: "/noticias/", t: "Noticias" }) });
      assert.equal(r.status, 204);
      const h = await fetch(`http://127.0.0.1:${port}/health`);
      assert.equal(h.status, 200);
      assert.equal(got.length, 0, "no manda nada antes del flush");
      server.kill("SIGTERM");
      const [code] = await once(server, "exit");
      assert.equal(code, 0, out);
      const post = got.find((g) => g.method === "POST");
      assert.ok(post, out);
      assert.equal(post.auth, "Bearer tok-srv");
      assert.deepEqual(post.body.map((r) => [r.kind, r.path, r.count]), [["view", "/noticias/", 1]]);
    } finally {
      server.kill("SIGKILL");
      fake.close();
    }
  });
});
