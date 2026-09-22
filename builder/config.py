# builder/config.py — configuración por variables de entorno
import os
from dataclasses import dataclass, field


def _env(name, default=""):
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    directus_url: str = field(default_factory=lambda: _env("DIRECTUS_URL", "http://directus:8055"))
    directus_token: str = field(default_factory=lambda: _env("DIRECTUS_TOKEN"))
    builder_token: str = field(default_factory=lambda: _env("BUILDER_TOKEN"))
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    sites_root: str = field(default_factory=lambda: _env("SITES_ROOT", "/srv/sites"))
    repo_dir: str = field(default_factory=lambda: _env("REPO_DIR", "/app/site"))
    keep_releases: int = field(default_factory=lambda: int(_env("KEEP_RELEASES", "10")))
