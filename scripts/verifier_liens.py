#!/usr/bin/env python3
"""Teste toutes les URL présentes dans data/ et signale celles qui ne répondent pas.

Usage : python3 scripts/verifier_liens.py
Certains sites (x.com, instagram, sites protégés par Cloudflare) bloquent les robots :
un code 403/429 est signalé comme « bloqué », pas comme lien mort.
"""
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


def urls_in(obj, where, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            urls_in(v, where, out)
    elif isinstance(obj, list):
        for v in obj:
            urls_in(v, where, out)
    elif isinstance(obj, str) and obj.startswith("http"):
        out.setdefault(obj, set()).add(where)


def status(url):
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 400, 404):
                continue  # certains serveurs refusent HEAD
            return e.code
        except Exception as e:  # noqa: BLE001
            if method == "GET":
                return type(e).__name__
    return "?"


urls = {}
for f in DATA.rglob("*.json"):
    urls_in(json.loads(f.read_text(encoding="utf-8")), str(f.relative_to(DATA)), urls)

with ThreadPoolExecutor(max_workers=16) as ex:
    results = dict(zip(urls, ex.map(status, urls)))

morts = {u: s for u, s in results.items() if s in (404, 410) or isinstance(s, str)}
bloques = {u: s for u, s in results.items() if s in (401, 403, 429, 999)}
print(f"{len(urls)} URL testées · {len(morts)} mortes ou injoignables · {len(bloques)} bloquées (robots)")
for u, s in sorted(morts.items()):
    print(f"  MORT {s} – {u}  ({', '.join(sorted(urls[u]))})")
