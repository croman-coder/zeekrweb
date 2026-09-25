// Tests de la API de conversiones de Meta (functions/_lib/meta-capi.js) y de cómo la llama lead.js.
// Sin dependencias: node --test api/
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  META_PIXEL_ID, GRAPH_VERSION, normalizarTelefono, sha256, eventIdValido, cookieFbValida, urlDelSitio,
  ipDelCliente, armarEventoLead, motivoParaNoEnviar, enviarLeadMeta,
} from "../functions/_lib/meta-capi.js";
import { handle } from "../functions/_lib/lead.js";

const CHROME = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36";
const h = (s) => createHash("sha256").update(s).digest("hex");
const AHORA = Date.parse("2026-09-25T15:00:00Z");
const PAGINA = "https://zeekrlife.com.py/modelos/zeekr-7x/?utm_source=ig&fbclid=abc";
const FBP = "fb.1.1727270000000.1234567890";
const FBC = "fb.1.1727270000000.IwAR2abc_DEF-123";
const LEAD = { nombre: "Juan Pérez González", telefono: "0981 123-456", email: null, tipo: "Prueba de manejo" };
const META = { event_id: "0b6c1a52-8f1e-4c3a-9d2e-5f4b3a2c1d0e", fbp: FBP, fbc: FBC, event_source_url: PAGINA, consentimiento: "aceptado" };
const ENV = { META_CAPI_TOKEN: "EAAB-token-de-prueba" };

function headers(extra = {}) {
  return new Headers({ "user-agent": CHROME, "cf-connecting-ip": "181.120.10.20", referer: "https://zeekrlife.com.py/", ...extra });
}

/** Graph API falsa: guarda cada pedido y responde lo que se le pida. */
function fakeGraph({ status = 200, body = { events_received: 1, fbtrace_id: "x" }, fail = null } = {}) {
  const calls = [];
  const fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init, body: init.body ? JSON.parse(init.body) : null });
    if (fail) throw fail;
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  };
  return { calls, fetch };
}
function fakeLog() {
  const lines = { log: [], error: [] };
  return { lines, log: (m) => lines.log.push(String(m)), error: (m) => lines.error.push(String(m)), warn: (m) => lines.error.push(String(m)) };
}

describe("normalizarTelefono", () => {
  const casos = [
    ["0981 123-456", "595981123456"],
    ["+595 981 123456", "595981123456"],
    ["981123456", "595981123456"],
    ["021 555 123", "59521555123"],
    ["00595 981 123456", "595981123456"],
    ["+54 9 11 1234 5678", "5491112345678"],
    ["(0981) 123 456", "595981123456"],
    ["000981123456", "595981123456"],
    ["12345", "12345"],
  ];
  for (const [raw, esperado] of casos) test(`${raw} → ${esperado}`, () => assert.equal(normalizarTelefono(raw), esperado));
  test("sin dígitos útiles → vacío (no se manda ph)", () => {
    for (const raw of ["", "0", "000", "abc", null, undefined]) assert.equal(normalizarTelefono(raw), "", String(raw));
  });
});

describe("validaciones de lo que manda el navegador", () => {
  test("sha256 en hexadecimal", async () => {
    assert.equal(await sha256("py"), h("py"));
    assert.equal(await sha256("juan"), h("juan"));
  });
  test("event_id: hasta 100 caracteres [A-Za-z0-9_.:-]", () => {
    assert.equal(eventIdValido(META.event_id), META.event_id);
    assert.equal(eventIdValido("lz1abc.9:x_y-z"), "lz1abc.9:x_y-z");
    for (const bad of ["", "a".repeat(101), "con espacio", "<script>", "ñandú", 123, null, undefined, {}]) assert.equal(eventIdValido(bad), null, String(bad));
  });
  test("fbp/fbc: fb.<n>.<número>.<id> y hasta 300 caracteres", () => {
    assert.equal(cookieFbValida(FBP), FBP);
    assert.equal(cookieFbValida(FBC), FBC);
    for (const bad of ["", "fb.1.abc.123", "fb.12.1.x", "fb.1.1.", "xx.1.1.abc", "fb.1.1.a b", `fb.1.1.${"a".repeat(300)}`, 42, null]) {
      assert.equal(cookieFbValida(bad), null, String(bad));
    }
  });
  test("url del sitio: solo https en zeekrlife.com.py", () => {
    assert.equal(urlDelSitio(PAGINA), PAGINA);
    for (const bad of ["http://zeekrlife.com.py/", "https://www.zeekrlife.com.py/", "https://preview-zeekr.santarosa.lat/", "https://zeekr.santarosa.lat/",
      "https://zeekrlife.com.py.evil.com/", "javascript:alert(1)", "no es url", "", null, `https://zeekrlife.com.py/${"a".repeat(2000)}`]) {
      assert.equal(urlDelSitio(bad), null, String(bad));
    }
  });
  test("IP: cf-connecting-ip primero, después la 1.ª de x-forwarded-for, x-nf-client-connection-ip y x-real-ip", () => {
    assert.equal(ipDelCliente(new Headers({ "cf-connecting-ip": "1.2.3.4", "x-forwarded-for": "5.6.7.8" })), "1.2.3.4");
    assert.equal(ipDelCliente(new Headers({ "x-forwarded-for": "5.6.7.8, 10.0.0.1" })), "5.6.7.8");
    assert.equal(ipDelCliente(new Headers({ "x-nf-client-connection-ip": "2800:a4:1::1" })), "2800:a4:1::1");
    assert.equal(ipDelCliente(new Headers({ "x-forwarded-for": "basura", "x-real-ip": "9.9.9.9" })), "9.9.9.9");
    assert.equal(ipDelCliente(new Headers({})), null);
  });
});

describe("armarEventoLead", () => {
  test("evento completo: datos hasheados, sin hashear los técnicos y el event_id del navegador", async () => {
    const ev = await armarEventoLead({ lead: { ...LEAD, email: " Juan.Perez@Example.COM " }, meta: META, headers: headers(), ahora: AHORA });
    assert.deepEqual(ev, {
      event_name: "Lead",
      event_time: Math.floor(AHORA / 1000),
      event_id: META.event_id,
      action_source: "website",
      event_source_url: PAGINA,
      user_data: {
        em: [h("juan.perez@example.com")],
        ph: [h("595981123456")],
        fn: [h("juan")],
        ln: [h("pérez gonzález")],
        country: [h("py")],
        client_ip_address: "181.120.10.20",
        client_user_agent: CHROME,
        fbp: FBP,
        fbc: FBC,
      },
      custom_data: { content_name: "Prueba de manejo" },
    });
  });
  test("omite lo que falta: sin email, sin apellido, sin cookies, sin IP", async () => {
    const ev = await armarEventoLead({ lead: { nombre: "  Ana ", telefono: "0", tipo: "Consulta" }, meta: {}, headers: new Headers({ "user-agent": CHROME }), ahora: AHORA, nuevoId: () => "id-nuevo" });
    assert.deepEqual(Object.keys(ev.user_data).sort(), ["client_user_agent", "country", "fn"]);
    assert.deepEqual(ev.user_data.fn, [h("ana")]);
    assert.equal(ev.event_id, "id-nuevo");
    assert.deepEqual(ev.custom_data, { content_name: "Consulta" });
    for (const v of Object.values(ev.user_data).flat()) assert.notEqual(v, h(""), "nunca el hash de un texto vacío");
  });
  test("lo inválido del navegador se descarta: event_id nuevo, sin fbp/fbc", async () => {
    const ev = await armarEventoLead({ lead: LEAD, meta: { event_id: "<x>", fbp: "cualquiera", fbc: 42 }, headers: headers(), nuevoId: () => "uuid-servidor" });
    assert.equal(ev.event_id, "uuid-servidor");
    assert.equal(ev.user_data.fbp, undefined);
    assert.equal(ev.user_data.fbc, undefined);
    const sinMeta = await armarEventoLead({ lead: LEAD, meta: "no es objeto", headers: headers(), nuevoId: () => "otro" });
    assert.equal(sinMeta.event_id, "otro");
  });
  test("event_source_url: la del navegador si es del sitio; si no, el Referer; si no, la home", async () => {
    const hs = headers({ referer: "https://zeekrlife.com.py/noticias/" });
    assert.equal((await armarEventoLead({ lead: LEAD, meta: { event_source_url: "http://zeekrlife.com.py/x" }, headers: hs })).event_source_url, "https://zeekrlife.com.py/noticias/");
    assert.equal((await armarEventoLead({ lead: LEAD, meta: {}, headers: new Headers({ "user-agent": CHROME }) })).event_source_url, "https://zeekrlife.com.py/");
    assert.equal((await armarEventoLead({ lead: LEAD, meta: {}, headers: headers({ referer: "https://otro.com/" }) })).event_source_url, "https://zeekrlife.com.py/");
  });
});

describe("enviarLeadMeta", () => {
  test("sin META_CAPI_TOKEN no hace nada y no escribe en el log", async () => {
    const g = fakeGraph(), l = fakeLog();
    for (const env of [{}, { META_CAPI_TOKEN: "  " }, { META_PIXEL_ID: "123" }]) {
      const r = await enviarLeadMeta({ lead: LEAD, meta: META, headers: headers(), env, fetch: g.fetch, log: l });
      assert.deepEqual(r, { enviado: false, motivo: "sin configurar" });
    }
    assert.equal(g.calls.length, 0);
    assert.deepEqual(l.lines, { log: [], error: [] });
  });
  test("manda el evento a la Graph API v21.0 con el píxel por defecto", async () => {
    const g = fakeGraph(), l = fakeLog();
    const r = await enviarLeadMeta({ lead: LEAD, meta: META, headers: headers(), env: ENV, ref: 555, fetch: g.fetch, log: l, ahora: AHORA });
    assert.deepEqual(r, { enviado: true, status: 200 });
    assert.equal(g.calls.length, 1);
    const c = g.calls[0];
    assert.equal(GRAPH_VERSION, "v21.0");
    assert.equal(c.url, `https://graph.facebook.com/v21.0/${META_PIXEL_ID}/events`);
    assert.equal(c.init.method, "POST");
    assert.equal(c.body.access_token, ENV.META_CAPI_TOKEN);
    assert.equal("test_event_code" in c.body, false);
    assert.equal(c.body.data.length, 1);
    assert.equal(c.body.data[0].event_id, META.event_id);
    assert.equal(c.body.data[0].event_name, "Lead");
    assert.ok(c.init.signal, "con AbortController (tope de tiempo)");
    assert.deepEqual(l.lines.log, ["meta capi (lead 555): Lead enviado a Meta"]);
  });
  test("META_PIXEL_ID pisa el píxel y META_TEST_EVENT_CODE agrega test_event_code", async () => {
    const g = fakeGraph();
    await enviarLeadMeta({ lead: LEAD, meta: META, headers: headers(), env: { ...ENV, META_PIXEL_ID: "999", META_TEST_EVENT_CODE: "TEST123" }, fetch: g.fetch, log: fakeLog() });
    assert.equal(g.calls[0].url, "https://graph.facebook.com/v21.0/999/events");
    assert.equal(g.calls[0].body.test_event_code, "TEST123");
  });
  test("no manda si el visitante rechazó las cookies, si es un bot o si el formulario vino de otro host", async () => {
    const g = fakeGraph();
    const casos = [
      [{ ...META, consentimiento: "rechazado" }, headers(), "sin consentimiento"],
      [META, headers({ "user-agent": "Googlebot/2.1 (+http://www.google.com/bot.html)" }), "bot"],
      [META, headers({ "user-agent": "Mozilla/5.0 HeadlessChrome/130.0" }), "bot"],
      [META, new Headers({ "cf-connecting-ip": "1.2.3.4" }), "bot"],
      [{ ...META, event_source_url: "https://preview-zeekr.santarosa.lat/modelos/" }, headers(), "fuera del sitio"],
      [{ ...META, event_source_url: "https://zeekr.santarosa.lat/" }, headers(), "fuera del sitio"],
      [{ event_id: "abc" }, headers({ referer: "http://localhost:8000/" }), "fuera del sitio"],
    ];
    for (const [meta, hs, motivo] of casos) {
      assert.equal(motivoParaNoEnviar({ meta, headers: hs, env: ENV }), motivo);
      assert.deepEqual(await enviarLeadMeta({ lead: LEAD, meta, headers: hs, env: ENV, fetch: g.fetch, log: fakeLog() }), { enviado: false, motivo });
    }
    assert.equal(g.calls.length, 0);
    assert.equal(motivoParaNoEnviar({ meta: {}, headers: new Headers({ "user-agent": CHROME }), env: ENV }), null, "sin página conocida se manda igual");
  });
  test("error de Meta: una línea de log con el código y el mensaje, sin token ni datos personales", async () => {
    const g = fakeGraph({ status: 400, body: { error: { message: "Invalid parameter", code: 100 } } }), l = fakeLog();
    const r = await enviarLeadMeta({ lead: { ...LEAD, email: "juan@example.com" }, meta: META, headers: headers(), env: ENV, ref: 7, fetch: g.fetch, log: l });
    assert.deepEqual(r, { enviado: false, motivo: "error", status: 400 });
    assert.deepEqual(l.lines.error, ["meta capi (lead 7): Meta respondió HTTP 400 (Invalid parameter)"]);
    const todo = JSON.stringify(l.lines);
    for (const secreto of [ENV.META_CAPI_TOKEN, "Juan", "juan@example.com", "981", "181.120.10.20"]) assert.equal(todo.includes(secreto), false, secreto);
  });
  test("si la red falla o Meta no responde en el tope, devuelve sin lanzar", async () => {
    const l = fakeLog();
    const r = await enviarLeadMeta({ lead: LEAD, meta: META, headers: headers(), env: ENV, fetch: fakeGraph({ fail: new TypeError("fetch failed") }).fetch, log: l });
    assert.deepEqual(r, { enviado: false, motivo: "error" });
    const colgado = (url, init) => new Promise((_, reject) => init.signal.addEventListener("abort", () => reject(Object.assign(new Error("aborted"), { name: "AbortError" }))));
    const t0 = Date.now();
    const r2 = await enviarLeadMeta({ lead: LEAD, meta: META, headers: headers(), env: ENV, fetch: colgado, log: l, timeoutMs: 50 });
    assert.deepEqual(r2, { enviado: false, motivo: "error" });
    assert.ok(Date.now() - t0 < 1000);
    assert.deepEqual(l.lines.error, ["meta capi: no se pudo enviar", "meta capi: Meta no respondió en 0.05 s"]);
  });
});

describe("lead.js manda el Lead a Meta cuando Bitrix lo crea", () => {
  const BITRIX = "https://bitrix.test/rest/1/abc/";
  /** fetch falso para Bitrix y la Graph API. graph: función que decide la respuesta de Meta. */
  function withFakes(fn, { bitrixFail = false, graph = () => new Response(JSON.stringify({ events_received: 1 })) } = {}) {
    return async () => {
      const real = globalThis.fetch;
      const meta = [];
      globalThis.fetch = async (url, init = {}) => {
        const u = String(url);
        if (u.startsWith("https://graph.facebook.com/")) { meta.push(JSON.parse(init.body)); return graph(); }
        const m = u.replace(BITRIX, "").replace(".json", "");
        if (bitrixFail && m === "crm.lead.add") return new Response(JSON.stringify({ error: "X", error_description: "caído" }));
        const result = { "user.get": [{ ID: "139", NAME: "ANA", LAST_NAME: "P" }], "crm.lead.list": [], "crm.lead.add": 555 }[m];
        return new Response(JSON.stringify({ result }));
      };
      try { await fn(meta); } finally { globalThis.fetch = real; }
    };
  }
  let n = 0;
  const leadReq = (body, extra = {}) => new Request("http://leads-api/lead", {
    method: "POST", headers: { "cf-connecting-ip": `10.9.0.${++n}`, "user-agent": CHROME, referer: "https://zeekrlife.com.py/modelos/zeekr-7x/", ...extra }, body: JSON.stringify(body),
  });
  const env = { BITRIX_WEBHOOK_URL: BITRIX, ADVISOR_IDS: "139", ...ENV };
  const body = { nombre: "Juan Pérez", telefono: "0981 123 456", tipo: "Consulta", pagina: PAGINA, idioma: "es", website: "", meta: META };

  test("lead creado → un Lead a Meta con el event_id del navegador; la respuesta no cambia", withFakes(async (meta) => {
    const res = await handle(leadReq(body), env);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { ok: true, leadId: 555, asesor: "Ana" });
    assert.equal(meta.length, 1, "en Cloudflare (sin metaEnSegundoPlano) handle espera a la API de conversiones");
    const ev = meta[0].data[0];
    assert.equal(ev.event_id, META.event_id);
    assert.deepEqual(ev.custom_data, { content_name: "Consulta" });
    assert.deepEqual(ev.user_data.ph, [h("595981123456")]);
    assert.deepEqual(ev.user_data.fn, [h("juan")]);
    assert.deepEqual(ev.user_data.ln, [h("pérez")]);
    assert.equal(ev.user_data.client_ip_address, `10.9.0.${n}`);
  }));

  test("honeypot, datos inválidos, rechazo de cookies o Bitrix caído → nada a Meta", withFakes(async (meta) => {
    assert.equal((await handle(leadReq({ ...body, website: "spam" }), env)).status, 200);
    assert.equal((await handle(leadReq({ ...body, nombre: "x" }), env)).status, 422);
    assert.equal((await handle(leadReq({ ...body, meta: { ...META, consentimiento: "rechazado" } }), env)).status, 200);
    assert.equal(meta.length, 0);
  }));

  test("Bitrix con error → 502 y nada a Meta", withFakes(async (meta) => {
    assert.equal((await handle(leadReq(body), env)).status, 502);
    assert.equal(meta.length, 0);
  }, { bitrixFail: true }));

  test("si Meta falla o tira un error, la respuesta del lead es la misma", withFakes(async (meta) => {
    const res = await handle(leadReq(body), env);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { ok: true, leadId: 555, asesor: "Ana" });
    assert.equal(meta.length, 1);
  }, { graph: () => { throw new Error("red caída"); } }));

  test("sin META_CAPI_TOKEN el lead funciona igual y no se llama a Meta", withFakes(async (meta) => {
    const res = await handle(leadReq(body), { BITRIX_WEBHOOK_URL: BITRIX, ADVISOR_IDS: "139" });
    assert.equal(res.status, 200);
    assert.equal(meta.length, 0);
  }));

  test("en Node (metaEnSegundoPlano) responde sin esperar a Meta", async () => {
    let soltar;
    const pendiente = new Promise((r) => { soltar = r; });
    let llamadas = 0;
    await withFakes(async () => {
      const res = await handle(leadReq(body), env, { metaEnSegundoPlano: true });
      assert.equal(res.status, 200, "respondió con Meta todavía colgado");
      for (let i = 0; i < 20 && !llamadas; i++) await new Promise((r) => setTimeout(r, 5));
      assert.equal(llamadas, 1);
      soltar(new Response(JSON.stringify({ events_received: 1 })));
      await new Promise((r) => setTimeout(r, 10));
    }, { graph: () => { llamadas++; return pendiente; } })();
  });
});
