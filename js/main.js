/* ZEEKR Paraguay — interacciones (vanilla, sin dependencias) */
(function () {
  "use strict";

  var doc = document;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

  function $(sel, ctx) { return (ctx || doc).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }

  /* Deja inerte todo lo que no sea el panel abierto (header/main/footer). */
  function setInertOutside(panel, on) {
    $$("body > *").forEach(function (el) {
      if (el === panel || el.contains(panel) || el.tagName === "SCRIPT") return;
      if (on) el.setAttribute("inert", ""); else el.removeAttribute("inert");
    });
  }
  function trapTab(e, panel) {
    if (e.key !== "Tab") return;
    var items = $$(FOCUSABLE, panel).filter(function (el) { return el.offsetParent !== null || el === doc.activeElement; });
    if (!items.length) return;
    var first = items[0], last = items[items.length - 1];
    if (e.shiftKey && doc.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && doc.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  function lockScroll(on) { doc.documentElement.style.overflow = on ? "hidden" : ""; }

  /* ----- header: fondo al scrollear ----- */
  var header = $("#siteHeader");
  var scrolled = false;
  function onScroll() {
    var s = window.scrollY > 24;
    if (s !== scrolled) { scrolled = s; header.classList.toggle("is-scrolled", s); }
  }
  if (header) { window.addEventListener("scroll", onScroll, { passive: true }); onScroll(); }

  /* ----- panel de modelos (desktop) ----- */
  var modelsPanel = $("#modelsPanel");
  var navShade = $(".nav-shade");
  var modelsTrigger = $("[data-toggle-models]");
  function toggleModels(open) {
    if (!modelsPanel || !modelsTrigger) return;
    modelsPanel.hidden = !open;
    if (navShade) navShade.hidden = !open;
    modelsTrigger.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) { var f = $(FOCUSABLE, modelsPanel); if (f) f.focus(); } else if (doc.activeElement && modelsPanel.contains(doc.activeElement)) modelsTrigger.focus();
  }

  /* ----- menú móvil ----- */
  var mobileMenu = $("#mobileMenu");
  var burger = $("[data-open-menu]");
  function openMenu() {
    if (!mobileMenu) return;
    mobileMenu.hidden = false;
    burger.setAttribute("aria-expanded", "true");
    lockScroll(true);
    setInertOutside(mobileMenu, true);
    var c = $("[data-close-menu]", mobileMenu); if (c) c.focus();
  }
  function closeMenu() {
    if (!mobileMenu || mobileMenu.hidden) return;
    mobileMenu.hidden = true;
    burger.setAttribute("aria-expanded", "false");
    lockScroll(false);
    setInertOutside(mobileMenu, false);
    burger.focus();
  }

  /* ----- cookies / consentimiento (carga GA solo con permiso) ----- */
  var banner = $("#cookieBanner");
  var ckSettings = $("#cookieSettings");
  var CK_KEY = "zeekr-consent";
  function readConsent() { try { return JSON.parse(localStorage.getItem(CK_KEY) || "null"); } catch (e) { return null; } }
  function saveConsent(analytics) {
    try { localStorage.setItem(CK_KEY, JSON.stringify({ necessary: true, analytics: !!analytics, at: Date.now() })); } catch (e) { /* sin storage: no persiste */ }
    if (banner) banner.hidden = true;
    if (analytics && window.__zkGA) window.__zkGA();
  }
  if (banner && !readConsent()) banner.hidden = false;

  /* ----- modal de contacto ----- */
  var modal = $("#contactModal");
  var lastFocus = null;
  function openContact(model) {
    if (!modal) return;
    lastFocus = doc.activeElement;
    var sel = $('select[name="modelo"]', modal);
    if (sel) {
      sel.selectedIndex = 0;
      if (model) Array.prototype.forEach.call(sel.options, function (o, i) { if (o.value.toLowerCase() === model.toLowerCase()) sel.selectedIndex = i; });
    }
    closeMenu();
    modal.hidden = false;
    lockScroll(true);
    setInertOutside(modal, true);
    var first = $("input", modal);
    if (first && window.matchMedia("(min-width: 768px)").matches) first.focus(); else $(".modal-panel", modal).focus();
  }
  function closeContact() {
    if (!modal || modal.hidden) return;
    modal.hidden = true;
    lockScroll(false);
    setInertOutside(modal, false);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  /* ----- delegación de clicks ----- */
  doc.addEventListener("click", function (e) {
    var t = e.target;
    if (t.closest("[data-toggle-models]")) { e.preventDefault(); toggleModels(modelsPanel.hidden); return; }
    if (t.closest("[data-close-models]")) { toggleModels(false); return; }
    if (modelsPanel && !modelsPanel.hidden && !t.closest("#modelsPanel")) toggleModels(false);
    if (t.closest("[data-cookie-accept]")) { saveConsent(true); return; }
    if (t.closest("[data-cookie-reject]")) { saveConsent(false); return; }
    var cs = t.closest("[data-cookie-settings]");
    if (cs && ckSettings) { ckSettings.hidden = !ckSettings.hidden; cs.setAttribute("aria-expanded", ckSettings.hidden ? "false" : "true"); return; }
    if (t.closest("[data-cookie-save]")) { var an = $("#ckAnalytics"); saveConsent(an ? an.checked : false); return; }
    var opener = t.closest("[data-open-contact]");
    if (opener) { e.preventDefault(); openContact(opener.getAttribute("data-model")); return; }
    if (t.closest("[data-close-contact]")) { closeContact(); return; }
    if (t.closest("[data-open-menu]")) { e.preventDefault(); openMenu(); return; }
    if (t.closest("[data-close-menu]")) { if (t.closest("button")) e.preventDefault(); closeMenu(); }
  });
  doc.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeContact(); closeMenu(); toggleModels(false); return; }
    if (modal && !modal.hidden) trapTab(e, $(".modal-panel", modal));
    else if (mobileMenu && !mobileMenu.hidden) trapTab(e, mobileMenu);
  });

  /* ----- formulario → WhatsApp ----- */
  function setError(input, on) {
    var field = input.closest(".field");
    var err = field && field.querySelector(".field-error");
    if (field) field.classList.toggle("has-error", on);
    if (err) err.hidden = !on;
    input.setAttribute("aria-invalid", on ? "true" : "false");
    if (err) { if (on) input.setAttribute("aria-describedby", err.id); else input.removeAttribute("aria-describedby"); }
  }
  function formToWa(form) {
    var nombre = form.elements.nombre, tel = form.elements.telefono;
    var okName = nombre.value.trim().length >= 2;
    var okTel = (tel.value.replace(/\D/g, "").length >= 6);
    setError(nombre, !okName); setError(tel, !okTel);
    var status = $(".form-status", form);
    if (!okName || !okTel) { (okName ? tel : nombre).focus(); if (status) status.textContent = "Revisá los campos marcados para continuar."; return; }
    var labels = { nombre: "Nombre", telefono: "Teléfono", modelo: "Modelo de interés", mensaje: "Mensaje" };
    var lines = ["nombre", "telefono", "modelo", "mensaje"].map(function (k) {
      var el = form.elements[k]; return el && el.value.trim() ? labels[k] + ": " + el.value.trim() : null;
    }).filter(Boolean);
    lines.push("Origen: zeekrlife.com.py");
    var text = "Hola ZEEKR Paraguay, quiero coordinar una prueba de manejo y recibir más información.\n" + lines.join("\n");
    if (status) status.textContent = "Abriendo WhatsApp…";
    window.open("https://wa.me/" + form.getAttribute("data-wa") + "?text=" + encodeURIComponent(text), "_blank", "noopener");
    if (window.gtag) window.gtag("event", "generate_lead", { method: "whatsapp", model: form.elements.modelo.value });
    setTimeout(function () { if (status) status.textContent = "Listo. Si WhatsApp no se abrió, escribinos al 0971 370 006."; }, 1200);
  }
  doc.addEventListener("submit", function (e) {
    var form = e.target.closest("form");
    if (form && form.id === "waForm") { e.preventDefault(); formToWa(form); }
  });
  $$("#waForm input").forEach(function (i) { i.addEventListener("input", function () { if (i.getAttribute("aria-invalid") === "true") setError(i, false); }); });

  /* ----- hero: carrusel ----- */
  var hero = $("#hero");
  if (hero) {
    var slides = $$("[data-slide]", hero);
    var bars = $$(".pager-bar", hero);
    var counter = $("[data-counter]", hero);
    var status = $("[data-slide-status]", hero);
    var playBtn = $("[data-toggle-play]", hero);
    var track = $(".hero-track", hero);
    var idx = 0, timer = null, DUR = 6000, userPaused = reduceMotion, hovering = false;

    function restartBar(bar) {
      bar.classList.remove("is-active");
      requestAnimationFrame(function () { requestAnimationFrame(function () { bar.classList.add("is-active"); }); });
    }
    function show(n, announce) {
      idx = (n + slides.length) % slides.length;
      slides.forEach(function (s, i) {
        var on = i === idx;
        s.classList.toggle("is-active", on);
        if (on) s.removeAttribute("aria-hidden"); else s.setAttribute("aria-hidden", "true");
      });
      bars.forEach(function (b, i) {
        b.classList.toggle("is-done", false);
        if (i === idx) restartBar(b); else b.classList.remove("is-active");
        if (i === idx) b.setAttribute("aria-current", "true"); else b.removeAttribute("aria-current");
      });
      if (counter) counter.textContent = String(idx + 1).padStart(2, "0");
      if (announce && status) status.textContent = "Diapositiva " + (idx + 1) + " de " + slides.length + ": " + $(".slide-title", slides[idx]).textContent;
    }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function play() {
      stop();
      if (userPaused || hovering || doc.hidden) return;
      timer = setInterval(function () { show(idx + 1, false); }, DUR);
    }
    function syncPaused() {
      var paused = userPaused || hovering;
      hero.classList.toggle("is-paused", paused);
      if (track) track.setAttribute("aria-live", paused ? "polite" : "off");
      if (playBtn) {
        playBtn.setAttribute("aria-pressed", userPaused ? "true" : "false");
        playBtn.setAttribute("aria-label", userPaused ? "Reanudar reproducción automática" : "Pausar reproducción automática");
      }
    }
    function go(n, announce) { show(n, announce); play(); }

    bars.forEach(function (b) { b.addEventListener("click", function () { go(parseInt(b.getAttribute("data-goto"), 10) || 0, true); }); });
    var prev = $("[data-prev]", hero), next = $("[data-next]", hero);
    if (prev) prev.addEventListener("click", function () { go(idx - 1, true); });
    if (next) next.addEventListener("click", function () { go(idx + 1, true); });
    if (playBtn) playBtn.addEventListener("click", function () { userPaused = !userPaused; syncPaused(); play(); });

    hero.addEventListener("mouseenter", function () { hovering = true; syncPaused(); stop(); });
    hero.addEventListener("mouseleave", function () { hovering = false; syncPaused(); play(); });
    hero.addEventListener("focusin", function () { hovering = true; syncPaused(); stop(); });
    hero.addEventListener("focusout", function (e) { if (!hero.contains(e.relatedTarget)) { hovering = false; syncPaused(); play(); } });
    hero.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") { e.preventDefault(); go(idx + 1, true); }
      if (e.key === "ArrowLeft") { e.preventDefault(); go(idx - 1, true); }
    });
    /* swipe (pointer events) */
    var px = null, py = null;
    hero.addEventListener("pointerdown", function (e) { if (e.pointerType === "mouse") return; px = e.clientX; py = e.clientY; }, { passive: true });
    hero.addEventListener("pointerup", function (e) {
      if (px === null) return;
      var dx = e.clientX - px, dy = e.clientY - py; px = py = null;
      if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.5) go(dx < 0 ? idx + 1 : idx - 1, true);
    });
    hero.addEventListener("pointercancel", function () { px = py = null; });
    doc.addEventListener("visibilitychange", function () { if (doc.hidden) stop(); else play(); });

    syncPaused();
    show(0, false);
    play();
  }

  /* ----- video decorativo: autoplay en pantalla, botón pausa ----- */
  $$("[data-video]").forEach(function (video) {
    var section = video.closest(".video-section");
    var btn = section && $("[data-video-toggle]", section);
    var userPaused = reduceMotion;
    function sync() {
      var paused = video.paused;
      if (section) section.classList.toggle("is-paused", paused);
      if (btn) { btn.setAttribute("aria-pressed", paused ? "true" : "false"); btn.setAttribute("aria-label", paused ? "Reproducir video" : "Pausar video"); }
    }
    function tryPlay() { if (userPaused) return; var p = video.play(); if (p && p.catch) p.catch(function () {}); }
    if (btn) btn.addEventListener("click", function () { userPaused = !video.paused; if (video.paused) tryPlay(); else video.pause(); });
    video.addEventListener("play", sync); video.addEventListener("pause", sync);
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) tryPlay(); else video.pause(); });
      }, { threshold: 0.25 }).observe(video);
    } else tryPlay();
    sync();
  });

  /* ----- galerías: flechas cuando tienen foco ----- */
  $$("[data-gallery]").forEach(function (g) {
    g.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault();
      var item = g.firstElementChild; var step = item ? item.getBoundingClientRect().width + 16 : 320;
      g.scrollBy({ left: e.key === "ArrowRight" ? step : -step, behavior: reduceMotion ? "auto" : "smooth" });
    });
  });

  /* ----- aparición al scrollear ----- */
  var reveals = $$(".reveal");
  if (reveals.length && "IntersectionObserver" in window && !reduceMotion) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
    reveals.forEach(function (el) { io.observe(el); });
  } else reveals.forEach(function (el) { el.classList.add("in"); });
})();
