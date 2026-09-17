/* ZEEKR Paraguay — interactions (vanilla, sin dependencias) */
(function () {
  "use strict";

  /* ----- header scrolled ----- */
  var header = document.getElementById("siteHeader");
  function onScroll() {
    if (!header) return;
    header.classList.toggle("scrolled", window.scrollY > 24);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ----- panel de modelos ----- */
  var modelsPanel = document.getElementById("modelsPanel");
  var navShade = document.querySelector(".nav-shade");
  var modelsTrigger = document.querySelector("[data-toggle-models]");
  function toggleModels(open) {
    if (!modelsPanel || !modelsTrigger) return;
    modelsPanel.hidden = !open;
    if (navShade) navShade.hidden = !open;
    modelsTrigger.setAttribute("aria-expanded", open ? "true" : "false");
  }
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-toggle-models]")) {
      e.preventDefault();
      toggleModels(modelsPanel.hidden);
      return;
    }
    if (e.target.closest("[data-close-models]")) { toggleModels(false); return; }
    if (modelsPanel && !modelsPanel.hidden && !e.target.closest("#modelsPanel") && !e.target.closest("[data-toggle-models]")) toggleModels(false);
  });

  /* ----- banner de cookies ----- */
  var banner = document.getElementById("cookieBanner");
  var ckSettings = document.getElementById("cookieSettings");
  var CK_KEY = "zeekr-consent";
  function readConsent() {
    try { return JSON.parse(localStorage.getItem(CK_KEY) || "null"); } catch (e) { return null; }
  }
  function saveConsent(analytics) {
    try { localStorage.setItem(CK_KEY, JSON.stringify({ necessary: true, analytics: !!analytics, at: Date.now() })); } catch (e) {}
    if (banner) banner.hidden = true;
    if (ckSettings) ckSettings.hidden = true;
  }
  if (banner && !readConsent()) banner.hidden = false;
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-cookie-accept]")) { saveConsent(true); return; }
    if (e.target.closest("[data-cookie-reject]")) { saveConsent(false); return; }
    if (e.target.closest("[data-cookie-settings]") && ckSettings) { ckSettings.hidden = false; return; }
    if (e.target.closest("[data-cookie-save]")) {
      var an = document.getElementById("ckAnalytics");
      saveConsent(an ? an.checked : false);
    }
  });

  /* ----- hero slider / pager ----- */
  var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
  var bars = Array.prototype.slice.call(document.querySelectorAll(".pager-bar"));
  if (slides.length > 1 && bars.length) {
    var idx = 0, timer = null, DUR = 5000;
    function show(n) {
      idx = (n + slides.length) % slides.length;
      slides.forEach(function (s, i) {
        s.classList.toggle("active", i === idx);
        s.setAttribute("aria-hidden", i === idx ? "false" : "true");
      });
      bars.forEach(function (b, i) {
        b.classList.remove("active");
        void b.offsetWidth; // reinicia animación de progreso
      });
      bars[idx].classList.add("active");
    }
    function play() { stop(); timer = setInterval(function () { show(idx + 1); }, DUR); }
    function stop() { if (timer) clearInterval(timer); }
    bars.forEach(function (b) {
      b.addEventListener("click", function () { show(parseInt(b.dataset.goto, 10) || 0); play(); });
    });
    var hero = document.querySelector(".hero");
    if (hero) {
      hero.addEventListener("mouseenter", stop);
      hero.addEventListener("mouseleave", play);
    }
    document.addEventListener("visibilitychange", function () { document.hidden ? stop() : play(); });
    show(0); play();
  }

  /* ----- modal contacto ----- */
  var modal = document.getElementById("contactModal");
  var lastFocus = null;
  function openContact(model) {
    if (!modal) return;
    lastFocus = document.activeElement;
    if (model && modal.querySelector('select[name="modelo"]')) {
      var sel = modal.querySelector("select[name=modelo]");
      var opts = Array.prototype.map.call(sel.options, function (o) { return o.value || o.text; });
      opts.forEach(function (o, i) { if (o.toLowerCase().indexOf(model.toLowerCase()) > -1) sel.selectedIndex = i; });
    }
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    var first = modal.querySelector("input,button"); if (first) first.focus();
  }
  function closeContact() {
    if (!modal) return;
    modal.hidden = true; modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    if (lastFocus) lastFocus.focus();
  }
  document.addEventListener("click", function (e) {
    var opener = e.target.closest("[data-open-contact]");
    if (opener) { e.preventDefault(); openContact(opener.dataset.model); return; }
    if (e.target.closest("[data-close-contact]")) { closeContact(); }
    var menuOpener = e.target.closest("[data-open-menu]");
    if (menuOpener) {
      e.preventDefault();
      var mm = document.getElementById("mobileMenu"), ov = document.querySelector(".menu-overlay");
      if (mm) { mm.hidden = false; menuOpener.setAttribute("aria-expanded", "true"); document.body.style.overflow = "hidden"; }
      if (ov) ov.hidden = false;
      return;
    }
    if (e.target.closest("[data-close-menu]")) {
      e.preventDefault();
      var mm2 = document.getElementById("mobileMenu"), ov2 = document.querySelector(".menu-overlay");
      if (mm2) mm2.hidden = true;
      if (ov2) ov2.hidden = true;
      document.body.style.overflow = "";
      var burger = document.querySelector("[data-open-menu]");
      if (burger) burger.setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    closeContact();
    var mm = document.getElementById("mobileMenu");
    if (mm && !mm.hidden) { mm.hidden = true; if (document.querySelector(".menu-overlay")) document.querySelector(".menu-overlay").hidden = true; document.body.style.overflow = ""; }
  });

  /* ----- form → WhatsApp ----- */
  function formToWa(form) {
    var fields = ["nombre", "telefono", "modelo", "mensaje"].filter(function (id) { return form.querySelector('[name="' + id + '"]'); });
    var lines = [];
    fields.forEach(function (id) {
      var el = form.querySelector('[name="' + id + '"]');
      if (el && el.value) {
        var label = { nombre: "Nombre", telefono: "Teléfono", modelo: "Modelo de interés", mensaje: "Mensaje" }[id] || id;
        lines.push(label + ": " + el.value.trim());
      }
    });
    lines.push("Origen: zeekrlife.com.py (test drive / contacto)");
    var text = "Hola ZEEKR Paraguay, quiero coordinar una prueba de manejo y más información.\n" + lines.join("\n");
    window.open("https://wa.me/" + form.dataset.wa + "?text=" + encodeURIComponent(text), "_blank", "noopener");
  }
  document.addEventListener("submit", function (e) {
    var form = e.target.closest && e.target.closest("form");
    if (!form) return;
    if (form.id === "waForm") { e.preventDefault(); formToWa(form); return; }
    if (form.classList.contains("js-wa")) { e.preventDefault(); formToWa(form); }
  });

  /* ----- chips de color (ficha modelo) ----- */
  var chips = document.querySelectorAll(".chip[data-bg]");
  chips.forEach(function (c) {
    c.addEventListener("click", function () {
      document.querySelectorAll(".chip[data-bg]").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
      c.setAttribute("aria-pressed", "true");
      var view = document.getElementById(c.dataset.target);
      if (view) view.style.backgroundColor = c.dataset.bg;
      var name = document.getElementById(c.dataset.target + "Name");
      if (name) { name.textContent = c.dataset.name; }
    });
  });
})();
