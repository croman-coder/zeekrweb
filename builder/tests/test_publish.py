import os

from builder import publish as P


def ws(tmp_path, content="v1"):
    w = tmp_path / "ws"
    (w / "css").mkdir(parents=True, exist_ok=True)
    (w / "index.html").write_text(content)
    if not (w / "css" / "a.css").exists():          # sin cambios entre releases → debe hardlinkearse
        (w / "css" / "a.css").write_text("body{}")
    (w / "build_site.py").write_text("print()")          # excluido
    (w / "i18n_missing_en.txt").write_text("x")           # excluido
    return w


def test_release_switch_and_link_dest(tmp_path):
    root = tmp_path / "sites"
    r1 = P.new_release(root, "zeekr", ws(tmp_path))
    assert (r1 / "index.html").read_text() == "v1" and not (r1 / "build_site.py").exists() and not (r1 / "i18n_missing_en.txt").exists()
    assert P.target(root / "zeekr" / "current") is None
    P.switch(root, "zeekr", "current", r1)
    assert P.target(root / "zeekr" / "current") == r1.resolve()
    r2 = P.new_release(root, "zeekr", ws(tmp_path, "v2"))
    assert r2 != r1 and (r2 / "index.html").read_text() == "v2" and (r1 / "index.html").read_text() == "v1"
    assert os.stat(r2 / "css" / "a.css").st_ino == os.stat(r1 / "css" / "a.css").st_ino     # sin cambios → hardlink (link-dest)
    P.switch(root, "zeekr", "current", r2)
    assert P.previous_release(root, "zeekr") == r1.resolve()
    P.switch(root, "zeekr", "current", P.previous_release(root, "zeekr"))                     # rollback
    assert P.target(root / "zeekr" / "current") == r1.resolve()


def test_preview_kind_and_prune(tmp_path):
    root = tmp_path / "sites"
    pubs = [P.new_release(root, "zeekr", ws(tmp_path, str(i))) for i in range(4)]
    prev = [P.new_release(root, "zeekr", ws(tmp_path, "p"), kind="preview") for _ in range(3)]
    assert all(p.name.endswith("-preview") for p in prev) and len(P.releases(root, "zeekr")) == 4 and len(P.releases(root, "zeekr", "preview")) == 3
    P.switch(root, "zeekr", "current", pubs[0])                 # la más vieja está protegida
    P.switch(root, "zeekr", "preview", prev[0])
    removed = P.prune(root, "zeekr", keep=2, keep_preview=1)
    assert pubs[0].exists() and pubs[1] not in [p.resolve() for p in P.releases(root, "zeekr")] and pubs[2].exists() and pubs[3].exists()
    assert prev[0].exists() and not prev[1].exists() and prev[2].exists()
    assert len(removed) == 2
