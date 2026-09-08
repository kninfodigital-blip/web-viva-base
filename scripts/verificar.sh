#!/usr/bin/env bash
# Batería de producción (tras cada deploy): cabeceras, negociación Markdown, robots, sitemap, ARD, security.txt, fuentes, redirección de barra.
# Uso: bash scripts/verificar.sh dominio.com
set -u; D="${1:?dominio sin https}"; ok=0; ko=0
chk(){ if eval "$2" >/dev/null 2>&1; then echo "OK    $1"; ok=$((ok+1)); else echo "FALLO $1"; ko=$((ko+1)); fi; }
chk "/ responde 200 text/html"                 "curl -sI https://$D/ | grep -qi 'content-type: text/html'"
chk "/ lleva cabecera Link (describedby/alternate/ard)" "curl -sI https://$D/ | grep -i '^link:' | grep -q describedby"
chk "/ con Accept: text/markdown devuelve Markdown"    "curl -s -o /dev/null -D - -H 'Accept: text/markdown' https://$D/ | grep -qi 'content-type: text/markdown'"
chk "/servicios con Accept: text/markdown → .md"       "curl -s -o /dev/null -D - -H 'Accept: text/markdown' https://$D/servicios | grep -qi 'content-type: text/markdown'"
chk "/servicios/ redirige 308 a /servicios"            "curl -sI https://$D/servicios/ | grep -qE 'HTTP/[0-9.]+ 308'"
chk "/index.md text/markdown + CORS"                   "curl -sI https://$D/index.md | grep -qi 'access-control-allow-origin: \*'"
chk "robots.txt text/plain con Content-Signal y Sitemap" "curl -s https://$D/robots.txt | grep -q '^Content-Signal' && curl -s https://$D/robots.txt | grep -q '^Sitemap:'"
chk "sitemap.xml 200"                                  "curl -sI https://$D/sitemap.xml | grep -qE 'HTTP/[0-9.]+ 200'"
chk "llms.txt text/markdown"                           "curl -sI https://$D/llms.txt | grep -qi 'content-type: text/markdown'"
chk "ard.json y ai-catalog.json idénticos"             "diff <(curl -s https://$D/.well-known/ard.json) <(curl -s https://$D/.well-known/ai-catalog.json)"
chk "security.txt 200"                                 "curl -sI https://$D/.well-known/security.txt | grep -qE 'HTTP/[0-9.]+ 200'"
chk "fuentes con caché inmutable"                      "curl -sI https://$D/assets/fonts/inter-var.woff2 | grep -qi 'immutable'"
chk "enlaces de llms.txt responden (200; externos 2xx/3xx)" "! curl -s https://$D/llms.txt | grep -o 'https://[^) ]*' | sed 's/[.,;]$//' | sort -u | while read u; do c=\$(curl -s -o /dev/null -m 20 -w '%{http_code}' \"\$u\"); case \"\$u\" in https://$D/*) [ \"\$c\" = 200 ] || echo \"\$c \$u\";; *) [ \"\${c:0:1}\" = 2 ] || [ \"\${c:0:1}\" = 3 ] || echo \"\$c \$u\";; esac; done | grep -q ."
echo "== $ok OK · $ko FALLO =="; [ "$ko" -eq 0 ]
