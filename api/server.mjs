// Servidor Node (Coolify) para la API de leads. Reusa functions/_lib/lead.js tal cual.
import http from "node:http";
import { handle } from "../functions/_lib/lead.js";

const PORT = Number(process.env.PORT || 8000);

http.createServer(async (req, res) => {
  try {
    const chunks = [];
    for await (const ch of req) chunks.push(ch);
    const url = `http://${req.headers.host || "localhost"}${req.url}`;
    const request = new Request(url, {
      method: req.method, headers: req.headers,
      body: ["GET", "HEAD"].includes(req.method) ? undefined : Buffer.concat(chunks),
    });
    const response = await handle(request, process.env);
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch (e) {
    console.error(e);
    res.writeHead(500, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: false, detail: "Error interno" }));
  }
}).listen(PORT, "0.0.0.0", () => console.log(`zeekr-leads-api escuchando en :${PORT}`));
