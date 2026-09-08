# Analítica y consentimiento (apagado de serie)

**De serie la web no carga ningún script de terceros**: sin píxel, sin Google Analytics, sin mapas embebidos. Por eso no hay banner de cookies (no hace falta), la página de cookies no se genera y Lighthouse no encuentra terceros. Es la configuración recomendada para un negocio local: menos fricción y más nota.

## Si un cliente pide píxel de Meta o GA4

1. En `config.json` → `"analitica": { "activa": true, "proveedor": "meta" | "ga4", "id": "<ID>" }`.
2. Ejecuta `python3 scripts/build.py`: aparece la página `/cookies` (parametrizada con el proveedor), el enlace en el pie y el texto de la política de privacidad cambia.
3. **Consent-first (obligatorio en la UE)**: el script del proveedor solo se carga tras pulsar «Aceptar». El hueco está preparado en `scripts/build.py` → función `footer()`: añade el banner de `../skills generales/PLAYBOOK-seo-geo-agent-ready/seo-rendimiento-web/plantillas/banner-consentimiento.html` (position:fixed + `hidden`, dos botones de igual peso, carga del tercero solo en `cargarTerceros()`). Sustituye `{{DOMINIO_TERCERO}}`/`{{ID_PIXEL}}` por los del proveedor.
4. Re-mide (`bash scripts/medir.sh`): Lighthouse mide el camino SIN consentimiento, así que la nota no debe cambiar; comprueba en la pestaña Red que sin aceptar no sale ninguna petición al proveedor.

Hasta que se haga el paso 3, `analitica.activa: true` solo cambia los textos legales: no se carga nada. Nunca pongas el script del proveedor en el `<head>`.
