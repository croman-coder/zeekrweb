import os
import shutil

import pytest

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


def test_new_release_failure_leaves_no_partial_release(tmp_path):
    root = tmp_path / "sites"
    r1 = P.new_release(root, "zeekr", ws(tmp_path))
    P.switch(root, "zeekr", "current", r1)
    before = P.releases(root, "zeekr")

    nonexistent_workspace = tmp_path / "does_not_exist"   # rsync falla: no hay fuente que copiar
    with pytest.raises(RuntimeError) as exc_info:
        P.new_release(root, "zeekr", nonexistent_workspace)
    assert "rsync" in str(exc_info.value)                 # el motivo del fallo (stderr) no se pierde

    assert P.releases(root, "zeekr") == before             # ninguna release parcial quedó visible
    assert P.target(root / "zeekr" / "current") == r1.resolve()  # current no se vio afectado

    rel_dir = root / "zeekr" / "releases"
    assert not any(p.name.startswith(".tmp-") for p in rel_dir.iterdir())  # tampoco quedó staging huérfano


def test_releases_ignores_staging_dirs(tmp_path):
    root = tmp_path / "sites"
    r1 = P.new_release(root, "zeekr", ws(tmp_path))
    P.switch(root, "zeekr", "current", r1)
    r2 = P.new_release(root, "zeekr", ws(tmp_path, "v2"))
    P.switch(root, "zeekr", "current", r2)

    # simula una release a medio copiar (un proceso que murió antes del rename atómico)
    rel_dir = root / "zeekr" / "releases"
    staging = rel_dir / ".tmp-99999999-999999"
    staging.mkdir()
    (staging / "index.html").write_text("mid-copy")

    assert staging not in P.releases(root, "zeekr")
    assert staging not in P.releases(root, "zeekr", "preview")
    assert P.previous_release(root, "zeekr") == r1.resolve()   # el staging nunca es candidato a rollback


def test_new_release_cleans_up_orphaned_staging(tmp_path):
    root = tmp_path / "sites"
    P.site_dir(root, "zeekr")
    rel_dir = root / "zeekr" / "releases"
    orphan = rel_dir / ".tmp-11111111-111111"
    orphan.mkdir()
    (orphan / "leftover").write_text("x")

    P.new_release(root, "zeekr", ws(tmp_path))

    assert not orphan.exists()


def test_prune_keep_zero_protects_only_current_and_preview(tmp_path):
    root = tmp_path / "sites"
    pubs = [P.new_release(root, "zeekr", ws(tmp_path, str(i))) for i in range(3)]
    prev = [P.new_release(root, "zeekr", ws(tmp_path, "p"), kind="preview") for _ in range(2)]
    P.switch(root, "zeekr", "current", pubs[0])    # la más vieja publish sigue protegida
    P.switch(root, "zeekr", "preview", prev[0])    # la más vieja preview sigue protegida

    removed = P.prune(root, "zeekr", keep=0, keep_preview=0)

    assert pubs[0].exists() and prev[0].exists()
    assert not pubs[1].exists() and not pubs[2].exists()
    assert not prev[1].exists()
    assert len(removed) == 3


def test_target_none_for_broken_symlink_and_new_release_without_link_dest(tmp_path):
    root = tmp_path / "sites"
    r1 = P.new_release(root, "zeekr", ws(tmp_path))
    P.switch(root, "zeekr", "current", r1)
    shutil.rmtree(r1)                              # current queda apuntando a una release borrada

    assert P.target(root / "zeekr" / "current") is None

    r2 = P.new_release(root, "zeekr", ws(tmp_path, "v2"))   # no debe fallar ni pasar --link-dest a un path inexistente
    assert (r2 / "index.html").read_text() == "v2"


def test_new_release_with_empty_workspace(tmp_path):
    root = tmp_path / "sites"
    empty_ws = tmp_path / "empty_ws"
    empty_ws.mkdir()

    r = P.new_release(root, "zeekr", empty_ws)

    assert r.is_dir()
    assert list(r.iterdir()) == []
    assert r in P.releases(root, "zeekr")
