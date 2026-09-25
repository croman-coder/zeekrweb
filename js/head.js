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
/* Píxel de Meta (dataset "Zeekr Paraguay"): el mismo permiso que Google Analytics (el banner tiene una sola
   categoría opcional) y solo en el dominio real: el alias, la vista previa y localhost no mandan nada. Con
   META_PIXEL_ID vacío no se carga nada. functions/_lib/meta-capi.js usa el mismo ID y los mismos hosts. */
(function () {
  var META_PIXEL_ID = "1384147742910671";
  var META_HOSTS = ["zeekrlife.com.py"];
  window.__zkMeta = function () {
    if (window.__zkMetaOn || !META_PIXEL_ID || META_HOSTS.indexOf(location.hostname) < 0) return;
    window.__zkMetaOn = 1;
    var n = window.fbq = function () { if (n.callMethod) n.callMethod.apply(n, arguments); else n.queue.push(arguments); };
    if (!window._fbq) window._fbq = n;
    n.push = n; n.loaded = true; n.version = "2.0"; n.queue = [];
    n("init", META_PIXEL_ID);
    n("track", "PageView");
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://connect.facebook.net/en_US/fbevents.js";
    document.head.appendChild(s);
  };
})();
try {
  var c = JSON.parse(localStorage.getItem("zeekr-consent") || "null");
  if (c && c.analytics) { window.__zkGA(); window.__zkMeta(); }
} catch (e) { /* sin storage */ }
