# builder/Dockerfile — contexto de build: raíz del repo (necesita build_site.py, css, js, fonts, images)
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends rsync && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY builder/requirements.txt builder/requirements.txt
RUN pip install --no-cache-dir -r builder/requirements.txt
COPY builder builder
COPY build_site.py i18n.py site/
COPY css site/css
COPY js site/js
COPY fonts site/fonts
COPY images site/images
ENV REPO_DIR=/app/site SITES_ROOT=/srv/sites PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1
CMD ["uvicorn", "builder.app:app", "--host", "0.0.0.0", "--port", "8000"]
