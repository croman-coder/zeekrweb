# builder/publish.py — releases inmutables + symlinks atómicos (current / preview), rollback y limpieza.
import os
import shutil
import subprocess
import time
from pathlib import Path

EXCLUDE = ("build_site.py", "i18n.py", "content.json", "__pycache__", "i18n_missing_*.txt", "*.part")


def site_dir(root, slug):
    p = Path(root) / slug
    (p / "releases").mkdir(parents=True, exist_ok=True)
    return p


def target(link):
    link = Path(link)
    return Path(os.path.realpath(link)) if link.is_symlink() and link.exists() else None


def releases(root, slug, kind="publish"):
    rel = site_dir(root, slug) / "releases"
    return sorted(p.resolve() for p in rel.iterdir() if p.is_dir() and p.name.endswith("-preview") == (kind == "preview"))


def new_release(root, slug, workspace, kind="publish"):
    """Copia el workspace a releases/<ts>[-preview] con rsync; los archivos sin cambios se hardlinkean a `current`."""
    site = site_dir(root, slug)
    suffix = "-preview" if kind == "preview" else ""
    dest = site / "releases" / (time.strftime("%Y%m%d-%H%M%S") + suffix)
    while dest.exists():                       # dos builds en el mismo segundo: esperar al siguiente
        time.sleep(0.25)
        dest = site / "releases" / (time.strftime("%Y%m%d-%H%M%S") + suffix)
    # -c: compara por contenido (no por mtime/tamaño) para que un archivo regenerado igual se hardlinkee y uno distinto nunca se confunda
    cmd = ["rsync", "-a", "-c", "--delete", *[f"--exclude={e}" for e in EXCLUDE]]
    base = target(site / "current")
    if base:
        cmd.append(f"--link-dest={base}")
    cmd += [f"{Path(workspace)}/", f"{dest}/"]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return dest.resolve()


def switch(root, slug, name, release):
    """Repunta el symlink <name> (current|preview) de forma atómica (rename)."""
    link = site_dir(root, slug) / name
    tmp = link.with_name(f".{name}.tmp")
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    os.symlink(Path(release).resolve(), tmp)
    os.replace(tmp, link)
    return link


def previous_release(root, slug):
    cur = target(site_dir(root, slug) / "current")
    rel = releases(root, slug)
    if cur is None or cur not in rel:
        return None
    i = rel.index(cur)
    return rel[i - 1] if i > 0 else None


def prune(root, slug, keep=10, keep_preview=2):
    """Borra releases viejas (nunca las apuntadas por current/preview). Devuelve las borradas."""
    site = site_dir(root, slug)
    protected = {t for t in (target(site / "current"), target(site / "preview")) if t}
    removed = []
    for kind, n in (("publish", keep), ("preview", keep_preview)):
        old = releases(root, slug, kind)[:-n] if n > 0 else releases(root, slug, kind)
        for p in old:
            if p not in protected:
                shutil.rmtree(p)
                removed.append(p)
    return removed
