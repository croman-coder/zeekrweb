/* Cabecera síncrona: clase .js antes del primer render + Google Analytics y píxel de Meta solo con consentimiento. */
document.documentElement.classList.add("js");
window.__zkGA = function () {
  if (window.__zkGAOn) return;
  window.__zkGAOn = 1;
  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { dataLayer.push(arguments); };
  gtag("js", new Date());
  gtag("config", "G-E6H9ZC5CG3", { anonymize_ip: true });
  // Propiedad "ZEEKR PY" en la cuenta de marketing@ (sep 2026). La de arriba queda
  // hasta confirmar que la nueva recibe datos.
  gtag("config", "G-0QL9QHCG4L", { anonymize_ip: true });
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=G-E6H9ZC5CG3";
  document.head.appendChild(s);
};
/* Píxel de Meta (ZEEKR Paraguay, 1384147742910671): el código base de Meta sin script inline (la CSP no lo
   permite). Va con la misma aceptación que GA: el aviso de cookies tiene una sola categoría opcional
   ("Analíticas y rendimiento"). Solo en zeekrlife.com.py: el alias y la vista previa no ensucian las
   audiencias. Devuelve true la vez que lo enciende (main.js suma ahí el ViewContent de la página de modelo). */
window.__zkFB = function () {
  if (window.__zkFBOn || window.fbq || location.hostname !== "zeekrlife.com.py") return false;
  window.__zkFBOn = 1;
  var n = window.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
  if (!window._fbq) window._fbq = n;
  n.push = n; n.loaded = true; n.version = "2.0"; n.queue = [];
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://connect.facebook.net/en_US/fbevents.js";
  document.head.appendChild(s);
  n("init", "1384147742910671");
  n("track", "PageView");
  return true;
};
try {
  var c = JSON.parse(localStorage.getItem("zeekr-consent") || "null");
  if (c && c.analytics) { window.__zkGA(); window.__zkFB(); }
} catch (e) { /* sin storage */ }
