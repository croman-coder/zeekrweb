// Tests de la API de leads de ZEEKR (functions/_lib/lead.js). Sin dependencias: node --test api/
import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { normalizePhone, validate, nextAdvisor, createLead, handle, resetState, LeadError } from "../functions/_lib/lead.js";

const ENV = { BITRIX_WEBHOOK_URL: "https://bitrix.test/rest/19/secreto/", ADVISOR_IDS: "139,2171,31765" };

/** Bitrix falso: user.get / crm.lead.list / crm.lead.add sobre un estado en memoria. */
function fakeBitrix({ users = [], leads = [] } = {}) {
  const calls = [];
  let nextId = 1000;
  const state = { calls, leads, users };
  state.fetch = async (url, init = {}) => {
    const method = new URL(url).pathname.split("/").pop().replace(/\.json$/, "");
    const body = init.body ? JSON.parse(init.body) : {};
    calls.push({ method, body });
    const ok = (result) => new Response(JSON.stringify({ result }), { status: 200 });
    if (method === "user.get") {
      const fl = body.filter || {};
      let r = state.users.filter((u) => u.ACTIVE !== false);
      if (fl.UF_DEPARTMENT != null) r = r.filter((u) => u.UF_DEPARTMENT.includes(fl.UF_DEPARTMENT));
      if (fl.ID) r = r.filter((u) => fl.ID.includes(Number(u.ID)));
      return ok(r);
    }
    if (method === "crm.lead.list") {
      const r = state.leads.filter((l) => l.SOURCE_ID === body.filter?.SOURCE_ID).sort((a, b) => b.ID - a.ID);
      return ok(r.map((l) => ({ ID: String(l.ID), ASSIGNED_BY_ID: String(l.ASSIGNED_BY_ID) })));
    }
    if (method === "crm.lead.add") {
      const id = nextId++;
      state.leads.push({ ID: id, SOURCE_ID: body.fields.SOURCE_ID, ASSIGNED_BY_ID: body.fields.ASSIGNED_BY_ID, fields: body.fields });
      return ok(id);
    }
    return new Response(JSON.stringify({ error: "ERROR_METHOD_NOT_FOUND", error_description: method }), { status: 200 });
  };
  return state;
}

// Departamento 29 "ZEEKR" y 133 "MULTIMARCAS CDE" de Bitrix tal como estaban el 02/10/2026 (cargos aproximados).
const TEAM = [
  { ID: "139", NAME: "WALTER", LAST_NAME: "LEGUIZAMON", WORK_POSITION: "ASESOR DE VENTAS", UF_DEPARTMENT: [29] },
  { ID: "2171", NAME: "ALAN", LAST_NAME: "RIQUELME", WORK_POSITION: "ASESOR DE VENTAS", UF_DEPARTMENT: [29] },
  { ID: "31765", NAME: "MARTIN", LAST_NAME: "TROCHE", WORK_POSITION: "ASESOR DE VENTAS", UF_DEPARTMENT: [29] },
  { ID: "49", NAME: "VALERIA", LAST_NAME: "MARTINEZ", WORK_POSITION: "Brand Manager", UF_DEPARTMENT: [29, 133] },
  { ID: "73", NAME: "LUIS", LAST_NAME: "BAEZ", WORK_POSITION: "SUB GERENTE", UF_DEPARTMENT: [29] },
];
const CDE = [
  { ID: "21707", NAME: "WALTER", LAST_NAME: "BAVERA", WORK_POSITION: "Jefe de Ventas Multimarcas CDE", UF_DEPARTMENT: [133] },
  { ID: "39", NAME: "BRUNO", LAST_NAME: "CAPOSSELA", WORK_POSITION: "Gerente de Ventas", UF_DEPARTMENT: [133] },
  { ID: "16001", NAME: "MATHIAS", LAST_NAME: "ACOSTA", WORK_POSITION: "ASESOR RENAULT JAC CDE", UF_DEPARTMENT: [141] },
  { ID: "19827", NAME: "PEDRO", LAST_NAME: "OCAMPOS", WORK_POSITION: "ASESOR DE VENTAS", UF_DEPARTMENT: [141] },
];
const ALL = [...TEAM, ...CDE];
const good = { nombre: "Ana Martínez", telefono: "0981 123 456", modelo: "ZEEKR 7X", mensaje: "Quiero probarlo" };

let realFetch;
beforeEach(() => { resetState(); realFetch = globalThis.fetch; });
afterEach(() => { globalThis.fetch = realFetch; });
const use = (bx) => { globalThis.fetch = bx.fetch; return bx; };
const added = (bx) => bx.calls.filter((c) => c.method === "crm.lead.add").map((c) => c.body.fields);

describe("normalizePhone", () => {
  for (const [raw, out] of [["0981 123 456", "+595981123456"], ["+595 981 123 456", "+595981123456"], ["595981123456", "+595981123456"]])
    test(`${raw} → ${out}`, () => assert.equal(normalizePhone(raw), out));
});

describe("validate", () => {
  test("datos mínimos válidos; tipo por defecto Prueba de manejo", () => {
    const l = validate(good);
    assert.equal(l.nombre, "Ana Martínez"); assert.equal(l.tipo, "Prueba de manejo"); assert.equal(l.sucursal, null);
  });
  test("nombre o teléfono inválidos → 422", () => {
    assert.throws(() => validate({ ...good, nombre: "A" }), (e) => e instanceof LeadError && e.status === 422);
    assert.throws(() => validate({ ...good, telefono: "123" }), (e) => e instanceof LeadError && e.status === 422);
  });
  test("sucursal: reconoce CDE (varias grafías); otro valor es Asunción; sin dato queda en null", () => {
    for (const v of ["cde", "CDE", " Ciudad del Este ", "ciudad-del-este"]) assert.equal(validate({ ...good, sucursal: v }).sucursal, "cde", v);
    for (const v of ["asuncion", "Asunción y resto del país", "otra"]) assert.equal(validate({ ...good, sucursal: v }).sucursal, "asuncion", v);
    for (const v of [undefined, null, "", "   "]) assert.equal(validate({ ...good, sucursal: v }).sucursal, null, String(v));
  });
});

describe("Asunción (el reparto de siempre)", () => {
  test("con ADVISOR_IDS reparte entre ellos y la cola corre sola", async () => {
    const bx = use(fakeBitrix({ users: ALL }));
    const got = [];
    for (let i = 0; i < 6; i++) {
      const a = await nextAdvisor(ENV);
      got.push(a.id);
      bx.leads.push({ ID: 3000 + i, SOURCE_ID: "WEB_SR_ZEEKR", ASSIGNED_BY_ID: a.id });
    }
    assert.deepEqual(got, [139, 2171, 31765, 139, 2171, 31765]);
  });
  test("sin ADVISOR_IDS: departamento 29 por cargo ASESOR (no entran la brand manager ni el sub gerente)", async () => {
    const bx = use(fakeBitrix({ users: ALL }));
    const a = await nextAdvisor({ BITRIX_WEBHOOK_URL: ENV.BITRIX_WEBHOOK_URL });
    assert.equal(a.id, 139);
    assert.equal(bx.calls.find((c) => c.method === "user.get").body.filter.UF_DEPARTMENT, 29);
  });
  test("lead sin sucursal o de Asunción: asesor de Zeekr, sin ciudad", async () => {
    const bx = use(fakeBitrix({ users: ALL }));
    await createLead({ ...good, sucursal: "asuncion" }, ENV);
    await createLead(good, ENV);
    const [a, b] = added(bx);
    assert.equal(a.ASSIGNED_BY_ID, 139); assert.equal(b.ASSIGNED_BY_ID, 2171);
    assert.equal(a.ADDRESS_CITY, undefined); assert.equal(b.ADDRESS_CITY, undefined);
    assert.match(a.COMMENTS, /Sucursal elegida: Asunción y resto del país/);
    assert.ok(!/Sucursal elegida/.test(b.COMMENTS));
    assert.equal(a.SOURCE_ID, "WEB_SR_ZEEKR"); assert.equal(a.UF_CRM_1775591500778, 301);
  });
});

describe("Sucursal Ciudad del Este (CDE)", () => {
  const cdeBody = { ...good, sucursal: "cde" };

  test("sin CDE_ADVISOR_IDS: el departamento 133 no tiene ASESOR → recibe el jefe de ventas multimarca de CDE", async () => {
    const bx = use(fakeBitrix({ users: ALL }));
    const r = await createLead(cdeBody, ENV);
    assert.equal(r.ok, true); assert.equal(r.sucursal, "cde");
    assert.equal(r.asesor, null);                                // el de reserva no figura en el equipo: la pantalla dice "Un asesor te contacta"
    assert.equal(added(bx)[0].ASSIGNED_BY_ID, 21707);
    assert.equal(bx.calls.find((c) => c.method === "user.get").body.filter.UF_DEPARTMENT, 133);
  });
  test("configuración de producción (CDE_ADVISOR_IDS=16001): los de CDE van todos a Mathias (Pedro es exclusivo de Renault) y nunca caen en Asunción ni en el jefe", async () => {
    const bx = use(fakeBitrix({ users: ALL }));
    const env = { ...ENV, CDE_ADVISOR_IDS: "16001" };
    const got = [];
    for (let i = 0; i < 6; i++) {
      resetState();
      const r = await createLead(cdeBody, env);
      assert.equal(r.sucursal, "cde");
      got.push(added(bx).at(-1).ASSIGNED_BY_ID);
    }
    assert.ok(got.every((id) => id === 16001), `solo Mathias (16001), ni Pedro (19827) ni el jefe: ${got}`);
    assert.deepEqual([...new Set(added(bx).map((f) => f.ADDRESS_CITY))], ["Ciudad del Este"]);
    // y con la cola actualizándose sigue siendo Mathias (único del pool)
    const alt = use(fakeBitrix({ users: ALL }));
    const seq = [];
    for (let i = 0; i < 4; i++) {
      resetState();
      const a = await nextAdvisor(env, "cde");
      seq.push(a.id);
      alt.leads.push({ ID: 5000 + i, SOURCE_ID: "WEB_SR_ZEEKR", ASSIGNED_BY_ID: a.id });
    }
    assert.deepEqual(seq, [16001, 16001, 16001, 16001]);
  });
  test("CDE_ADVISOR_IDS explícito arma el equipo de CDE y rota entre ellos", async () => {
    const bx = use(fakeBitrix({ users: ALL }));
    const env = { ...ENV, CDE_ADVISOR_IDS: "21707, 39" };
    const got = [];
    for (let i = 0; i < 4; i++) {
      const a = await nextAdvisor(env, "cde");
      got.push(a.id);
      bx.leads.push({ ID: 3000 + i, SOURCE_ID: "WEB_SR_ZEEKR", ASSIGNED_BY_ID: a.id });
    }
    assert.deepEqual(got, [39, 21707, 39, 21707]); // sin lead previo gana el id más bajo (39); después alterna
    assert.deepEqual(bx.calls.find((c) => c.method === "user.get").body.filter.ID, [21707, 39]);
  });
  test("lead de CDE: ciudad, sucursal en las notas y en el origen; marca y fuente de ZEEKR", async () => {
    const bx = use(fakeBitrix({ users: ALL }));
    await createLead(cdeBody, { ...ENV, CDE_ADVISOR_IDS: "21707" });
    const [f] = added(bx);
    assert.equal(f.ASSIGNED_BY_ID, 21707);
    assert.equal(f.ADDRESS_CITY, "Ciudad del Este");
    assert.match(f.COMMENTS, /Sucursal elegida: Ciudad del Este/);
    assert.match(f.SOURCE_DESCRIPTION, /Ciudad del Este/);
    assert.equal(f.SOURCE_ID, "WEB_SR_ZEEKR"); assert.equal(f.UF_CRM_1775591500778, 301);
    assert.match(f.TITLE, /ZEEKR 7X - Prueba de manejo - ZEEKR Web Santa Rosa/);
  });
  test("la cola de Asunción no cuenta para CDE ni al revés; cada equipo se cachea por separado", async () => {
    const bx = use(fakeBitrix({ users: ALL, leads: [
      { ID: 1, SOURCE_ID: "WEB_SR_ZEEKR", ASSIGNED_BY_ID: 139 },
      { ID: 2, SOURCE_ID: "WEB_SR_ZEEKR", ASSIGNED_BY_ID: 21707 },
    ] }));
    const env = { ...ENV, CDE_ADVISOR_IDS: "21707,39" };
    assert.equal((await nextAdvisor(env, "cde")).id, 39);      // 21707 ya recibió el último; 39 nunca
    assert.equal((await nextAdvisor(env)).id, 2171);           // Asunción: 139 recibió; gana el siguiente que nunca recibió
    await nextAdvisor(env, "cde"); await nextAdvisor(env);
    assert.equal(bx.calls.filter((c) => c.method === "user.get").length, 2);
  });
  test("CDE_FALLBACK_ASSIGNEE_ID y CDE_DEPARTMENT_ID se pueden cambiar; el responsable de Asunción no recibe CDE", async () => {
    const bx = use(fakeBitrix({ users: TEAM }));                // Bitrix sin nadie en el departamento 133
    await createLead(cdeBody, { ...ENV, FALLBACK_ASSIGNEE_ID: "73" });
    assert.equal(added(bx)[0].ASSIGNED_BY_ID, 21707);
    resetState();
    await createLead(cdeBody, { ...ENV, CDE_FALLBACK_ASSIGNEE_ID: "45", CDE_DEPARTMENT_ID: "135" });
    assert.equal(added(bx)[1].ASSIGNED_BY_ID, 45);
    assert.equal(bx.calls.filter((c) => c.method === "user.get").at(-1).body.filter.UF_DEPARTMENT, 135);
  });
  test("honeypot: un robot con sucursal no crea nada ni toca Bitrix", async () => {
    const bx = use(fakeBitrix({ users: ALL }));
    const r = await createLead({ ...cdeBody, website: "http://spam.test" }, ENV);
    assert.deepEqual(r, { ok: true, leadId: null });
    assert.equal(bx.calls.length, 0);
  });
  test("HTTP: sucursal=cde responde 200 con el nombre del asesor y el lead queda en CDE", async () => {
    const bx = use(fakeBitrix({ users: ALL }));
    const logs = [];
    const realLog = console.log; console.log = (...a) => logs.push(a.join(" "));
    let res;
    try {
      res = await handle(new Request("http://api.test/lead", {
        method: "POST", headers: { "content-type": "application/json", "cf-connecting-ip": "3.3.3.3" }, body: JSON.stringify(cdeBody),
      }), { ...ENV, CDE_ADVISOR_IDS: "21707" });
    } finally { console.log = realLog; }
    assert.equal(res.status, 200);
    const j = await res.json();
    assert.equal(j.ok, true); assert.equal(j.asesor, "Walter"); assert.equal(j.sucursal, "cde");
    assert.equal(added(bx)[0].ASSIGNED_BY_ID, 21707);
    assert.ok(logs.some((l) => /sucursal=cde/.test(l)), logs.join("|"));
  });
  test("HTTP: sin Bitrix configurado → 503 y no revienta", async () => {
    use(fakeBitrix({ users: ALL }));
    const realErr = console.error; console.error = () => {};
    let res;
    try {
      res = await handle(new Request("http://api.test/lead", {
        method: "POST", headers: { "content-type": "application/json", "cf-connecting-ip": "4.4.4.4" }, body: JSON.stringify(cdeBody),
      }), {});
    } finally { console.error = realErr; }
    assert.equal(res.status, 503);
  });
});
