#!/usr/bin/env python3
"""Build du site (lancé par Netlify à chaque déploiement, ou à la main) :

1. data/meta.json : date de dernière mise à jour (scripts/meta.py) ;
2. candidats/<id>.html : une page statique par personnalité, à partir du gabarit
   candidat.html, avec titre, description, balises de partage, données structurées
   et un résumé lisible sans JavaScript (utile aux moteurs de recherche) ;
3. balises SEO des pages principales (entre <!--SEO--> et <!--/SEO-->) ;
4. données structurées de la FAQ (FAQPage) ;
5. sitemap.xml et robots.txt.

URL du site : variable SITE_URL, sinon URL (fournie par Netlify), sinon valeur par défaut.
"""
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = (os.environ.get("SITE_URL") or os.environ.get("URL") or "https://2027etmoi.netlify.app").rstrip("/")
NOM_SITE = "2027 et moi"
OG_DEFAUT = f"{SITE}/assets/og.jpg"

STATUTS = {"declare": "candidat déclaré", "primaire": "candidat à la primaire", "pressenti": "candidature pressentie",
           "empeche": "candidature empêchée", "renonce": "pas candidat"}
THEMES = {"economie": "Économie, fiscalité et finances publiques", "travail": "Travail, salaires et pouvoir d'achat",
          "retraites": "Retraites et protection sociale", "sante": "Santé", "education": "Éducation, jeunesse et recherche",
          "ecologie": "Écologie, climat et énergie", "immigration": "Immigration et intégration",
          "securite": "Sécurité et justice", "international": "Europe, international et défense",
          "institutions": "Institutions et démocratie", "logement": "Logement",
          "territoires": "Agriculture, ruralité et services publics locaux"}

# Pages principales : titre et description optimisés pour la recherche
PAGES = {
    "index.html": ("Présidentielle 2027 : candidats, programmes et sondages, tout sourcé",
                   "Élection présidentielle 2027 en France : qui sont les candidats, que proposent-ils, que disent les sondages ? Programmes comparés thème par thème, parcours, données de campagne. Toutes les informations sont sourcées, sans parti pris."),
    "candidats.html": ("Candidats à la présidentielle 2027 : la liste complète et sourcée",
                       "Liste des candidats à l'élection présidentielle 2027 : déclarés, en primaire ou pressentis, avec leur parti, leurs propositions phares, les sondages et les liens vers leurs programmes."),
    "mes-priorites.html": ("Mes priorités : quels candidats 2027 proposent ce qui compte pour vous ?",
                           "Choisissez vos thèmes, réagissez à des propositions anonymes des candidats à la présidentielle 2027, puis découvrez qui propose quoi. Sans recommandation de vote, rien n'est enregistré."),
    "comparateur.html": ("Comparateur des programmes de la présidentielle 2027",
                         "Comparez les programmes des candidats à la présidentielle 2027 thème par thème : économie, retraites, santé, écologie, immigration, sécurité… Chaque mesure renvoie à sa source."),
    "donnees.html": ("Présidentielle 2027 en données : programmes, chiffrage, temps de parole",
                     "Les candidatures à la présidentielle 2027 en faits vérifiables : déclaration, désignation, programme, chiffrage, sondages, temps de parole TV et radio (Arcom), évaluations externes. Sans note ni classement."),
    "sondages.html": ("Sondages présidentielle 2027 : moyenne des intentions de vote",
                      "Intentions de vote au 1er tour de la présidentielle 2027 : moyenne des sondages récents et détail de chaque enquête (Ifop, Ipsos, Elabe, Odoxa, OpinionWay…), avec les notices officielles."),
    "faq.html": ("Présidentielle 2027 : questions fréquentes (dates, parrainages, primaires)",
                 "Quand a lieu la présidentielle 2027 ? Comment devient-on candidat ? Que valent les sondages ? Réponses sourcées sur l'élection, les programmes et la méthode du site 2027 et moi."),
}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def esc(s):
    return html.escape(str(s or ""), quote=True)


def seo_block(titre, description, url, image=OG_DEFAUT, type_="website", jsonld=None):
    tags = [
        f'<link rel="canonical" href="{esc(url)}">',
        f'<meta property="og:site_name" content="{NOM_SITE}">',
        '<meta property="og:locale" content="fr_FR">',
        f'<meta property="og:type" content="{type_}">',
        f'<meta property="og:title" content="{esc(titre)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:url" content="{esc(url)}">',
        f'<meta property="og:image" content="{esc(image)}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(titre)}">',
        f'<meta name="twitter:description" content="{esc(description)}">',
        f'<meta name="twitter:image" content="{esc(image)}">',
    ]
    for obj in jsonld or []:
        tags.append('<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>")
    return "<!--SEO-->\n  " + "\n  ".join(tags) + "\n  <!--/SEO-->"


def inject(s, block):
    if "<!--SEO-->" in s:
        return re.sub(r"<!--SEO-->.*?<!--/SEO-->", lambda _: block, s, flags=re.S)
    return s.replace("</head>", f"  {block}\n</head>", 1)


def set_title_desc(s, titre, description):
    s = re.sub(r"<title>.*?</title>", f"<title>{esc(titre)}</title>", s, count=1, flags=re.S)
    return re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(description)}">', s, count=1)


def couper(t, n=155):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[: t.rfind(" ", 0, n - 1)].rstrip(" ,;:") + "…"


# --- 1. meta.json
subprocess.run([sys.executable, str(ROOT / "scripts" / "meta.py")], check=True)
meta = load(DATA / "meta.json")
lastmod = max(filter(None, [meta.get("publication"), meta.get("donnees")]))

WEBSITE = {"@context": "https://schema.org", "@type": "WebSite", "name": NOM_SITE, "url": SITE + "/", "inLanguage": "fr-FR",
           "description": PAGES["index.html"][1]}

# Version des fichiers CSS/JS (empreinte du contenu) pour forcer leur rechargement après une mise à jour
import hashlib
VERSIONS = {f.name: hashlib.sha1(f.read_bytes()).hexdigest()[:8] for f in (ROOT / "assets").glob("*") if f.suffix in (".css", ".js")}


def versionner(s):
    return re.sub(r'(/assets/([\w.-]+\.(?:css|js)))(\?v=\w+)?"',
                  lambda m: f'{m.group(1)}?v={VERSIONS[m.group(2)]}"' if m.group(2) in VERSIONS else m.group(0), s)


# --- 2. pages principales
for page, (titre, desc) in PAGES.items():
    f = ROOT / page
    if not f.exists():
        continue
    url = SITE + ("/" if page == "index.html" else f"/{page}")
    s = set_title_desc(f.read_text(encoding="utf-8"), f"{titre} | {NOM_SITE}" if page != "index.html" else f"{titre} — {NOM_SITE}", desc)
    jsonld = [WEBSITE] if page == "index.html" else []
    if page == "faq.html":
        qa = []
        for q, a in re.findall(r"<summary>(.*?)</summary>\s*<div class=\"answer\">(.*?)</div>", s, flags=re.S):
            a = re.sub(r'<span class="source">.*?</span>', "", a, flags=re.S)
            texte = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", a))).strip()
            qa.append({"@type": "Question", "name": html.unescape(re.sub(r"<[^>]+>", "", q)).strip(),
                       "acceptedAnswer": {"@type": "Answer", "text": texte}})
        jsonld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": qa})
    f.write_text(versionner(inject(s, seo_block(titre, desc, url, jsonld=jsonld))), encoding="utf-8")

# --- 3. pages candidats
cands = load(DATA / "candidats.json")["candidats"]
(ROOT / "candidat.html").write_text(versionner((ROOT / "candidat.html").read_text(encoding="utf-8")), encoding="utf-8")
gabarit = (ROOT / "candidat.html").read_text(encoding="utf-8")
out = ROOT / "candidats"
out.mkdir(exist_ok=True)
for old in out.glob("*.html"):
    old.unlink()

for c in cands:
    cid = c["id"]
    prog = load(DATA / "programmes" / f"{cid}.json") if (DATA / "programmes" / f"{cid}.json").exists() else None
    bio = load(DATA / "biographies" / f"{cid}.json") if (DATA / "biographies" / f"{cid}.json").exists() else None
    statut = STATUTS.get(c["statut"], c["statut"])
    titre = f"{c['nom']} : programme 2027, parcours et sondages"
    base = (bio or {}).get("presentation", {}).get("texte") or f"{c['nom']} ({c['parti']}), {statut} à l'élection présidentielle 2027."
    desc = couper(f"{c['nom']} ({c['parti']}), {statut} à la présidentielle 2027 : programme par thème, parcours, sondages. {base}")
    url = f"{SITE}/candidats/{cid}.html"
    photo = (bio or {}).get("photo", {}).get("url")
    sameas = [u for k, u in (c.get("liens") or {}).items() if k in ("wikipedia", "campagne", "x", "instagram", "youtube")]
    personne = {"@type": "Person", "name": c["nom"], "affiliation": {"@type": "Organization", "name": c["parti"]}}
    if photo:
        personne["image"] = photo
    if sameas:
        personne["sameAs"] = sameas
    if base:
        personne["description"] = couper(base, 300)
    jsonld = [
        {"@context": "https://schema.org", "@type": "ProfilePage", "name": titre, "url": url, "inLanguage": "fr-FR",
         "dateModified": (prog or {}).get("mise_a_jour") or lastmod, "mainEntity": personne},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Présidentielle 2027", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Candidats", "item": f"{SITE}/candidats.html"},
            {"@type": "ListItem", "position": 3, "name": c["nom"], "item": url}]},
    ]

    # Résumé lisible sans JavaScript, remplacé par la fiche complète au chargement
    mesures = (prog or {}).get("mesures", [])
    par_theme = {}
    for m in mesures:
        par_theme.setdefault(m["theme"], []).append(m)
    resume = [f'<article id="loading" class="prerender">',
              f'<p class="kicker">{esc(c["parti"])}</p><h1>{esc(c["nom"])}</h1>',
              f'<p class="lede">{esc(c["nom"])}, {esc(statut)} à l\'élection présidentielle 2027. {esc(c.get("statut_detail"))}</p>']
    if base:
        resume.append(f"<p>{esc(base)}</p>")
    if par_theme:
        resume.append(f"<h2>Programme de {esc(c['nom'])} pour 2027</h2>")
        for t, label in THEMES.items():
            if t in par_theme:
                resume.append(f"<h3>{esc(label)}</h3><ul>" + "".join(
                    f'<li>{esc(m["texte"])} (<a href="{esc(m["source"]["url"])}" rel="noopener">source</a>)</li>' for m in par_theme[t]) + "</ul>")
    resume.append("</article>")

    s = set_title_desc(gabarit, f"{titre} | {NOM_SITE}", desc)
    s = s.replace('<p class="notice" id="loading">Chargement…</p>', "\n".join(resume))
    s = inject(s, seo_block(titre, desc, url, image=photo or OG_DEFAUT, type_="profile", jsonld=jsonld))
    (out / f"{cid}.html").write_text(s, encoding="utf-8")

# --- 3 bis. liste statique des candidats sur l'accueil (liens internes, lisible sans JavaScript)
BLOCS = {"gauche": "Gauche", "ecolo": "Écologistes", "centre": "Centre", "droite": "Droite",
         "extdroite": "Droite nationaliste", "autre": "Autres"}
en_lice = [c for c in cands if c["statut"] in ("declare", "primaire", "pressenti")]
groupes = []
for b, label in BLOCS.items():
    membres = sorted((c for c in en_lice if c["bloc"] == b), key=lambda c: c["id"])
    if membres:
        groupes.append(f'<div class="cand-group"><h3><span class="dot {b}"></span>{esc(label)} <span class="fold-count">{len(membres)}</span></h3><ul class="cand-links">'
                       + "".join(f'<li><a href="/candidats/{c["id"]}.html">{esc(c["nom"])}</a> <span class="party">{esc(c["parti"])}</span></li>' for c in membres)
                       + "</ul></div>")
accueil = ROOT / "index.html"
if accueil.exists():
    s_acc = accueil.read_text(encoding="utf-8")
    # Chiffres clés et répartition par parti
    from collections import Counter
    par_statut = Counter(c["statut"] for c in en_lice)
    par_parti = Counter(c["parti"] for c in en_lice)
    chiffres = (f'<div class="kpis">'
                f'<div class="kpi"><span class="kpi-n">{len(en_lice)}</span><span class="kpi-l">candidatures recensées</span></div>'
                f'<div class="kpi"><span class="kpi-n">{par_statut["declare"]}</span><span class="kpi-l">déclarées</span></div>'
                f'<div class="kpi"><span class="kpi-n">{par_statut["primaire"]}</span><span class="kpi-l">en primaire</span></div>'
                f'<div class="kpi"><span class="kpi-n">{par_statut["pressenti"]}</span><span class="kpi-l">pressenties</span></div>'
                f'<div class="kpi"><span class="kpi-n">{len(par_parti)}</span><span class="kpi-l">partis ou mouvements</span></div></div>')
    partis = ('<details class="card partis"><summary><h3>Répartition par parti ou mouvement</h3></summary><ul class="partis-list">'
              + "".join(f'<li><span>{esc(pt)}</span><strong>{n}</strong></li>' for pt, n in sorted(par_parti.items(), key=lambda x: (-x[1], x[0])))
              + '</ul><p class="notice">Candidatures déclarées, en primaire ou pressenties, telles que recensées sur ce site. '
              'Plusieurs candidats d\'un même parti peuvent s\'affronter dans une primaire ; la liste officielle sera arrêtée par le Conseil constitutionnel vers la mi-mars 2027.</p></details>')
    bloc = f'<!--CANDIDATS-->\n      {chiffres}\n      <div class="cand-groups">{"".join(groupes)}</div>\n      {partis}\n      <!--/CANDIDATS-->'
    accueil.write_text(re.sub(r"<!--CANDIDATS-->.*?<!--/CANDIDATS-->", lambda _: bloc, s_acc, flags=re.S), encoding="utf-8")

# --- 4. sitemap.xml et robots.txt
urls = [(SITE + "/", "1.0"), *[(f"{SITE}/{p}", "0.8") for p in PAGES if p != "index.html"],
        *[(f"{SITE}/candidats/{c['id']}.html", "0.7" if c["statut"] != "renonce" else "0.4") for c in cands]]
(ROOT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{esc(u)}</loc><lastmod>{lastmod}</lastmod><priority>{p}</priority></url>\n" for u, p in urls)
    + "</urlset>\n", encoding="utf-8")
(ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /candidat.html\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

print(f"build : {len(cands)} pages candidats, {len(urls)} URL dans le sitemap, site = {SITE}")
