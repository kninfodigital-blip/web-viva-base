#!/usr/bin/env python3
"""Web Viva Base — generador estático (solo biblioteca estándar, Python ≥ 3.9).

Fuente única: config.json (datos del negocio) + contenido/<idioma>/*.json (textos por página) + legales/<idioma>/*.md.
Genera en dist/: HTML de cada página (limpio, CSS inline, fuentes auto-alojadas), su .md para agentes, legales,
robots.txt, sitemap.xml, llms.txt, .well-known/{ard.json, ai-catalog.json, security.txt}, JSON-LD por página,
y reescribe vercel.json (routes: barra final, negociación Accept: text/markdown, cabeceras, noindex en previews).
Uso: python3 scripts/build.py   (falla con mensaje claro si la config no cumple contraste AA o faltan datos).
"""
import datetime, html, json, pathlib, re, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
CFG = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
UI = json.loads((ROOT / 'scripts' / 'ui.json').read_text(encoding='utf-8'))
DOM = CFG['dominio'].strip().lower()
BASE = 'https://' + DOM
IDIOMAS = CFG['idiomas']['activos']
DEF = CFG['idiomas']['defecto']
HOY = CFG.get('legal', {}).get('fecha_actualizacion') or datetime.date.today().isoformat()
NEG = CFG['negocio']; CON = CFG['contacto']; COL = CFG['colores']
E = html.escape
LOCALE = {'es': 'es_ES', 'ca': 'ca_ES', 'en': 'en_GB', 'fr': 'fr_FR'}

def t(v, lang):
    """Texto localizado: str o {es:..., ca:...}."""
    if isinstance(v, dict):
        return v.get(lang) or v.get(DEF) or next(iter(v.values()), '')
    return v or ''

def fail(msg):
    print('ERROR: ' + msg); sys.exit(1)

# ----------------------------------------------------------------------------- contraste AA (skill seo-rendimiento-web §3.1)
def lum(hexc):
    h = hexc.lstrip('#'); r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def ratio(fg, bg):
    a, b = lum(fg), lum(bg); return (max(a, b) + 0.05) / (min(a, b) + 0.05)

def comprobar_colores():
    pares = [('texto', 'fondo', 4.5), ('texto', 'fondo_alterno', 4.5), ('texto_suave', 'fondo', 4.5), ('texto_suave', 'fondo_alterno', 4.5),
             ('primario', 'fondo', 4.5), ('primario', 'fondo_alterno', 4.5), ('sobre_primario', 'primario', 4.5), ('sobre_primario', 'primario_oscuro', 4.5)]
    malos = [(a, b, round(ratio(COL[a], COL[b]), 2)) for a, b, u in pares if ratio(COL[a], COL[b]) < u]
    if malos:
        fail('contraste insuficiente (WCAG AA exige 4.5:1): ' + ', '.join(f'{a} sobre {b} = {r}:1' for a, b, r in malos) + '. Ajusta config.json → colores.')
    if ratio(COL['acento'], COL['primario']) < 3:
        print('AVISO: el acento sobre el primario no llega a 3:1; úsalo solo decorativo (no para texto pequeño).')

# ----------------------------------------------------------------------------- utilidades
def url(lang, slug):
    p = ('/' if lang == DEF else f'/{lang}/') + (slug or '')
    return p.rstrip('/') or '/'

def abs_url(lang, slug): return BASE + url(lang, slug)
def digits(tel): return re.sub(r'\D', '', tel or '')
def wa_url(lang):
    txt = t(CON.get('whatsapp_texto', ''), lang)
    from urllib.parse import quote
    return f"https://wa.me/{digits(CON['whatsapp'])}" + (f"?text={quote(txt)}" if txt else '')

def cargar_paginas(lang):
    d = ROOT / 'contenido' / lang
    pags = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(d.glob('*.json'))]
    for p in pags:
        p.setdefault('slug', ''); p.setdefault('orden', 99)
        if not p.get('title') or not p.get('description'): fail(f'{lang}/{p.get("slug") or "inicio"}: faltan title o description')
    return sorted(pags, key=lambda p: p['orden'])

def md_from(md, lang):
    """Markdown mínimo → HTML (títulos, listas, párrafos, negrita, enlaces)."""
    out, lista = [], False
    for line in md.split('\n'):
        s = line.rstrip()
        if s.startswith('- '):
            if not lista: out.append('<ul>'); lista = True
            out.append('<li>' + inline(s[2:]) + '</li>'); continue
        if lista: out.append('</ul>'); lista = False
        if not s: continue
        m = re.match(r'^(#{1,6})\s+(.*)', s)
        if m:
            n = len(m.group(1)); out.append(f'<h{n}>{inline(m.group(2))}</h{n}>'); continue
        if s.startswith('> '): out.append('<p class="resumen">' + inline(s[2:]) + '</p>'); continue
        if s.startswith('Fuente: '): continue
        out.append('<p>' + inline(s) + '</p>')
    if lista: out.append('</ul>')
    return '\n'.join(out)

def inline(s):
    s = E(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
    return s

# ----------------------------------------------------------------------------- CSS (inline en <head>, ~9 KB)
UNICODE_LATIN = 'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD'
def css():
    c = COL
    return f"""
@font-face{{font-family:'Inter';font-style:normal;font-weight:400 600;font-display:swap;src:url('/assets/fonts/inter-var.woff2') format('woff2');unicode-range:{UNICODE_LATIN};}}
@font-face{{font-family:'Montserrat';font-style:normal;font-weight:700 800;font-display:swap;src:url('/assets/fonts/montserrat-var.woff2') format('woff2');unicode-range:{UNICODE_LATIN};}}
@font-face{{font-family:'Inter Fallback';font-style:normal;font-weight:400;src:local('Arial'),local('ArialMT'),local('Helvetica');size-adjust:107.1194%;ascent-override:90.4365%;descent-override:22.518%;line-gap-override:0%;}}
@font-face{{font-family:'Inter Fallback';font-style:normal;font-weight:500;src:local('Arial'),local('ArialMT'),local('Helvetica');size-adjust:108.2147%;ascent-override:89.5211%;descent-override:22.29%;line-gap-override:0%;}}
@font-face{{font-family:'Inter Fallback';font-style:normal;font-weight:600;src:local('Arial Bold'),local('Arial-BoldMT'),local('Helvetica Bold');size-adjust:101.5259%;ascent-override:95.419%;descent-override:23.7586%;line-gap-override:0%;}}
@font-face{{font-family:'Montserrat Fallback';font-style:normal;font-weight:700;src:local('Arial Bold'),local('Arial-BoldMT'),local('Helvetica Bold');size-adjust:110.4212%;ascent-override:87.6644%;descent-override:22.7312%;line-gap-override:0%;}}
@font-face{{font-family:'Montserrat Fallback';font-style:normal;font-weight:800;src:local('Arial Bold'),local('Arial-BoldMT'),local('Helvetica Bold');size-adjust:112.5046%;ascent-override:86.0409%;descent-override:22.3102%;line-gap-override:0%;}}
:root{{--p:{c['primario']};--pd:{c['primario_oscuro']};--a:{c['acento']};--f:{c['fondo']};--f2:{c['fondo_alterno']};--t:{c['texto']};--ts:{c['texto_suave']};--b:{c['borde']};--sp:{c['sobre_primario']};--r:14px;--max:1120px;}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
[hidden]{{display:none!important}}
html{{-webkit-text-size-adjust:100%;scroll-behavior:smooth}}
@media (prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}*{{transition:none!important;animation:none!important}}}}
body{{font-family:Inter,'Inter Fallback',sans-serif;font-size:17px;line-height:1.6;color:var(--t);background:var(--f)}}
h1,h2,h3{{font-family:Montserrat,'Montserrat Fallback',sans-serif;font-weight:800;line-height:1.15;letter-spacing:-.01em}}
h1{{font-size:clamp(1.9rem,4.6vw,3rem)}}h2{{font-size:clamp(1.5rem,3.2vw,2.1rem);margin-bottom:.6em}}h3{{font-size:1.15rem;font-weight:700;margin-bottom:.35em}}
p{{margin-bottom:1em}}a{{color:var(--p);text-underline-offset:3px}}a:hover{{color:var(--pd)}}
img,svg{{max-width:100%;height:auto;display:block}}
.wrap{{width:min(var(--max),100% - 2.5rem);margin-inline:auto}}
.skip{{position:absolute;left:-999px;top:8px;background:var(--pd);color:var(--sp);padding:.6rem 1rem;border-radius:8px;z-index:200}}.skip:focus{{left:8px}}
header.top{{position:sticky;top:0;z-index:100;background:var(--f);border-bottom:1px solid var(--b)}}
.nav{{display:flex;align-items:center;justify-content:space-between;gap:1rem;min-height:68px}}
.nav .logo{{display:flex;align-items:center;min-height:44px}}.nav .logo img{{height:36px;width:auto}}
.nav ul{{list-style:none;display:flex;gap:.25rem;align-items:center}}
.nav ul a{{display:inline-block;padding:.65rem .8rem;text-decoration:none;color:var(--t);font-weight:500;border-radius:8px;min-height:44px}}.nav ul a:hover,.nav ul a[aria-current]{{background:var(--f2);color:var(--pd)}}
.nav .cta{{background:var(--p);color:var(--sp)!important;font-weight:600}}.nav .cta:hover{{background:var(--pd)!important}}
.nav .lang{{font-size:.9rem;padding:.65rem .6rem}}
.menu-btn{{display:none;background:none;border:1px solid var(--b);border-radius:8px;padding:.55rem .8rem;font:inherit;font-weight:600;color:var(--t);min-height:44px;cursor:pointer}}
@media (max-width:820px){{.menu-btn{{display:inline-block}}.nav ul{{display:none;position:absolute;left:0;right:0;top:100%;background:var(--f);border-bottom:1px solid var(--b);flex-direction:column;align-items:stretch;padding:.5rem 1.25rem 1rem}}.nav ul.open{{display:flex}}.nav ul a{{display:block}}}}
main{{display:block}}
section{{padding:clamp(3rem,7vw,5.5rem) 0}}section.alt{{background:var(--f2)}}
.hero{{padding:clamp(3.5rem,9vw,6.5rem) 0;background:linear-gradient(160deg,var(--f2),var(--f) 60%)}}
.hero h1{{max-width:22ch;margin-bottom:1rem}}.hero p{{max-width:60ch;font-size:1.15rem;color:var(--ts)}}
.btns{{display:flex;flex-wrap:wrap;gap:.75rem;margin-top:1.5rem}}
.btn{{display:inline-flex;align-items:center;justify-content:center;gap:.5rem;min-height:48px;padding:.8rem 1.4rem;border-radius:10px;font-weight:600;text-decoration:none;border:2px solid var(--p);background:var(--p);color:var(--sp);cursor:pointer;font:inherit;font-weight:600}}
.btn:hover{{background:var(--pd);border-color:var(--pd);color:var(--sp)}}.btn.sec{{background:transparent;color:var(--pd)}}.btn.sec:hover{{background:var(--f2)}}
.grid{{display:grid;gap:1.25rem}}.g2{{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}}.g3{{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}}
.card{{background:var(--f);border:1px solid var(--b);border-radius:var(--r);padding:1.5rem}}section.alt .card{{background:var(--f)}}
.card a.mas{{font-weight:600;text-decoration:none}}.card a.mas:hover{{text-decoration:underline}}
.cifras{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem}}.cifra{{font-family:Montserrat,'Montserrat Fallback',sans-serif;font-size:2.2rem;font-weight:800;color:var(--pd);line-height:1}}.cifra+p{{margin:.4rem 0 0;color:var(--ts)}}
.pasos ol{{counter-reset:p;list-style:none;display:grid;gap:1.25rem;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}}.pasos li{{counter-increment:p;padding-left:3.2rem;position:relative}}.pasos li::before{{content:counter(p);position:absolute;left:0;top:0;width:2.4rem;height:2.4rem;border-radius:50%;background:var(--p);color:var(--sp);display:grid;place-items:center;font-weight:700}}
blockquote{{border-left:4px solid var(--a);padding:.25rem 0 .25rem 1rem;font-size:1.05rem}}blockquote footer{{color:var(--ts);font-size:.95rem;margin-top:.4rem}}
details{{border:1px solid var(--b);border-radius:10px;padding:.9rem 1.1rem;margin-bottom:.75rem;background:var(--f)}}summary{{cursor:pointer;font-weight:600;list-style:none;display:flex;justify-content:space-between;gap:1rem;min-height:28px}}summary::after{{content:'+';color:var(--pd);font-weight:700}}details[open] summary::after{{content:'–'}}details p{{margin:.75rem 0 0;color:var(--ts)}}
.cta-box{{background:var(--pd);color:var(--sp);border-radius:var(--r);padding:clamp(2rem,5vw,3.5rem);text-align:center}}.cta-box h2{{color:var(--sp)}}.cta-box p{{color:var(--sp);opacity:.92;max-width:60ch;margin-inline:auto}}.cta-box .btn{{background:var(--a);border-color:var(--a);color:var(--t)}}.cta-box .btn:hover{{filter:brightness(.95)}}
.serv h3 a{{text-decoration:none;color:var(--t)}}.serv ul{{margin:.75rem 0 0 1.1rem;color:var(--ts)}}
.chips{{display:flex;flex-wrap:wrap;gap:.5rem;list-style:none}}.chips li{{background:var(--f);border:1px solid var(--b);border-radius:999px;padding:.4rem .9rem;font-weight:500}}
.tag{{display:inline-block;font-size:.8rem;font-weight:600;color:var(--pd);background:var(--f2);border-radius:999px;padding:.2rem .7rem;margin-bottom:.6rem}}
.cont{{display:grid;gap:2rem;grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}}.cont dl{{display:grid;grid-template-columns:auto 1fr;gap:.5rem 1rem}}.cont dt{{font-weight:600}}.cont dd{{color:var(--ts)}}
form .campo{{display:grid;gap:.35rem;margin-bottom:1rem}}form label{{font-weight:600}}form input,form textarea{{font:inherit;padding:.75rem .9rem;border:1px solid var(--b);border-radius:8px;background:#fff;color:var(--t);width:100%;min-height:48px}}form textarea{{min-height:130px;resize:vertical}}form input:focus,form textarea:focus{{outline:3px solid var(--a);outline-offset:1px}}
.check{{display:flex;gap:.6rem;align-items:flex-start;font-weight:400}}.check input{{width:20px;min-height:20px;margin-top:.3rem}}
.msg{{padding:.9rem 1rem;border-radius:8px;margin-top:1rem;font-weight:500}}.msg.ok{{background:#E6F4EA;color:#0B4F2E;border:1px solid #9CD3B0}}.msg.err{{background:#FDECEA;color:#7A1E15;border:1px solid #F1A8A0}}
.hp{{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}}
footer.pie{{background:var(--pd);color:var(--sp);padding:3rem 0 2rem;font-size:.95rem}}footer.pie a{{color:var(--sp)}}footer.pie .cols{{display:grid;gap:1.5rem;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}}footer.pie ul{{list-style:none}}footer.pie li{{margin-bottom:.4rem}}footer.pie .fin{{margin-top:2rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,.25);opacity:.9;font-size:.85rem}}
.wa{{position:fixed;right:16px;bottom:16px;z-index:90;display:flex;align-items:center;gap:.55rem;background:#25D366;color:#0B1F14;font-weight:700;text-decoration:none;padding:.8rem 1.1rem;border-radius:999px;box-shadow:0 10px 30px rgba(0,0,0,.25);min-height:52px}}.wa:hover{{background:#1FB958;color:#0B1F14}}.wa svg{{width:24px;height:24px}}
@media (max-width:600px){{.wa span{{display:none}}.wa{{padding:.9rem}}}}
.legal-page{{max-width:76ch}}.legal-page h2{{font-size:1.3rem;margin-top:1.8rem}}.legal-page ul{{margin:0 0 1em 1.2rem}}.resumen{{color:var(--ts);font-size:1.05rem}}
.demo-badge{{background:var(--a);color:var(--t);text-align:center;font-size:.85rem;font-weight:600;padding:.45rem .75rem}}
.equipo .card p.rol{{color:var(--ts);font-weight:500;margin-bottom:.4rem}}
"""

WA_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.4.1-.2 0-.3 0-.5l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.8 12 12 0 0 0 4.6 4c1.7.7 2 .6 2.8.5a2.4 2.4 0 0 0 1.6-1.1c.2-.6.2-1 .1-1.1l-.5-.3z"/></svg>'

# ----------------------------------------------------------------------------- JSON-LD
def jsonld(lang, page, paginas):
    org_id = BASE + '/#negocio'
    horas = [{'@type': 'OpeningHoursSpecification', 'dayOfWeek': h['dias'], 'opens': h['abre'], 'closes': h['cierra']} for h in CON.get('horario', [])]
    org = {'@type': ['LocalBusiness', NEG.get('tipo_schema', 'LocalBusiness')] if NEG.get('tipo_schema') not in (None, '', 'LocalBusiness') else 'LocalBusiness',
           '@id': org_id, 'name': NEG['nombre'], 'legalName': NEG.get('razon_social') or NEG['nombre'], 'url': BASE + '/', 'telephone': CON['telefono'], 'email': CON['email'],
           'description': t(NEG.get('descripcion_corta'), lang), 'image': BASE + CFG['imagenes'].get('og', ''), 'logo': BASE + CFG['imagenes'].get('logo', ''),
           'address': {'@type': 'PostalAddress', 'streetAddress': CON['direccion']['calle'], 'addressLocality': CON['direccion']['localidad'], 'addressRegion': CON['direccion'].get('region', ''), 'postalCode': CON['direccion']['cp'], 'addressCountry': CON['direccion']['pais']},
           'areaServed': [{'@type': 'City', 'name': l} for l in CFG['zona'].get('localidades', [])], 'inLanguage': lang}
    if CON.get('geo'): org['geo'] = {'@type': 'GeoCoordinates', 'latitude': CON['geo']['lat'], 'longitude': CON['geo']['lng']}
    if horas: org['openingHoursSpecification'] = horas
    redes = [v for v in CFG.get('redes', {}).values() if v]
    if redes: org['sameAs'] = redes
    if CON.get('google_maps'): org['hasMap'] = CON['google_maps']
    if NEG.get('nif'): org['vatID'] = NEG['nif']
    graph = [org, {'@type': 'WebSite', '@id': BASE + '/#website', 'url': BASE + '/', 'name': NEG['nombre'], 'inLanguage': lang, 'publisher': {'@id': org_id}},
             {'@type': 'WebPage', '@id': abs_url(lang, page['slug']) + '#webpage', 'url': abs_url(lang, page['slug']), 'name': page['title'], 'description': page['description'], 'inLanguage': lang, 'isPartOf': {'@id': BASE + '/#website'}, 'about': {'@id': org_id}}]
    tipos = {s['tipo'] for s in page['secciones']}
    if 'servicios' in tipos or 'servicios_detalle' in tipos:
        for s in CFG['servicios']:
            graph.append({'@type': 'Service', '@id': abs_url(lang, 'servicios') + '#' + s['id'], 'name': t(s['nombre'], lang), 'description': t(s['resumen'], lang), 'serviceType': t(s['nombre'], lang),
                          'provider': {'@id': org_id}, 'areaServed': [{'@type': 'City', 'name': l} for l in CFG['zona'].get('localidades', [])], 'url': abs_url(lang, 'servicios') + '#' + s['id']})
    for s in page['secciones']:
        if s['tipo'] == 'faq':
            graph.append({'@type': 'FAQPage', '@id': abs_url(lang, page['slug']) + '#faq', 'mainEntity': [{'@type': 'Question', 'name': q['p'], 'acceptedAnswer': {'@type': 'Answer', 'text': q['r']}} for q in s['items']]})
    if page['slug']:
        graph.append({'@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': 1, 'name': UI[lang].get('atras', 'Inicio').replace('Volver al inicio', 'Inicio').replace("Tornar a l'inici", 'Inici'), 'item': abs_url(lang, '')}, {'@type': 'ListItem', 'position': 2, 'name': page.get('nav') or page['title'], 'item': abs_url(lang, page['slug'])}]})
    return json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False).replace('<', '\\u003c')

# ----------------------------------------------------------------------------- secciones HTML + Markdown
def btn_wa(lang, texto, cls='btn'):
    if cls == 'wa':  # botón fijo: el texto se oculta en móvil, el nombre accesible va en aria-label
        return f'<a class="wa" href="{wa_url(lang)}" target="_blank" rel="noopener" aria-label="{E(texto)}">{WA_ICON}<span aria-hidden="true">{E(texto)}</span></a>'
    return f'<a class="{cls}" href="{wa_url(lang)}" target="_blank" rel="noopener">{E(texto)}</a>'

def sec_html(s, lang, page):
    u = UI[lang]; tipo = s['tipo']; H = []
    if tipo == 'hero':
        H.append(f'<section class="hero"><div class="wrap"><h1>{E(s["titulo"])}</h1><p>{E(s["texto"])}</p><div class="btns">{btn_wa(lang, s.get("boton") or u["cita"])}')
        if s.get('boton2'): H.append(f'<a class="btn sec" href="{url(lang, s.get("boton2_url", "/servicios").strip("/"))}">{E(s["boton2"])}</a>')
        H.append('</div></div></section>')
    elif tipo == 'cabecera':
        H.append(f'<section class="hero"><div class="wrap"><h1>{E(s["titulo"])}</h1><p>{E(s["texto"])}</p></div></section>')
    elif tipo == 'cifras':
        H.append('<section><div class="wrap cifras">' + ''.join(f'<div><div class="cifra">{E(i["cifra"])}</div><p>{E(i["texto"])}</p></div>' for i in s['items']) + '</div></section>')
    elif tipo == 'servicios':
        cards = ''.join(f'<article class="card serv"><h3><a href="{url(lang, "servicios")}#{sv["id"]}">{E(t(sv["nombre"], lang))}</a></h3><p>{E(t(sv["resumen"], lang))}</p><a class="mas" href="{url(lang, "servicios")}#{sv["id"]}">{E(u["leer_mas"])} {E(t(sv["nombre"], lang).lower())}</a></article>' for sv in CFG['servicios'])
        H.append(f'<section class="alt"><div class="wrap"><h2>{E(s["titulo"])}</h2>{"<p>" + E(s["texto"]) + "</p>" if s.get("texto") else ""}<div class="grid g2">{cards}</div></div></section>')
    elif tipo == 'servicios_detalle':
        det = s.get('detalle', {}); blocks = []
        for sv in CFG['servicios']:
            d = det.get(sv['id'], {}); pars = ''.join(f'<p>{E(p)}</p>' for p in d.get('parrafos', [E(t(sv['resumen'], lang))]))
            inc = ('<ul>' + ''.join(f'<li>{E(i)}</li>' for i in d.get('incluye', [])) + '</ul>') if d.get('incluye') else ''
            blocks.append(f'<article class="card serv" id="{sv["id"]}"><h2>{E(t(sv["nombre"], lang))}</h2>{pars}{inc}<div class="btns">{btn_wa(lang, u["cita"])}</div></article>')
        H.append('<section><div class="wrap grid g2">' + ''.join(blocks) + '</div></section>')
    elif tipo == 'pasos':
        H.append(f'<section class="pasos"><div class="wrap"><h2>{E(s["titulo"])}</h2><ol>' + ''.join(f'<li><h3>{E(i["titulo"])}</h3><p>{E(i["texto"])}</p></li>' for i in s['items']) + '</ol></div></section>')
    elif tipo == 'testimonios':
        H.append(f'<section class="alt"><div class="wrap"><h2>{E(s["titulo"])}</h2><div class="grid g2">' + ''.join(f'<blockquote class="card"><p>«{E(i["texto"])}»</p><footer>{E(i["autor"])}</footer></blockquote>' for i in s['items']) + '</div></div></section>')
    elif tipo == 'faq':
        H.append(f'<section><div class="wrap"><h2>{E(s["titulo"])}</h2>' + ''.join(f'<details><summary>{E(q["p"])}</summary><p>{E(q["r"])}</p></details>' for q in s['items']) + '</div></section>')
    elif tipo == 'cta':
        H.append(f'<section><div class="wrap"><div class="cta-box"><h2>{E(s["titulo"])}</h2><p>{E(s["texto"])}</p><div class="btns" style="justify-content:center">{btn_wa(lang, s.get("boton") or u["whatsapp"])}</div></div></div></section>')
    elif tipo == 'texto':
        H.append(f'<section><div class="wrap legal-page"><h2>{E(s["titulo"])}</h2>' + ''.join(f'<p>{E(p)}</p>' for p in s['parrafos']) + '</div></section>')
    elif tipo == 'valores':
        H.append(f'<section class="alt"><div class="wrap"><h2>{E(s["titulo"])}</h2><div class="grid g3">' + ''.join(f'<article class="card"><h3>{E(i["titulo"])}</h3><p>{E(i["texto"])}</p></article>' for i in s['items']) + '</div></div></section>')
    elif tipo == 'equipo':
        H.append(f'<section class="equipo"><div class="wrap"><h2>{E(s["titulo"])}</h2><div class="grid g3">' + ''.join(f'<article class="card"><h3>{E(i["nombre"])}</h3><p class="rol">{E(i["rol"])}</p><p>{E(i["texto"])}</p></article>' for i in s['items']) + '</div></div></section>')
    elif tipo == 'zona':
        H.append(f'<section><div class="wrap"><h2>{E(u["zona_titulo"])} {E(t(CFG["zona"]["nombre"], lang))}</h2><ul class="chips">' + ''.join(f'<li>{E(l)}</li>' for l in CFG['zona']['localidades']) + f'</ul><p style="margin-top:1.25rem"><a href="{E(CON["google_maps"])}" target="_blank" rel="noopener">{E(u["como_llegar"])}</a></p></div></section>')
    elif tipo == 'proyectos':
        cards = []
        for n, i in enumerate(s['items'], 1):
            img = i.get('imagen') or f'/assets/img/caso-{((n - 1) % 3) + 1}.svg'
            tag = ('<span class="tag">' + E(i['etiqueta']) + '</span>') if i.get('etiqueta') else ''
            cards.append(f'<article class="card"><img src="{E(img)}" width="640" height="400" loading="lazy" decoding="async" alt="{E(i.get("alt") or i["titulo"])}" style="border-radius:10px;margin-bottom:1rem">{tag}<h3>{E(i["titulo"])}</h3><p>{E(i["texto"])}</p></article>')
        H.append(f'<section class="alt"><div class="wrap"><h2>{E(s["titulo"])}</h2>{"<p>" + E(s["texto"]) + "</p>" if s.get("texto") else ""}<div class="grid g3">{"".join(cards)}</div></div></section>')
    elif tipo == 'contacto':
        priv = url(lang, 'privacidad')
        form = '' if not CFG.get('formulario', {}).get('activo', True) else f'''<form id="contacto" method="post" action="/api/send-email" novalidate>
<div class="campo"><label for="f-nombre">{E(u["form_nombre"])}</label><input id="f-nombre" name="nombre" type="text" autocomplete="name" required minlength="2" maxlength="120"></div>
<div class="campo"><label for="f-tel">{E(u["form_telefono"])}</label><input id="f-tel" name="telefono" type="tel" autocomplete="tel" required minlength="7" maxlength="40"></div>
<div class="campo"><label for="f-email">{E(u["form_email"])}</label><input id="f-email" name="email" type="email" autocomplete="email" maxlength="254"></div>
<div class="campo"><label for="f-msg">{E(u["form_mensaje"])}</label><textarea id="f-msg" name="mensaje" required minlength="5" maxlength="3000"></textarea></div>
<div class="hp" aria-hidden="true"><label for="f-web">Web</label><input id="f-web" name="web" type="text" tabindex="-1" autocomplete="off"></div>
<div class="campo"><label class="check"><input type="checkbox" name="privacidad" required> <span>{E(u["form_privacidad"])} (<a href="{priv}">{E(u["privacidad"]).lower()}</a>)</span></label></div>
<button class="btn" type="submit">{E(u["form_enviar"])}</button>
<p class="msg ok" id="f-ok" hidden>{E(u["form_ok"])}</p><p class="msg err" id="f-err" hidden>{E(u["form_error"])}</p><p class="msg err" id="f-falta" hidden>{E(u["form_falta"])}</p></form>'''
        H.append(f'''<section><div class="wrap cont"><div><h2>{E(u["contacto"])}</h2><dl>
<dt>{E(u["direccion"])}</dt><dd>{E(CON["direccion"]["calle"])}, {E(CON["direccion"]["cp"])} {E(CON["direccion"]["localidad"])}<br><a href="{E(CON["google_maps"])}" target="_blank" rel="noopener">{E(u["como_llegar"])}</a></dd>
<dt>{E(u["telefono"])}</dt><dd><a href="tel:{E(CON["telefono"])}">{E(CON.get("telefono_visible") or CON["telefono"])}</a></dd>
<dt>WhatsApp</dt><dd><a href="{wa_url(lang)}" target="_blank" rel="noopener">{E(u["whatsapp"])}</a></dd>
<dt>{E(u["email"])}</dt><dd><a href="mailto:{E(CON["email"])}">{E(CON["email"])}</a></dd>
<dt>{E(u["horario"])}</dt><dd>{E(t(CON.get("horario_visible", ""), lang))}</dd></dl></div><div>{form}</div></div></section>''')
    else:
        fail(f'tipo de sección desconocido: {tipo}')
    return ''.join(H)

def sec_md(s, lang, page):
    u = UI[lang]; tipo = s['tipo']; M = []
    if tipo in ('hero', 'cabecera'):
        M.append(f'## {s["titulo"]}\n\n{s["texto"]}\n\n- [{s.get("boton") or u["cita"]}]({wa_url(lang)})')
    elif tipo == 'cifras': M += [f'- **{i["cifra"]}** {i["texto"]}' for i in s['items']]
    elif tipo == 'servicios':
        M.append(f'## {s["titulo"]}\n\n{s.get("texto", "")}\n'); M += [f'- [{t(sv["nombre"], lang)}]({abs_url(lang, "servicios")}#{sv["id"]}): {t(sv["resumen"], lang)}' for sv in CFG['servicios']]
    elif tipo == 'servicios_detalle':
        for sv in CFG['servicios']:
            d = s.get('detalle', {}).get(sv['id'], {}); M.append(f'## {t(sv["nombre"], lang)}\n\n' + '\n\n'.join(d.get('parrafos', [t(sv['resumen'], lang)])))
            if d.get('incluye'): M.append('\n'.join(f'- {i}' for i in d['incluye']))
    elif tipo in ('pasos', 'valores', 'equipo'):
        M.append(f'## {s["titulo"]}\n'); M += [f'- **{i.get("titulo") or i.get("nombre")}**{(" · " + i["rol"]) if i.get("rol") else ""}: {i["texto"]}' for i in s['items']]
    elif tipo == 'testimonios': M.append(f'## {s["titulo"]}\n'); M += [f'> «{i["texto"]}» — {i["autor"]}\n' for i in s['items']]
    elif tipo == 'faq': M.append(f'## {s["titulo"]}\n'); M += [f'**{q["p"]}**\n\n{q["r"]}\n' for q in s['items']]
    elif tipo == 'cta': M.append(f'## {s["titulo"]}\n\n{s["texto"]}\n\n- [{s.get("boton") or u["whatsapp"]}]({wa_url(lang)})')
    elif tipo == 'texto': M.append(f'## {s["titulo"]}\n\n' + '\n\n'.join(s['parrafos']))
    elif tipo == 'zona': M.append(f'## {u["zona_titulo"]} {t(CFG["zona"]["nombre"], lang)}\n\n' + ', '.join(CFG['zona']['localidades']) + f'\n\n- [{u["como_llegar"]}]({CON["google_maps"]})')
    elif tipo == 'proyectos': M.append(f'## {s["titulo"]}\n\n{s.get("texto", "")}\n'); M += [f'- **{i["titulo"]}** ({i.get("etiqueta", "")}): {i["texto"]}' for i in s['items']]
    elif tipo == 'contacto':
        M.append(f'## {u["contacto"]}\n\n- {u["direccion"]}: {CON["direccion"]["calle"]}, {CON["direccion"]["cp"]} {CON["direccion"]["localidad"]} ([{u["como_llegar"]}]({CON["google_maps"]}))\n- {u["telefono"]}: {CON.get("telefono_visible") or CON["telefono"]} (tel:{CON["telefono"]})\n- WhatsApp: {wa_url(lang)}\n- {u["email"]}: {CON["email"]}\n- {u["horario"]}: {t(CON.get("horario_visible", ""), lang)}')
    return '\n\n'.join(M)

# ----------------------------------------------------------------------------- página completa
def head(lang, title, desc, canon_slug, alternates, ld, is_legal=False, noindex=False):
    hl = ''.join(f'<link rel="alternate" hreflang="{l}" href="{abs_url(l, sl)}">' for l, sl in alternates) + (f'<link rel="alternate" hreflang="x-default" href="{abs_url(DEF, canon_slug)}">' if len(alternates) > 1 else '')
    md_href = url(lang, canon_slug).rstrip('/') + ('/index.md' if not canon_slug else '.md')
    og = CFG['imagenes'].get('og')
    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
{'<meta name="robots" content="noindex, nofollow">' if noindex else ''}
<link rel="canonical" href="{abs_url(lang, canon_slug)}">
{hl}
<meta property="og:type" content="website"><meta property="og:site_name" content="{E(NEG['nombre'])}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{abs_url(lang, canon_slug)}"><meta property="og:locale" content="{LOCALE.get(lang, lang)}">
{f'<meta property="og:image" content="{BASE + og}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">' if og else ''}
<meta name="theme-color" content="{COL['primario']}">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="text/markdown" href="{md_href}">
<link rel="ard" type="application/json" href="/.well-known/ard.json"><link rel="ai-catalog" type="application/json" href="/.well-known/ai-catalog.json"><link rel="sitemap" type="application/xml" href="/sitemap.xml">
<link rel="preload" href="/assets/fonts/montserrat-var.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/assets/fonts/inter-var.woff2" as="font" type="font/woff2" crossorigin>
<style>{css()}</style>
<script type="application/ld+json">{ld}</script>
</head>'''

def nav(lang, paginas, actual_slug):
    u = UI[lang]
    items = ''.join('<li><a href="' + url(lang, p['slug']) + '"' + (' aria-current="page"' if p['slug'] == actual_slug else '') + '>' + E(p['nav']) + '</a></li>' for p in paginas if p.get('nav'))
    langs = ''.join(f'<li><a class="lang" lang="{l}" hreflang="{l}" href="{url(l, actual_slug)}" aria-label="{E(u["idioma"])}: {l.upper()}">{l.upper()}</a></li>' for l in IDIOMAS if l != lang)
    return f'''<a class="skip" href="#contenido">{E(u["ir_contenido"])}</a>
<header class="top"><nav class="nav wrap" aria-label="Principal"><a class="logo" href="{url(lang, "")}" aria-label="{E(NEG["nombre"])}"><img src="{E(CFG["imagenes"]["logo"])}" alt="{E(NEG["nombre"])}" width="160" height="40"></a>
<button class="menu-btn" type="button" aria-expanded="false" aria-controls="menu">{E(u["menu"])}</button>
<ul id="menu">{items}{langs}<li><a class="cta" href="{wa_url(lang)}" target="_blank" rel="noopener">{E(u["cita"])}</a></li></ul></nav></header>'''

def footer(lang, paginas):
    u = UI[lang]; d = CON['direccion']
    legales = ''.join(f'<li><a href="{url(lang, sl)}">{E(u[k])}</a></li>' for sl, k in [('aviso-legal', 'legal'), ('privacidad', 'privacidad')] + ([('cookies', 'cookies')] if CFG.get('analitica', {}).get('activa') else []))
    demo = f'<div class="demo-badge">{E(u["demo"])}</div>' if CFG.get('demo') else ''
    return f'''<footer class="pie"><div class="wrap cols"><div><strong>{E(NEG["nombre"])}</strong><p>{E(t(NEG.get("descripcion_corta"), lang))}</p></div>
<div><ul><li>{E(d["calle"])}<br>{E(d["cp"])} {E(d["localidad"])}</li><li><a href="tel:{E(CON["telefono"])}">{E(CON.get("telefono_visible") or CON["telefono"])}</a></li><li><a href="mailto:{E(CON["email"])}">{E(CON["email"])}</a></li><li>{E(t(CON.get("horario_visible", ""), lang))}</li></ul></div>
<div><ul>{''.join(f'<li><a href="{url(lang, p["slug"])}">{E(p["nav"])}</a></li>' for p in paginas if p.get("nav"))}{legales}</ul></div></div>
<div class="wrap fin">© {datetime.date.today().year} {E(NEG.get("razon_social") or NEG["nombre"])}{(" · NIF " + E(NEG["nif"])) if NEG.get("nif") else ""}</div></footer>{demo}
{btn_wa(lang, u["whatsapp"], "wa")}
<script>
(function(){{var b=document.querySelector('.menu-btn'),m=document.getElementById('menu');if(b&&m){{b.addEventListener('click',function(){{var o=m.classList.toggle('open');b.setAttribute('aria-expanded',o?'true':'false');b.textContent=o?{json.dumps(u["cerrar"])}:{json.dumps(u["menu"])};}});}}
var f=document.getElementById('contacto');if(!f)return;var ok=document.getElementById('f-ok'),er=document.getElementById('f-err'),fa=document.getElementById('f-falta'),bt=f.querySelector('button[type=submit]');
f.addEventListener('submit',function(e){{e.preventDefault();ok.hidden=er.hidden=fa.hidden=true;var d=Object.fromEntries(new FormData(f).entries());
var tel=(d.telefono||'').replace(/\\D/g,'');if(!d.nombre||d.nombre.trim().length<2||tel.length<7||!d.mensaje||d.mensaje.trim().length<5||!d.privacidad||(d.email&&!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]{{2,}}$/.test(d.email))){{fa.hidden=false;return;}}
d.pagina=location.pathname;bt.disabled=true;var txt=bt.textContent;bt.textContent={json.dumps(u["form_enviando"])};
fetch(f.action,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(d)}}).then(function(r){{return r.ok?r.json():Promise.reject(r)}}).then(function(){{f.reset();ok.hidden=false;}}).catch(function(){{er.hidden=false;}}).finally(function(){{bt.disabled=false;bt.textContent=txt;}});}});}})();
</script>'''

def render_page(lang, page, paginas, alternates):
    ld = jsonld(lang, page, paginas)
    body = ''.join(sec_html(s, lang, page) for s in page['secciones'])
    return head(lang, page['title'], page['description'], page['slug'], alternates, ld) + '\n<body>\n' + nav(lang, paginas, page['slug']) + f'\n<main id="contenido">{body}</main>\n' + footer(lang, paginas) + '\n</body>\n</html>\n'

def render_md(lang, page):
    resumen = page['description']
    cuerpo = '\n\n'.join(sec_md(s, lang, page) for s in page['secciones'])
    return f'# {page["title"]}\n\nFuente: {abs_url(lang, page["slug"])}\n\n> {resumen}\n\n{cuerpo}\n'

# ----------------------------------------------------------------------------- legales
def legales(lang, paginas, alternates_fn):
    L = CFG['legal']; out = []
    hoy_txt = HOY
    subst = {'DOMINIO': DOM, 'TITULAR': L['titular'], 'NIF': L['nif'], 'DOMICILIO': L['domicilio'], 'EMAIL': L['email'], 'HOSTING': L['hosting'], 'FECHA': hoy_txt, 'NEGOCIO': NEG['nombre'],
             'REGISTRO_LINEA': (f"- Datos registrales: {L['registro']}" if L.get('registro') else ''),
             'COOKIES_ANALITICA': ({'es': 'Con tu consentimiento (banner al entrar) cargamos herramientas de medición de ' + (CFG['analitica'].get('proveedor') or 'terceros') + '. Sin consentimiento no se carga ninguna.', 'ca': 'Amb el teu consentiment (avís en entrar) carreguem eines de mesura de ' + (CFG['analitica'].get('proveedor') or 'tercers') + '. Sense consentiment no se’n carrega cap.'}.get(lang, '')) if CFG.get('analitica', {}).get('activa') else {'es': 'Este sitio no utiliza cookies de análisis ni de publicidad.', 'ca': 'Aquest lloc no fa servir galetes d’anàlisi ni de publicitat.'}.get(lang, '')}
    archivos = ['aviso-legal', 'privacidad'] + (['cookies'] if CFG.get('analitica', {}).get('activa') else [])
    for slug in archivos:
        src = ROOT / 'legales' / lang / f'{slug}.md'
        if not src.exists(): src = ROOT / 'legales' / DEF / f'{slug}.md'
        md = src.read_text(encoding='utf-8')
        for k, v in subst.items(): md = md.replace('{{' + k + '}}', v)
        md = re.sub(r'\n\n\n+', '\n\n', md)
        titulo = re.search(r'^# (.*)$', md, re.M).group(1)
        desc = re.search(r'^> (.*)$', md, re.M).group(1)
        page = {'slug': slug, 'title': f'{titulo} · {NEG["nombre"]}', 'description': desc, 'secciones': [], 'nav': None}
        ld = jsonld(lang, page, paginas)
        body = md_from(re.sub(r'^# .*\n', '', md, count=1), lang)
        h = head(lang, page['title'], desc, slug, alternates_fn(slug), ld, is_legal=True) + '\n<body>\n' + nav(lang, paginas, slug) + f'\n<main id="contenido"><section><div class="wrap legal-page"><h1>{E(titulo)}</h1>{body}</div></section></main>\n' + footer(lang, paginas) + '\n</body>\n</html>\n'
        out.append((slug, page, h, md))
    return out

# ----------------------------------------------------------------------------- ficheros de agentes y hosting
def robots(paginas_por_idioma):
    gem = CFG.get('ia', {}).get('permitir_entrenamiento_gemini', True)
    grupo_gemini = ("# 2b) EXCEPCIÓN documentada (decisión del titular): Google-Extended puede citar esta web en Gemini a cambio de visibilidad\nUser-Agent: Google-Extended\nContent-Signal: ai-train=yes, search=yes, ai-input=yes\nDisallow: /api/\nAllow: /\n" if gem else '')
    bloq_extra = '' if gem else 'User-Agent: Google-Extended\n'
    return f"""# robots.txt — https://{DOM}
# {NEG['nombre']}. Política: ser ENCONTRADOS por buscadores y asistentes de IA (búsqueda y respuestas con cita: permitido);
# NO autorizamos el uso del contenido para entrenar modelos{', salvo Google-Extended (ver 2b)' if gem else ''}.
#
# As a condition of accessing this website, you agree to abide by the following content signals:
# (a) If a content-signal = yes, you may collect content for the corresponding use.
# (b) If a content-signal = no, you may not collect content for the corresponding use.
# (c) If the website operator does not include a content signal for a corresponding use, the website operator neither grants nor restricts permission via content signal with respect to the corresponding use.
# search: building a search index and providing search results. ai-input: inputting content into one or more AI models. ai-train: training or fine-tuning AI models.
# ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS OF RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE 2019/790 ON COPYRIGHT AND RELATED RIGHTS IN THE DIGITAL SINGLE MARKET.

# 1) Por defecto: todo abierto salvo endpoints internos
User-Agent: *
Content-Signal: ai-train=no, search=yes, ai-input=yes
Disallow: /api/
Allow: /

# 2) Buscadores y asistentes de IA (índice, citas, visitas a petición del usuario): PERMITIDOS
User-Agent: Googlebot
User-Agent: bingbot
User-Agent: Applebot
User-Agent: Amzn-SearchBot
User-Agent: OAI-SearchBot
User-Agent: ChatGPT-User
User-Agent: Claude-SearchBot
User-Agent: Claude-User
User-Agent: PerplexityBot
User-Agent: Perplexity-User
User-Agent: DuckAssistBot
User-Agent: MistralAI-Index
User-Agent: MistralAI-User
User-Agent: meta-webindexer
User-Agent: meta-externalfetcher
User-Agent: facebookexternalhit
Content-Signal: ai-train=no, search=yes, ai-input=yes
Disallow: /api/
Allow: /

{grupo_gemini}
# 3) Rastreadores de ENTRENAMIENTO: bloqueados
User-Agent: GPTBot
User-Agent: ClaudeBot
User-Agent: Applebot-Extended
User-Agent: CCBot
User-Agent: meta-externalagent
User-Agent: Bytespider
User-Agent: MistralAI-Training
{bloq_extra}Content-Signal: ai-train=no, search=yes, ai-input=yes
Disallow: /

Sitemap: {BASE}/sitemap.xml
# Catálogo ARD para agentes: {BASE}/.well-known/ard.json (sin directiva Agentmap: Lighthouse la considera inválida)
"""

def sitemap(entradas):
    """entradas: lista de (lang, slug, [(lang2, slug2)...])"""
    xs = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for lang, slug, alts in entradas:
        xs.append(f'<url><loc>{abs_url(lang, slug)}</loc><lastmod>{HOY}</lastmod>' + ''.join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{abs_url(l, s)}"/>' for l, s in alts) + '</url>')
    xs.append('</urlset>'); return '\n'.join(xs) + '\n'

def llms(paginas_por_idioma, legales_por_idioma):
    lang = DEF; u = UI[lang]; d = CON['direccion']
    servs = '; '.join(f'{t(s["nombre"], lang)} ({t(s["resumen"], lang)})' for s in CFG['servicios'])
    resumen = (f"{NEG['nombre']} — {t(NEG.get('descripcion_corta'), lang)} Servicios: {servs}. Zona: {t(CFG['zona']['nombre'], lang)} ({', '.join(CFG['zona']['localidades'])}). "
               f"Dirección: {d['calle']}, {d['cp']} {d['localidad']}. Teléfono {CON.get('telefono_visible') or CON['telefono']}, WhatsApp {wa_url(lang)}, email {CON['email']}. Horario: {t(CON.get('horario_visible', ''), lang)}.")
    L = [f'# {NEG["nombre"]}', '', f'> {resumen}', '', 'Notas para agentes:', '', f'- Idiomas del sitio: {", ".join(IDIOMAS)} (por defecto {DEF}).',
         '- Todas las páginas devuelven Markdown si se piden con `Accept: text/markdown` y también existen como `.md` en la misma ruta.',
         '- La cita y el contacto los hace siempre la persona (WhatsApp, teléfono o formulario); no hay reserva ni pago automáticos en esta web.', '']
    for lg in IDIOMAS:
        L.append(f'## Páginas ({lg})'); L.append('')
        for p in paginas_por_idioma[lg]:
            L.append(f'- [{p["nav"] or p["title"]}]({abs_url(lg, p["slug"]).rstrip("/") + ("/index.md" if not p["slug"] else ".md")}): {p["description"]}')
        for slug, page, _, _ in legales_por_idioma[lg]:
            L.append(f'- [{page["title"].split(" · ")[0]}]({abs_url(lg, slug)}.md)')
        L.append('')
    L += ['## Contactar', '', f'- WhatsApp: {wa_url(lang)}', f'- Teléfono: {CON["telefono"]}', f'- Email: {CON["email"]}', f'- Formulario: {abs_url(lang, "contacto")}', '',
          '## Optional', '', f'- [Catálogo ARD para agentes]({BASE}/.well-known/ard.json)', f'- [Sitemap]({BASE}/sitemap.xml)', f'- [security.txt]({BASE}/.well-known/security.txt)', '']
    return '\n'.join(L)

def ard(paginas_por_idioma):
    lang = DEF; ent = []
    def e(ident, nombre, tipo, u, desc, qs):
        return {'identifier': f'urn:air:{DOM}:{ident}', 'displayName': nombre, 'type': tipo, 'url': u, 'description': desc, 'tags': [NEG.get('sector', ''), CON['direccion']['localidad']], 'representativeQueries': qs, 'version': '1.0', 'updatedAt': HOY + 'T00:00:00Z'}
    ent.append(e('docs:llms-txt', f'{NEG["nombre"]} — llms.txt', 'text/markdown', BASE + '/llms.txt', f'Resumen de {NEG["nombre"]} ({NEG.get("sector", "")}, {CON["direccion"]["localidad"]}) e índice de páginas en Markdown.', [f'qué hace {NEG["nombre"]}', f'{NEG.get("sector", "")} en {CON["direccion"]["localidad"]}', f'horario y teléfono de {NEG["nombre"]}']))
    for p in paginas_por_idioma[lang]:
        ident = 'docs:' + (p['slug'] or 'portada')
        ent.append(e(ident, p['nav'] or p['title'], 'text/markdown', abs_url(lang, p['slug']).rstrip('/') + ('/index.md' if not p['slug'] else '.md'), p['description'], [f'{p["nav"] or "portada"} de {NEG["nombre"]}', p['description'][:80].rstrip('.')]))
    ent.append(e('action:whatsapp', 'Pedir cita por WhatsApp', 'text/html', wa_url(lang), 'Conversación de WhatsApp con el negocio para pedir cita o resolver dudas. La escribe siempre la persona.', [f'pedir cita en {NEG["nombre"]}', f'whatsapp de {NEG["nombre"]}']))
    return json.dumps({'specVersion': '1.0', 'host': {'displayName': NEG['nombre'], 'identifier': f'did:web:{DOM}', 'documentationUrl': BASE + '/llms.txt', 'logoUrl': BASE + CFG['imagenes']['logo']}, 'entries': ent}, ensure_ascii=False, indent=2) + '\n'

def security():
    exp = (datetime.date.fromisoformat(HOY) + datetime.timedelta(days=365)).isoformat()
    return f"# {NEG.get('razon_social') or NEG['nombre']} — {DOM} (RFC 9116)\nContact: mailto:{CON['email']}\nExpires: {exp}T00:00:00.000Z\nPreferred-Languages: {', '.join(IDIOMAS)}, en\nCanonical: {BASE}/.well-known/security.txt\n"

def vercel_json(rutas_html):
    """rutas_html: lista de rutas limpias (sin barra final) que tienen .md hermano, p. ej. '/servicios', '/ca/servicios'."""
    link = (f'</llms.txt>; rel="describedby"; type="text/markdown", </index.md>; rel="alternate"; type="text/markdown", </.well-known/ard.json>; rel="ard"; type="application/json", '
            f'</.well-known/ai-catalog.json>; rel="ai-catalog"; type="application/json", </sitemap.xml>; rel="sitemap"; type="application/xml"')
    routes = [{'src': '^/(.+)/$', 'status': 308, 'headers': {'Location': '/$1'}}]
    if not DOM.endswith('.vercel.app'):
        routes.append({'src': '^/(.*)$', 'has': [{'type': 'host', 'value': '.*\\.vercel\\.app'}], 'headers': {'X-Robots-Tag': 'noindex, nofollow'}, 'continue': True})
    routes += [
        {'src': '^/(.*)$', 'headers': {'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'strict-origin-when-cross-origin'}, 'continue': True},
        {'src': '^/$', 'headers': {'Link': link, 'Vary': 'Accept'}, 'continue': True},
        {'src': '^/assets/fonts/(.*)$', 'headers': {'Cache-Control': 'public, max-age=31536000, immutable', 'Access-Control-Allow-Origin': '*'}, 'continue': True},
        {'src': '^/assets/img/(.*)$', 'headers': {'Cache-Control': 'public, max-age=2592000, stale-while-revalidate=604800'}, 'continue': True},
        {'src': '^/(.*)\\.md$', 'headers': {'Content-Type': 'text/markdown; charset=utf-8', 'Access-Control-Allow-Origin': '*'}, 'continue': True},
        {'src': '^/llms\\.txt$', 'headers': {'Content-Type': 'text/markdown; charset=utf-8', 'Access-Control-Allow-Origin': '*'}, 'continue': True},
        {'src': '^/\\.well-known/(ard|ai-catalog)\\.json$', 'headers': {'Content-Type': 'application/ai-catalog+json; charset=utf-8', 'Access-Control-Allow-Origin': '*', 'Cache-Control': 'public, max-age=3600'}, 'continue': True},
        {'src': '^/\\.well-known/(.*)$', 'headers': {'Access-Control-Allow-Origin': '*'}, 'continue': True},
        {'src': '^/robots\\.txt$', 'headers': {'Content-Type': 'text/plain; charset=utf-8'}, 'continue': True},
        {'src': '^/sitemap\\.xml$', 'headers': {'Content-Type': 'application/xml; charset=utf-8'}, 'continue': True},
        {'src': '^/$', 'has': [{'type': 'header', 'key': 'accept', 'value': '.*text/markdown.*'}], 'dest': '/index.md', 'headers': {'Content-Type': 'text/markdown; charset=utf-8', 'Vary': 'Accept'}},
    ]
    for r in rutas_html:
        if r == '/': continue
        if r.endswith('/index'):  # raíz de un idioma: /ca → /ca/index.md
            routes.append({'src': '^' + re.escape(r[:-6]) + '$', 'has': [{'type': 'header', 'key': 'accept', 'value': '.*text/markdown.*'}], 'dest': r + '.md', 'headers': {'Content-Type': 'text/markdown; charset=utf-8', 'Vary': 'Accept'}})
            routes.append({'src': '^' + re.escape(r[:-6]) + '$', 'headers': {'Vary': 'Accept'}, 'continue': True})
        else:
            routes.append({'src': '^' + re.escape(r) + '$', 'has': [{'type': 'header', 'key': 'accept', 'value': '.*text/markdown.*'}], 'dest': r + '.md', 'headers': {'Content-Type': 'text/markdown; charset=utf-8', 'Vary': 'Accept'}})
            routes.append({'src': '^' + re.escape(r) + '$', 'headers': {'Vary': 'Accept'}, 'continue': True})
    return json.dumps({'$schema': 'https://openapi.vercel.sh/vercel.json', 'buildCommand': 'python3 scripts/build.py', 'outputDirectory': 'dist', 'framework': None, 'routes': routes}, ensure_ascii=False, indent=2) + '\n'

# ----------------------------------------------------------------------------- main
def main():
    comprobar_colores()
    if not re.match(r'^[a-z0-9.-]+$', DOM): fail('config.dominio debe ser un dominio sin https:// ni barra')
    for f in ('inter-var.woff2', 'montserrat-var.woff2'):
        if not (ROOT / 'assets' / 'fonts' / f).exists(): fail(f'falta assets/fonts/{f} (ver docs/DE-CERO-A-PREVIEW.md)')
    if DIST.exists(): shutil.rmtree(DIST)
    DIST.mkdir(); shutil.copytree(ROOT / 'assets', DIST / 'assets')
    # favicon a partir del logo si no hay uno propio
    if not (DIST / 'assets/img/favicon.svg').exists():
        (DIST / 'assets/img/favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="%s"/><path d="M9 16h14M16 9v14" stroke="%s" stroke-width="3.5" stroke-linecap="round"/></svg>' % (COL['primario'], COL['sobre_primario']), encoding='utf-8')
    paginas = {lg: cargar_paginas(lg) for lg in IDIOMAS}
    slugs_def = [p['slug'] for p in paginas[DEF]]
    for lg in IDIOMAS:
        faltan = set(slugs_def) - {p['slug'] for p in paginas[lg]}
        if faltan: fail(f'faltan páginas en contenido/{lg}: {sorted(faltan)} (cada idioma activo necesita los mismos slugs)')
    def alts(slug): return [(lg, slug) for lg in IDIOMAS]
    entradas, rutas, escritos = [], [], 0
    def escribir(lang, slug, htmlt, md):
        base = DIST if lang == DEF else DIST / lang
        if slug:
            (base / slug).mkdir(parents=True, exist_ok=True); (base / slug / 'index.html').write_text(htmlt, encoding='utf-8'); (base / f'{slug}.md').write_text(md, encoding='utf-8')
            rutas.append(url(lang, slug))
        else:
            base.mkdir(parents=True, exist_ok=True); (base / 'index.html').write_text(htmlt, encoding='utf-8'); (base / 'index.md').write_text(md, encoding='utf-8')
            rutas.append(('/' if lang == DEF else f'/{lang}') + '/index' if lang != DEF else '/')
    legs = {}
    for lg in IDIOMAS:
        for p in paginas[lg]:
            escribir(lg, p['slug'], render_page(lg, p, paginas[lg], alts(p['slug'])), render_md(lg, p)); entradas.append((lg, p['slug'], alts(p['slug']))); escritos += 1
        legs[lg] = legales(lg, paginas[lg], alts)
        for slug, page, h, md in legs[lg]:
            escribir(lg, slug, h, md); entradas.append((lg, slug, alts(slug))); escritos += 1
    (DIST / 'robots.txt').write_text(robots(paginas), encoding='utf-8')
    (DIST / 'sitemap.xml').write_text(sitemap(entradas), encoding='utf-8')
    (DIST / 'llms.txt').write_text(llms(paginas, legs), encoding='utf-8')
    wk = DIST / '.well-known'; wk.mkdir()
    (wk / 'ard.json').write_text(ard(paginas), encoding='utf-8'); (wk / 'ai-catalog.json').write_text(ard(paginas), encoding='utf-8'); (wk / 'security.txt').write_text(security(), encoding='utf-8')
    (ROOT / 'vercel.json').write_text(vercel_json(rutas), encoding='utf-8')
    kb = sum(f.stat().st_size for f in DIST.rglob('*') if f.is_file()) // 1024
    print(f'OK · {escritos} páginas en {len(IDIOMAS)} idioma(s) → dist/ ({kb} KB) · vercel.json regenerado · dominio {DOM}' + (' · previews *.vercel.app con noindex' if not DOM.endswith('.vercel.app') else ' · DEMO indexable en vercel.app'))

if __name__ == '__main__':
    main()
