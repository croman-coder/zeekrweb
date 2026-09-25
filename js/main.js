/* ZEEKR Paraguay — interacciones (vanilla, sin dependencias) */
(function () {
  "use strict";

  var doc = document;
  var I18N = {};
  try { var i18nEl = doc.getElementById("zk-i18n"); if (i18nEl) I18N = JSON.parse(i18nEl.textContent || "{}"); } catch (e) { I18N = {}; }
  function tr(key, fallback) { return I18N[key] != null ? I18N[key] : fallback; }
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

  /* ----- estadísticas propias → /api/hit (sin cookies, sin IDs, sin datos personales) -----
     Una visita por página cargada y un clic por enlace a WhatsApp. Solo desde zeekrlife.com.py: el alias
     zeekr.santarosa.lat y la vista previa no cuentan. Las 404 tampoco. Nunca rompe la página. */
  function statHit(kind) {
    if (location.hostname !== "zeekrlife.com.py" || !navigator.sendBeacon) return;
    try { navigator.sendBeacon("/api/hit", JSON.stringify({ k: kind, p: location.pathname, t: doc.title })); } catch (e) { /* sin estadística */ }
  }
  if (!$(".notfound")) {
    if (doc.prerendering) doc.addEventListener("prerenderingchange", function () { statHit("view"); }, { once: true });
    else statHit("view");
  }

  /* ----- píxel de Meta: js/head.js lo carga solo con permiso y en zeekrlife.com.py; sin píxel esto no hace nada ----- */
  function newEventId() {
    try { if (window.crypto && crypto.randomUUID) return crypto.randomUUID(); } catch (e) { /* sin randomUUID */ }
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
  }
  function metaTrack(name, params, eventId) {
    if (typeof window.fbq !== "function") return;
    try { window.fbq("track", name, params, { eventID: eventId || newEventId() }); } catch (e) { /* sin píxel */ }
  }
  /* Contacto = enlace a un número (wa.me/<número>, …whatsapp.com/send?phone=…). Compartir una noticia
     (wa.me/?text=…) también cuenta como clic a WhatsApp en las estadísticas, pero no es un contacto. */
  function waContact(a) {
    try {
      var u = new URL(a.href, location.href);
      if (u.hostname === "wa.me") return u.pathname.replace(/\//g, "") !== "";
      if (/(^|\.)whatsapp\.com$/.test(u.hostname) && /^\/send\/?$/.test(u.pathname)) return !!u.searchParams.get("phone");
    } catch (e) { /* href inválido */ }
    return false;
  }
  function waPlace(a) {
    if (a.hasAttribute("data-success-wa")) return "form_success";
    if (a.closest("#contactModal")) return "contact_modal";
    if (a.closest(".site-header")) return "header";
    if (a.closest(".site-footer")) return "footer";
    if (a.closest(".contact-strip")) return "contact_strip";
    return "page";
  }
  doc.addEventListener("click", function (e) {
    var wa = e.target.closest && e.target.closest('a[href*="wa.me/"], a[href*="whatsapp.com/"]');
    if (!wa) return;
    statHit("whatsapp");
    if (waContact(wa)) metaTrack("Contact", { content_name: waPlace(wa) });
  }, true);

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

  /* ----- selector de idioma ----- */
  var langBtn = $(".lang-btn"), langMenu = $("#langMenu");
  function toggleLang(open) {
    if (!langBtn || !langMenu) return;
    langMenu.hidden = !open;
    langBtn.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) { var f = $("a", langMenu); if (f) f.focus(); }
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

  /* ----- cookies / consentimiento (carga GA y el píxel de Meta solo con permiso) ----- */
  var banner = $("#cookieBanner");
  var ckSettings = $("#cookieSettings");
  var CK_KEY = "zeekr-consent";
  var consentNow = null;   // lo elegido en esta visita (vale aunque el navegador no deje guardarlo)
  function readConsent() { try { return JSON.parse(localStorage.getItem(CK_KEY) || "null"); } catch (e) { return null; } }
  function analyticsOk() {
    if (consentNow !== null) return consentNow;
    var c = readConsent();
    return !!(c && c.analytics);
  }
  function saveConsent(analytics) {
    consentNow = !!analytics;
    try { localStorage.setItem(CK_KEY, JSON.stringify({ necessary: true, analytics: !!analytics, at: Date.now() })); } catch (e) { /* sin storage: no persiste */ }
    if (banner) banner.hidden = true;
    if (analytics && window.__zkGA) window.__zkGA();
    if (analytics && window.__zkMeta) window.__zkMeta();
  }
  if (banner && !readConsent()) banner.hidden = false;

  /* ----- modal de contacto ----- */
  var modal = $("#contactModal");
  var lastFocus = null;
  var MODES = I18N.modes || {
    "test-drive": { eyebrow: "Prueba de manejo", title: "Agendá tu prueba de manejo", sub: "Elegí el modelo y un asesor coordina con vos día, hora y lugar.", channels: "¿Preferís hablar ahora?", submit: "Agendar prueba de manejo", tipo: "Prueba de manejo", done: "Registramos tu solicitud de prueba de manejo." },
    "contacto": { eyebrow: "Contacto", title: "Contáctanos", sub: "Elegí cómo preferís hablar con nosotros.", channels: "Llamanos o escribinos", submit: "Enviar consulta", tipo: "Consulta", done: "Registramos tu consulta." }
  };
  function setMode(intent) {
    var m = MODES[intent] || MODES["test-drive"];
    var panel = $(".modal-panel", modal);
    panel.setAttribute("data-mode", MODES[intent] ? intent : "test-drive");
    ["eyebrow", "title", "sub", "channels"].forEach(function (k) { var el = $('[data-m="' + k + '"]', modal); if (el) el.textContent = m[k]; });
    var orForm = $('[data-m="form"]', modal); if (orForm) orForm.hidden = intent !== "contacto";
    var btn = $("#waForm [type=submit]", modal); if (btn) { btn.setAttribute("data-label", m.submit); btn.querySelector("span").textContent = m.submit; }
    var tipo = $('#waForm [name="tipo"]', modal); if (tipo) tipo.value = m.tipo;
    var done = $("[data-success-what]", modal); if (done) done.textContent = m.done;
    modal.setAttribute("data-intent", intent);
  }
  function openContact(model, intent) {
    if (!modal) return;
    lastFocus = doc.activeElement;
    setMode(intent || "test-drive");
    var sel = $('select[name="modelo"]', modal);
    if (sel) {
      sel.selectedIndex = 0;
      if (model) Array.prototype.forEach.call(sel.options, function (o, i) { if (o.value.toLowerCase() === model.toLowerCase()) sel.selectedIndex = i; });
    }
    closeMenu();
    modal.hidden = false;
    lockScroll(true);
    setInertOutside(modal, true);
    var first = intent === "contacto" ? $(".contact-card", modal) : $("input", modal);
    if (first && window.matchMedia("(min-width: 768px)").matches && intent !== "contacto") first.focus(); else $(".modal-panel", modal).focus();
  }
  function closeContact() {
    if (!modal || modal.hidden) return;
    var f = $("#waForm", modal); if (f && f.hidden) resetForm(f);
    modal.hidden = true;
    lockScroll(false);
    setInertOutside(modal, false);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  /* ----- delegación de clicks ----- */
  doc.addEventListener("click", function (e) {
    var t = e.target;
    if (t.closest(".lang-btn")) { e.preventDefault(); toggleLang(langMenu.hidden); return; }
    if (langMenu && !langMenu.hidden && !t.closest(".lang")) toggleLang(false);
    if (t.closest("[data-toggle-models]")) { e.preventDefault(); toggleModels(modelsPanel.hidden); return; }
    if (t.closest("[data-close-models]")) { toggleModels(false); return; }
    if (modelsPanel && !modelsPanel.hidden && !t.closest("#modelsPanel")) toggleModels(false);
    if (t.closest("[data-cookie-accept]")) { saveConsent(true); return; }
    if (t.closest("[data-cookie-reject]")) { saveConsent(false); return; }
    var cs = t.closest("[data-cookie-settings]");
    if (cs && ckSettings) { ckSettings.hidden = !ckSettings.hidden; cs.setAttribute("aria-expanded", ckSettings.hidden ? "false" : "true"); return; }
    if (t.closest("[data-cookie-save]")) { var an = $("#ckAnalytics"); saveConsent(an ? an.checked : false); return; }
    var opener = t.closest("[data-open-contact]");
    if (opener) { e.preventDefault(); openContact(opener.getAttribute("data-model"), opener.getAttribute("data-intent") || "test-drive"); return; }
    if (t.closest("[data-close-contact]")) { closeContact(); return; }
    if (t.closest("[data-open-menu]")) { e.preventDefault(); openMenu(); return; }
    if (t.closest("[data-close-menu]")) { if (t.closest("button")) e.preventDefault(); closeMenu(); }
  });
  doc.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeContact(); closeMenu(); toggleModels(false); toggleLang(false); return; }
    if (modal && !modal.hidden) trapTab(e, $(".modal-panel", modal));
    else if (mobileMenu && !mobileMenu.hidden) trapTab(e, mobileMenu);
  });

  /* ----- UTM: se guardan en la sesión para adjuntarlas al lead ----- */
  var UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"];
  try {
    var q = new URLSearchParams(location.search), found = {};
    UTM_KEYS.forEach(function (k) { if (q.get(k)) found[k] = q.get(k).slice(0, 160); });
    if (Object.keys(found).length) sessionStorage.setItem("zk-utm", JSON.stringify(found));
  } catch (e) { /* sin storage */ }
  function utms() { try { return JSON.parse(sessionStorage.getItem("zk-utm") || "{}"); } catch (e) { return {}; } }

  /* ----- datos para la API de conversiones de Meta (functions/_lib/meta-capi.js) -----
     Van siempre en el POST. Si el visitante no aceptó las cookies, el servidor no manda nada a Meta
     ("rechazado" también si todavía no eligió: el sitio pide permiso antes de medir, igual que con GA). */
  function cookie(name) {
    try { var m = doc.cookie.match(new RegExp("(?:^|;\\s*)" + name + "=([^;]*)")); return m ? m[1] : ""; } catch (e) { return ""; }   // nunca frena el formulario
  }
  function metaData(eventId) {
    var ok = analyticsOk();
    var m = { event_id: eventId, event_source_url: location.href, consentimiento: ok ? "aceptado" : "rechazado" };
    if (!ok) return m;
    var fbp = cookie("_fbp"), fbc = cookie("_fbc");
    if (!fbc) {
      try { var id = new URLSearchParams(location.search).get("fbclid"); if (id && /^[A-Za-z0-9_.\-]+$/.test(id)) fbc = "fb.1." + Date.now() + "." + id; } catch (e) { /* sin fbclid */ }
    }
    if (fbp) m.fbp = fbp;
    if (fbc) m.fbc = fbc;
    return m;
  }

  /* ----- formulario → API (Bitrix) con respaldo a WhatsApp ----- */
  function setError(input, on) {
    var field = input.closest(".field");
    var err = field && field.querySelector(".field-error");
    if (field) field.classList.toggle("has-error", on);
    if (err) err.hidden = !on;
    input.setAttribute("aria-invalid", on ? "true" : "false");
    if (err) { if (on) input.setAttribute("aria-describedby", err.id); else input.removeAttribute("aria-describedby"); }
  }
  function waUrl(form) {
    var labels = I18N.waLabels || { nombre: "Nombre", telefono: "Teléfono", modelo: "Modelo de interés", mensaje: "Mensaje" };
    var lines = ["nombre", "telefono", "modelo", "mensaje"].map(function (k) {
      var el = form.elements[k]; return el && el.value.trim() ? labels[k] + ": " + el.value.trim() : null;
    }).filter(Boolean);
    lines.push(tr("origin", "Origen") + ": zeekrlife.com.py");
    var tipo = form.elements.tipo ? form.elements.tipo.value : "Prueba de manejo";
    var intros = I18N.waIntro || { "Consulta": "Hola ZEEKR Paraguay, quiero hacer una consulta.", "Prueba de manejo": "Hola ZEEKR Paraguay, quiero coordinar una prueba de manejo." };
    var intro = intros[tipo] || intros["Prueba de manejo"];
    var text = intro + "\n" + lines.join("\n");
    return "https://wa.me/" + form.getAttribute("data-wa") + "?text=" + encodeURIComponent(text);
  }
  function showSuccess(form, data, wa) {
    var box = form.parentNode.querySelector(".form-success");
    if (!box) return;
    var first = (form.elements.nombre.value.trim().split(/\s+/)[0] || "").replace(/^./, function (c) { return c.toUpperCase(); });
    box.querySelector("[data-success-name]").textContent = first;
    box.querySelector("[data-success-advisor]").textContent = data && data.asesor ? tr("advisor", "{name} te contacta en el día.").replace("{name}", data.asesor) : tr("advisorDefault", "Un asesor te contacta en el día.");
    box.querySelector("[data-success-wa]").href = wa;
    form.hidden = true;
    ["modal-channels", "modal-sub", "modal-or-form"].forEach(function (k) { var el = form.parentNode.querySelector("." + k); if (el) el.hidden = true; });
    box.hidden = false;
    box.querySelector("[data-success-wa]").focus();
  }
  function resetForm(form) {
    var box = form.parentNode.querySelector(".form-success");
    if (box) box.hidden = true;
    form.hidden = false;
    ["modal-channels", "modal-sub"].forEach(function (k) { var el = form.parentNode.querySelector("." + k); if (el) el.hidden = false; });
    form.reset();
    var st = $(".form-status", form); if (st) st.textContent = "";
    var btn = form.querySelector("[type=submit]"); if (btn) { btn.disabled = false; btn.querySelector("span").textContent = btn.getAttribute("data-label"); }
  }
  function submitLead(form) {
    var nombre = form.elements.nombre, tel = form.elements.telefono;
    var okName = nombre.value.trim().length >= 2;
    var okTel = (tel.value.replace(/\D/g, "").length >= 6);
    setError(nombre, !okName); setError(tel, !okTel);
    var status = $(".form-status", form);
    if (!okName || !okTel) { (okName ? tel : nombre).focus(); if (status) status.textContent = tr("fix", "Revisá los campos marcados para continuar."); return; }
    var btn = form.querySelector("[type=submit]");
    var wa = waUrl(form);
    var payload = {
      nombre: nombre.value.trim(), telefono: tel.value.trim(),
      modelo: form.elements.modelo.value, mensaje: (form.elements.mensaje.value || "").trim() || null,
      tipo: form.elements.tipo ? form.elements.tipo.value : "Prueba de manejo",
      pagina: location.href.split("#")[0], website: form.elements.website ? form.elements.website.value : "",
      idioma: form.elements.idioma ? form.elements.idioma.value : doc.documentElement.lang
    };
    var u = utms(); UTM_KEYS.forEach(function (k) { if (u[k]) payload[k] = u[k]; });
    var eventId = newEventId();   // el mismo en el píxel y en la API de conversiones: Meta cuenta un solo Lead
    payload.meta = metaData(eventId);
    btn.disabled = true; btn.querySelector("span").textContent = tr("sending", "Enviando…");
    if (status) status.textContent = "";
    var ctrl = ("AbortController" in window) ? new AbortController() : null;
    var t = setTimeout(function () { if (ctrl) ctrl.abort(); }, 12000);
    fetch("/api/lead", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload), signal: ctrl ? ctrl.signal : undefined })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok && d.ok, data: d }; }); })
      .then(function (res) {
        clearTimeout(t);
        if (!res.ok) throw new Error(res.data && res.data.detail ? String(res.data.detail) : "error");
        if (window.gtag) window.gtag("event", "generate_lead", { method: "web_form", model: payload.modelo });
        if (!payload.website) metaTrack("Lead", { content_name: payload.tipo }, eventId);
        showSuccess(form, res.data, wa);
      })
      .catch(function () {
        clearTimeout(t);
        /* respaldo: el lead no se pierde, va directo por WhatsApp */
        if (window.gtag) window.gtag("event", "generate_lead", { method: "whatsapp_fallback", model: payload.modelo });
        metaTrack("Contact", { content_name: "whatsapp_fallback" });   // no hay lead en Bitrix: es un contacto
        window.open(wa, "_blank", "noopener");
        if (status) status.textContent = tr("fallback", "No pudimos registrar la consulta en el sistema; te llevamos a WhatsApp para que un asesor te atienda igual.");
        btn.disabled = false; btn.querySelector("span").textContent = btn.getAttribute("data-label");
      });
  }
  doc.addEventListener("submit", function (e) {
    var form = e.target.closest("form");
    if (form && form.id === "waForm") { e.preventDefault(); submitLead(form); }
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
    var idx = 0, timer = null, DUR = 6000, userPaused = false, hovering = false;

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
      if (announce && status) status.textContent = tr("slide", "Diapositiva {n} de {t}: {title}").replace("{n}", idx + 1).replace("{t}", slides.length).replace("{title}", $(".slide-title", slides[idx]).textContent);
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
        playBtn.setAttribute("aria-label", userPaused ? tr("resume", "Reanudar reproducción automática") : tr("pause", "Pausar reproducción automática"));
      }
    }
    function go(n, announce) { show(n, announce); play(); }

    bars.forEach(function (b) { b.addEventListener("click", function () { go(parseInt(b.getAttribute("data-goto"), 10) || 0, true); }); });
    var prev = $("[data-prev]", hero), next = $("[data-next]", hero);
    if (prev) prev.addEventListener("click", function () { go(idx - 1, true); });
    if (next) next.addEventListener("click", function () { go(idx + 1, true); });
    if (playBtn) playBtn.addEventListener("click", function () { userPaused = !userPaused; syncPaused(); play(); });

    /* corre solo: no se pausa con el mouse; sí al navegar con teclado dentro del hero */
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
      if (btn) { btn.setAttribute("aria-pressed", paused ? "true" : "false"); btn.setAttribute("aria-label", paused ? tr("videoPlay", "Reproducir video") : tr("videoPause", "Pausar video")); }
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
