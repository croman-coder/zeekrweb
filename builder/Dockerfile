# builder/Dockerfile — contexto de build: raíz del repo (necesita build_site.py, css, js, fonts, images)
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends rsync && rm -rf /var/lib/apt/lists/*
# Corre sin root. Solo /srv/sites necesita ser escribible: /app se lee nomás, así que queda de root
# (chownearlo duplicaría los 85 MB de assets en otra capa). Un volumen nombrado hereda estos permisos al
# montarse; si en su lugar se usa un bind mount, la carpeta del host tiene que ser de este uid (10001).
RUN useradd --system --uid 10001 --create-home builder && mkdir -p /srv/sites && chown builder:builder /srv/sites
WORKDIR /app
COPY builder/requirements.txt builder/requirements.txt
RUN pip install --no-cache-dir -r builder/requirements.txt
COPY builder/*.py builder/
COPY build_site.py i18n.py site/
COPY css site/css
COPY js site/js
COPY fonts site/fonts
COPY images site/images
ENV REPO_DIR=/app/site SITES_ROOT=/srv/sites PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER builder
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1
CMD ["uvicorn", "builder.app:app", "--host", "0.0.0.0", "--port", "8000"]
