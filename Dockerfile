FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf

# El sitio sale del volumen zeekr_sites (/srv/sites/zeekr/current, lo que publica el panel). Esta copia del
# repo queda en la imagen como red de seguridad: nginx la usa para los estáticos que no estén en la release
# (URLs viejas de imágenes) y entera si no hay ninguna publicación. Ver nginx.conf.
COPY . /usr/share/nginx/html

# Fuentes del generador, del builder y del panel, snapshots y el docker-compose.yaml que Coolify escribe en el
# directorio de build: no se sirven (nginx además los bloquea por nombre)
RUN rm -f /usr/share/nginx/html/build_site.py /usr/share/nginx/html/Dockerfile /usr/share/nginx/html/nginx.conf \
    /usr/share/nginx/html/.dockerignore /usr/share/nginx/html/.gitignore /usr/share/nginx/html/_headers /usr/share/nginx/html/_redirects \
    /usr/share/nginx/html/docker-compose*.yaml /usr/share/nginx/html/docker-compose*.yml \
    && rm -rf /usr/share/nginx/html/.git /usr/share/nginx/html/.claude /usr/share/nginx/html/www_zeekrlife_com*.html \
    /usr/share/nginx/html/api /usr/share/nginx/html/functions \
    /usr/share/nginx/html/builder /usr/share/nginx/html/cms /usr/share/nginx/html/scripts /usr/share/nginx/html/content

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --spider -q http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
