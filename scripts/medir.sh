#!/usr/bin/env bash
# Mide con Lighthouse 13 (móvil + escritorio + navegación agéntica) y deja los JSON en medicion/<fecha>/.
# Uso: bash scripts/medir.sh https://dominio.com/ [etiqueta]        (en local: bash scripts/medir.sh http://localhost:4174/ local)
set -euo pipefail
URL="${1:?URL, p. ej. https://dominio.com/}"; TAG="${2:-$(date +%F)}"; OUT="medicion/$TAG"; mkdir -p "$OUT"
CATS="performance,accessibility,best-practices,seo"
for P in "" servicios contacto; do
  npx --yes lighthouse@13.4.1 "${URL%/}/$P" --only-categories="$CATS" --output=json --output-path="$OUT/movil-${P:-inicio}.json" --chrome-flags="--headless=new" --quiet
done
npx --yes lighthouse@13.4.1 "$URL" --preset=desktop --only-categories="$CATS" --output=json --output-path="$OUT/desktop-inicio.json" --chrome-flags="--headless=new" --quiet
npx --yes lighthouse@13.4.1 "$URL" --only-categories=agentic-browsing --output=json --output-path="$OUT/agentic-inicio.json" --chrome-flags="--headless=new" --quiet
python3 scripts/lh-resumen.py "$OUT"/*.json
