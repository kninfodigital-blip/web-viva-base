# Web Viva Base

Plantilla («starter») de la que nace cada web de cliente del servicio **Web Viva** de Knowin: 5 páginas tipo (Inicio · Servicios · Sobre nosotros · Zona · Contacto), legales del cliente, formulario al email del cliente, CTA de WhatsApp fija, i18n es/ca activable, y de serie **Lighthouse 100/100/100/100** (móvil y escritorio) y la capa «agent-ready» de contenido (robots con política de bots de IA y Content-Signal, llms.txt, Markdown por página con negociación `Accept`, JSON-LD LocalBusiness/Service/FAQPage, ARD, security.txt, sitemap con hreflang).

**Stack**: HTML estático generado por `scripts/build.py` (Python, sin dependencias) + Vercel (`vercel.json` en formato `routes`) + una función serverless (`api/send-email.js`, nodemailer) para el formulario. El mismo stack que metodoconstruccions.com, con un generador para que producir una web sea rellenar `config.json` y los textos, no perseguir notas.

- Empezar: [docs/DE-CERO-A-PREVIEW.md](docs/DE-CERO-A-PREVIEW.md)
- Analítica y consentimiento (apagado de serie): [docs/ANALITICA.md](docs/ANALITICA.md)
- Fuente de verdad técnica: las skills de `Proyectos Webs/skills generales/PLAYBOOK-seo-geo-agent-ready`

## Estructura

```
config.json            ← ÚNICO archivo de configuración (negocio, contacto, zona, idiomas, colores, servicios, legal, analítica)
contenido/es/*.json    ← una página por archivo (borrar = quitar página; duplicar = página nueva)
contenido/ca/*.json    ← mismos slugs en cada idioma activo
legales/<idioma>/*.md  ← plantillas legales del CLIENTE con {{placeholders}} de config.legal
assets/fonts, assets/img
scripts/build.py       ← genera dist/ y vercel.json
scripts/medir.sh · scripts/verificar.sh · scripts/lh-resumen.py
api/send-email.js      ← formulario → Gmail del cliente (variables de entorno en Vercel)
docs/
```

## Comandos

```bash
python3 scripts/build.py                 # genera dist/
npx --yes serve -l 4174 dist             # preview local
vercel deploy --prod --yes               # deploy (Vercel ejecuta el build)
bash scripts/medir.sh https://dominio/   # Lighthouse móvil/escritorio/agéntica
bash scripts/verificar.sh dominio        # batería de producción
```

Demo (negocio ficticio, datos de ejemplo): https://web-viva-base.vercel.app
