#!/usr/bin/env python3
"""Resume JSON de Lighthouse: puntuaciones, métricas y auditorías con peso que restan. Uso: python3 scripts/lh-resumen.py medicion/*/*.json"""
import json, sys
for f in sys.argv[1:]:
    d = json.load(open(f)); c = d['categories']; a = d['audits']
    if 'agentic-browsing' in c:
        refs = [(r['id'], a[r['id']].get('score'), a[r['id']].get('scoreDisplayMode')) for r in c['agentic-browsing']['auditRefs']]
        ap = [x for x in refs if x[2] not in ('notApplicable', 'manual', 'informative')]
        print(f'{f}: navegación agéntica {sum(1 for x in ap if x[1] == 1)}/{len(ap)} comprobaciones aplicables superadas (' + ', '.join(f'{i}={s}' for i, s, m in ap) + ')'); continue
    sc = {k: round(v['score'] * 100) for k, v in c.items()}
    met = {k: a[k]['displayValue'] for k in ('first-contentful-paint', 'largest-contentful-paint', 'cumulative-layout-shift', 'total-blocking-time') if k in a}
    print(f'{f}: {sc} · {met} · LH {d["lighthouseVersion"]} · {d["fetchTime"][:16]}')
    for cat in c.values():
        for ref in cat['auditRefs']:
            x = a[ref['id']]
            if ref.get('weight', 0) > 0 and x.get('score') is not None and x['score'] < 1: print(f'   ✗ {cat["id"]}/{ref["id"]} (peso {ref["weight"]}): {x.get("displayValue") or x.get("title")}')
