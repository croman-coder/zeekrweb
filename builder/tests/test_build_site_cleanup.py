# builder/tests/test_build_site_cleanup.py — cobertura real de build_site.cleanup_html(): hasta la ronda 2
# nadie la ejercitaba contra archivos de verdad (los tests de build_runner solo usan un `generate()` falso).
import build_site as bs


def _write(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_cleanup_html_removes_stale_pages_keeps_current_pages_and_other_assets(tmp_path, monkeypatch):
    """Arma un workspace con páginas "de la corrida anterior" (modelo/noticia que se despublicó, o un
    borrador que alguien previsualizó) y "de la corrida actual" (lo que HTML_PAGES tiene ahora), y llama
    la cleanup_html() real. Tiene que borrar solo lo viejo, y solo dentro de las carpetas que esta corrida
    reclama (modelos/, en/, noticias/) — nunca css/, images/ ni un archivo no-HTML que conviva ahí."""
    monkeypatch.chdir(tmp_path)

    # "corrida anterior": zeekr-9x se despublicó → su página en es y en en/ quedó huérfana, sola en su carpeta
    _write(tmp_path / "modelos" / "zeekr-9x" / "index.html", "BORRADOR VIEJO 9X")
    _write(tmp_path / "en" / "models" / "zeekr-9x" / "index.html", "OLD EN 9X")
    # una noticia borrada del CMS, pero con un archivo no-HTML al lado (no lo tiene que tocar, y por eso
    # tampoco puede borrar la carpeta aunque el index.html sí se vaya)
    _write(tmp_path / "noticias" / "vieja-que-se-borro" / "index.html", "NOTICIA VIEJA")
    _write(tmp_path / "noticias" / "vieja-que-se-borro" / "nota.txt", "no es una página")
    # assets fuera de las carpetas que esta corrida reclama: cleanup_html no tiene que caminarlos nunca
    _write(tmp_path / "css" / "zeekr-site.css", "body{}")
    _write(tmp_path / "images" / "cms" / "foo.jpg", "img")

    # "corrida actual": esto es lo único que el generador escribió en esta pasada
    _write(tmp_path / "modelos" / "zeekr-7x" / "index.html", "ZEEKR 7X")
    _write(tmp_path / "en" / "models" / "zeekr-7x" / "index.html", "ZEEKR 7X EN")
    _write(tmp_path / "noticias" / "index.html", "listado")

    original_html_pages = set(bs.HTML_PAGES)                       # cleanup_html() lee el global del módulo
    bs.HTML_PAGES = {
        "modelos/zeekr-7x/index.html",
        "en/models/zeekr-7x/index.html",
        "noticias/index.html",
    }
    try:
        bs.cleanup_html()
    finally:
        bs.HTML_PAGES = original_html_pages                        # no contaminar otros tests

    # las páginas de esta corrida siguen intactas
    assert (tmp_path / "modelos" / "zeekr-7x" / "index.html").read_text() == "ZEEKR 7X"
    assert (tmp_path / "en" / "models" / "zeekr-7x" / "index.html").read_text() == "ZEEKR 7X EN"
    assert (tmp_path / "noticias" / "index.html").read_text() == "listado"

    # las páginas huérfanas se borraron, y la carpeta vacía que dejaron también
    assert not (tmp_path / "modelos" / "zeekr-9x" / "index.html").exists()
    assert not (tmp_path / "modelos" / "zeekr-9x").exists()
    assert not (tmp_path / "en" / "models" / "zeekr-9x" / "index.html").exists()
    assert not (tmp_path / "en" / "models" / "zeekr-9x").exists()

    # la noticia huérfana se borró, pero el archivo no-HTML que convivía con ella sobrevivió (y por eso
    # la carpeta no quedó vacía, así que tampoco se borró)
    assert not (tmp_path / "noticias" / "vieja-que-se-borro" / "index.html").exists()
    assert (tmp_path / "noticias" / "vieja-que-se-borro" / "nota.txt").read_text() == "no es una página"
    assert (tmp_path / "noticias" / "vieja-que-se-borro").is_dir()

    # css/ e images/ no son carpetas que esta corrida reclame (no hay ningún index.html ahí en HTML_PAGES):
    # cleanup_html() nunca las camina
    assert (tmp_path / "css" / "zeekr-site.css").read_text() == "body{}"
    assert (tmp_path / "images" / "cms" / "foo.jpg").read_text() == "img"
