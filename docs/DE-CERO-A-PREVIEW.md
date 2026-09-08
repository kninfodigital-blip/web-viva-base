# De cero a preview en 15 minutos

Requisitos en el Mac: Python 3 (viene con macOS), Node 18+ (`node -v`), Vercel CLI autenticado (`vercel whoami`), git.

## Pasos

1. **Clona la plantilla** (o «Use this template» en GitHub) en una carpeta con el nombre del cliente, en minúsculas y sin espacios: será el nombre del proyecto en Vercel.
   ```bash
   git clone https://github.com/kninfodigital-blip/web-viva-base.git web-cliente && cd web-cliente && rm -rf .git && git init
   ```
2. **Edita `config.json`** (único archivo de configuración): dominio del cliente (sin https), nombre, razón social, NIF, dirección, teléfono, WhatsApp, horario, zona y localidades, idiomas activos (`["es"]` o `["es","ca"]`), colores, servicios, imágenes, datos legales. Pon `"demo": false`.
3. **Textos**: sustituye el lorem de `contenido/es/*.json` (y `contenido/ca/` si el catalán está activo). Cada archivo es una página; para quitar una página borra su archivo (en TODOS los idiomas activos); para añadir otra, duplica uno y cambia `slug`, `orden` y `nav`. Tipos de sección disponibles: `hero`, `cabecera`, `cifras`, `servicios`, `servicios_detalle`, `pasos`, `testimonios`, `faq`, `cta`, `texto`, `valores`, `equipo`, `zona`, `proyectos`, `contacto`.
4. **Imágenes**: logo SVG en `assets/img/logo.svg` (160×40), imagen OG 1200×630 en `assets/img/og.png`, y fotos en WebP ≤ 100 KB (`cwebp -q 78 -resize 1200 0 foto.jpg -o assets/img/foto.webp`) con `width`/`height` reales en el JSON de la página.
5. **Genera y mira en local**:
   ```bash
   python3 scripts/build.py          # falla con mensaje claro si los colores no cumplen contraste AA o faltan páginas en un idioma
   npx --yes serve -l 4174 dist      # http://localhost:4174
   ```
6. **Formulario → email del cliente**: en Vercel (tras el primer deploy) `Settings → Environment Variables`: `GMAIL_USER`, `GMAIL_APP_PASS` (contraseña de aplicación de Google, ver skill `formulario-web-a-gmail`), `TO_EMAIL` (opcional), `SUBJECT_PREFIX` (opcional). Sin ellas el formulario devuelve 503 y la web muestra el mensaje de error con WhatsApp como alternativa.
7. **Preview en Vercel**: `vercel deploy --yes` (preview) o `vercel deploy --prod --yes` (producción del proyecto). Vercel ejecuta `python3 scripts/build.py` y publica `dist/`. Mientras el `dominio` de `config.json` no sea `*.vercel.app`, todas las URLs `*.vercel.app` llevan `X-Robots-Tag: noindex` automáticamente: la preview no se indexa.
8. **Verifica en producción**: `bash scripts/verificar.sh <preview>.vercel.app` (cabeceras, negociación Markdown, robots, sitemap, ARD) y `bash scripts/medir.sh https://<preview>.vercel.app/ preview` (Lighthouse móvil/escritorio/agéntica). Objetivo: 100×4 (garantía del contrato: ≥ 90).
9. **Publicar en el dominio del cliente**: añade el dominio en Vercel (Settings → Domains), apunta el DNS y vuelve a desplegar. El `noindex` desaparece solo en el dominio del cliente. Opcional: TXT `_catalog._agents` = `url=https://<dominio>/.well-known/ard.json`.
10. **Cierre**: test de agentes en https://isitagentready.com/<dominio>?profile=content (nivel máximo del perfil de contenido), guarda `medicion/` en `05_Evidencias` del cliente, y git commit.

## Checklist antes de entregar

- [ ] `config.json` sin datos de la demo (nombre, NIF, dirección, teléfonos, email, `demo: false`)
- [ ] Textos reales en todas las páginas y en todos los idiomas activos; sin «lorem» (`grep -ri lorem contenido`)
- [ ] Legales revisadas por el cliente (titular, NIF, domicilio, email): `legales/<idioma>/*.md` se rellenan solos desde `config.legal`
- [ ] Logo, OG e imágenes propias del cliente (≤ 100 KB cada una, con `width`/`height`)
- [ ] `python3 scripts/build.py` sin avisos de contraste
- [ ] Variables del formulario en Vercel y prueba de envío real (llega al email del cliente)
- [ ] Lighthouse móvil ≥ 90 ×4 en portada, servicios y contacto (`scripts/medir.sh`)
- [ ] `scripts/verificar.sh` sin FALLO en la URL final
- [ ] Sin analítica de terceros salvo petición expresa (ver `docs/ANALITICA.md`)
- [ ] Dominio del cliente en Vercel, canonical y sitemap apuntando a él, `noindex` desaparecido
