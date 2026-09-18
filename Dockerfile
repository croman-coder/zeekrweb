FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY . /usr/share/nginx/html

# Fuentes del generador y snapshots no se sirven
RUN rm -f /usr/share/nginx/html/build_site.py /usr/share/nginx/html/Dockerfile /usr/share/nginx/html/nginx.conf \
    /usr/share/nginx/html/.dockerignore /usr/share/nginx/html/_headers /usr/share/nginx/html/_redirects \
    && rm -rf /usr/share/nginx/html/.git /usr/share/nginx/html/.claude /usr/share/nginx/html/www_zeekrlife_com*.html \
    /usr/share/nginx/html/api /usr/share/nginx/html/functions

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --spider -q http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
