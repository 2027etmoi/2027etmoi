#!/usr/bin/env python3
"""Signale les pages modifiées aux moteurs qui suivent le protocole IndexNow
(Bing, et ceux qui s'y alimentent : DuckDuckGo, Ecosia, plusieurs assistants).

Lancé par .github/workflows/indexnow.yml après chaque mise en ligne.
Usage : python3 scripts/indexnow.py          pages modifiées depuis deux jours
        python3 scripts/indexnow.py --tout   toutes les pages du plan du site

La clé n'est pas un secret : le protocole demande qu'elle soit publiée à la
racine du site (/<clé>.txt), ce qui prouve que la demande vient de l'éditeur.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

SITE = "https://2027etmoi.fr"
CLE = "366f3af6fe0f6ba247ec880ad0ee10fb"
# Pages dont le contenu change à presque chaque mise à jour, signalées à chaque fois
TOUJOURS = {f"{SITE}/", f"{SITE}/actualite.html", f"{SITE}/sondages.html", f"{SITE}/candidats.html"}

plan = urllib.request.urlopen(f"{SITE}/sitemap.xml", timeout=30).read().decode("utf-8")
entrees = re.findall(r"<url><loc>(.*?)</loc>(?:<lastmod>(.*?)</lastmod>)?", plan)
tout = "--tout" in sys.argv
seuil = (date.today() - timedelta(days=2)).isoformat()
urls = [u for u, maj in entrees if tout or u in TOUJOURS or (maj and maj >= seuil)]
if not urls:
    print("IndexNow : rien à signaler")
    sys.exit(0)

corps = {"host": SITE.split("//")[1], "key": CLE, "keyLocation": f"{SITE}/{CLE}.txt", "urlList": urls}
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=json.dumps(corps).encode("utf-8"),
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    rep = urllib.request.urlopen(req, timeout=30)
    print(f"IndexNow : {len(urls)} adresse(s) signalée(s), réponse {rep.status}")
except urllib.error.HTTPError as e:
    print(f"IndexNow : erreur {e.code} — {e.read()[:300].decode('utf-8', 'replace')}")
    sys.exit(1)
