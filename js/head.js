/* Cabecera síncrona: clase .js antes del primer render + Google Analytics solo con consentimiento. */
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
try {
  var c = JSON.parse(localStorage.getItem("zeekr-consent") || "null");
  if (c && c.analytics) window.__zkGA();
} catch (e) { /* sin storage */ }
