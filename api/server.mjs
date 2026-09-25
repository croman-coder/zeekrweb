// Servidor Node (Coolify) para la API de leads. Reusa functions/_lib/lead.js tal cual.
// Traefik publica la app bajo /api con stripprefix: /api/lead llega como /lead y /api/hit como /hit.
//   /hit → contador propio de visitas (functions/_lib/stats.js); el resto → lead.js.
// El Lead a la API de conversiones de Meta sale en segundo plano: la respuesta al formulario no lo espera.
import http from "node:http";
import { handle } from "../functions/_lib/lead.js";
import { createStats } from "../functions/_lib/stats.js";
import { META_PIXEL_ID } from "../functions/_lib/meta-capi.js";

const PORT = Number(process.env.PORT || 8000);
const stats = createStats(process.env);
stats.start();

const server = http.createServer(async (req, res) => {
  try {
    const chunks = [];
    for await (const ch of req) chunks.push(ch);
    const url = `http://${req.headers.host || "localhost"}${req.url}`;
    const request = new Request(url, {
      method: req.method, headers: req.headers,
      body: ["GET", "HEAD"].includes(req.method) ? undefined : Buffer.concat(chunks),
    });
    const path = new URL(url).pathname.replace(/\/+$/, "");
    const response = /\/hit$/.test(path) ? await stats.hit(request) : await handle(request, process.env, { stats, metaEnSegundoPlano: true });
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch (e) {
    console.error(e);
    res.writeHead(500, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: false, detail: "Error interno" }));
  }
}).listen(PORT, "0.0.0.0", () => {
  console.log(`zeekr-leads-api escuchando en :${PORT}`);
  console.log(`estadísticas: ${stats.enabled ? "activadas (envío a Directus cada " + (Number(process.env.STATS_FLUSH_MS) || 60000) / 1000 + " s)" : "desactivadas (faltan DIRECTUS_URL o DIRECTUS_STATS_TOKEN)"}`);
  const pixel = String(process.env.META_PIXEL_ID || "").trim() || META_PIXEL_ID;
  console.log(`meta capi: ${String(process.env.META_CAPI_TOKEN || "").trim() ? `activada (píxel ${pixel}${String(process.env.META_TEST_EVENT_CODE || "").trim() ? ", eventos de prueba" : ""})` : "desactivada (falta META_CAPI_TOKEN)"}`);
});

// Al apagar (redeploy, docker stop): guardar lo acumulado antes de salir (máx. 8 s; docker espera 10).
let closing = false;
async function shutdown(signal) {
  if (closing) return;
  closing = true;
  stats.stop();
  server.close();
  const res = await Promise.race([stats.flush(), new Promise((r) => setTimeout(() => r({ ok: false, error: "tiempo agotado" }), 8000))]);
  console.log(`${signal}: estadísticas ${res.ok ? `guardadas (${res.sent || 0} claves)` : `sin guardar (${res.error})`}; saliendo`);
  process.exit(0);
}
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
