# -*- coding: utf-8 -*-
"""Generador estático del sitio ZEEKR Paraguay (zeekrlife.com.py).

Arquitectura visual de zeekrlife.com/es-mx (hero slider fullscreen, modelos
fullscreen con indicadores, noticias sobre blanco, footer negro) con contenido
de ZEEKR Paraguay. Tipografía oficial ZeekrHeadline / ZeekrText.

Salida (URLs limpias):
  /                      index.html
  /modelos/              modelos/index.html
  /modelos/zeekr-001/    modelos/zeekr-001/index.html   (idem zeekr-x, zeekr-7x)
  /noticias/             noticias/index.html
  /noticias/<slug>/      artículos con cuerpo (eventos propios)
  /nosotros/             nosotros/index.html
  /404.html, sitemap.xml, robots.txt, site.webmanifest, favicon.svg, icons/

Además genera derivados de imagen responsive (WebP + JPEG/PNG) en images/_opt/
e imágenes Open Graph 1200×630 en images/_opt/og/.

Ejecutar: python3 build_site.py
"""
import datetime as _dt
import hashlib
import json
import os
import re
import unicodedata

from PIL import Image, ImageDraw, ImageFile, ImageOps

ImageFile.LOAD_TRUNCATED_IMAGES = True

DOMAIN = "https://zeekrlife.com.py"
SITE_NAME = "ZEEKR Paraguay"
GA_ID = "G-E6H9ZC5CG3"
WA_NUMBER = "595971370006"
TODAY = _dt.date.today().isoformat()

PHONES = [
    ("Ventas", "0971 370 006", "+595971370006"),
    ("Ventas", "0976 979 155", "+595976979155"),
    ("Ventas", "0976 203 280", "+595976203280"),
    ("Postventa", "0974 772 247", "+595974772247"),
]

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

PAGES = []  # (url_path, lastmod) para el sitemap


# ----------------------------------------------------------------- utilidades
def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower())
    return s.strip("-")


def file_hash(path):
    with open(path, "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()[:8]


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(iso):
    d = _dt.date.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


# ------------------------------------------------------------ imágenes (opt)
OPT_DIR = "images/_opt"
_size_cache = {}
GENERATED = set()  # derivados producidos en esta corrida (para purgar huérfanos)


def img_size(path):
    if path not in _size_cache:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            _size_cache[path] = im.size
    return _size_cache[path]


def _derivative(src, width, fmt, alpha):
    """Genera (si hace falta) el derivado y devuelve (url, w, h)."""
    rel = os.path.splitext(src)[0]
    rel = rel[len("images/"):] if rel.startswith("images/") else rel
    ext = {"webp": "webp", "jpeg": "jpg", "png": "png"}[fmt]
    out = f"{OPT_DIR}/{rel}-{width}.{ext}"
    ow, oh = img_size(src)
    width = min(width, ow)
    height = round(oh * width / ow)
    GENERATED.add(out)
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGBA" if alpha else "RGB")
            if im.width != width:
                im = im.resize((width, height), Image.LANCZOS)
            if fmt == "webp":
                im.save(out, "WEBP", quality=82, method=6)
            elif fmt == "png":
                im.save(out, "PNG", optimize=True)
            else:
                im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return "/" + out, width, height


def picture(src, alt, widths, sizes="100vw", cls="", img_cls="", loading="lazy",
            fetchpriority=None, mobile=None, mobile_widths=(480, 780), decoding="async",
            alpha=False, attrs=""):
    """<picture> responsive con WebP + fallback, width/height explícitos."""
    ow, oh = img_size(src)
    widths = sorted({min(w, ow) for w in widths})
    fmt_fb = "png" if alpha else "jpeg"
    web = [_derivative(src, w, "webp", alpha) for w in widths]
    srcset_w = ", ".join(f"{u} {w}w" for u, w, h in web)
    # fallback (navegadores sin WebP, <1 %): un solo JPEG/PNG en el tamaño intermedio
    fb_src = _derivative(src, widths[len(widths) // 2], fmt_fb, alpha)
    sources = ""
    if mobile:
        mw, mh = img_size(mobile)
        mws = sorted({min(w, mw) for w in mobile_widths})
        mweb = [_derivative(mobile, w, "webp", alpha) for w in mws]
        sources += f'<source media="(max-width:767px)" type="image/webp" srcset="{", ".join(f"{u} {w}w" for u, w, h in mweb)}" sizes="100vw">'
    sources += f'<source type="image/webp" srcset="{srcset_w}" sizes="{sizes}">'
    fp = f' fetchpriority="{fetchpriority}"' if fetchpriority else ""
    ic = f' class="{img_cls}"' if img_cls else ""
    pc = f' class="{cls}"' if cls else ""
    return (f'<picture{pc}>{sources}<img{ic} src="{fb_src[0]}" '
            f'width="{fb_src[1]}" height="{fb_src[2]}" alt="{esc(alt)}" loading="{loading}" decoding="{decoding}"{fp}{attrs}></picture>')


def og_image(src, name, pos=(0.5, 0.5)):
    """Recorte 1200×630 para Open Graph."""
    out = f"{OPT_DIR}/og/{name}.jpg"
    GENERATED.add(out)
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im = ImageOps.fit(im, (1200, 630), Image.LANCZOS, centering=pos)
            im.save(out, "JPEG", quality=84, optimize=True, progressive=True)
    return "/" + out


# ---------------------------------------------------------------- iconografía
LOGO_PATH = ("M25.6667 25.6667H18.6667V17.0226L11.6667 10.027V2.33114H25.6667V25.6667Z"
             "M2.33333 25.6667V2.33114H9.33334V10.9994L16.3333 17.995V25.6776L2.33333 25.6667Z"
             "M28 0H0V28H28V0Z")
LOGO_SVG = ('<svg class="logo" width="28" height="28" viewBox="0 0 28 28" fill="currentColor" '
            f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false"><path d="{LOGO_PATH}"/></svg>')

WORDMARK_SVG = ('<svg class="wordmark" width="114" height="14" viewBox="0 0 114 14" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">'
                '<path d="M16.7588 0.048261L5.77493 11.633H16.1841V14H0V13.9583L10.9838 2.37355H0.60937V0H16.7588V0.048261Z"/>'
                '<path d="M85.439 13.9912L75.2879 6.76747V13.9912H72.4688V0H75.2879V6.72798L85.1528 0H89.5073L79.6012 6.6863L89.8521 13.9912H85.439Z"/>'
                '<path d="M114.003 13.9912L106.313 8.76371H107.738C110.442 8.76371 112.823 7.19962 112.823 4.52554V4.34127C112.823 1.62551 110.423 0 107.636 0H96.3594V13.9912H99.1785V6.6863L109.805 13.9912H114.003ZM99.1959 2.36478H107.697C108.753 2.36478 109.731 2.80351 110.015 3.66123C110.07 4.25002 110.07 4.84274 110.015 5.43152C109.731 6.19273 108.753 6.66437 107.697 6.66437H99.1959V2.36478Z"/>'
                '<path d="M39.7392 11.5014V13.9912H25.3594V0H39.7392V2.48982H28.1048V5.49295H39.1277V7.98276H28.1048V11.4926L39.7392 11.5014Z"/>'
                '<path d="M63.2917 11.5014V13.9912H48.9141V0H63.2917V2.48982H51.6573V5.49295H62.6802V7.98276H51.6573V11.4926L63.2917 11.5014Z"/>'
                '</svg>')

ICON_ARROW = '<svg class="ico" viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M4 10h11M10.5 5.5 15 10l-4.5 4.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_WA = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.9 9.9 0 0 0 4.74 1.21c5.46 0 9.91-4.45 9.91-9.91S17.5 2 12.04 2m0 18.15c-1.48 0-2.93-.4-4.2-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.24-8.24s8.24 3.7 8.24 8.24-3.7 8.24-8.23 8.24m4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.12-.17.25-.64.81-.78.97-.14.17-.29.19-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.02-.38.11-.51.11-.11.25-.29.37-.43s.17-.25.25-.41c.08-.17.04-.31-.02-.43s-.56-1.34-.76-1.84c-.2-.48-.41-.42-.56-.43h-.48c-.17 0-.43.06-.66.31-.22.25-.86.85-.86 2.07s.89 2.4 1.01 2.56c.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.14-1.18s-.22-.16-.47-.28"/></svg>'
ICON_PHONE = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>'
ICON_PLAY = '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M6 4.5v11l9-5.5z" fill="currentColor"/></svg>'
ICON_PAUSE = '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M6 4.5h3v11H6zm5 0h3v11h-3z" fill="currentColor"/></svg>'
ICON_CHEV_L = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m14.5 6-6 6 6 6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_CHEV_R = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m9.5 6 6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_DOWNLOAD = '<svg class="ico" viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M10 3v9m0 0 3.5-3.5M10 12 6.5 8.5M4 15.5h12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def _logo_polys(scale, off):
    """Polígonos del isotipo (cuadro con dos recortes)."""
    def pts(seq):
        return [(off + x * scale, off + y * scale) for x, y in seq]
    right = pts([(25.6667, 25.6667), (18.6667, 25.6667), (18.6667, 17.0226), (11.6667, 10.027), (11.6667, 2.33114), (25.6667, 2.33114)])
    left = pts([(2.33333, 25.6667), (2.33333, 2.33114), (9.33334, 2.33114), (9.33334, 10.9994), (16.3333, 17.995), (16.3333, 25.6776)])
    return right, left


def render_logo_png(size, fg, bg, pad_ratio=0.22):
    ss = 4  # supersampling
    S = size * ss
    im = Image.new("RGBA", (S, S), bg)
    d = ImageDraw.Draw(im)
    pad = S * pad_ratio
    scale = (S - 2 * pad) / 28
    d.rectangle([pad, pad, S - pad, S - pad], fill=fg)
    for poly in _logo_polys(scale, pad):
        d.polygon(poly, fill=bg)
    return im.resize((size, size), Image.LANCZOS)


def build_icons():
    os.makedirs("icons", exist_ok=True)
    black = (10, 10, 10, 255)
    white = (255, 255, 255, 255)
    clear = (0, 0, 0, 0)
    # Favicon: isotipo negro sobre transparente (como la marca)
    render_logo_png(180, black, white).convert("RGB").save("icons/apple-touch-icon.png", optimize=True)
    render_logo_png(192, black, white).convert("RGB").save("icons/icon-192.png", optimize=True)
    render_logo_png(512, black, white).convert("RGB").save("icons/icon-512.png", optimize=True)
    render_logo_png(512, black, white, pad_ratio=0.3).convert("RGB").save("icons/icon-512-maskable.png", optimize=True)
    fav32 = render_logo_png(32, black, clear, pad_ratio=0.03)
    fav32.save("icons/favicon-32.png", optimize=True)
    fav32.save("favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    open("favicon.svg", "w").write(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 28 28">'
        f'<path fill="#0A0A0A" d="{LOGO_PATH}"/></svg>\n')
    manifest = {
        "name": "ZEEKR Paraguay", "short_name": "ZEEKR PY", "start_url": "/", "display": "browser",
        "background_color": "#FFFFFF", "theme_color": "#0A0A0A", "lang": "es-PY",
        "icons": [
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/icons/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    json.dump(manifest, open("site.webmanifest", "w"), ensure_ascii=False, indent=1)
    if os.path.exists("favicon.png"):
        os.remove("favicon.png")
    print("OK icons")


# ------------------------------------------------------------------ contenido
MODELS = {
    "7x": {
        "slug": "zeekr-7x", "name": "ZEEKR 7X", "short": "7X",
        "eyebrow": "SUV eléctrico de próxima generación",
        "tagline": "El SUV de próxima generación",
        "claim": "Diseñado para que disfrutes cada viaje, construido para llegar más lejos.",
        "hero_desktop": "images/hero/7x-desktop.jpg", "hero_mobile": "images/hero/7x-mobile.jpg", "hero_pos": "60% 50%",
        "card": "images/zeekr7x/seguridad-banner.jpg", "card_pos": "50% 38%", "card_pos_m": "50% 28%",
        "stats": [("800 V", "Sistema de alto voltaje"), ("3,8 s", "0–100 km/h"), ("543 km", "Autonomía WLTP")],
        "pdf": "images/zeekr7x/ficha-tecnica-zeekr-7x.pdf",
        "meta_title": "ZEEKR 7X | SUV eléctrico premium 800 V — ZEEKR Paraguay",
        "meta_desc": "ZEEKR 7X en Paraguay: SUV eléctrico de próxima generación con sistema de 800 V, cabina Snapdragon 8295, 0–100 km/h en 3,8 s y hasta 543 km de autonomía WLTP. Versiones, dimensiones y garantía.",
        "schema_desc": "SUV eléctrico premium de próxima generación. Sistema de alto voltaje de 800 V, 0–100 km/h en 3,8 s (Performance), hasta 543 km de autonomía WLTP y batería de hasta 100 kWh.",
        "faq": [
            ("¿Qué autonomía tiene el ZEEKR 7X?", "Hasta 480 km (WLTP) en la versión Smart con batería de 75 kWh y hasta 543 km (WLTP) en la versión Performance con batería de 100 kWh. La autonomía real varía según clima, camino, carga y estilo de manejo."),
            ("¿Qué garantía tiene el ZEEKR 7X en Paraguay?", "5 años o 100.000 km para el vehículo y 8 años o 160.000 km para la batería, lo que ocurra primero."),
            ("¿Qué versiones del ZEEKR 7X hay disponibles?", "Smart (421 HP, 0–100 km/h en 6,0 s, 480 km WLTP) y Performance (646 HP, 0–100 km/h en 3,8 s, 543 km WLTP)."),
            ("¿Cómo agendo un test drive del ZEEKR 7X?", "Escribinos por WhatsApp al 0971 370 006 o completá el formulario de contacto del sitio: un asesor te responde en el día."),
        ],
    },
    "x": {
        "slug": "zeekr-x", "name": "ZEEKR X", "short": "X",
        "eyebrow": "SUV urbano premium",
        "tagline": "El SUV urbano premium",
        "claim": "Audaz, inteligente y elegante.",
        "hero_desktop": "images/hero/x-desktop.jpg", "hero_mobile": "images/hero/x-mobile.jpg", "hero_pos": "50% 50%",
        "card": "images/modelos/x.jpg", "card_pos": "50% 50%", "card_pos_m": "42% 50%",
        "stats": [("440 km", "Autonomía WLTP"), ("3,8 s", "0–100 km/h (AWD)"), ("428 HP", "Potencia máxima")],
        "pdf": "images/zeekrx/ficha-tecnica-zeekr-x.pdf",
        "meta_title": "ZEEKR X | SUV eléctrico urbano premium — ZEEKR Paraguay",
        "meta_desc": "ZEEKR X en Paraguay: SUV eléctrico urbano premium con hasta 440 km de autonomía WLTP, 0–100 km/h en 3,8 s (AWD), techo panorámico doble y control XTCS. Conocé sus versiones y agendá tu test drive.",
        "schema_desc": "SUV compacto eléctrico premium. Hasta 440 km de autonomía WLTP (RWD), 0–100 km/h en 3,8 s (AWD) y batería de 69 kWh.",
        "faq": [
            ("¿Qué autonomía tiene el ZEEKR X?", "Hasta 440 km (WLTP) en la versión Premium RWD y hasta 420 km (WLTP) en la versión Flagship AWD, con batería de 69 kWh."),
            ("¿Cuánto acelera el ZEEKR X?", "La versión Flagship AWD de 428 HP acelera de 0 a 100 km/h en 3,8 s; la Premium RWD de 268 HP lo hace en 5,6 s."),
            ("¿Qué asistencias a la conducción tiene?", "ZEEKR AD con 5 cámaras HD, 5 radares milimétricos y 12 sensores ultrasónicos, con más de 10 funciones como crucero adaptativo y asistente de estacionamiento."),
        ],
    },
    "001": {
        "slug": "zeekr-001", "name": "ZEEKR 001", "short": "001",
        "eyebrow": "Crossover eléctrico de lujo",
        "tagline": "El crossover de lujo",
        "claim": "Impresionante, potente, refinado.",
        "hero_desktop": "images/hero/001-desktop.jpg", "hero_mobile": "images/hero/001-mobile.jpg", "hero_pos": "50% 50%",
        "card": "images/modelos/001.jpg", "card_pos": "55% 50%", "card_pos_m": "40% 50%",
        "stats": [("620 km", "Autonomía WLTP"), ("3,8 s", "0–100 km/h (AWD)"), ("536 HP", "Potencia máxima")],
        "pdf": "images/zeekr001/ficha-tecnica-zeekr-001.pdf",
        "meta_title": "ZEEKR 001 | Crossover eléctrico de lujo — ZEEKR Paraguay",
        "meta_desc": "ZEEKR 001 en Paraguay: crossover eléctrico premium con hasta 620 km de autonomía WLTP, 0–100 km/h en 3,8 s (AWD) y batería de 100 kWh. Ficha técnica, versiones y test drive.",
        "schema_desc": "Deportivo familiar eléctrico premium. Hasta 620 km de autonomía WLTP, aceleración 0–100 km/h en 3,8 s (AWD) y batería de 100 kWh.",
        "faq": [
            ("¿Qué autonomía tiene el ZEEKR 001?", "Hasta 620 km (WLTP) en la versión Sport RWD y hasta 580 km (WLTP) en la Flagship AWD, con batería de 100 kWh."),
            ("¿Cuánto tarda en cargar el ZEEKR 001?", "Del 10 % al 80 % en menos de 30 minutos con carga rápida DC de 200 kW."),
            ("¿Qué diferencia a la versión Flagship?", "Doble motor AWD de 536 HP, 0–100 km/h en 3,8 s, suspensión neumática activa, rines de 22″ y asientos con ventilación y masaje."),
        ],
    },
}
MODEL_ORDER = ["7x", "x", "001"]


def model_url(key):
    return f"/modelos/{MODELS[key]['slug']}/"


NEWS = [
    {
        "slug": "lanzamiento-zeekr-7x-alma",
        "date": "2026-07-28",
        "kicker": "Evento · Asunción",
        "title": "ZEEKR 7X: así fue su lanzamiento en Paraguay",
        "lead": "Santa Rosa Paraguay presentó oficialmente el ZEEKR 7X en una noche exclusiva en Alma, Asunción, con invitados, prensa y el nuevo SUV eléctrico de próxima generación como protagonista.",
        "place": "Alma, Asunción",
        "quote": ("Paraguay tiene un enorme potencial; su dinamismo económico lo convierte en un escenario ideal para adoptar nuevas tecnologías en movilidad.", "Manuel Antelo", "Grupo Antelo"),
        "img": "images/noticias/alma-2026/01-zeekr-7x-alma.jpg",
        "body": [
            "La velada reunió a clientes, aliados y medios de comunicación en un espacio pensado para vivir la marca de cerca: diseño escandinavo, tecnología de vanguardia y la experiencia ZEEKR en primera persona.",
            "El ZEEKR 7X se develó ante los invitados con una presentación de sus dos versiones —Smart y Performance— y de sus tecnologías clave: sistema de alto voltaje de 800 V, cabina con procesador Qualcomm Snapdragon 8295, pantalla central Mini-LED de 16″ y una autonomía de hasta 543 km (WLTP).",
            "Los asistentes recorrieron el interior del vehículo, conocieron sus materiales y descubrieron un espacio interior de categoría superior, mientras la música en vivo acompañó la noche.",
            "El ZEEKR 7X ya se puede conocer en Paraguay. Agendá tu prueba de manejo y descubrí por qué es el SUV eléctrico de próxima generación.",
        ],
        "gallery": [
            ("images/noticias/alma-2026/02-presentacion-7x.jpg", "Presentación del ZEEKR 7X ante los invitados en Alma"),
            ("images/noticias/alma-2026/03-zeekr-7x-frente.jpg", "Frente del ZEEKR 7X durante el lanzamiento"),
            ("images/noticias/alma-2026/04-zeekr-7x-trasera.jpg", "Detalle trasero del ZEEKR 7X con la pantalla de presentación"),
            ("images/noticias/alma-2026/05-interior-volante.jpg", "Interior del ZEEKR 7X: volante y luz ambiental"),
            ("images/noticias/alma-2026/06-tunel-de-luz.jpg", "Túnel de luz de acceso al evento"),
            ("images/noticias/alma-2026/07-marco-zeekr.jpg", "Marco luminoso con el isotipo ZEEKR"),
            ("images/noticias/alma-2026/08-musica-en-vivo.jpg", "Música en vivo durante el lanzamiento"),
            ("images/noticias/alma-2026/09-presentacion.jpg", "Presentación de la marca ZEEKR en Paraguay"),
        ],
        "cta_model": "7x",
    },
    {
        "slug": "lanzamiento-zeekr-7x-ciudad-del-este",
        "draft": True,  # ← quitar cuando estén fotos en images/noticias/cde-2026/ y fecha confirmada
        "date": "2026-09-01",
        "kicker": "Evento · Ciudad del Este",
        "title": "El ZEEKR 7X llegó a Ciudad del Este",
        "lead": "Santa Rosa Paraguay presentó el ZEEKR 7X en Ciudad del Este: una noche con invitados, prensa y el SUV eléctrico de próxima generación develado en vivo.",
        "place": "Ciudad del Este",
        "place_locality": "Ciudad del Este",
        "quote": ("El futuro no se parece a nada de lo que conocés.", None, "Pantalla del lanzamiento"),
        "quote_pos": 0,
        "img": "images/noticias/cde-2026/01-portada.jpg",
        "body": [
            "Con esa frase en pantalla y el vehículo aún cubierto, arrancó la presentación del ZEEKR 7X ante los invitados del Este del país. Agustín Varela, Director País, presentó la marca y el modelo antes del develado.",
            "El ZEEKR 7X se mostró en sus dos versiones —Smart y Performance— con sus tecnologías clave: sistema de alto voltaje de 800 V, cabina con procesador Qualcomm Snapdragon 8295, pantalla central Mini-LED de 16″ y hasta 543 km de autonomía (WLTP).",
            "Los asistentes recorrieron el interior, probaron la cabina digital y se fotografiaron en el photo wall ZEEKR 7X. Ciudad del Este suma así su primera experiencia ZEEKR en vivo.",
            "El ZEEKR 7X ya se puede conocer en Paraguay. Agendá tu prueba de manejo y descubrí por qué es el SUV eléctrico de próxima generación.",
        ],
        "gallery": [],
        "cta_model": "7x",
    },
    {"date": "2025-01-08", "title": "ZEEKR en CES 2025: tecnología líder en la industria, estrategia de co-creación y una solución energética global", "img": "images/noticias/ces-2025.png", "kicker": "ZEEKR Global"},
    {"date": "2025-01-06", "title": "ZEEKR amplía su asociación con Qualcomm para ofrecer una experiencia de entretenimiento inmersiva en los vehículos del futuro", "img": "images/noticias/asociacion-qualcomm.png", "kicker": "ZEEKR Global"},
    {"date": "2024-12-13", "title": "ZEEKR 001: luces inteligentes para iluminar tu camino", "img": "images/noticias/luces-inteligentes.png", "kicker": "Tecnología"},
    {"date": "2024-12-06", "title": "ZEEKR: la revolución eléctrica que nace desde el punto cero", "img": "images/noticias/revolucion-electrica.png", "kicker": "Marca"},
    {"date": "2024-11-14", "title": "¿AWD o RWD? Descubrí las diferencias de tracción en los modelos ZEEKR", "img": "images/noticias/diferencias-traccion.png", "kicker": "Tecnología"},
    {"date": "2024-10-25", "title": "Sumergite en la experiencia de audio premium de ZEEKR", "img": "images/noticias/audio-premium.png", "kicker": "Tecnología"},
    {"date": "2024-08-23", "title": "¿Por qué el ZEEKR X es el SUV eléctrico que define una nueva era de movilidad?", "img": "images/noticias/suvelectrico.png", "kicker": "ZEEKR X"},
    {"date": "2024-05-10", "title": "Un hito en el viaje global de ZEEKR: la compañía completa su oferta pública inicial en la Bolsa de Nueva York", "img": "images/noticias/noticia1.jpg", "kicker": "ZEEKR Global"},
    {"date": "2024-04-09", "title": "ZEEKR M-Vision, un concepto completamente reimaginado para el futuro de la movilidad", "img": "images/noticias/noticia2.png", "kicker": "Concepto"},
]
NEWS = [n for n in NEWS if not n.get("draft")]  # borradores (sin fotos/fecha confirmadas) no se publican
NEWS.sort(key=lambda n: n["date"], reverse=True)


def news_url(n):
    return f"/noticias/{n['slug']}/" if n.get("body") else None


HOME_FAQ = [
    ("¿Qué modelos ZEEKR están disponibles en Paraguay?", "ZEEKR 001 (crossover eléctrico de lujo), ZEEKR X (SUV urbano premium) y ZEEKR 7X (SUV de próxima generación). Podés conocer cada modelo en detalle y agendar una prueba de manejo."),
    ("¿Qué autonomía tienen los vehículos ZEEKR?", "Hasta 620 km WLTP en el ZEEKR 001 (RWD), hasta 440 km en el ZEEKR X (RWD) y hasta 543 km en el ZEEKR 7X (Performance). La autonomía real varía según clima, camino, carga y estilo de manejo."),
    ("¿Cuánto tarda en cargar un ZEEKR?", "El ZEEKR 001 pasa del 10 % al 80 % en menos de 30 minutos con carga rápida DC de 200 kW, y el ZEEKR 7X incorpora un sistema de alto voltaje de 800 V para carga ultrarrápida."),
    ("¿Qué garantía tiene el ZEEKR 7X?", "5 años o 100.000 km para el vehículo y 8 años o 160.000 km para la batería, lo que ocurra primero."),
    ("¿Cómo agendo una prueba de manejo?", "Escribinos por WhatsApp al 0971 370 006 o completá el formulario de contacto: un asesor te responde en el día."),
]


# ------------------------------------------------------------------ partials
def btn(label, href=None, kind="cream", extra="", icon=None, attrs=""):
    inner = f"<span>{label}</span>" + (icon or "")
    cls = f"btn btn-{kind}{(' ' + extra) if extra else ''}"
    if href:
        return f'<a class="{cls}" href="{href}"{attrs}>{inner}</a>'
    return f'<button class="{cls}" type="button"{attrs}>{inner}</button>'


def header(active=""):
    def cls(a):
        return "menu-link is-active" if a == active else "menu-link"
    gates = "\n".join(
        f'''        <a class="gate-card" href="{model_url(k)}">
          {picture(f"images/menu/zeekr_{k}.png", MODELS[k]["name"], (300, 600), sizes="260px", alpha=True)}
          <span class="gate-name">{MODELS[k]["name"]}</span>
          <span class="gate-sub">{MODELS[k]["eyebrow"]}</span>
        </a>''' for k in ["001", "x", "7x"])
    return f'''
<a class="skip-link" href="#main">Saltar al contenido</a>
<header class="site-header" id="siteHeader">
  <div class="header-inner">
    <div class="header-left">
      <a class="header-logo" href="/" aria-label="ZEEKR Paraguay — Inicio">{LOGO_SVG}</a>
      <nav class="header-menus" aria-label="Principal">
        <button class="menu-link models-trigger {cls('modelos')}" type="button" aria-expanded="false" aria-controls="modelsPanel" data-toggle-models>Modelos</button>
        <a class="{cls('nosotros')}" href="/nosotros/">Nosotros</a>
        <a class="{cls('noticias')}" href="/noticias/">Noticias</a>
      </nav>
    </div>
    <a class="header-wordmark" href="/" aria-label="ZEEKR Paraguay — Inicio">{WORDMARK_SVG}</a>
    <div class="header-right">
      <button class="menu-link" type="button" data-open-contact data-intent="contacto">Contáctanos</button>
      <a class="header-wa" href="https://wa.me/{WA_NUMBER}" target="_blank" rel="noopener" aria-label="WhatsApp ZEEKR Paraguay">{ICON_WA}</a>
      <button class="burger" type="button" aria-label="Abrir menú" aria-expanded="false" aria-controls="mobileMenu" data-open-menu><span></span><span></span></button>
    </div>
  </div>
  <div class="models-panel" id="modelsPanel" hidden>
    <div class="models-panel-inner">
      <div class="models-panel-head">
        <p class="models-heading">Modelos</p>
        <a class="text-link" href="/modelos/">Ver todos los modelos {ICON_ARROW}</a>
      </div>
{gates}
    </div>
  </div>
  <div class="mobile-menu" id="mobileMenu" hidden>
    <div class="mobile-menu-head">
      <a href="/" aria-label="ZEEKR Paraguay — Inicio">{LOGO_SVG}</a>
      <button class="mm-close" type="button" aria-label="Cerrar menú" data-close-menu><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg></button>
    </div>
    <nav aria-label="Menú móvil">
      <p class="mm-eyebrow">Modelos</p>
      <a data-close-menu href="{model_url('7x')}">ZEEKR 7X</a>
      <a data-close-menu href="{model_url('x')}">ZEEKR X</a>
      <a data-close-menu href="{model_url('001')}">ZEEKR 001</a>
      <p class="mm-eyebrow">Marca</p>
      <a data-close-menu href="/noticias/">Noticias</a>
      <a data-close-menu href="/nosotros/">Nosotros</a>
    </nav>
    <div class="mm-actions">
      {btn("Agendá tu prueba de manejo", kind="accent", attrs=' data-open-contact data-intent="test-drive"')}
      {btn("Contáctanos", kind="outline", attrs=' data-open-contact data-intent="contacto"')}
    </div>
  </div>
</header>
<div class="nav-shade" data-close-models hidden></div>
<div class="cookie-banner" id="cookieBanner" hidden role="dialog" aria-label="Consentimiento de cookies">
  <div class="cookie-inner">
    <p class="cookie-text">Cuando visitás nuestro sitio web (“Plataformas ZEEKR”), utilizamos cookies y otras tecnologías de seguimiento similares para mejorar la funcionalidad de las Plataformas ZEEKR, el rendimiento, medir el tráfico del sitio web, analizar el comportamiento del usuario y ajustar nuestro contenido y servicios. Si hacés clic en “Aceptar todo” nos autorizás a procesar tus datos personales para tales fines. Si hacés clic en “Rechazar todo” solo utilizaremos cookies y tecnologías estrictamente necesarias para la funcionalidad de la Plataforma ZEEKR. Para más información o para consentir cookies específicas, hacé clic en “Configuración de cookies”.</p>
    <div class="cookie-actions">
      <button class="btn btn-outline-dark" type="button" data-cookie-settings aria-expanded="false" aria-controls="cookieSettings">Configuración de cookies</button>
      <button class="btn btn-dark" type="button" data-cookie-reject>Rechazar todo</button>
      <button class="btn btn-dark" type="button" data-cookie-accept>Aceptar todo</button>
    </div>
    <div class="cookie-settings" id="cookieSettings" hidden>
      <label class="check"><input type="checkbox" checked disabled><span>Necesarias (siempre activas)</span></label>
      <label class="check"><input type="checkbox" id="ckAnalytics" checked><span>Analíticas y rendimiento (Google Analytics)</span></label>
      <button class="btn btn-dark" type="button" data-cookie-save>Guardar preferencias</button>
    </div>
  </div>
</div>'''


def footer():
    phones = "".join(f'<li><a href="tel:{tel}"><span class="ph-kind">{kind}</span> {num}</a></li>' for kind, num, tel in PHONES)
    return f'''
<footer class="site-footer">
  <div class="footer-grid">
    <div class="footer-brand">
      <a class="footer-logo" href="/" aria-label="ZEEKR Paraguay — Inicio">{LOGO_SVG}{WORDMARK_SVG}</a>
      <p class="footer-tag">Distribuidor oficial ZEEKR en Paraguay.<br>Santa Rosa Paraguay.</p>
    </div>
    <nav class="footer-col" aria-label="Modelos">
      <p class="footer-title">Modelos</p>
      <ul>
        <li><a href="{model_url('7x')}">ZEEKR 7X</a></li>
        <li><a href="{model_url('x')}">ZEEKR X</a></li>
        <li><a href="{model_url('001')}">ZEEKR 001</a></li>
        <li><a href="/modelos/">Todos los modelos</a></li>
      </ul>
    </nav>
    <nav class="footer-col" aria-label="Compañía">
      <p class="footer-title">Compañía</p>
      <ul>
        <li><a href="/nosotros/">Nosotros</a></li>
        <li><a href="/noticias/">Noticias</a></li>
        <li><button type="button" class="link-btn" data-open-contact data-intent="contacto">Contáctanos</button></li>
        <li><button type="button" class="link-btn" data-open-contact data-intent="test-drive">Prueba de manejo</button></li>
      </ul>
    </nav>
    <div class="footer-col">
      <p class="footer-title">Atención a clientes</p>
      <ul class="footer-phones">{phones}</ul>
    </div>
    <div class="footer-col footer-social">
      <p class="footer-title">Seguinos</p>
      <div class="social-row">
        <a href="https://www.instagram.com/zeekrparaguay/" rel="noopener" target="_blank" aria-label="Instagram de ZEEKR Paraguay">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true" focusable="false"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r="1" fill="currentColor" stroke="none"/></svg>
        </a>
        <a href="https://wa.me/{WA_NUMBER}" rel="noopener" target="_blank" aria-label="WhatsApp de ZEEKR Paraguay">{ICON_WA}</a>
        <a href="https://www.linkedin.com/company/zeekr" rel="noopener" target="_blank" aria-label="LinkedIn de ZEEKR">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true" focusable="false"><path d="M4.98 3.5A2.49 2.49 0 1 1 5 8.48a2.49 2.49 0 0 1-.02-4.98ZM3 9.75h4v11H3v-11Zm6.5 0h3.83v1.5h.05c.53-1 1.84-2.06 3.79-2.06 4.05 0 4.8 2.67 4.8 6.14v5.42h-4v-4.8c0-1.15-.02-2.63-1.6-2.63-1.6 0-1.85 1.25-1.85 2.55v4.88h-4v-11Z"/></svg>
        </a>
      </div>
    </div>
  </div>
  <div class="footer-bottom">
    <p class="footer-copy">© 2026 ZEEKR y todos sus afiliados. Todos los derechos reservados · <span translate="no">ZEEKR Paraguay</span></p>
    <p class="footer-disclaimer">Toda la información contenida en este material está basada en datos disponibles al momento de su publicación. Las fotos y pantallas son de carácter ilustrativo y de referencia. Los datos de autonomía y prestaciones se basan en ciclos de prueba (WLTP / pruebas de ingeniería) y pueden variar según clima, camino, carga, batería y configuración del vehículo.</p>
  </div>
</footer>
{contact_modal()}'''


def contact_modal():
    cards = "".join(f'<a class="contact-card" href="tel:{tel}"><span>{kind}</span><strong>{num}</strong></a>' for kind, num, tel in PHONES)
    options = "".join(f'<option value="{MODELS[k]["name"]}">{MODELS[k]["name"]}</option>' for k in MODEL_ORDER)
    return f'''
<div class="modal-contact" id="contactModal" hidden role="dialog" aria-modal="true" aria-labelledby="cmTitle">
  <div class="modal-mask" data-close-contact></div>
  <div class="modal-panel" tabindex="-1" data-mode="test-drive">
    <button class="modal-close" type="button" aria-label="Cerrar" data-close-contact><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg></button>
    <p class="eyebrow eyebrow-dark" data-m="eyebrow">Prueba de manejo</p>
    <h2 id="cmTitle" data-m="title">Agendá tu prueba de manejo</h2>
    <p class="modal-sub" data-m="sub">Elegí el modelo y un asesor coordina con vos día, hora y lugar.</p>
    <div class="modal-channels">
      <p class="modal-or" data-m="channels">¿Preferís hablar ahora?</p>
      <div class="contact-cards">{cards}</div>
      <a class="btn btn-outline-dark btn-block" href="https://wa.me/{WA_NUMBER}" target="_blank" rel="noopener" data-m-wa><span>Escribinos por WhatsApp</span>{ICON_WA}</a>
    </div>
    <p class="modal-or modal-or-form" data-m="form" hidden>O dejanos tu consulta y te llamamos</p>
    <form id="waForm" class="contact-form" data-wa="{WA_NUMBER}" novalidate>
      <input type="hidden" name="tipo" value="Prueba de manejo">
      <div class="field">
        <label for="cf-nombre">Nombre y apellido</label>
        <input id="cf-nombre" type="text" name="nombre" required autocomplete="name" placeholder="Ej.: Ana Martínez">
        <p class="field-error" id="cf-nombre-error" hidden>Ingresá tu nombre para que podamos contactarte.</p>
      </div>
      <div class="field">
        <label for="cf-tel">Teléfono</label>
        <input id="cf-tel" type="tel" name="telefono" required autocomplete="tel" inputmode="tel" placeholder="Ej.: 0981 123 456">
        <p class="field-error" id="cf-tel-error" hidden>Ingresá un teléfono válido (ej.: 0981 123 456).</p>
      </div>
      <div class="field">
        <label for="cf-modelo">Modelo de interés</label>
        <select id="cf-modelo" name="modelo" autocomplete="off">{options}<option value="Aún no lo sé">Aún no lo sé</option></select>
      </div>
      <div class="field">
        <label for="cf-msg">Mensaje <span class="opt">(opcional)</span></label>
        <textarea id="cf-msg" name="mensaje" rows="2" autocomplete="off" placeholder="Contanos qué te interesa…"></textarea>
      </div>
      <div class="hp" aria-hidden="true"><label for="cf-web">Sitio web</label><input id="cf-web" type="text" name="website" tabindex="-1" autocomplete="off"></div>
      <button class="btn btn-accent btn-block" type="submit" data-label="Agendar prueba de manejo"><span>Agendar prueba de manejo</span>{ICON_ARROW}</button>
      <p class="form-status" role="status" aria-live="polite"></p>
      <p class="form-note">Un asesor ZEEKR te contacta en el día. Al enviar aceptás que ZEEKR Paraguay procese tus datos para gestionar tu consulta.</p>
    </form>
    <div class="form-success" hidden>
      <div class="success-icon" aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false"><path d="m5 12.5 4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
      <h3>¡Listo, <span data-success-name></span>!</h3>
      <p><span data-success-what>Registramos tu solicitud.</span> <span data-success-advisor></span></p>
      <div class="success-actions">
        <a class="btn btn-accent" href="#" target="_blank" rel="noopener" data-success-wa><span>Continuar por WhatsApp</span>{ICON_WA}</a>
        <button class="btn btn-outline-dark" type="button" data-close-contact>Cerrar</button>
      </div>
    </div>
  </div>
</div>'''


def head_block(title, desc, path, jsonld, og_img, preload="", preload_mobile=None):
    url = DOMAIN + path
    css_v = file_hash("css/zeekr-site.css")
    ld = json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/")
    pre = f'\n  <link rel="preload" as="image" href="{preload}" media="(min-width:768px)">' if preload else ""
    if preload_mobile:
        srcset = ", ".join(f"{u} {w}w" for u, w, h in preload_mobile)
        pre += f'\n  <link rel="preload" as="image" imagesrcset="{srcset}" imagesizes="100vw" media="(max-width:767px)">'
    return f'''  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="canonical" href="{url}">
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
  <meta name="theme-color" content="#0A0A0A">
  <meta name="color-scheme" content="dark">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="es_PY">
  <meta property="og:url" content="{url}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:image" content="{DOMAIN}{og_img}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{esc(title)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(desc)}">
  <meta name="twitter:image" content="{DOMAIN}{og_img}">
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">
  <link rel="preload" href="/fonts/ZeekrHeadline-Regular.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/fonts/ZeekrText-Regular.woff2" as="font" type="font/woff2" crossorigin>{pre}
  <link rel="stylesheet" href="/css/zeekr-site.css?v={css_v}">
  <script>document.documentElement.classList.add('js');window.__zkGA=function(){{if(window.__zkGAOn)return;window.__zkGAOn=1;window.dataLayer=window.dataLayer||[];window.gtag=function(){{dataLayer.push(arguments)}};gtag('js',new Date());gtag('config','{GA_ID}',{{anonymize_ip:true}});var s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id={GA_ID}';document.head.appendChild(s)}};try{{var c=JSON.parse(localStorage.getItem('zeekr-consent')||'null');if(c&&c.analytics)window.__zkGA()}}catch(e){{}}</script>
  <script type="application/ld+json">{ld}</script>'''


def render_page(path, title, desc, content, nav_active, jsonld, og_img, preload="", body_cls="", lastmod=None, preload_mobile=None):
    """path: '/', '/modelos/zeekr-7x/', '/404.html'."""
    if path.endswith("/"):
        out = os.path.join(path.strip("/"), "index.html") if path != "/" else "index.html"
    else:
        out = path.lstrip("/")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    js_v = file_hash("js/main.js")
    html = f'''<!DOCTYPE html>
<html lang="es-PY">
<head>
{head_block(title, desc, path, jsonld, og_img, preload, preload_mobile)}
</head>
<body class="{body_cls}">
{header(nav_active)}
<main id="main" tabindex="-1">
{content}
</main>
{footer()}
<script src="/js/main.js?v={js_v}" defer></script>
</body>
</html>
'''
    with open(out, "w") as fh:
        fh.write(html)
    if not path.endswith("404.html"):
        PAGES.append((path, lastmod or TODAY))
    print("OK", out)


ORG = {
    "@type": ["AutoDealer", "Organization"], "@id": DOMAIN + "/#org",
    "name": SITE_NAME, "alternateName": "Zeekr Paraguay", "url": DOMAIN + "/",
    "logo": {"@type": "ImageObject", "url": DOMAIN + "/icons/icon-512.png", "width": 512, "height": 512},
    "image": DOMAIN + "/images/_opt/og/home.jpg",
    "description": "Distribuidor oficial de ZEEKR en Paraguay: vehículos eléctricos premium ZEEKR 001, ZEEKR X y ZEEKR 7X.",
    "brand": {"@type": "Brand", "name": "ZEEKR"},
    "parentOrganization": {"@type": "Organization", "name": "Santa Rosa Paraguay"},
    "areaServed": {"@type": "Country", "name": "Paraguay"},
    "telephone": "+595971370006",
    "contactPoint": [
        {"@type": "ContactPoint", "telephone": "+595-971-370-006", "contactType": "sales", "areaServed": "PY", "availableLanguage": ["es"]},
        {"@type": "ContactPoint", "telephone": "+595-974-772-247", "contactType": "customer service", "areaServed": "PY", "availableLanguage": ["es"]},
    ],
    "sameAs": ["https://www.instagram.com/zeekrparaguay/", "https://www.zeekrlife.com/"],
}
WEBSITE = {"@type": "WebSite", "@id": DOMAIN + "/#website", "name": SITE_NAME, "url": DOMAIN + "/", "inLanguage": "es-PY", "publisher": {"@id": DOMAIN + "/#org"}}


def breadcrumb(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(items)]}


def faq_schema(qa):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]}


def graph(*items):
    return {"@context": "https://schema.org", "@graph": [WEBSITE, ORG, *items]}


# ------------------------------------------------------------------ bloques
def eyebrow(text, dark=False):
    return f'<p class="eyebrow{" eyebrow-dark" if dark else ""}">{text}</p>'


def stat_items(stats):
    return "".join(f'<div class="ind"><span class="ind-value">{v}</span><span class="ind-label">{l}</span></div>' for v, l in stats)


def faq_block(qa, title="Preguntas frecuentes", kicker="Te ayudamos"):
    items = "".join(
        f'<details class="faq-item"><summary><span>{q}</span><span class="faq-icon" aria-hidden="true"></span></summary><div class="faq-body"><p>{a}</p></div></details>'
        for q, a in qa)
    return f'''
<section class="section faq-section" aria-labelledby="faqTitle">
  <div class="faq-grid">
    <div class="faq-head reveal">{eyebrow(kicker)}<h2 id="faqTitle">{title}</h2></div>
    <div class="faq-list reveal">{items}</div>
  </div>
</section>'''


def contact_strip(model_name=None):
    attr = f' data-model="{model_name}"' if model_name else ""
    return f'''
<section class="contact-strip" id="contacto" aria-labelledby="contactTitle">
  <div class="contact-inner reveal">
    <div class="contact-copy">
      {eyebrow("Estamos para ayudarte")}
      <h2 id="contactTitle">¿Listo para manejar un ZEEKR?</h2>
      <p>Coordiná tu prueba de manejo con un asesor. Ventas: <a href="tel:+595971370006">0971&nbsp;370&nbsp;006</a> · <a href="tel:+595976979155">0976&nbsp;979&nbsp;155</a> · <a href="tel:+595976203280">0976&nbsp;203&nbsp;280</a> · Postventa: <a href="tel:+595974772247">0974&nbsp;772&nbsp;247</a></p>
    </div>
    <div class="contact-actions">
      {btn("Agendá tu prueba de manejo", kind="accent", attrs=' data-open-contact data-intent="test-drive"' + attr)}
      {btn("Escribinos por WhatsApp", href=f"https://wa.me/{WA_NUMBER}", kind="outline", icon=ICON_WA, attrs=' target="_blank" rel="noopener"')}
    </div>
  </div>
</section>'''


def page_intro(kicker, title, lead=None, tag="h1"):
    return f'''
<section class="page-intro">
  <div class="page-intro-inner reveal">
    {eyebrow(kicker)}
    <{tag}>{title}</{tag}>
    {f"<p class='lead'>{lead}</p>" if lead else ""}
  </div>
</section>'''


# ------------------------------------------------------------------ home
def hero_slider():
    slides, dots = [], []
    n = len(MODEL_ORDER)
    for i, key in enumerate(MODEL_ORDER):
        m = MODELS[key]
        first = i == 0
        pic = picture(m["hero_desktop"], f"{m['name']} — {m['claim']}", (1200, 1800, 2400), sizes="100vw",
                      cls="slide-media", img_cls="slide-image", loading="eager" if first else "lazy",
                      fetchpriority="high" if first else None, mobile=m["hero_mobile"],
                      decoding="sync" if first else "async")
        slides.append(f'''
    <div class="slide{' is-active' if first else ''}" role="group" aria-roledescription="diapositiva" aria-label="{i + 1} de {n}" data-slide{'' if first else ' aria-hidden="true"'}>
      {pic}
      <div class="slide-shade" aria-hidden="true"></div>
      <div class="slide-content">
        <p class="eyebrow">{m['eyebrow']}</p>
        <h2 class="slide-title">{m['name']}</h2>
        <p class="slide-claim">{m['claim']}</p>
        <div class="slide-actions">
          {btn(f"Conocé el {m['name']}", href=model_url(key), kind="accent")}
          {btn("Agendá tu prueba de manejo", kind="cream", attrs=f' data-open-contact data-intent="test-drive" data-model="{m["name"]}"')}
        </div>
      </div>
    </div>''')
        dots.append(f'<button class="pager-bar{" is-active" if first else ""}" type="button" data-goto="{i}" aria-label="Ir a la diapositiva {i + 1}: {m["name"]}"{" aria-current=\"true\"" if first else ""}></button>')
    return f'''
<section class="hero" id="hero" aria-roledescription="carrusel" aria-label="Modelos destacados">
  <div class="hero-track" aria-live="off">{''.join(slides)}
  </div>
  <div class="hero-ui">
    <p class="hero-counter" aria-hidden="true"><span data-counter>01</span><span class="hero-counter-sep">/</span>{n:02d}</p>
    <div class="hero-pager" role="group" aria-label="Diapositivas">{''.join(dots)}</div>
    <div class="hero-controls">
      <button class="hero-ctl hero-ctl-a11y" type="button" data-toggle-play aria-label="Pausar reproducción automática" aria-pressed="false"><span class="ico-pause">{ICON_PAUSE}</span><span class="ico-play">{ICON_PLAY}</span></button>
    </div>
  </div>
  <p class="sr-only" role="status" aria-live="polite" data-slide-status></p>
</section>'''


def brand_statement():
    return f'''
<section class="statement" aria-labelledby="stTitle">
  <div class="statement-inner reveal">
    {eyebrow("ZEEKR Paraguay")}
    <h1 id="stTitle">Vehículos eléctricos premium que reimaginan la forma de moverse.</h1>
    <p>Diseño escandinavo, tecnología de vanguardia y el respaldo del Grupo Geely. ZEEKR llega a Paraguay de la mano de Santa Rosa Paraguay, con los modelos 001, X y 7X.</p>
    <a class="text-link" href="/nosotros/">Conocé la marca {ICON_ARROW}</a>
  </div>
</section>'''


def model_card(key, heading="h2"):
    m = MODELS[key]
    pic = picture(m["card"], f"{m['name']}, {m['tagline'].lower()}", (960, 1600, 2200), sizes="100vw",
                  cls="model-media", img_cls="model-image", attrs=f' style="--pos:{m["card_pos"]};--pos-m:{m.get("card_pos_m", m["card_pos"])}"')
    return f'''
<article class="model-card" id="modelo-{m['slug']}">
  {pic}
  <div class="model-shade" aria-hidden="true"></div>
  <div class="model-content">
    <div class="model-head reveal">
      {eyebrow(m['eyebrow'])}
      <{heading} class="model-title"><a href="{model_url(key)}">{m['name']}</a></{heading}>
      <p class="model-claim">{m['claim']}</p>
    </div>
    <div class="model-foot reveal">
      <div class="model-stats">{stat_items(m['stats'])}</div>
      <div class="model-actions">
        {btn(f"Descubrí el {m['name']}", href=model_url(key), kind="cream", icon=ICON_ARROW, extra="btn-arrow")}
        {btn("Agendá tu prueba de manejo", kind="outline", attrs=f' data-open-contact data-intent="test-drive" data-model="{m["name"]}"')}
      </div>
    </div>
  </div>
</article>'''


def tech_strip():
    items = [
        ("Arquitectura SEA", "Plataforma 100 % eléctrica, modular y escalable del Grupo Geely: la base de cada ZEEKR."),
        ("Actualizaciones OTA", "Software que evoluciona con el tiempo: tu ZEEKR incorpora mejoras de forma remota."),
        ("Diseño desde Gotemburgo", "Centro global de diseño en Suecia, dirigido por Stefan Sielaff."),
        ("Seguridad integral", "Estructuras reforzadas y asistencias avanzadas a la conducción en toda la gama."),
    ]
    lis = "".join(f'<li class="tech-item reveal"><h3>{h}</h3><p>{p}</p></li>' for h, p in items)
    return f'''
<section class="section tech" aria-labelledby="techTitle">
  <div class="section-head reveal">{eyebrow("Tecnología")}<h2 id="techTitle">Ingeniería que se siente en cada viaje</h2></div>
  <ul class="tech-grid">{lis}</ul>
</section>'''


def news_card(n, heading="h3"):
    url = news_url(n)
    pic = picture(n["img"], n["title"], (480, 800, 1200), sizes="(min-width:992px) 33vw, (min-width:600px) 50vw, 100vw", cls="news-media")
    date = f'<time class="news-date" datetime="{n["date"]}">{fecha_larga(n["date"])}</time>'
    kicker = f'<span class="news-kicker">{n.get("kicker", "")}</span>' if n.get("kicker") else ""
    title = f'<{heading} class="news-title">{n["title"]}</{heading}>'
    if url:
        return f'<article class="news-item reveal"><a class="news-link" href="{url}">{pic}<div class="news-body"><p class="news-meta">{kicker}{date}</p>{title}<span class="text-link">Leer la nota {ICON_ARROW}</span></div></a></article>'
    return f'<article class="news-item reveal">{pic}<div class="news-body"><p class="news-meta">{kicker}{date}</p>{title}</div></article>'


def build_index():
    news = "".join(news_card(n) for n in NEWS[:3])
    models = "".join(model_card(k) for k in MODEL_ORDER)
    content = hero_slider() + brand_statement() + f'''
<section class="models" aria-label="Modelos ZEEKR">{models}
</section>''' + tech_strip() + f'''
<section class="news" aria-labelledby="newsTitle">
  <div class="section-head reveal">{eyebrow("Novedades", dark=True)}<h2 id="newsTitle">Últimas noticias</h2></div>
  <div class="news-grid">{news}</div>
  <div class="section-more reveal">{btn("Ver todas las noticias", href="/noticias/", kind="outline-dark")}</div>
</section>''' + faq_block(HOME_FAQ) + contact_strip()
    og = og_image(MODELS["7x"]["hero_desktop"], "home")
    jsonld = graph(
        {"@type": "ItemList", "name": "Modelos ZEEKR Paraguay", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": MODELS[k]["name"], "url": DOMAIN + model_url(k)} for i, k in enumerate(MODEL_ORDER)]},
        faq_schema(HOME_FAQ),
    )
    render_page("/", "ZEEKR Paraguay | Vehículos eléctricos premium: 7X, X y 001",
                "Descubrí los vehículos eléctricos premium ZEEKR en Paraguay: ZEEKR 7X, ZEEKR X y ZEEKR 001. Diseño escandinavo, tecnología líder y autonomía real. Agendá tu prueba de manejo.",
                content, "", jsonld, og, preload=_derivative(MODELS["7x"]["hero_desktop"], 1800, "webp", False)[0], body_cls="page-home has-hero",
                preload_mobile=[_derivative(MODELS["7x"]["hero_mobile"], w, "webp", False) for w in (480, 780)])


# ------------------------------------------------------------------ modelos
def model_hero(m, image=None, mobile=None, cta=True, h1=None, kicker=None):
    img = image or m["card"]
    pic = picture(img, f"{m['name']} — {m['tagline']}", (1200, 1800, 2400), sizes="100vw", cls="hero-media",
                  img_cls="hero-bg", loading="eager", fetchpriority="high", mobile=mobile, decoding="sync",
                  attrs=f' style="--pos:{m.get("hero_pos", "50% 50%")}"')
    stats = f'<div class="stats-row">{stat_items(m["stats"])}</div>' if m.get("stats") else ""
    actions = f'''<div class="hero-actions">{btn("Agendá tu prueba de manejo", kind="accent", attrs=f' data-open-contact data-intent="test-drive" data-model="{m["name"]}"')}{btn("Ficha técnica (PDF)", href="/" + m["pdf"], kind="outline", icon=ICON_DOWNLOAD, attrs=' target="_blank" rel="noopener"') if m.get("pdf") else ""}</div>''' if cta else ""
    return f'''
<section class="hero-model">
  {pic}
  <div class="hero-shade" aria-hidden="true"></div>
  <div class="hero-inner">
    {eyebrow(kicker or m["eyebrow"])}
    <h1>{h1 or m['name']}</h1>
    <p class="claim">{m['claim']}</p>
    {actions}
    {stats}
  </div>
</section>'''


def spec_table(rows, caption):
    trs = "".join(f'<tr><th scope="row">{k}</th><td>{v}</td></tr>' for k, v in rows)
    return f'<table class="spec"><caption class="sr-only">{caption}</caption><tbody>{trs}</tbody></table>'


def sec_split(kicker, title, text, image, alt, reverse=False, dark=False):
    pic = picture(image, alt, (640, 960, 1400), sizes="(min-width:992px) 50vw, 100vw", cls="visual")
    body = f'<div class="split-copy reveal">{eyebrow(kicker)}<h2>{title}</h2><p>{text}</p></div>'
    return f'<section class="section{" dark" if dark else ""}"><div class="split{" reverse" if reverse else ""}">{pic}{body}</div></section>'


def sec_features(kicker, title, items, intro=None, dark=False, cols=3):
    lis = "".join(f'<li class="feature reveal"><h3>{h}</h3><p>{p}</p></li>' for h, p in items)
    return f'''<section class="section{" dark" if dark else ""}"><div class="section-head reveal">{eyebrow(kicker)}<h2>{title}</h2>{f"<p class='lead'>{intro}</p>" if intro else ""}</div><ul class="feature-list cols-{cols}">{lis}</ul></section>'''


def sec_stats(kicker, title, stats, dark=False):
    return f'''<section class="section{" dark" if dark else ""}"><div class="section-head reveal">{eyebrow(kicker)}<h2>{title}</h2></div><div class="stat-grid reveal">{stat_items(stats)}</div></section>'''


def sec_band(image, alt, kicker, title, text=None, pos="50% 50%"):
    pic = picture(image, alt, (960, 1600, 2400), sizes="100vw", cls="band-media", attrs=f' style="object-position:{pos}"')
    return f'''<section class="band">{pic}<div class="band-shade" aria-hidden="true"></div><div class="band-content reveal">{eyebrow(kicker)}<h2>{title}</h2>{f"<p>{text}</p>" if text else ""}</div></section>'''


def sec_gallery(kicker, title, images):
    figs = "".join(
        f'<li class="gallery-item">{picture(src, alt, (480, 800, 1200), sizes="(min-width:992px) 30vw, 78vw")}<figcaption>{alt}</figcaption></li>'
        for src, alt in images)
    return f'''<section class="section gallery-section" aria-label="{title}"><div class="section-head reveal">{eyebrow(kicker)}<h2>{title}</h2></div><ul class="gallery reveal" data-gallery tabindex="0" aria-label="Galería: deslizá para ver más">{figs}</ul></section>'''


def sec_compare(kicker, title, cols, intro=None):
    parts = "".join(f'<div class="spec-col reveal"><h3>{name}</h3>{f"<p class=spec-sub>{sub}</p>" if sub else ""}{spec_table(rows, f"Ficha técnica {name}")}</div>' for name, sub, rows in cols)
    return f'''<section class="section"><div class="section-head reveal">{eyebrow(kicker)}<h2>{title}</h2>{f"<p class='lead'>{intro}</p>" if intro else ""}</div><div class="spec-cols">{parts}</div></section>'''


def sec_video(src, poster, kicker, title, text):
    pic = _derivative(poster, 1600, "jpeg", False)
    return f'''
<section class="video-section">
  <video class="video-bg" muted loop playsinline preload="metadata" poster="{pic[0]}" aria-label="{title}" data-video>
    <source src="/{src}" type="video/mp4">
  </video>
  <div class="band-shade" aria-hidden="true"></div>
  <div class="band-content reveal">{eyebrow(kicker)}<h2>{title}</h2><p>{text}</p></div>
  <button class="hero-ctl video-toggle" type="button" data-video-toggle aria-label="Pausar video" aria-pressed="false"><span class="ico-pause">{ICON_PAUSE}</span><span class="ico-play">{ICON_PLAY}</span></button>
</section>'''


def model_jsonld(key, url):
    m = MODELS[key]
    car = {"@type": ["Product", "Car"], "name": m["name"], "brand": {"@type": "Brand", "name": "ZEEKR"},
           "manufacturer": {"@type": "Organization", "name": "ZEEKR"},
           "model": m["short"], "vehicleConfiguration": m["tagline"], "fuelType": "Electric",
           "description": m["schema_desc"], "url": DOMAIN + url,
           "image": [DOMAIN + _derivative(m["card"], 1600, "jpeg", False)[0], DOMAIN + _derivative(m["hero_desktop"], 1800, "jpeg", False)[0]],
           "offers": {"@type": "Offer", "availability": "https://schema.org/InStock", "url": DOMAIN + url,
                      "seller": {"@id": DOMAIN + "/#org"}, "priceCurrency": "PYG", "price": "0", "priceSpecification": {"@type": "PriceSpecification", "priceCurrency": "PYG", "description": "Consultar precio con un asesor"}}}
    # sin precio público: mejor no declarar Offer con price ficticio
    car.pop("offers")
    return graph(car, breadcrumb([("Inicio", "/"), ("Modelos", "/modelos/"), (m["name"], url)]), faq_schema(m["faq"]))


def page_7x():
    m = MODELS["7x"]
    url = model_url("7x")
    content = model_hero(m, image="images/hero/7x-desktop.jpg", mobile="images/hero/7x-mobile.jpg") + \
        sec_features("Explorá lo que hace único al ZEEKR 7X", "Conocé el SUV de próxima generación", [
            ("Diseño futurista", "Líneas limpias, proporciones elegantes y una presencia que destaca en la ciudad."),
            ("Cabina Snapdragon 8295", "Respuesta inmediata, controles fluidos y una experiencia digital de primer nivel."),
            ("Confort de primera clase", "Asientos NAPPA con ventilación, calefacción y masaje para viajar mejor."),
            ("Seguridad que anticipa", "ADAS avanzado y 7 airbags para manejar con total confianza."),
            ("0–100 km/h en 3,8 s", "Aceleración contundente y control total, sin sacrificar estabilidad."),
            ("Sistema de alto voltaje 800 V", "Carga ultrarrápida y gestión térmica eficiente para rendir siempre."),
        ]) + \
        sec_video("images/zeekr7x/video-exterior.mp4", "images/zeekr7x/diseno-exterior.jpg", "Exterior", "Presencia que se anticipa", "Proporciones de SUV con la elegancia de un diseño escandinavo: firma lumínica continua, superficies limpias y detalles que hablan de calidad.") + \
        sec_split("Interior", "Un interior que te hace sentir como en casa", "Asientos tapizados en piel, volante con calefacción y memorias, luz ambiental personalizable y mucho más. La segunda fila suma calefacción, reclinación eléctrica y cortina de privacidad.", "images/zeekr7x/tecnologia-2.jpg", "Interior del ZEEKR 7X con vista al mar", dark=True) + \
        sec_features("Tecnología", "Tecnología que impulsa el futuro", [
            ("Procesador Qualcomm 8295", "Chip de 5 nm para una experiencia digital en cabina más rápida y avanzada, líder en su segmento."),
            ("Sistema interactivo total", "Panel HD de 13″, head-up display AR de 36″ y pantalla central Mini-LED 3.5K de 16″."),
            ("ZEEKR OTA + App", "Actualizaciones por aire y control remoto del vehículo desde la app, desde cualquier lugar."),
            ("Batería Qilin 100 kWh", "Autonomía de hasta 543 km WLTP en la versión Performance."),
            ("Gestión térmica PTM 2.0", "Administra el calor del vehículo y aprovecha mejor la energía para un desempeño eficiente."),
            ("Arquitectura SEA", "Plataforma nativa eléctrica del Grupo Geely, con cerca de 30 años de experiencia en fabricación de vehículos."),
        ]) + \
        sec_split("Seguridad", "Protección integral de 720° para cada pasajero", "Estructura tipo cúpula reforzada, 7 airbags con cortina, trasera de aluminio de una pieza y batería con 10 rejillas capaz de resistir hasta 75 toneladas de impacto lateral.", "images/zeekr7x/generacion-1.jpg", "Vista en corte del ZEEKR 7X con sus airbags desplegados", reverse=True) + \
        sec_features("Seguridad", "Diseñado para anticiparse", [
            ("Seguridad activa 360°", "Asistencias avanzadas combinadas con múltiples cámaras, en todo momento."),
            ("Modo Centinela", "Graba automáticamente la actividad circundante al detectar comportamiento sospechoso, con acceso solo para el propietario."),
            ("Estructura tipo cúpula", "Absorbe la energía del impacto y protege pasajeros y batería."),
        ], dark=True) + \
        sec_gallery("Galería", "Cada detalle, a la vista", [
            ("images/zeekr7x/apariencia-1.jpg", "ZEEKR 7X, vista trasera en estudio"),
            ("images/zeekr7x/apariencia-3.jpg", "ZEEKR 7X, vista lateral trasera"),
            ("images/zeekr7x/apariencia-6.jpg", "Firma lumínica frontal del ZEEKR 7X"),
            ("images/zeekr7x/diseno-interior-1.jpg", "Cabina del ZEEKR 7X con pantalla central Mini-LED"),
            ("images/zeekr7x/diseno-interior-2.jpg", "Asientos traseros del ZEEKR 7X"),
            ("images/zeekr7x/generacion-3.jpg", "Techo panorámico del ZEEKR 7X"),
            ("images/zeekr7x/lujo-confort.jpg", "Espacio interior del ZEEKR 7X en uso"),
            ("images/zeekr7x/sentidos-3.jpg", "Cabina del ZEEKR 7X vista desde arriba"),
        ]) + \
        sec_compare("Versiones", "Elegí el ZEEKR 7X que se adapta a tu estilo", [
            ("Smart", "Tu acceso al ZEEKR 7X", [("Autonomía", "480 km (WLTP)"), ("Aceleración 0–100 km/h", "6,0 s"), ("Potencia máxima", "421 HP · RWD"), ("Batería", "75 kWh")]),
            ("Performance", "La máxima expresión", [("Autonomía", "543 km (WLTP)"), ("Aceleración 0–100 km/h", "3,8 s"), ("Potencia máxima", "646 HP · AWD"), ("Batería", "100 kWh")]),
        ]) + \
        sec_compare("Especificaciones", "Dimensiones y garantía", [
            ("Dimensiones", None, [("Longitud", "4.787 mm"), ("Ancho (incl. espejos)", "1.930 mm"), ("Altura máxima", "1.650 mm"), ("Distancia entre ejes", "2.900 mm")]),
            ("Garantía", None, [("Vehículo", "5 años o 100.000 km, lo que ocurra primero"), ("Batería", "8 años o 160.000 km, lo que ocurra primero")]),
        ]) + faq_block(m["faq"], title="Preguntas frecuentes sobre el ZEEKR 7X") + contact_strip(m["name"])
    og = og_image(m["card"], "zeekr-7x", pos=(0.6, 0.5))
    render_page(url, m["meta_title"], m["meta_desc"], content, "modelos", model_jsonld("7x", url), og,
                preload=_derivative("images/hero/7x-desktop.jpg", 1800, "webp", False)[0], body_cls="page-model has-hero",
                preload_mobile=[_derivative("images/hero/7x-mobile.jpg", w, "webp", False) for w in (480, 780)])


def page_x():
    m = MODELS["x"]
    url = model_url("x")
    content = model_hero(m, image="images/zeekrx/exterior-mist-grey.jpg") + \
        sec_split("El SUV urbano que potencia tu estilo de vida", "Llevando el SUV urbano al siguiente nivel", "El ZEEKR X es un SUV compacto de lujo creado para los estilos de vida urbanos de hoy: el compañero perfecto para aventureros y familias. Líneas atrevidas, tecnología inteligente y máxima comodidad en un solo vehículo.", "images/zeekrx/prestacion1.png", "ZEEKR X circulando por la ciudad") + \
        sec_stats("Prestaciones", "0–100 km/h en 3,8 s (AWD)", [("428 HP", "Potencia máxima (AWD)"), ("190 km/h", "Velocidad máxima"), ("440 km", "Autonomía WLTP (RWD)"), ("69 kWh", "Batería")], dark=True) + \
        sec_features("Prestaciones", "Ingeniería para la ciudad", [
            ("XTCS antideslizante inteligente", "Control de tracción propio de ZEEKR: identifica y controla el derrape en 6 ms, 10 veces más rápido que un TCS tradicional."),
            ("Techo panorámico doble", "Tragaluz de 1,21 m² con aislamiento térmico y acústico, y barrera UV del 99 %."),
            ("Seguridad integral", "Vigas anticolisión multicapa de 8 tubos y 7 airbags con protección envolvente de 360°."),
        ]) + \
        sec_band("images/zeekrx/interior-charcoal-black-and-golden-trim.jpg", "Interior del ZEEKR X en Charcoal Black con detalles dorados", "Interior", "Cabina inteligente, materiales nobles", "Charcoal Black con acabados dorados, pantalla central y una experiencia digital que evoluciona con actualizaciones OTA.", pos="50% 40%") + \
        sec_features("Inteligente", "ZEEKR AD y cabina inteligente", [
            ("Actualizaciones OTA", "Las actualizaciones de software garantizan que tu vehículo esté siempre al día."),
            ("ZEEKR AD", "5 cámaras HD, 5 radares milimétricos y 12 sensores ultrasónicos con más de 10 funciones de asistencia: crucero adaptativo y estacionamiento."),
            ("Luces diurnas de doble línea", "56 LED independientes integran DRL, luces laterales e intermitentes en un solo sistema."),
        ], dark=True) + \
        sec_gallery("Galería", "El ZEEKR X en detalle", [
            ("images/zeekrx/caracteristica1.jpg", "Detalle del techo panorámico del ZEEKR X"),
            ("images/zeekrx/caracteristica3.jpg", "Cabina del ZEEKR X"),
            ("images/zeekrx/caracteristica4.jpg", "Detalle de la cámara del ZEEKR X"),
            ("images/zeekrx/inteligente3.png", "Pantalla central del ZEEKR X"),
            ("images/zeekrx/inteligente4.png", "Sensores de ZEEKR AD"),
            ("images/zeekrx/prestacion2.png", "ZEEKR X en la ciudad al atardecer"),
        ]) + \
        sec_compare("Versiones", "Elegí el ZEEKR X que se adapta a tu estilo", [
            ("Flagship AWD", "La máxima experiencia ZEEKR", [("Aceleración 0–100 km/h", "3,8 s"), ("Motor", "Doble"), ("Tracción", "All Wheel Drive"), ("Autonomía", "420 km (WLTP)"), ("Potencia", "428 HP"), ("Rines", "Aluminio 20″")]),
            ("Premium RWD", "Tu acceso a ZEEKR", [("Aceleración 0–100 km/h", "5,6 s"), ("Motor", "Sencillo"), ("Tracción", "Rear Wheel Drive"), ("Autonomía", "440 km (WLTP)"), ("Potencia", "268 HP"), ("Rines", "Aluminio 19″")]),
        ]) + \
        sec_compare("Especificaciones", "Dimensiones", [
            ("Dimensiones", None, [("Longitud", "4.432 mm"), ("Ancho", "1.836 mm"), ("Altura", "1.566 mm"), ("Distancia entre ejes", "2.750 mm")]),
        ]) + faq_block(m["faq"], title="Preguntas frecuentes sobre el ZEEKR X") + contact_strip(m["name"])
    og = og_image(m["card"], "zeekr-x")
    render_page(url, m["meta_title"], m["meta_desc"], content, "modelos", model_jsonld("x", url), og,
                preload=_derivative("images/zeekrx/exterior-mist-grey.jpg", 1800, "webp", False)[0], body_cls="page-model has-hero")


def page_001():
    m = MODELS["001"]
    url = model_url("001")
    content = model_hero(m, image="images/zeekr001/exterior-phantom-black.jpg") + \
        sec_split("El crossover de lujo, reinventado", "El primer deportivo familiar eléctrico puro producido en masa del mundo", "El ZEEKR 001 ofrece algo nuevo para todos. La combinación de elegancia y confort brinda un viaje lujoso para las aventuras de toda la familia.", "images/zeekr001/prestacion1.png", "ZEEKR 001 en ruta de montaña") + \
        sec_split("Arquitectura SEA", "Tecnología que lleva los vehículos eléctricos más lejos", "Cada ZEEKR se basa en la Arquitectura de Experiencia Sostenible (SEA): una plataforma totalmente eléctrica, modular y escalable que integra las últimas tecnologías. Autonomía de hasta 620 km y carga del 10 % al 80 % en menos de 30 minutos con carga DC de 200 kW.", "images/zeekr001/chasis1.jpg", "Chasis y arquitectura SEA del ZEEKR 001", reverse=True, dark=True) + \
        sec_stats("Prestaciones", "0–100 km/h en 3,8 s (AWD)", [("536 HP", "Potencia máxima (AWD)"), ("200 km/h", "Velocidad máxima"), ("620 km", "Autonomía WLTP (RWD)"), ("100 kWh", "Batería")]) + \
        sec_features("Prestaciones", "Potencia con refinamiento", [
            ("Suspensión neumática automática", "Ajuste de altura en cinco niveles en tiempo real. Disponible en la versión Flagship."),
            ("Frenos regenerativos", "Aprovechan la energía para recargar la batería mientras manejás."),
            ("Motores de alto rendimiento", "536 HP, 16.500 rpm de rotación máxima y hasta 97,86 % de eficiencia."),
        ]) + \
        sec_band("images/zeekr001/interior-charcoal-black-and-golden-trim.jpg", "Interior del ZEEKR 001 en Charcoal Black con detalles dorados", "Interior", "Lujo digital, materiales de primera", "Acabados premium y tecnología de cabina de última generación, siempre al día gracias a las actualizaciones OTA.", pos="50% 45%") + \
        sec_features("Inteligente", "Cabina inteligente con OTA", [
            ("Falcon Eye Vidar", "15 cámaras HD, 7 kits de cámaras de 8 MP, radar de alcance ultralargo de 250 m y 12 sensores ultrasónicos."),
            ("Interior lujoso", "Materiales de primera calidad y acabados cuidados: tecnología digital de cabina de última generación."),
            ("Baúl de hasta 2.144 L", "Baúl divisible que puede ampliarse hasta 2.144 litros, para usarlo como quieras."),
        ], dark=True) + \
        sec_gallery("Galería", "El ZEEKR 001 en detalle", [
            ("images/zeekr001/caracteristica1.jpg", "Frente del ZEEKR 001"),
            ("images/zeekr001/caracteristica2.jpg", "Firma lumínica trasera del ZEEKR 001"),
            ("images/zeekr001/caracteristica3.jpg", "Cabina digital del ZEEKR 001"),
            ("images/zeekr001/caracteristica4.jpg", "Baúl del ZEEKR 001 con asientos abatidos"),
            ("images/zeekr001/inteligente3.jpg", "Interior delantero del ZEEKR 001"),
            ("images/zeekr001/prestacion3.png", "ZEEKR 001 en movimiento"),
        ]) + \
        sec_compare("Versiones", "La máxima experiencia ZEEKR", [
            ("Flagship AWD", "La máxima expresión", [("Aceleración 0–100 km/h", "3,8 s"), ("Motor", "Doble"), ("Tracción", "All Wheel Drive"), ("Autonomía", "580 km (WLTP)"), ("Potencia", "536 HP"), ("Rines de aluminio", "22″"), ("Suspensión activa", "Sí"), ("Sistema de audio", "Yamaha, 12 parlantes + subwoofer"), ("Asientos con ventilación y masaje", "Sí")]),
            ("Sport RWD", "Tu acceso al ZEEKR 001", [("Aceleración 0–100 km/h", "7,2 s"), ("Motor", "Sencillo"), ("Tracción", "Rear Wheel Drive"), ("Autonomía", "620 km (WLTP)"), ("Potencia", "268 HP"), ("Rines de aluminio", "21″"), ("Suspensión activa", "No"), ("Sistema de audio", "Yamaha, 12 parlantes + subwoofer"), ("Asientos con ventilación y masaje", "No")]),
        ]) + \
        sec_compare("Especificaciones", "Dimensiones", [
            ("Dimensiones", None, [("Longitud", "4.955 mm"), ("Ancho", "2.005 mm"), ("Altura", "1.560 mm"), ("Distancia entre ejes", "2.999 mm")]),
        ]) + faq_block(m["faq"], title="Preguntas frecuentes sobre el ZEEKR 001") + contact_strip(m["name"])
    og = og_image(m["card"], "zeekr-001", pos=(0.6, 0.5))
    render_page(url, m["meta_title"], m["meta_desc"], content, "modelos", model_jsonld("001", url), og,
                preload=_derivative("images/zeekr001/exterior-phantom-black.jpg", 1800, "webp", False)[0], body_cls="page-model has-hero")


def page_modelos():
    cards = "".join(model_card(k) for k in MODEL_ORDER)
    content = page_intro("Gama ZEEKR Paraguay", "Modelos", "Tres formas de vivir la movilidad eléctrica premium: el SUV de próxima generación, el SUV urbano y el crossover de lujo.") + f'<section class="models" aria-label="Modelos ZEEKR">{cards}</section>' + contact_strip()
    jsonld = graph(
        {"@type": "CollectionPage", "name": "Modelos ZEEKR Paraguay", "url": DOMAIN + "/modelos/", "inLanguage": "es-PY",
         "mainEntity": {"@type": "ItemList", "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "name": MODELS[k]["name"], "url": DOMAIN + model_url(k)} for i, k in enumerate(MODEL_ORDER)]}},
        breadcrumb([("Inicio", "/"), ("Modelos", "/modelos/")]))
    render_page("/modelos/", "Modelos ZEEKR en Paraguay | 7X, X y 001 — ZEEKR Paraguay",
                "Conocé la gama ZEEKR en Paraguay: ZEEKR 7X (SUV de próxima generación), ZEEKR X (SUV urbano premium) y ZEEKR 001 (crossover eléctrico de lujo). Fichas técnicas y test drive.",
                content, "modelos", jsonld, og_image("images/hero/7x-desktop.jpg", "modelos"), body_cls="page-list")


# ------------------------------------------------------------------ noticias
def page_noticias():
    featured = next((n for n in NEWS if n.get("body")), None)
    rest = [n for n in NEWS if n is not featured]
    feat_html = ""
    if featured:
        url = news_url(featured)
        pic = picture(featured["img"], featured["title"], (800, 1200, 1800), sizes="(min-width:992px) 60vw, 100vw", cls="feat-media", loading="eager", fetchpriority="high")
        feat_html = f'''
<section class="section featured-news" aria-labelledby="featTitle">
  <article class="featured reveal">
    <a class="featured-link" href="{url}">
      {pic}
      <div class="featured-body">
        <p class="news-meta"><span class="news-kicker">{featured["kicker"]}</span><time class="news-date" datetime="{featured["date"]}">{fecha_larga(featured["date"])}</time></p>
        <h2 id="featTitle">{featured["title"]}</h2>
        <p class="lead">{featured["lead"]}</p>
        <span class="btn btn-cream btn-arrow"><span>Leer la nota</span>{ICON_ARROW}</span>
      </div>
    </a>
  </article>
</section>'''
    grid = "".join(news_card(n) for n in rest)
    content = page_intro("ZEEKR Paraguay", "Noticias", "Lanzamientos, eventos y tecnología ZEEKR en Paraguay y el mundo.") + feat_html + f'''
<section class="section news-archive" aria-label="Todas las noticias">
  <div class="section-head reveal">{eyebrow("Novedades")}<h2>Más noticias</h2></div>
  <div class="news-grid news-grid-dark">{grid}</div>
</section>''' + contact_strip()
    jsonld = graph(
        {"@type": "CollectionPage", "name": "Noticias — ZEEKR Paraguay", "url": DOMAIN + "/noticias/", "inLanguage": "es-PY",
         "mainEntity": {"@type": "ItemList", "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "name": n["title"], **({"url": DOMAIN + news_url(n)} if news_url(n) else {})} for i, n in enumerate(NEWS)]}},
        breadcrumb([("Inicio", "/"), ("Noticias", "/noticias/")]))
    render_page("/noticias/", "Noticias ZEEKR Paraguay | Lanzamientos, eventos y tecnología EV",
                "Todas las noticias de ZEEKR en Paraguay: lanzamientos, eventos, tecnología eléctrica, alianzas y novedades de los modelos 7X, X y 001.",
                content, "noticias", jsonld, og_image(featured["img"] if featured else "images/hero/7x-desktop.jpg", "noticias"), body_cls="page-list")


def page_article(n):
    url = news_url(n)
    m = MODELS.get(n.get("cta_model"))
    cover = picture(n["img"], n["title"], (960, 1600, 2400), sizes="100vw", cls="article-cover", loading="eager", fetchpriority="high")
    paras = [f"<p>{p}</p>" for p in n["body"]]
    if n.get("quote"):
        q, who, org = n["quote"]
        foot = f"<footer><cite>{who}</cite>{' · ' + org if org else ''}</footer>" if who else (f"<footer>{org}</footer>" if org else "")
        paras.insert(n.get("quote_pos", 2), f'<blockquote class="article-quote"><p>“{q}”</p>{foot}</blockquote>')
    body = "".join(paras)
    gallery = ""
    if n.get("gallery"):
        figs = "".join(f'<figure class="masonry-item reveal">{picture(src, alt, (480, 800, 1200), sizes="(min-width:992px) 33vw, (min-width:600px) 50vw, 100vw")}<figcaption>{alt}</figcaption></figure>' for src, alt in n["gallery"])
        gallery = f'<section class="section article-gallery" aria-label="Galería del evento"><div class="section-head reveal">{eyebrow("Galería")}<h2>La noche en imágenes</h2></div><div class="masonry">{figs}</div></section>'
    model_cta = ""
    if m:
        model_cta = f'''
<aside class="article-model reveal" aria-label="Modelo relacionado">
  {picture(m["card"], m["name"], (640, 960, 1400), sizes="(min-width:992px) 40vw, 100vw", cls="article-model-media", attrs=f' style="object-position:{m["card_pos"]}"')}
  <div class="article-model-body">
    {eyebrow(m["eyebrow"])}
    <h2>{m["name"]}</h2>
    <p>{m["claim"]}</p>
    <div class="model-actions">{btn(f"Descubrí el {m['name']}", href=model_url(n["cta_model"]), kind="cream", icon=ICON_ARROW, extra="btn-arrow")}{btn("Agendá tu prueba de manejo", kind="outline", attrs=f' data-open-contact data-intent="test-drive" data-model="{m["name"]}"')}</div>
  </div>
</aside>'''
    content = f'''
<article class="article">
  <header class="article-head">
    <div class="article-head-inner reveal">
      <nav class="crumbs" aria-label="Migas de pan"><a href="/">Inicio</a><span aria-hidden="true">/</span><a href="/noticias/">Noticias</a></nav>
      <p class="news-meta"><span class="news-kicker">{n["kicker"]}</span><time class="news-date" datetime="{n["date"]}">{fecha_larga(n["date"])}</time></p>
      <h1>{n["title"]}</h1>
      <p class="lead">{n["lead"]}</p>
    </div>
  </header>
  <div class="article-cover-wrap reveal">{cover}</div>
  <div class="article-body reveal">{body}
    <p class="article-share">Compartir: <a href="https://wa.me/?text={esc(n['title'])}%20{DOMAIN}{url}" target="_blank" rel="noopener">WhatsApp</a> · <a href="https://www.linkedin.com/sharing/share-offsite/?url={DOMAIN}{url}" target="_blank" rel="noopener">LinkedIn</a></p>
  </div>
  {gallery}
  {model_cta}
</article>''' + contact_strip(m["name"] if m else None)
    images = [DOMAIN + _derivative(n["img"], 1600, "jpeg", False)[0]] + [DOMAIN + _derivative(s, 1200, "jpeg", False)[0] for s, _ in n.get("gallery", [])]
    article = {"@type": "NewsArticle", "headline": n["title"], "description": n["lead"], "datePublished": n["date"], "dateModified": n["date"],
               "inLanguage": "es-PY", "url": DOMAIN + url, "mainEntityOfPage": DOMAIN + url, "image": images,
               "articleSection": "Eventos", "author": {"@id": DOMAIN + "/#org"}, "publisher": {"@id": DOMAIN + "/#org"},
               **({"contentLocation": {"@type": "Place", "name": n["place"], "address": {"@type": "PostalAddress", "addressLocality": n.get("place_locality", "Asunción"), "addressCountry": "PY"}}} if n.get("place") else {}),
               "about": [{"@type": "Car", "name": m["name"], "brand": {"@type": "Brand", "name": "ZEEKR"}}] if m else []}
    jsonld = graph(article, breadcrumb([("Inicio", "/"), ("Noticias", "/noticias/"), (n["title"], url)]))
    render_page(url, f"{n['title']} — ZEEKR Paraguay", n["lead"], content, "noticias", jsonld,
                og_image(n["img"], n["slug"]), body_cls="page-article", lastmod=n["date"])


# ------------------------------------------------------------------ nosotros
def page_nosotros():
    hero = model_hero({"name": "Nosotros", "tagline": "Somos ZEEKR", "eyebrow": "Somos ZEEKR",
                       "claim": "Por medio del diseño, la tecnología y la innovación, motivamos a todos a reimaginar los automóviles eléctricos.",
                       "card": "images/nosotros/manufactura2.jpg", "card_pos": "50% 50%", "stats": []}, cta=False,
                      h1="Más allá del punto de partida")
    content = hero + f'''
<section class="section" aria-labelledby="nameTitle">
  <div class="section-head reveal">{eyebrow("Nuestro nombre")}<h2 id="nameTitle">ZEEKR: tres letras, una idea</h2></div>
  <ul class="feature-list cols-3 brand-letters">
    <li class="feature reveal"><h3><span class="big-letter">ZE</span></h3><p>Zero: el punto de partida hacia las posibilidades infinitas.</p></li>
    <li class="feature reveal"><h3><span class="big-letter">E</span></h3><p>La evolución hacia la era eléctrica.</p></li>
    <li class="feature reveal"><h3><span class="big-letter">KR</span></h3><p>Kriptón: un gas inusual que emite luz cuando se electrifica.</p></li>
  </ul>
</section>''' + sec_features("Nuestros valores", "Un ambiente armonioso entre el ser humano, la tecnología y la naturaleza", [
        ("Diversidad", "Promovemos la diversidad y celebramos las diferencias. Con una actitud abierta logramos innovar para un mejor futuro."),
        ("Igualdad", "Mantenemos la mente abierta y una comunicación transparente. La igualdad es necesaria en todas nuestras relaciones."),
        ("Sostenibilidad", "Nos esforzamos por un futuro mejor para todos, abriendo camino con diseño innovador y soluciones tecnológicas."),
    ], dark=True) + \
        sec_split("Manufactura inteligente", "Fábricas de vanguardia, mente nórdica", "Los vehículos ZEEKR se producen en una de las fábricas más avanzadas del mundo. El aclamado diseñador Stefan Sielaff dirige el centro global de diseño en Gotemburgo, Suecia, donde mentes creativas de todo el mundo diseñan los ZEEKR del futuro.", "images/nosotros/manufactura1.png", "Planta de manufactura inteligente ZEEKR") + \
        sec_split("Geely Holding Group", "Liderando el mundo de la movilidad desde Hangzhou", "Geely Holding Group posee, invierte y gestiona múltiples marcas —Geely Auto, Lynk &amp; Co, ZEEKR, Volvo, Polestar, Lotus, LEVC, Farizon, Radar y Cao Cao Mobility— con foco en innovación y movilidad sostenible. ZEEKR es la marca de lujo eléctrico del Grupo, comprometida con liderar el futuro de la movilidad centrada en la tecnología y el consumidor.", "images/nosotros/holding.jpg", "Sede de Geely Holding Group", reverse=True, dark=True) + \
        sec_band("images/nosotros/valor2.png", "Dos ZEEKR 001 frente a un puente", "En Paraguay", "Santa Rosa Paraguay, distribuidor oficial", "Ventas, postventa y asesoramiento especializado para que tu experiencia ZEEKR sea completa desde el primer día.") + \
        contact_strip()
    jsonld = graph({"@type": "AboutPage", "name": "Nosotros — ZEEKR Paraguay", "url": DOMAIN + "/nosotros/", "inLanguage": "es-PY", "about": {"@id": DOMAIN + "/#org"}},
                   breadcrumb([("Inicio", "/"), ("Nosotros", "/nosotros/")]))
    render_page("/nosotros/", "Nosotros | ZEEKR Paraguay — la marca eléctrica premium de Geely",
                "Conocé la historia de ZEEKR: diseño en Gotemburgo, manufactura inteligente en Hangzhou, el Grupo Geely y Santa Rosa Paraguay como distribuidor oficial de la movilidad eléctrica premium.",
                content, "nosotros", jsonld, og_image("images/nosotros/manufactura2.jpg", "nosotros"),
                preload=_derivative("images/nosotros/manufactura2.jpg", 1800, "webp", False)[0], body_cls="page-model has-hero")


# ------------------------------------------------------------------ 404
def page_404():
    content = f'''
<section class="page-intro notfound">
  <div class="page-intro-inner">
    {eyebrow("Error 404")}
    <h1>Esta página no existe</h1>
    <p class="lead">Puede que el enlace haya cambiado. Volvé al inicio o explorá los modelos ZEEKR.</p>
    <div class="model-actions">{btn("Ir al inicio", href="/", kind="cream")}{btn("Ver modelos", href="/modelos/", kind="outline", icon=ICON_ARROW, extra="btn-arrow")}</div>
  </div>
</section>'''
    render_page("/404.html", "Página no encontrada — ZEEKR Paraguay", "La página que buscás no existe.", content, "",
                graph(), og_image("images/hero/7x-desktop.jpg", "home"), body_cls="page-list")


# ------------------------------------------------------------------ sitemap / robots
def build_meta():
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, lastmod in PAGES:
        sm.append(f"  <url><loc>{DOMAIN}{path}</loc><lastmod>{lastmod}</lastmod></url>")
    sm.append("</urlset>")
    open("sitemap.xml", "w").write("\n".join(sm) + "\n")
    open("robots.txt", "w").write(f"User-agent: *\nAllow: /\nDisallow: /404.html\n\nSitemap: {DOMAIN}/sitemap.xml\n")
    # Cloudflare Pages / Netlify: mismas redirecciones y cabeceras que nginx.conf
    legacy = [("/index.html", "/"), ("/zeekr001.html", "/modelos/zeekr-001/"), ("/zeekrx.html", "/modelos/zeekr-x/"),
              ("/zeekr7x.html", "/modelos/zeekr-7x/"), ("/noticias.html", "/noticias/"), ("/nosotros.html", "/nosotros/")]
    lines = [f"{a} {b} 301" for a, b in legacy] + [f"https://www.{DOMAIN.split('//')[1]}/* {DOMAIN}/:splat 301"]
    open("_redirects", "w").write("\n".join(lines) + "\n")
    sec = ["  X-Content-Type-Options: nosniff", "  X-Frame-Options: SAMEORIGIN",
           "  Referrer-Policy: strict-origin-when-cross-origin", "  Permissions-Policy: camera=(), microphone=(), geolocation=()"]
    hdr = ["/*", *sec, "/images/*", "  Cache-Control: public, max-age=2592000, immutable", "/fonts/*",
           "  Cache-Control: public, max-age=31536000, immutable", "/css/*", "  Cache-Control: public, max-age=2592000, immutable",
           "/js/*", "  Cache-Control: public, max-age=2592000, immutable", "/icons/*", "  Cache-Control: public, max-age=2592000, immutable",
           "/api/*", "  Cache-Control: no-store"]
    open("_headers", "w").write("\n".join(hdr) + "\n")
    print("OK sitemap.xml robots.txt _redirects _headers")


def cleanup_legacy():
    for f in ["zeekr001.html", "zeekrx.html", "zeekr7x.html", "noticias.html", "nosotros.html"]:
        if os.path.exists(f):
            os.remove(f)
            print("rm", f)
    # derivados huérfanos en images/_opt
    for root, _dirs, files in os.walk(OPT_DIR):
        for f in files:
            path = os.path.join(root, f)
            if path not in GENERATED:
                os.remove(path)
                print("rm", path)


def main():
    build_icons()
    build_index()
    page_modelos()
    page_7x()
    page_x()
    page_001()
    page_noticias()
    for n in NEWS:
        if n.get("body"):
            page_article(n)
    page_nosotros()
    page_404()
    build_meta()
    cleanup_legacy()


if __name__ == "__main__":
    main()
