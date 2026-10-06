// QA del filtro de zona (Asunción / Ciudad del Este / otras zonas) de ZEEKR Paraguay, con Chromium real.
//   node scripts/qa-sucursal.mjs [base]          base por defecto: http://127.0.0.1:8812 (python3 -m http.server 8812 en la raíz del repo)
//   PLAYWRIGHT=/ruta/a/playwright/index.mjs CHROME=/usr/bin/google-chrome SHOTS=/ruta/capturas node scripts/qa-sucursal.mjs <base>
// No toca el CRM: /api/lead se intercepta (page.route) y los enlaces a wa.me se responden con un stub, así que sirve igual
// contra producción o contra la vista previa. Sale con código 1 si algo falla.
import fs from "node:fs";

const PW = process.env.PLAYWRIGHT || "/home/croman/.hermes/hermes-agent/node_modules/playwright/index.mjs";
const CHROME = process.env.CHROME || "/usr/bin/google-chrome";
const BASE = (process.argv[2] || "http://127.0.0.1:8812").replace(/\/$/, "");
const SHOTS = process.env.SHOTS || "";
if (SHOTS) fs.mkdirSync(SHOTS, { recursive: true });
const { chromium } = await import(PW);

const WA_ASU = "595971370006", WA_CDE = "595972350200";
const LANGS = [
  { p: "", name: "es", h2: "¿Con qué sucursal querés hablar?", lab: "Zona", ph: "Elegí tu zona", asu: "Asunción", cde: "Ciudad del Este", otr: "Otras zonas", suc: "Sucursal" },
  { p: "/en", name: "en", h2: "Which branch would you like to talk to?", lab: "Area", ph: "Choose your area", asu: "Asunción", cde: "Ciudad del Este", otr: "Other areas", suc: "Branch" },
  { p: "/pt", name: "pt", h2: "Com qual filial você quer falar?", lab: "Região", ph: "Escolha sua região", asu: "Assunção", cde: "Ciudad del Este", otr: "Outras regiões", suc: "Filial" },
  { p: "/zh", name: "zh", h2: "您想联系哪家门店？", lab: "区域", ph: "请选择您所在的区域", asu: "亚松森", cde: "东方市", otr: "其他地区", suc: "门店" },
];

let fails = 0, checks = 0;
const ok = (cond, msg) => { checks++; if (!cond) { fails++; console.log("  ✗", msg); } else console.log("  ✓", msg); };
const shot = async (page, name) => { if (SHOTS) { await page.waitForTimeout(500); await page.screenshot({ path: `${SHOTS}/${name}.png` }); } };   // 500 ms: que terminen las animaciones

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const errors = [];

async function newPage(viewport, { fail500 = false } = {}) {
  const context = await browser.newContext({ viewport, locale: "es-PY" });
  await context.addInitScript(() => {
    localStorage.setItem("zeekr-consent", JSON.stringify({ necessary: true, analytics: false, at: Date.now() }));
    window.__ev = [];
    window.gtag = function () { window.__ev.push([].slice.call(arguments)); };
  });
  await context.route(/https:\/\/(wa\.me|api\.whatsapp\.com)\/.*/, (r) => r.fulfill({ status: 200, contentType: "text/html", body: "<title>wa</title>" }));
  const page = await context.newPage();
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource|ERR_|net::/.test(m.text())) errors.push(`console: ${m.text()}`); });
  const posted = [];
  await page.route("**/api/lead", async (route) => {
    posted.push(JSON.parse(route.request().postData() || "{}"));
    if (fail500) return route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ ok: false, detail: "x" }) });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true, leadId: 1, asesor: "Walter", sucursal: posted.at(-1).sucursal }) });
  });
  return { context, page, posted };
}
const events = (page) => page.evaluate(() => window.__ev.filter((e) => e[1] === "click_whatsapp").map((e) => e[2]));
const open = (page) => page.evaluate(() => !!document.querySelector("#waChooser")?.open);

/* ---------- 1) selector de WhatsApp, en los 4 idiomas ---------- */
for (const L of LANGS) {
  console.log(`\n[${L.name}] selector de WhatsApp`);
  const { context, page } = await newPage({ width: 1440, height: 900 });
  await page.goto(`${BASE}${L.p}/`, { waitUntil: "load" });
  await page.click(".header-wa");
  ok(await open(page), "el botón de WhatsApp del encabezado abre el selector (no sale directo a WhatsApp)");
  ok((await page.textContent("#wcTitle")).trim() === L.h2, `título: ${L.h2}`);
  const opts = await page.$$eval("#waChooser a.wc-opt", (as) => as.map((a) => ({ href: a.href, name: a.querySelector(".wc-name").textContent.trim(), num: a.querySelector(".wc-num").textContent.trim() })));
  ok(opts.length === 3 && opts[0].href === `https://wa.me/${WA_ASU}` && opts[1].href === `https://wa.me/${WA_CDE}` && opts[2].href === `https://wa.me/${WA_ASU}`, "tres opciones: Asunción, Ciudad del Este y Otras zonas (esta, con el número de Asunción)");
  ok(opts[0].name === L.asu && opts[1].name === L.cde && opts[2].name === L.otr, `textos traducidos: ${L.asu} / ${L.cde} / ${L.otr}`);
  ok(opts[0].num === "0971 370 006" && opts[1].num === "0972 350 200" && opts[2].num === "0971 370 006", "se ve el número de cada una");
  ok((await events(page)).length === 0, "abrir el selector no cuenta como clic a WhatsApp");
  await shot(page, `chooser-${L.name}`);
  const [popup] = await Promise.all([context.waitForEvent("page"), page.click('a.wc-opt[data-wc-opt="cde"]')]);
  await popup.waitForURL(/wa\.me/, { timeout: 8000 }).catch(() => {});
  ok(popup.url().startsWith(`https://wa.me/${WA_CDE}`), `Ciudad del Este abre wa.me/${WA_CDE} (${popup.url()})`);
  await page.waitForFunction(() => !document.querySelector("#waChooser").open, null, { timeout: 3000 }).catch(() => {});
  ok(!(await open(page)), "el selector se cierra al elegir");
  const ev = await events(page);
  ok(ev.length === 1 && ev[0].sucursal === "cde" && ev[0].location === "header", `un solo click_whatsapp con sucursal=cde y location=header (${JSON.stringify(ev)})`);
  // Otras zonas: abre el WhatsApp de Asunción y cuenta con sucursal=otras
  await page.click(".header-wa");
  ok(await open(page), "el selector se vuelve a abrir");
  const [popup2] = await Promise.all([context.waitForEvent("page"), page.click('a.wc-opt[data-wc-opt="otras"]')]);
  await popup2.waitForURL(/wa\.me/, { timeout: 8000 }).catch(() => {});
  const ev2 = (await events(page)).at(-1);
  ok(popup2.url().startsWith(`https://wa.me/${WA_ASU}`) && ev2?.sucursal === "otras" && ev2?.location === "header", `Otras zonas abre wa.me/${WA_ASU} y cuenta con sucursal=otras (${JSON.stringify(ev2)})`);
  // teléfonos: el de CDE aparece en el pie y en la franja de contacto
  const tels = await page.$$eval('a[href^="tel:"]', (as) => [...new Set(as.map((a) => a.getAttribute("href")))]);
  ok(tels.includes("tel:+595972350200"), "el teléfono de ventas de Ciudad del Este está en el pie / la franja de contacto");
  await context.close();
}

/* ---------- 2) cerrar el selector y accesibilidad ---------- */
console.log("\n[es] cerrar, foco y modal de contacto");
{
  const { context, page } = await newPage({ width: 1440, height: 900 });
  await page.goto(`${BASE}/`, { waitUntil: "load" });
  await page.click(".header-wa");
  await page.keyboard.press("Escape");
  ok(!(await open(page)), "Esc cierra el selector");
  ok(await page.evaluate(() => document.activeElement?.classList.contains("header-wa")), "el foco vuelve al botón que lo abrió");
  await page.click(".header-wa");
  await page.mouse.click(6, 6);
  ok(!(await open(page)), "un clic en el fondo oscuro lo cierra");
  await page.click(".header-wa");
  await page.click("#waChooser [data-wc-close]");
  ok(!(await open(page)), "la X lo cierra");
  ok((await events(page)).length === 0, "ninguna de esas formas de cerrar cuenta como clic a WhatsApp");
  // pie y franja de contacto
  for (const [sel, label] of [['footer a[data-sucursal-wa]', "pie"], ['.contact-strip a[data-sucursal-wa]', "franja de contacto"]]) {
    await page.locator(sel).first().scrollIntoViewIfNeeded();
    await page.locator(sel).first().click();
    ok(await open(page), `el WhatsApp del ${label} abre el selector`);
    await page.keyboard.press("Escape");
  }
  // sobre el modal de contacto
  await page.locator('footer [data-open-contact][data-intent="test-drive"]').first().click();
  ok(await page.evaluate(() => !document.querySelector("#contactModal").hidden), "se abre el modal de prueba de manejo");
  ok(await page.evaluate(() => !document.querySelector("#waChooser").hasAttribute("inert")), "el selector no queda inerte cuando hay un modal abierto");
  await page.click("#contactModal [data-sucursal-wa]");
  ok(await open(page), "el WhatsApp del modal abre el selector encima");
  await page.keyboard.press("Escape");
  ok(!(await open(page)) && await page.evaluate(() => !document.querySelector("#contactModal").hidden), "Esc cierra solo el selector: el modal de contacto sigue abierto");
  await page.fill("#cf-nombre", "Prueba");
  ok((await page.inputValue("#cf-nombre")) === "Prueba", "el modal sigue usable después de cerrar el selector");
  const [popup] = await Promise.all([context.waitForEvent("page"), (async () => { await page.click("#contactModal [data-sucursal-wa]"); await page.click('a.wc-opt[data-wc-opt="asuncion"]'); })()]);
  await popup.waitForURL(/wa\.me/, { timeout: 8000 }).catch(() => {});
  ok(popup.url().startsWith(`https://wa.me/${WA_ASU}`), `Asunción abre wa.me/${WA_ASU}`);
  const ev = await events(page);
  ok(ev.at(-1)?.sucursal === "asuncion" && ev.at(-1)?.location === "formulario", `se registra sucursal=asuncion y location=formulario (${JSON.stringify(ev.at(-1))})`);
  await context.close();
}

/* ---------- 3) formulario: sucursal obligatoria y número de WhatsApp según la sucursal ---------- */
for (const L of LANGS) {
  console.log(`\n[${L.name}] formulario`);
  const { context, page, posted } = await newPage({ width: 1440, height: 900 });
  await page.goto(`${BASE}${L.p}/`, { waitUntil: "load" });
  await page.locator('footer [data-open-contact][data-intent="test-drive"]').first().click();
  const sel = await page.$$eval("#cf-sucursal option", (os) => os.map((o) => ({ v: o.value, t: o.textContent.trim(), d: o.disabled })));
  ok(sel.length === 4 && sel[0].v === "" && sel[0].d && sel[0].t === L.ph && sel[1].t === L.asu && sel[2].t === L.cde && sel[3].t === L.otr && sel.slice(1).map((o) => o.v).join() === "asuncion,cde,otras", `selector de zona sin valor por defecto: ${L.ph} / ${L.asu} / ${L.cde} / ${L.otr}`);
  ok((await page.textContent('label[for="cf-sucursal"]')).trim() === L.lab, `el campo se llama "${L.lab}"`);
  await page.fill("#cf-nombre", "Ana Martínez");
  await page.fill("#cf-tel", "0981 123 456");
  await page.click("#waForm [type=submit]");
  ok(posted.length === 0, "sin zona no se envía nada");
  ok(await page.evaluate(() => document.querySelector("#cf-sucursal").closest(".field").classList.contains("has-error") && !document.querySelector("#cf-sucursal-error").hidden), "marca el error en Sucursal");
  ok(await page.evaluate(() => document.activeElement.id === "cf-sucursal"), "el foco va al campo que falta");
  if (L.name === "es") await shot(page, "form-error-es");
  await page.selectOption("#cf-sucursal", "cde");
  ok(await page.evaluate(() => document.querySelector("#cf-sucursal-error").hidden), "elegir zona limpia el error");
  await page.click("#waForm [type=submit]");
  await page.waitForSelector(".form-success:not([hidden])");
  ok(posted.length === 1 && posted[0].sucursal === "cde" && posted[0].nombre === "Ana Martínez" && posted[0].tipo === "Prueba de manejo", `el pedido a la API lleva sucursal=cde (${JSON.stringify(posted[0]).slice(0, 150)}…)`);
  const href = await page.getAttribute("[data-success-wa]", "href");
  ok(href.startsWith(`https://wa.me/${WA_CDE}?text=`) && decodeURIComponent(href).includes(`${L.suc}: ${L.cde}`), `"Continuar por WhatsApp" va al número de CDE e incluye "${L.suc}: ${L.cde}"`);
  ok((await page.textContent(".form-success")).includes("Walter"), "la pantalla final nombra al asesor que devolvió la API");
  if (L.name === "es") await shot(page, "form-success-es");
  await page.click(".form-success [data-close-contact]");
  await page.locator('footer [data-open-contact][data-intent="test-drive"]').first().click();
  ok((await page.inputValue("#cf-sucursal")) === "", "al volver a abrir el formulario, la sucursal vuelve a estar sin elegir");
  await page.fill("#cf-nombre", "Ana Martínez");
  await page.fill("#cf-tel", "0981 123 456");
  await page.selectOption("#cf-sucursal", "asuncion");
  await page.click("#waForm [type=submit]");
  await page.waitForSelector(".form-success:not([hidden])");
  ok(posted.at(-1).sucursal === "asuncion", "sucursal=asuncion en el segundo envío");
  const href2 = await page.getAttribute("[data-success-wa]", "href");
  ok(href2.startsWith(`https://wa.me/${WA_ASU}?text=`) && decodeURIComponent(href2).includes(`${L.suc}: ${L.asu}`), "con Asunción, WhatsApp va al número de siempre");
  await page.click(".form-success [data-close-contact]");
  await page.locator('footer [data-open-contact][data-intent="test-drive"]').first().click();
  await page.fill("#cf-nombre", "Ana Martínez");
  await page.fill("#cf-tel", "0981 123 456");
  await page.selectOption("#cf-sucursal", "otras");
  await page.click("#waForm [type=submit]");
  await page.waitForSelector(".form-success:not([hidden])");
  ok(posted.at(-1).sucursal === "otras", "sucursal=otras en el tercer envío");
  const href3 = await page.getAttribute("[data-success-wa]", "href");
  ok(href3.startsWith(`https://wa.me/${WA_ASU}?text=`) && decodeURIComponent(href3).includes(`${L.suc}: ${L.otr}`), `con Otras zonas, WhatsApp va al número de Asunción e incluye "${L.suc}: ${L.otr}"`);
  await context.close();
}

console.log("\n[es] la API caída → respaldo a WhatsApp con el número de la sucursal");
{
  const { context, page, posted } = await newPage({ width: 1440, height: 900 }, { fail500: true });
  await page.goto(`${BASE}/`, { waitUntil: "load" });
  await page.locator('footer [data-open-contact][data-intent="test-drive"]').first().click();
  await page.fill("#cf-nombre", "Ana Martínez");
  await page.fill("#cf-tel", "0981 123 456");
  await page.selectOption("#cf-sucursal", "cde");
  const [popup] = await Promise.all([context.waitForEvent("page"), page.click("#waForm [type=submit]")]);
  await popup.waitForURL(/wa\.me/, { timeout: 8000 }).catch(() => {});
  ok(posted.length === 1 && popup.url().startsWith(`https://wa.me/${WA_CDE}?text=`), `el respaldo abre WhatsApp de Ciudad del Este (${popup.url().slice(0, 60)}…)`);
  await context.close();
}

/* ---------- 4) móvil ---------- */
console.log("\n[es] móvil 390x844");
{
  const { context, page } = await newPage({ width: 390, height: 844 });
  await page.goto(`${BASE}/`, { waitUntil: "load" });
  await page.locator("footer a[data-sucursal-wa]").first().scrollIntoViewIfNeeded();
  await page.locator("footer a[data-sucursal-wa]").first().click();
  ok(await open(page), "en el celular, el WhatsApp del pie abre el selector");
  const box = await page.locator("#waChooser .modal-panel").boundingBox();
  ok(box && box.x >= 0 && box.x + box.width <= 390, `el selector entra en la pantalla (${Math.round(box?.x)}–${Math.round(box?.x + box?.width)} de 390)`);
  await shot(page, "chooser-mobile");
  await page.keyboard.press("Escape");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.click(".burger");
  await page.locator('#mobileMenu [data-open-contact][data-intent="test-drive"]').first().click().catch(async () => { await page.keyboard.press("Escape"); await page.locator('footer [data-open-contact][data-intent="test-drive"]').first().click(); });
  await page.waitForSelector("#contactModal:not([hidden])");
  await page.locator("#cf-sucursal").scrollIntoViewIfNeeded();
  await shot(page, "form-mobile");
  const over = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  ok(!over, "sin desborde horizontal con el formulario abierto");
  await page.locator("#contactModal .contact-cards").scrollIntoViewIfNeeded();
  await shot(page, "cards-mobile");
  await context.close();
}

console.log("\n[es] escritorio: capturas del formulario y del pie");
{
  const { context, page } = await newPage({ width: 1440, height: 900 });
  await page.goto(`${BASE}/`, { waitUntil: "load" });
  await page.locator("footer").scrollIntoViewIfNeeded();
  await shot(page, "footer-desktop");
  await page.locator('footer [data-open-contact][data-intent="contacto"]').first().click();
  await shot(page, "modal-contacto-desktop");
  const over = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  ok(!over, "sin desborde horizontal con el modal de contacto abierto");
  await context.close();
}

ok(errors.length === 0, `sin errores de consola ni de página${errors.length ? ": " + errors.slice(0, 3).join(" | ") : ""}`);
await browser.close();
console.log(`\n${checks - fails}/${checks} comprobaciones OK${fails ? ` — ${fails} FALLARON` : ""}`);
process.exit(fails ? 1 : 0);
