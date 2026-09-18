// Cloudflare Pages Function: POST /api/lead  (mismo código que el servidor Node de Coolify)
import { handle } from "../_lib/lead.js";
export const onRequest = ({ request, env }) => handle(request, env);
