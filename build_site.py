# -*- coding: utf-8 -*-
"""Generador estático del sitio Zeekr Paraguay.

Rediseño con la arquitectura visual de zeekrlife.com/es-mx (hero slider,
secciones fullscreen de modelos, footer negro) + contenido de Zeekr Paraguay.

Ejecutar: python3 build_site.py
"""
import json
import os

DOMAIN = "https://zeekrlife.com.py"

# ------------------------------------------------------------------ partials
LOGO_SVG = ('<svg class="logo" viewBox="0 0 80 80" fill="currentColor" aria-hidden="true">'
            '<circle cx="40" cy="40" r="40"/>'
            '<path fill-rule="evenodd" fill="#0F0F0F" d="M13.3 10.7h22.2l-.05 34.6H13.3V34.4h10.4v-2.6H13.3V10.7Zm45.4 51.3H14.7L47 44.4l11.7 17.6Zm8-2H54.8l-.1-49.3h12V60Zm-12-49.3h12v38l-12 11.3Z"/></svg>')

WA_NUMBER = "595971370006"


def slugify(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")


def anchor(s):
    return "n-" + slugify(s)[:60].strip("-")

# --- datos de modelos ------------------------------------------------------
MODELS = {
    "001": {
        "name": "ZEEKR 001",
        "tagline": "El crossover de lujo",
        "claim": "Impresionante, potente, refinado.",
        "hero_desktop": "images/hero/001-desktop.jpg",
        "hero_mobile": "images/hero/001-mobile.jpg",
        "card": "images/modelos/001.jpg",
        "stats": [("620 km", "Autonomía (WLTP)"), ("3,8 s", "0–100 km/h (AWD)"), ("536 HP", "Potencia máxima")],
        "pages": {"home": "zeekr001.html"},
    },
    "x": {
        "name": "ZEEKR X",
        "tagline": "El SUV urbano premium",
        "claim": "Audaz, inteligente y elegante.",
        "hero_desktop": "images/hero/x-desktop.jpg",
        "hero_mobile": "images/hero/x-mobile.jpg",
        "card": "images/modelos/x.jpg",
        "stats": [("446 km", "Autonomía (WLTP)"), ("3,8 s", "0–100 km/h (AWD)"), ("428 HP", "Potencia máxima")],
        "pages": {"home": "zeekrx.html"},
    },
    "7x": {
        "name": "ZEEKR 7X",
        "tagline": "El SUV de próxima generación",
        "claim": "Diseñado para Noto disfrutar, construido para llegar más lejos.",
        "hero_desktop": "images/hero/7x-desktop.jpg",
        "hero_mobile": "images/hero/7x-mobile.jpg",
        "card": "images/modelos/7x.jpg",
        "stats": [("800 V", "Sistema de alto voltaje"), ("3,8 s", "Aceleración 0–100 km/h"), ("543 km", "Autonomía estimada")],
        "pages": {"home": "zeekr7x.html"},
    },
}

NEWS = [
    {"date": "2025-01-08", "day": "8 de enero de 2025", "title": "Zeekr en CES 2025: presenta tecnología líder en la industria, estrategia de co-creación y una solución energética global", "img": "images/noticias/ces-2025.png"},
    {"date": "2025-01-06", "day": "6 de enero de 2025", "title": "Zeekr amplía su asociación con Qualcomm para ofrecer una experiencia de entretenimiento inmersiva en los vehículos del futuro", "img": "images/noticias/asociacion-qualcomm.png"},
    {"date": "2024-12-06", "day": "6 de diciembre de 2024", "title": "Zeekr: la revolución eléctrica que nace desde el punto cero", "img": "images/noticias/revolucion-electrica.png"},
    {"date": "2024-12-13", "day": "13 de diciembre de 2024", "title": "ZEEKR 001: luces inteligentes para iluminar tu camino", "img": "images/noticias/luces-inteligentes.png"},
    {"date": "2024-11-14", "day": "14 de noviembre de 2024", "title": "¿AWD o RWD? Descubre las diferencias de tracción en los modelos Zeekr", "img": "images/noticias/diferencias-traccion.png"},
    {"date": "2024-10-25", "day": "25 de octubre de 2024", "title": "Sumérgete en la experiencia de audio premium de Zeekr", "img": "images/noticias/audio-premium.png"},
    {"date": "2024-08-23", "day": "23 de agosto de 2024", "title": "¿Por qué Zeekr X es el SUV eléctrico que define una nueva era de movilidad?", "img": "images/noticias/suvelectrico.png"},
    {"date": "2024-05-10", "day": "10 de mayo de 2024", "title": "Un hito importante en el viaje global de la empresa Zeekr, tras la finalización de la oferta pública inicial en la Bolsa de Nueva York", "img": "images/noticias/noticia1.jpg"},
    {"date": "2024-04-09", "day": "9 de abril de 2024", "title": "Zeekr M-Vision, un concepto completamente reimaginado para el futuro de la movilidad", "img": "images/noticias/noticia2.png"},
]


def header(active, root=""):
    def cls(a): return "menu-link active" if a == active else "menu-link"
    gates = [
        ("001", "ZEEKR 001", f"{root}zeekr001.html", f"{root}images/menu/zeekr_001.png"),
        ("x", "ZEEKR X", f"{root}zeekrx.html", f"{root}images/menu/zeekr_x.png"),
        ("7x", "ZEEKR 7X", f"{root}zeekr7x.html", f"{root}images/menu/zeekr_7x.png"),
    ]
    items = "\n".join(
        f"""      <a class="gate-card" href="{href}">
        <img src="{img}" alt="{name}" width="300" height="150">
        <span>{name}</span>
      </a>""" for a, name, href, img in gates)
    return f"""
<a class="skip-link" href="#main">Saltar al contenido</a>
<header class="site-header" id="siteHeader">
  <div class="header-inner">
    <div class="header-left">
      <a class="header-logo" href="{root}index.html" aria-label="ZEEKR Paraguay — Inicio">{LOGO_SVG}</a>
      <nav class="header-menus" aria-label="Principal">
        <button class="menu-link models-trigger {cls(active) if active else ''}" type="button" aria-expanded="false" aria-controls="modelsPanel" data-toggle-models>Modelos</button>
        <a class="{cls('nosotros')}" href="{root}nosotros.html">Nosotros</a>
        <a class="{cls('noticias')}" href="{root}noticias.html">Noticias</a>
        <a class="menu-link" href="#contacto-footer">Servicio</a>
      </nav>
    </div>
    <a class="header-wordmark" href="{root}index.html" aria-label="ZEEKR Paraguay — Inicio">ZEEKR</a>
    <div class="header-right">
      <a class="menu-link" href="#" data-open-contact>Prueba de manejo</a>
      <a class="menu-link" href="#" data-open-contact>Contáctanos</a>
      <a class="menu-link" href="{root}nosotros.html">Distribuidores</a>
      <span class="header-locale"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M3 12h18M12 3c3 3.5 3 14 0 18M12 3c-3 3.5-3 14 0 18" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>&nbsp;Paraguay/Español</span>
      <button class="burger" type="button" aria-label="Abrir menú" aria-expanded="false" aria-controls="mobileMenu" data-open-menu>
        <span></span><span></span>
      </button>
    </div>
  </div>
  <div class="models-panel" id="modelsPanel" hidden>
    <div class="models-panel-inner">
      <p class="models-heading">Modelos</p>
      {items}
    </div>
  </div>
  <div class="mobile-menu" id="mobileMenu" hidden>
    <div class="mobile-menu-head">
      <a href="{root}index.html" aria-label="ZEEKR Paraguay — Inicio">{LOGO_SVG}</a>
      <button class="mm-close" type="button" aria-label="Cerrar menú" data-close-menu>&times;</button>
    </div>
    <nav aria-label="Menú móvil">
      <a data-close-menu href="{root}index.html">Inicio</a>
      <a data-close-menu href="{root}zeekr001.html">ZEEKR 001</a>
      <a data-close-menu href="{root}zeekrx.html">ZEEKR X</a>
      <a data-close-menu href="{root}zeekr7x.html">ZEEKR 7X</a>
      <a data-close-menu href="{root}noticias.html">Noticias</a>
      <a data-close-menu href="{root}nosotros.html">Nosotros</a>
    </nav>
    <button class="btn btn-solid mobile-cta" data-open-contact>Contacto &amp; test drive</button>
  </div>
</header>
<div class="nav-shade" data-close-models hidden></div>
<div class="cookie-banner" id="cookieBanner" hidden role="dialog" aria-label="Consentimiento de cookies">
  <p class="cookie-text">Cuando visita nuestro sitio web ("Plataformas Zeekr"), utilizamos cookies y otras tecnologías de seguimiento similares para mejorar la funcionalidad de las Plataformas Zeekr, el rendimiento, medir el tráfico del sitio web, analizar el comportamiento del usuario y ajustar nuestro contenido y servicios. Si hace clic en "Aceptar todo" nos autoriza a procesar sus datos personales para tales fines. Si hace clic en "Rechazar todo" sólo utilizaremos cookies y tecnología de rastreo que sean estrictamente necesarias para la funcionalidad de la Plataforma Zeekr. Para más información o para consentir cookies específicas y tecnología de rastreo por favor haga clic en Configuración de Cookies.</p>
  <div class="cookie-actions">
    <button class="btn btn-outline-dark" type="button" data-cookie-settings>Configuración de Cookies</button>
    <button class="btn btn-dark" type="button" data-cookie-reject>Rechazar Todo</button>
    <button class="btn btn-dark" type="button" data-cookie-accept>Aceptar Todo</button>
  </div>
  <div class="cookie-settings" id="cookieSettings" hidden>
    <label><input type="checkbox" checked disabled> Necesarias (siempre activas)</label>
    <label><input type="checkbox" id="ckAnalytics" checked> Analíticas y rendimiento</label>
    <div class="cookie-actions">
      <button class="btn btn-dark" type="button" data-cookie-save>Guardar preferencias</button>
    </div>
  </div>
</div>"""


def footer(root=""):
    wa = f"https://wa.me/{WA_NUMBER}"
    return f"""
<footer class="site-footer" id="contacto-footer">
  <div class="footer-grid">
    <a class="footer-logo" href="{root}index.html" aria-label="ZEEKR Paraguay — Inicio">{LOGO_SVG}</a>
    <div class="footer-col">
      <p class="footer-title">Modelos</p>
      <ul>
        <li><a href="{root}zeekr001.html">ZEEKR 001</a></li>
        <li><a href="{root}zeekrx.html">ZEEKR X</a></li>
        <li><a href="{root}zeekr7x.html">ZEEKR 7X</a></li>
      </ul>
    </div>
    <div class="footer-col">
      <p class="footer-title">Compañía</p>
      <ul>
        <li><a href="{root}noticias.html">Noticias</a></li>
        <li><a href="{root}nosotros.html">Nosotros</a></li>
        <li><a href="#foot-contact" data-open-contact>Contáctanos</a></li>
        <li><a href="#foot-contact" data-open-contact>Prueba de manejo</a></li>
      </ul>
    </div>
    <div class="footer-col">
      <p class="footer-title">Atención a clientes</p>
      <ul>
        <li><a href="tel:+595971370006">0971 370 006 · ventas</a></li>
        <li><a href="tel:+595976979155">0976 979 155 · ventas</a></li>
        <li><a href="tel:+595976203280">0976 203 280 · ventas</a></li>
        <li><a href="tel:+595974772247">+595 974 772 247 · postventa</a></li>
      </ul>
    </div>
    <div class="footer-col footer-social">
      <p class="footer-title">Síguenos</p>
      <div class="social-row">
        <a href="https://www.instagram.com/zeekrparaguay/" rel="nofollow noopener" target="_blank" aria-label="Instagram de Zeekr Paraguay">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r="1" fill="currentColor" stroke="none"/></svg>
        </a>
        <a href="https://www.linkedin.com/company/zeekr" rel="nofollow noopener" target="_blank" aria-label="LinkedIn de Zeekr">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M4.98 3.5A2.49 2.49 0 1 1 5 8.48a2.49 2.49 0 0 1-.02-4.98ZM3 9.75h4v11H3v-11Zm6.5 0h3.83v1.5h.05c.53-1 1.84-2.06 3.79-2.06 4.05 0 4.8 2.67 4.8 6.14v5.42h-4v-4.8c0-1.15-.02-2.63-1.6-2.63-1.6 0-1.85 1.25-1.85 2.55v4.88h-4v-11Z"/></svg>
        </a>
      </div>
    </div>
  </div>
  <div class="footer-bottom">
    <p class="footer-copy">&copy; 2026 ZEEKR y todos sus afiliados. Todos los derechos reservados &middot; Zeekr Paraguay</p>
    <p class="footer-disclaimer">Toda la información contenida en este material está basada en datos disponibles al momento de su publicación. Las fotos y pantallas son de carácter ilustrativo y de referencia. Los datos de autonomía y prestaciones se basan en ciclos de prueba (WLTP / pruebas de ingeniería) y pueden variar según clima, camino, carga, batería y configuración del vehículo.</p>
  </div>
</footer>

<div class="modal-contact" id="contactModal" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cmTitle">
  <div class="modal-mask" data-close-contact></div>
  <div class="modal-panel">
    <button class="modal-close" type="button" aria-label="Cerrar" data-close-contact>&times;</button>
    <h2 id="cmTitle">Contacto</h2>
    <p class="modal-sub">Escribinos y un asesor te responde en el día.</p>
    <div class="contact-cards">
      <a class="contact-card" href="tel:+595971370006"><span>Ventas</span><strong>0971 370 006</strong></a>
      <a class="contact-card" href="tel:+595976979155"><span>Ventas</span><strong>0976 979 155</strong></a>
      <a class="contact-card" href="tel:+595976203280"><span>Ventas</span><strong>0976 203 280</strong></a>
      <a class="contact-card" href="tel:+595974772247"><span>Postventa</span><strong>0974 772 247</strong></a>
    </div>
    <form id="waForm" class="contact-form" data-wa="{WA_NUMBER}">
      <label class="sr-only" for="cf-nombre">Nombre y apellido</label>
      <input id="cf-nombre" type="text" name="nombre" placeholder="Nombre y apellido" required autocomplete="name">
      <label class="sr-only" for="cf-tel">Teléfono</label>
      <input id="cf-tel" type="tel" name="telefono" placeholder="Teléfono (ej. 0981 123 456)" required autocomplete="tel">
      <label class="sr-only" for="cf-modelo">Modelo de interés</label>
      <select id="cf-modelo" name="modelo" aria-label="Modelo de interés">
        <option>ZEEKR 001</option><option>ZEEKR X</option><option>ZEEKR 7X</option><option>Aún no lo sé</option>
      </select>
      <label class="sr-only" for="cf-msg">Mensaje</label>
      <textarea id="cf-msg" name="mensaje" rows="2" placeholder="Mensaje (opcional)"></textarea>
      <button class="btn btn-solid" type="submit">Enviar por WhatsApp</button>
      <p class="form-note">Al enviar, se abre WhatsApp con tu mensaje listo. Al enviarlo aceptás que Zeekr procese tus datos para gestionar tu consulta.</p>
    </form>
  </div>
</div>"""


def head_block(title, desc, canonical, jsonld, root="", og_img="images/og.jpg", preload=""):
    return f"""  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0F0F0F">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{DOMAIN}/{canonical}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <meta property="og:site_name" content="ZEEKR Paraguay">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{DOMAIN}/{canonical}">
  <meta property="og:locale" content="es_PY">
  <meta property="og:image" content="{DOMAIN}/{og_img}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{DOMAIN}/{og_img}">
  <link rel="icon" href="{root}favicon.png">
  <link rel="stylesheet" href="{root}css/zeekr-site.css?v=2">
  {f'<link rel="preload" as="image" href="{preload}" media="(min-width:768px)">' if preload else ''}
  <script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False) if not isinstance(jsonld, str) else jsonld}</script>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-E6H9ZC5CG3"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}};gtag('js',new Date());gtag('config','G-E6H9ZC5CG3');</script>"""


def render_page(fname, title, desc, canonical, content, nav_active, jsonld="", root="", og_img="images/og.jpg", preload=""):
    import json as _j
    head = head_block(title, desc, canonical, jsonld=_j.dumps(jsonld, ensure_ascii=False) if not isinstance(jsonld, str) else jsonld, root=root, og_img=og_img, preload=preload)
    html = f"""<!DOCTYPE html>
<html lang="es-PY">
<head>
{head}
</head>
<body class="page-{fname.replace('.html','') or 'home'}">
{header(nav_active, root)}
<main id="main">
{content}
</main>
{footer(root)}
<script src="{root}js/main.js?v=2" defer></script>
</body>
</html>"""
    open(fname, "w").write(html)
    print("OK", fname)


# ------------------------------------------------------------------ home
def heroes():
    slides = []
    order = ["7x", "x", "001"]
    for i, key in enumerate(order):
        m = MODELS[key]
        slides.append(f"""
        <figure class="slide{' active' if i == 0 else ''}"{'' if i == 0 else ' aria-hidden="true"'} data-slide>
          <picture>
            <source media="(max-width:767px)" srcset="{m['hero_mobile']}">
            <img class="slide-image" src="{m['hero_desktop']}" alt="ZEEKR {key.upper() if key!='7x' else '7X'} — {m['claim']}" fetchpriority="{'high' if i==0 else 'low'}" loading="{'eager' if i==0 else 'lazy'}">
          </figure>
          <div class="shade"></div>
          <div class="slide-content">
            <h2>{m['name']}</h2>
            <p>{m['claim']}</p>
            <div class="slide-buttons">
              <a class="btn btn-solid" href="{m['pages']['home']}">Conoce más</a>
              <button class="btn btn-outline-light" type="button" data-open-contact data-model="{m['name']}">Agendá tu test drive</button>
            </div>
          </div>
        </figure>""")
    bars = "".join(f'<button class="pager-bar{" active" if i==0 else ""}" data-goto="{i}" aria-label="Slide {i+1}"></button>' for i in range(3))
    return f"""
<section class="hero" aria-label="Modelos destacados">
  {"".join(slides)}
  <div class="hero-pager">{bars}</div>
</section>"""


def status_band():
    return """
<section class="status-band">
  <p>Somos <strong>ZEEKR</strong></p>
  <p class="status-sub">Por medio del diseño, la tecnología y la innovación motivamos a todos a reimaginar los automóviles eléctricos.</p>
</section>"""


def model_cards():
    items = []
    for key in ["001", "x", "7x"]:
        m = MODELS[key]
        title = m["name"]
        sub = m["tagline"]
        stats = "".join(
            f'<div class="ind"><span class="ind-value">{v}</span><span class="ind-label">{l}</span></div>'
            for v, l in m["stats"])
        items.append(f"""
        <article class="model-card" id="modelo-{key}">
          <figure class="model-media">
            <img src="{m['card']}" alt="{title}, {sub}" loading="lazy" srcset="{m['card']} 2200w" sizes="(max-width:991px) 100vw, 99vw">
            <div class="model-shade"></div>
          </figure>
          <div class="model-content">
            <div class="model-head">
              <h3><a href="{m['pages']['home']}">{title}</a></h3>
              <p class="model-sub">{sub}</p>
              <p class="model-claim">{m['claim']}</p>
            </div>
            <div class="model-stats">{stats}</div>
            <a class="btn btn-outline-light model-cta" href="{m['pages']['home']}">M&aacute;s informaci&oacute;n</a>
          </div>
        </article>""")
    return "".join(items)


def news_cards():
    cards = []
    for n in NEWS[:3]:
        cards.append(f"""
        <article class="news-item">
          <a href="noticias.html#{anchor(n['title'])}">
            <figure class="news-media"><img src="{n['img']}" alt="{n['title']}" loading="lazy"></figure>
            <p class="news-date">{n['day']}</p>
            <h3 class="news-title3">{n['title']}</h3>
          </a>
        </article>""")
    return "".join(cards)


def contact_strip():
    return """
<section class="contact-strip">
  <div>
    <h2>Estamos para ayudarte</h2>
    <p>Ventas: 0971&nbsp;370&nbsp;006 · 0976&nbsp;979&nbsp;155 · 0976&nbsp;203&nbsp;280<br>Postventa: +595&nbsp;974&nbsp;772&nbsp;247</p>
  </div>
  <button class="btn btn-solid" data-open-contact>Contáctanos</button>
</section>"""


HOME_JSONLD = {
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "WebSite", "name": "ZEEKR Paraguay", "url": DOMAIN + "/", "inLanguage": "es-PY"},
        {"@type": "Organization", "name": "ZEEKR Paraguay", "url": DOMAIN + "/",
         "logo": DOMAIN + "/favicon.png",
         "contactPoint": [
             {"@type": "ContactPoint", "telephone": "+595-971-370-006", "contactType": "sales", "availableLanguage": "es"},
             {"@type": "ContactPoint", "telephone": "+595-976-203-280", "contactType": "customer service", "availableLanguage": "es"},
         ]},
        {"@type": "ItemList", "name": "Modelos Zeekr Paraguay", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ZEEKR 001", "url": DOMAIN + "/zeekr001.html"},
            {"@type": "ListItem", "position": 2, "name": "ZEEKR X", "url": DOMAIN + "/zeekrx.html"},
            {"@type": "ListItem", "position": 3, "name": "ZEEKR 7X", "url": DOMAIN + "/zeekr7x.html"},
        ]},
    ],
}


def build_index():
    content = heroes() + status_band() + f"""
<section class="models" aria-label="Modelos Zeekr">
  {model_cards()}
</section>
<section class="news" aria-label="Últimas noticias">
  <h2 class="section-title">Últimas noticias</h2>
  <div class="news-grid">{news_cards()}</div>
  <div class="section-more"><a class="btn btn-outline-light" href="noticias.html">Ver todas las noticias</a></div>
</section>
""" + contact_strip()
    render_page(
        "index.html",
        "ZEEKR Paraguay | Vehículos Eléctricos Premium: 001, X y 7X",
        "Descubrí los vehículos eléctricos premium ZEEKR en Paraguay: ZEEKR 001, ZEEKR X y ZEEKR 7X. Diseño de vanguardia, tecnología líder mundial y autonomía real. Agendá tu test drive.",
        "",
        content,
        nav_active="",
        jsonld=HOME_JSONLD,
        preload=MODELS["7x"]["hero_desktop"],
    )


# ------------------------------------------------------------------ helpers de página
def hero_model(m):
    stats = "".join(f'<div class="ind"><span class="ind-value">{v}</span><span class="ind-label">{l}</span></div>' for v, l in m["stats"])
    return f"""
<section class="hero-model">
  <picture>
    <source media="(max-width:767px)" srcset="{m.get('model_hero_mobile', m['card'])}">
    <img class="hero-bg" src="{m.get('model_hero_desktop', m['card'])}" alt="{m['name']} — {m['tagline']}" fetchpriority="high">
  </picture>
  <div class="shade"></div>
  <div class="hero-inner">
    <p class="eyebrow">ZEEKR Paraguay</p>
    <h1>{m['name']}</h1>
    <p class="claim">{m['claim']}</p>
    <button class="btn btn-solid" type="button" data-open-contact data-model="{m['name']}">Agendá tu test drive</button>
    <div class="stats-row">{stats}</div>
  </div>
</section>"""


def spec_table(rows, caption):
    trs = "".join(f'<tr><td class="k">{k}</td><td>{v}</td></tr>' for k, v in rows)
    return f'<table class="spec"><caption class="sr-only">{caption}</caption><tbody>{trs}</tbody></table>'


def breadcrumb(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + "/" + u}
                                for i, (n, u) in enumerate(items)]}


# ------------------------------------------------------------------ ZEEKR 001
def page_001():
    m = MODELS["001"]
    content = hero_model(m) + """
<section class="section">
  <div class="split">
    <figure class="visual"><img src="images/zeekr001/caracteristica1.jpg" alt="ZEEKR 001 exterior" loading="lazy"></figure>
    <div>
      <p class="eyebrow kicker">El crossover de lujo, reinventado</p>
      <h2>El primer deportivo familiar eléctrico puro producido en masa del mundo</h2>
      <p style="margin-top:16px">El ZEEKR 001 ofrece algo nuevo para todos. La combinación de elegancia y confort brinda un paseo lujoso para aventuras de toda la familia.</p>
    </div>
  </div>
</section>
<section class="section dark">
  <div class="split">
    <div>
      <p class="eyebrow kicker">Arquitectura SEA</p>
      <h2>Tecnología que lleva los vehículos eléctricos más lejos</h2>
      <p style="margin-top:16px">Cada Zeekr se basa en la Arquitectura de Experiencia Sostenible (SEA): una plataforma totalmente eléctrica, modular y escalable que integra las últimas tecnologías. Autonomía de hasta 620 km y carga del 10% al 80% en menos de 30 minutos con carga estándar DC de 200 kW a bordo.</p>
    </div>
    <figure class="visual"><img src="images/zeekr001/chasis1.jpg" alt="Arquitectura SEA del ZEEKR 001" loading="lazy"></figure>
  </div>
</section>
<section class="section">
  <p class="eyebrow kicker">Prestaciones</p>
  <h2>0–100 km/h en 3,8 s (AWD)</h2>
  <div class="stat-grid">
    <div class="ind"><span class="ind-value">536 HP</span><span class="ind-label">Potencia máxima (AWD)</span></div>
    <div class="ind"><span class="ind-value">200 km/h</span><span class="ind-label">Velocidad máxima</span></div>
    <div class="ind"><span class="ind-value">620 km</span><span class="ind-label">Autonomía WLTP (RWD)</span></div>
    <div class="ind"><span class="ind-value">100 kWh</span><span class="ind-label">Batería</span></div>
  </div>
  <div class="feature-list">
    <div class="feature"><h3>Suspensión neumática automática</h3><p>Totalmente equipada*. Ajuste de altura en cinco niveles en tiempo real. *Solo disponible en Flagship.</p></div>
    <div class="feature"><h3>Frenos regenerativos</h3><p>Aprovecha la energía para recargar mientras conduces.</p></div>
    <div class="feature"><h3>Motores de alto rendimiento</h3><p>536 HP, 16.500 rpm de rotación máxima y hasta 97,86% de eficiencia del motor.</p></div>
  </div>
</section>
<section class="section dark">
  <p class="eyebrow kicker">Inteligente</p>
  <h2>Cabina inteligente con OTA</h2>
  <p style="color:var(--ink-70);margin-top:14px">Hardware potente y software en evolución continua. Las actualizaciones Over The Air garantizan que el vehículo esté siempre al día.</p>
  <div class="feature-list">
    <div class="feature"><h3>Falcon Eye Vidar</h3><p>15 cámaras HD, 7 kits de cámaras de 8 MP, radar de alcance ultralargo de 250 m y 12 radares ultrasónicos.</p></div>
    <div class="feature"><h3>Interior lujoso</h3><p>Materiales de primera calidad y acabados bellos: tecnología digital de cabina de última generación.</p></div>
    <div class="feature"><h3>Amplio maletero 2.144 L</h3><p>Cajuela divisible que puede ampliarse hasta 2.144 L, para usarla como quieras.</p></div>
  </div>
</section>
<section class="section">
  <p class="eyebrow kicker">Compara</p>
  <h2>La máxima experiencia Zeekr</h2>
  <div class="spec-cols">
    <div>
      <h3>Flagship AWD</h3>
      """ + spec_table([("Aceleración", "3,8 s"), ("Motor", "Doble"), ("Tracción", "All Wheel Drive"), ("Rango", "580 km (WLTP)"), ("Potencia", "536 HP"), ("Rines de aluminio", '22"'), ("Suspensión activa", "Sí"), ("Sistema de audio", "Yamaha 12 bocinas + 1 subwoofer"), ("Asientos ventilación + masaje", "Sí")], "Ficha técnica ZEEKR 001 Flagship AWD") + """
    </div>
    <div>
      <h3>Sport RWD</h3>
      """ + spec_table([("Aceleración", "7,2 s"), ("Motor", "Sencillo"), ("Tracción", "Rear Wheel Drive"), ("Rango", "620 km (WLTP)"), ("Potencia", "268 HP"), ("Rines de aluminio", '21"'), ("Suspensión activa", "No"), ("Sistema de audio", "Yamaha 12 bocinas + 1 subwoofer"), ("Asientos ventilación + masaje", "No")], "Ficha técnica ZEEKR 001 Sport RWD") + """
    </div>
  </div>
</section>
<section class="section">
  <h2>Dimensiones</h2>
  <div class="spec-cols" style="grid-template-columns:1fr">
    """ + spec_table([("Altura", "1.560 mm"), ("Largo", "4.955 mm"), ("Distancia entre ejes", "2.999 mm"), ("Ancho", "2.005 mm")], "Dimensiones ZEEKR 001") + """
  </div>
</section>""" + contact_strip()
    jsonld = {"@context": "https://schema.org", "@type": "Product", "name": "ZEEKR 001",
              "brand": {"@type": "Brand", "name": "ZEEKR"},
              "description": "Deportivo familiar eléctrico premium. Hasta 620 km de autonomía WLTP, aceleración 0–100 km/h en 3,8 s (AWD) y batería de 100 kWh.",
              "breadcrumb": "ZEEKR Paraguay > ZEEKR 001"}
    render_page("zeekr001.html", "ZEEKR 001 | Crossover eléctrico de lujo — ZEEKR Paraguay",
                "El ZEEKR 001 en Paraguay: crossover eléctrico premium con hasta 620 km de autonomía (WLTP), 0–100 km/h en 3,8 s y batería de 100 kWh. Ficha técnica completa y test drive.",
                "zeekr001.html", content, nav_active="001", jsonld=jsonld, preload=m["card"])


# ------------------------------------------------------------------ ZEEKR X
def page_x():
    m = MODELS["x"]
    content = hero_model(m) + """
<section class="section">
  <div class="split">
    <figure class="visual"><img src="images/zeekrx/caracteristica1.jpg" alt="ZEEKR X exterior urbano" loading="lazy"></figure>
    <div>
      <p class="eyebrow kicker">El SUV urbano que potencializa tu estilo de vida</p>
      <h2>Llevando el SUV urbano al siguiente nivel</h2>
      <p style="margin-top:16px">El nuevo ZEEKR X es un SUV compacto de lujo creado para los estilos de vida urbanos de hoy: el compañero perfecto para aventureros y familias. La combinación perfecta de líneas atrevidas, tecnología inteligente y máxima comodidad.</p>
    </div>
  </div>
</section>
<section class="section dark">
  <p class="eyebrow kicker">Prestaciones</p>
  <h2>0–100 km/h en 3,8 s (AWD)</h2>
  <div class="stat-grid">
    <div class="ind"><span class="ind-value">428 HP</span><span class="ind-label">Potencia máxima (AWD)</span></div>
    <div class="ind"><span class="ind-value">190 km/h</span><span class="ind-label">Velocidad máxima (AWD)</span></div>
    <div class="ind"><span class="ind-value">440 km</span><span class="ind-label">Autonomía WLTP (RWD)</span></div>
    <div class="ind"><span class="ind-value">69 kWh</span><span class="ind-label">Batería</span></div>
  </div>
  <div class="feature-list">
    <div class="feature"><h3>XTCS antideslizante inteligente</h3><p>Control de tracción propio de ZEEKR: identifica y controla el derrape en 6 ms, 10 veces más rápido que un TCS tradicional.</p></div>
    <div class="feature"><h3>Techo panorámico doble</h3><p>Tragaluz de 1,21 m² con aislamiento térmico y acústico, y barrera UV del 99%.</p></div>
    <div class="feature"><h3>Seguridad integral</h3><p>Vigas anticolisión multicapa de 8 tubos y 7 airbags con protección envolvente de 360°.</p></div>
  </div>
</section>
<section class="section">
  <p class="eyebrow kicker">Inteligente</p>
  <h2>ZEEKR AD y cabina inteligente</h2>
  <div class="feature-list">
    <div class="feature"><h3>OTA Over The Air</h3><p>Actualizaciones de software garantizan que tu vehículo esté siempre actualizado.</p></div>
    <div class="feature"><h3>ZEEKR AD</h3><p>5 cámaras HD, 5 radares milimétricos y 12 ultrasónicos con más de 10 funciones de asistencia: crucero adaptativo y estacionamiento.</p></div>
    <div class="feature"><h3>Luces diurnas de doble línea</h3><p>56 LED independientes integran DRL, luces laterales e intermitentes en un solo sistema.</p></div>
  </div>
</section>
<section class="section dark">
  <p class="eyebrow kicker">Compara</p>
  <h2>Elige el ZEEKR X que se adapte a tu estilo</h2>
  <div class="spec-cols">
    <div>
      <h3>Flagship AWD — La máxima experiencia Zeekr</h3>
      """ + spec_table([("Aceleración", "3,8 s"), ("Motor", "Doble"), ("Tracción", "All Wheel Drive"), ("Rango", "420 km (WLTP)"), ("Potencia", "428 HP"), ("Rines", 'Aluminio 20"')], "Ficha técnica ZEEKR X Flagship AWD") + """
    </div>
    <div>
      <h3>Premium RWD — Tu acceso a Zeekr</h3>
      """ + spec_table([("Aceleración", "5,6 s"), ("Motor", "Sencillo"), ("Tracción", "Rear Wheel Drive"), ("Rango", "440 km (WLTP)"), ("Potencia", "268 HP"), ("Rines", 'Aluminio 19"')], "Ficha técnica ZEEKR X Premium RWD") + """
    </div>
  </div>
</section>
<section class="section">
  <h2>Dimensiones</h2>
  <div class="spec-cols" style="grid-template-columns:1fr">
    """ + spec_table([("Altura", "1.566 mm"), ("Largo", "4.432 mm"), ("Distancia entre ejes", "2.750 mm"), ("Ancho", "1.836 mm")], "Dimensiones ZEEKR X") + """
  </div>
</section>""" + contact_strip()
    jsonld = {"@context": "https://schema.org", "@type": "Product", "name": "ZEEKR X",
              "brand": {"@type": "Brand", "name": "ZEEKR"},
              "description": "SUV compacto eléctrico premium. Hasta 440 km de autonomía WLTP (RWD), 0–100 km/h en 3,8 s (AWD) y batería de 69 kWh.",
              "breadcrumb": "ZEEKR Paraguay > ZEEKR X"}
    render_page("zeekrx.html", "ZEEKR X | SUV eléctrico urbano premium — ZEEKR Paraguay",
                "ZEEKR X en Paraguay: SUV eléctrico urbano premium con hasta 440 km de autonomía (WLTP), 0–100 km/h en 3,8 s, techo panorámico y XTCS inteligente. Conocé sus versiones.",
                "zeekrx.html", content, nav_active="x", jsonld=jsonld, preload=m["card"])


# ------------------------------------------------------------------ ZEEKR 7X
def page_7x():
    m = MODELS["7x"]
    content = hero_model(m) + """
<section class="section">
  <p class="eyebrow kicker">Explora lo que hace único al ZEEKR 7X</p>
  <h2>Conoce los SUV de próxima generación</h2>
  <div class="feature-list">
    <div class="feature"><h3>Diseño Futurista</h3><p>Líneas limpias, proporciones elegantes y un diseño que destaca.</p></div>
    <div class="feature"><h3>Cabina Snapdragon 8295</h3><p>Respuesta inmediata, controles fluidos y experiencia digital de alto nivel.</p></div>
    <div class="feature"><h3>Confort de primera clase</h3><p>Asientos NAPPA con ventilación, calefacción y masaje para viajar mejor.</p></div>
    <div class="feature"><h3>Seguridad que anticipa</h3><p>ADAS avanzado y 7 airbags para manejar con total confianza.</p></div>
    <div class="feature"><h3>0–100 km/h en 3,8 s</h3><p>Aceleración contundente y control total, sin sacrificar estabilidad.</p></div>
    <div class="feature"><h3>Sistema de alto voltaje 800 V</h3><p>Carga ultrarrápida y gestión térmica eficiente para rendir siempre.</p></div>
  </div>
</section>
<section class="section dark">
  <div class="split">
    <figure class="visual"><img src="images/zeekr7x/diseno-exterior.jpg" alt="Diseño exterior del ZEEKR 7X" loading="lazy"></figure>
    <div>
      <p class="eyebrow kicker">Exterior</p>
      <h2>Colores inspirados en la ciudad</h2>
      <div class="color-chips" role="group" aria-label="Colores exterior">
        <button class="chip" style="background:#101216" data-bg="#0F0F0F" data-name="Onyx Black" data-target="swatch" aria-pressed="true" aria-label="Onyx Black"></button>
        <button class="chip" style="background:#8E9194" data-bg="#8E9194" data-name="Tech Gray" data-target="swatch" aria-label="Tech Gray"></button>
        <button class="chip" style="background:#F2F1EC" data-bg="#F2F1EC" data-name="Crystal White" data-target="swatch" aria-label="Crystal White"></button>
        <button class="chip" style="linear-gradient(90deg,#3E6FA5,#C9CBD1)" data-bg="linear-gradient(90deg,#3E6FA5,#C9CBD1)" data-name="Brookblue + Silverroof" data-target="swatch" aria-label="Brookblue con techo silver"></button>
        <button class="chip" style="background:#2E4B33" data-bg="#2E4B33" data-name="Forest Green" data-target="swatch" aria-label="Forest Green"></button>
      </div>
      <div class="swatch-view" id="swatch" style="background:#0F0F0F;margin-top:18px;height:120px;border:1px solid var(--line-soft)"></div>
      <p style="margin-top:12px;color:var(--ink-70)">Color seleccionado: <strong><span id="swatchName">Onyx Black</span></strong></p>
    </div>
  </div>
</section>
<section class="section">
  <div class="split">
    <div>
      <p class="eyebrow kicker">Interior</p>
      <h2>Interiores que te hacen sentir como en casa</h2>
      <p style="margin-top:16px">Asientos forrados en piel, volante con calefacción y memorias, luz ambiental personalizable y mucho más. Asientos de segunda fila con calefacción, reclinación y cortina de privacidad eléctrica.</p>
    </div>
    <figure class="visual"><img src="images/zeekr7x/diseno-interior.jpg" alt="Diseño interior del ZEEKR 7X" loading="lazy"></figure>
  </div>
</section>
<section class="section dark">
  <p class="eyebrow kicker">Tecnología</p>
  <h2>Tecnología que impulsa el futuro</h2>
  <div class="feature-list">
    <div class="feature"><h3>Procesador Qualcomm 8295</h3><p>Chip de 5 nm que permite una experiencia digital en cabina más rápida y avanzada, líder en su segmento.</p></div>
    <div class="feature"><h3>Sistema interactivo total</h3><p>Panel HD de 13", head-up display AR de 36" y pantalla central Mini-LED 3.5K de 16".</p></div>
    <div class="feature"><h3>Zeekr OTA + App</h3><p>Actualizaciones por aire y control remoto de tu vehículo desde la app, desde cualquier lugar.</p></div>
    <div class="feature"><h3>Batería Qilin 100 kWh</h3><p>Autonomía máxima de hasta 615 km en la versión Premium.</p></div>
    <div class="feature"><h3>Gestión térmica PTM 2.0</h3><p>Gestiona el calor del vehículo y aprovecha mejor la energía para un desempeño eficiente.</p></div>
    <div class="feature"><h3>Arquitectura SEA</h3><p>Desarrollada sobre la plataforma SEA: cerca de 30 años de experiencia en fabricación de vehículos.</p></div>
  </div>
</section>
<section class="section">
  <p class="eyebrow kicker">Seguridad</p>
  <h2>Protección integral de 720° para cada pasajero</h2>
  <div class="feature-list">
    <div class="feature"><h3>Seguridad Activa 360°</h3><p>Asistencias avanzadas combinadas con múltiples cámaras, en todo momento.</p></div>
    <div class="feature"><h3>Modo Centinela</h3><p>Graba automáticamente la actividad circundante al detectar comportamiento sospechoso, con accesos solo para el propietario.</p></div>
    <div class="feature"><h3>Estructura tipo cúpula reforzada</h3><p>Absorbe la energía del impacto y protege pasajeros y batería.</p></div>
    <div class="feature"><h3>7 airbags + columna cortina</h3><p>Cobertura completa en la cabina para todos los ocupantes.</p></div>
    <div class="feature"><h3>Trasera aluminio una pieza</h3><p>Fundida a presión: mayor rigidez, ligereza y optimización del desempeño.</p></div>
    <div class="feature"><h3>Batería 10 rejillas</h3><p>Capaz de resistir hasta 75 toneladas de impacto lateral.</p></div>
  </div>
</section>
<section class="section dark">
  <p class="eyebrow kicker">Compara</p>
  <h2>Elige el ZEEKR 7X que se adapta a tu estilo</h2>
  <div class="spec-cols">
    <div>
      <h3>Smart</h3>
      """ + spec_table([("Autonomía", "480 km (WLTP)"), ("Aceleración 0–100 km/h", "6,0 s"), ("Potencia máxima", "421 HP RWD"), ("Batería", "75 kWh")], "Ficha técnica ZEEKR 7X Smart") + """
    </div>
    <div>
      <h3>Performance</h3>
      """ + spec_table([("Autonomía", "543 km (WLTP)"), ("Aceleración 0–100 km/h", "3,8 s"), ("Potencia máxima", "646 HP RWD"), ("Batería", "100 kWh")], "Ficha técnica ZEEKR 7X Performance") + """
    </div>
  </div>
</section>
<section class="section">
  <h2>Dimensiones y garantía</h2>
  <div class="spec-cols">
    <div>
      <h3>Dimensiones</h3>
      """ + spec_table([("Ancho (incl. espejos)", "1.930 mm"), ("Distancia entre ejes", "2.900 mm"), ("Longitud", "4.787 mm"), ("Altura máxima", "1.650 mm")], "Dimensiones ZEEKR 7X") + """
    </div>
    <div>
      <h3>Garantía</h3>
      """ + spec_table([("Vehículo", "5 años o 100.000 km, lo que ocurra primero"), ("Batería", "8 años o 160.000 km, lo que ocurra primero")], "Garantía ZEEKR 7X") + """
    </div>
  </div>
</section>""" + contact_strip()
    jsonld = {"@context": "https://schema.org", "@type": "Product", "name": "ZEEKR 7X",
              "brand": {"@type": "Brand", "name": "ZEEKR"},
              "description": "SUV de próxima generación con sistema de 800 V, aceleración 0–100 km/h en 3,8 s (Performance) y autonomía de hasta 543 km WLTP.",
              "breadcrumb": "ZEEKR Paraguay > ZEEKR 7X"}
    render_page("zeekr7x.html", "ZEEKR 7X | SUV eléctrico premium 800V y Snapdragon 8295 — ZEEKR Paraguay",
                "ZEEKR 7X en Paraguay: SUV eléctrico premium de próxima generación con sistema de 800 V, cabina Snapdragon 8295, 0–100 km/h en 3,8 s y hasta 543 km de autonomía. Dimensiones y garantía.",
                "zeekr7x.html", content, nav_active="7x", jsonld=jsonld, preload=m["card"])


# ------------------------------------------------------------------ Noticias
def page_noticias():
    entries = []
    for n in NEWS:
        entries.append(f"""
<article class="news-entry" id="{anchor(n['title'])}">
  <figure><img src="{n['img']}" alt="{n['title']}" loading="lazy"></figure>
  <div class="body">
    <p class="news-date">{n['day']}</p>
    <h2>{n['title']}</h2>
  </div>
</article>""")
    content = """
<section class="section" style="padding-bottom:32px">
  <p class="eyebrow kicker">ZEEKR Paraguay</p>
  <h1 class="section-title" style="text-align:left;margin:0">Noticias</h1>
</section>
<section class="news-list">""" + "".join(entries) + """</section>""" + contact_strip()
    jsonld = {"@context": "https://schema.org",
              "@type": "CollectionPage",
              "name": "Noticias — Zeekr Paraguay",
              "url": DOMAIN + "/noticias.html",
              "inLanguage": "es-PY",
              "about": {"@type": "Organization", "name": "ZEEKR Paraguay"}}
    render_page("noticias.html", "Noticias Zeekr Paraguay | Novedades y tecnología EV",
                "Todas las noticias de Zeekr en Paraguay: lanzamientos, tecnología eléctrica, alianzas, eventos internacionales y novedades de los modelos 001, X y 7X.",
                "noticias.html", content, nav_active="noticias", jsonld=jsonld)


# ------------------------------------------------------------------ Nosotros
def page_nosotros():
    content = hero_model({"name": "Nosotros",
                          "tagline": "Somos ZEEKR",
                          "claim": "Por medio del diseño, la tecnología y la innovación, motivamos a todos a reimaginar los automóviles eléctricos.",
                          "card": "images/nosotros/manufactura2.jpg",
                          "stats": []}) + """
<section class="section">
  <p class="eyebrow kicker">Nuestro nombre</p>
  <h2>ZEEKR: más allá del punto de partida</h2>
  <div class="brand-hex">
    <div class="feature"><h3>ZE</h3><p>Representa Zero, el punto de partida hacia las posibilidades infinitas.</p></div>
    <div class="feature"><h3>E</h3><p>Significa la evolución a la era eléctrica.</p></div>
    <div class="feature"><h3>KR</h3><p>Kriptón: un gas inusual que emite luz cuando se electrifica.</p></div>
  </div>
</section>
<section class="section dark">
  <p class="eyebrow kicker">Nuestros valores</p>
  <h2>Nuestro propósito es crear un ambiente armonioso entre el ser humano, la tecnología y la naturaleza</h2>
  <div class="feature-list">
    <div class="feature"><h3>Diversidad</h3><p>Promovemos la diversidad y celebramos las diferencias. Con una actitud abierta logramos innovar para un mejor futuro.</p></div>
    <div class="feature"><h3>Igualdad</h3><p>Mantenemos nuestra mente abierta y una comunicación transparente. La igualdad es necesaria en todas nuestras relaciones.</p></div>
    <div class="feature"><h3>Sostenibilidad</h3><p>Nos esforzamos por un futuro mejor para todos, abriendo camino con diseño innovador y soluciones tecnológicas.</p></div>
  </div>
</section>
<section class="section">
  <div class="split">
    <figure class="visual"><img src="images/nosotros/manufactura2.jpg" alt="Manufactura inteligente Zeekr" loading="lazy"></figure>
    <div>
      <p class="eyebrow kicker">Manufactura inteligente</p>
      <h2>Fábricas de vanguardia, mente nórdica</h2>
      <p style="margin-top:16px">Los vehículos ZEEKR se producen en una de las fábricas más avanzadas del mundo. El aclamado diseñador Stefan Sielaff dirige el centro global de diseño en Gotemburgo, Suecia, donde mentes creativas de todo el mundo diseñan los modelos ZEEKR del futuro.</p>
    </div>
  </div>
</section>
<section class="section">
  <div class="split">
    <div>
      <p class="eyebrow kicker">Geely Holding Group</p>
      <h2>Liderando el mundo de la movilidad Desde Hangzhou</h2>
      <p style="margin-top:16px">Geely Holding Group es dueño, invierte y gestiona múltiples marcas —Geely Auto, Lynk &amp; Co, Zeekr, Volvo, Polestar, Lotus, LEVC, Farizon, Radar y Cao Cao Mobility— con foco en innovación y movilidad sostenible. Zeekr es la marca de lujo eléctrico del Grupo, comprometida con dirigir el futuro de la movilidad centrada en la tecnología y el consumidor.</p>
    </div>
    <figure class="visual"><img src="images/nosotros/holding.jpg" alt="Geely Holding Group" loading="lazy"></figure>
  </div>
</section>""" + contact_strip()
    jsonld = {"@context": "https://schema.org", "@type": "AboutPage", "name": "Nosotros — Zeekr Paraguay", "url": DOMAIN + "/nosotros.html", "inLanguage": "es-PY"}
    render_page("nosotros.html", "Nosotros | ZEEKR Paraguay — la marca eléctrica premium de Geely",
                "Conocé la historia de Zeekr: diseño y tecnología de Gotemburgo y Hangzhou, el Grupo Geely y nuestra propuesta de movilidad eléctrica premium en Paraguay.",
                "nosotros.html", content, nav_active="nosotros", preload="images/nosotros/manufactura2.jpg")


# ------------------------------------------------------------------ sitemap / robots
def build_meta():

    urls = ["/", "/zeekr001.html", "/zeekrx.html", "/zeekr7x.html", "/noticias.html", "/nosotros.html"]
    today = "2026-09-17"
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"<url><loc>{DOMAIN}{u}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>{0.9 if u in ('/','/zeekr7x.html') else 0.8}</priority></url>")
    sm.append("</urlset>")
    open("sitemap.xml", "w").write("\n".join(sm))
    open("robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    print("OK sitemap.xml robots.txt –")


def main():
    build_index()
    build_meta()
    page_001()
    page_x()
    page_7x()
    page_noticias()
    page_nosotros()


if __name__ == "__main__":
    main()
