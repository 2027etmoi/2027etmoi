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
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = (os.environ.get("SITE_URL") or os.environ.get("URL") or "https://2027etmoi.fr").rstrip("/")
NOM_SITE = "2027 et moi"
OG_DEFAUT = f"{SITE}/assets/og.jpg"

# Phrases d'état d'une candidature. Tournures sans accord de genre : le site ne
# recense pas le genre des personnes et n'a pas à le déduire de leur prénom.
STATUTS = {"declare": "{nom} ({parti}) a déclaré sa candidature à l'élection présidentielle 2027.",
           "primaire": "{nom} ({parti}) est en lice dans une primaire pour l'élection présidentielle 2027.",
           "pressenti": "La candidature de {nom} ({parti}) est pressentie pour l'élection présidentielle 2027.",
           "empeche": "La candidature de {nom} ({parti}) est empêchée pour l'élection présidentielle 2027.",
           "renonce": "{nom} ({parti}) a renoncé à se présenter à l'élection présidentielle 2027."}
THEMES = {"economie": "Économie, fiscalité et finances publiques", "travail": "Travail, salaires et pouvoir d'achat",
          "retraites": "Retraites et protection sociale", "sante": "Santé", "education": "Éducation, jeunesse et recherche",
          "ecologie": "Écologie, climat et énergie", "immigration": "Immigration et intégration",
          "securite": "Sécurité et justice", "international": "Europe, international et défense",
          "institutions": "Institutions et démocratie", "logement": "Logement",
          "territoires": "Agriculture, ruralité et services publics locaux",
          "societe": "Société et libertés"}

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
    "a-propos.html": ("Qui sommes-nous : un site citoyen, sans parti, sans financement, sans publicité",
                      "Qui édite 2027 et moi, comment le site est financé et tenu à jour, pourquoi il n'est pas signé, et ses mentions légales : éditeur, hébergeur, données personnelles."),
    "contact.html": ("Contact — signaler une erreur ou proposer une source",
                     "Écrire à 2027 et moi : signaler une erreur sur un candidat, un programme ou un sondage, proposer une source, poser une question sur la méthode du site."),
    "faq.html": ("Présidentielle 2027 : questions fréquentes (dates, parrainages, primaires)",
                 "Quand a lieu la présidentielle 2027 ? Comment devient-on candidat ? Que valent les sondages ? Réponses sourcées sur l'élection, les programmes et la méthode du site 2027 et moi."),
}


MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]
JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def date_courte(iso):
    """2027-04-18 -> 18 avril 2027 (chaîne vide si le format est inattendu)."""
    try:
        d = date(*(int(x) for x in iso.split("-")))
    except (TypeError, ValueError, AttributeError):
        return ""
    return f"{'1er' if d.day == 1 else d.day} {MOIS_FR[d.month - 1]} {d.year}"


def date_fr(iso):
    """2027-04-18 -> dimanche 18 avril 2027 (chaîne vide si le format est inattendu)."""
    try:
        d = date(*(int(x) for x in iso.split("-")))
    except (TypeError, ValueError, AttributeError):
        return ""
    return f"{JOURS_FR[d.weekday()]} {date_courte(iso)}"


def pct(v):
    """2.0 -> « 2,0 % »."""
    return f"{v:.1f}".replace(".", ",") + " %"


def moyennes_sondages(data):
    """Moyenne, nombre de sondages et fourchette par candidat.

    Même calcul que computeMoyennes() dans assets/common.js : moyenne des
    hypothèses à l'intérieur d'un sondage, puis moyenne des sondages.
    """
    par_sondage = {}
    for s in data.get("sondages", []):
        acc = {}
        for h in s.get("hypotheses", []):
            for cid, v in (h.get("scores") or {}).items():
                if isinstance(v, (int, float)):
                    acc.setdefault(cid, []).append(v)
        for cid, vals in acc.items():
            par_sondage.setdefault(cid, []).append(sum(vals) / len(vals))
    return {cid: {"moyenne": sum(v) / len(v), "n": len(v), "min": min(v), "max": max(v)}
            for cid, v in par_sondage.items()}


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


def maj(*chemins):
    """Date « mise_a_jour » la plus récente parmi des fichiers de data/ (None si aucune)."""
    d = []
    for c in chemins:
        for f in ([DATA / c] if not str(c).endswith("*") else sorted(DATA.glob(str(c)))):
            if f.exists():
                v = load(f).get("mise_a_jour")
                if isinstance(v, str) and len(v) >= 10:
                    d.append(v[:10])
    return max(d) if d else None


# Chaque page est datée par les données qu'elle affiche, et non par la date du
# dernier déploiement : un <lastmod> identique partout et remis à jour à chaque
# build n'apporte aucune information aux moteurs de recherche.
D_CAND = maj("candidats.json")
D_SOND = maj("sondages.json")
D_CAL = maj("calendrier.json")
D_THEMES = maj("programmes/*.json", "questions.json")
D_DON = maj("candidats.json", "sondages.json", "candidatures.json", "evaluations.json", "temps-parole.json")
DATES_PAGES = {"index.html": D_CAND, "candidats.html": D_CAND, "sondages.html": D_SOND,
               "donnees.html": D_DON, "comparateur.html": D_THEMES, "mes-priorites.html": D_THEMES,
               "faq.html": None, "contact.html": None, "a-propos.html": None}  # textes rédigés, pas de date de données
dates_cand = {}

COURRIEL = "contact@2027etmoi.fr"
ORGANISATION = {"@context": "https://schema.org", "@type": "Organization", "name": NOM_SITE, "url": SITE + "/",
                "logo": f"{SITE}/assets/apple-touch-icon.png", "email": COURRIEL,
                "contactPoint": {"@type": "ContactPoint", "contactType": "rédaction", "email": COURRIEL,
                                 "url": f"{SITE}/contact.html", "availableLanguage": "fr"},
                "description": "Site d'information indépendant et non partisan sur l'élection présidentielle française de 2027."}
WEBSITE = {"@context": "https://schema.org", "@type": "WebSite", "name": NOM_SITE, "url": SITE + "/", "inLanguage": "fr-FR",
           "description": PAGES["index.html"][1], "publisher": {"@type": "Organization", "name": NOM_SITE, "url": SITE + "/"}}

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
    jsonld = [WEBSITE, ORGANISATION] if page == "index.html" else []
    if page == "candidats.html":
        jsonld.append({"@context": "https://schema.org", "@type": "ItemList", "name": "Candidats à l'élection présidentielle française de 2027",
                       "numberOfItems": len([c for c in load(DATA / "candidats.json")["candidats"] if c["statut"] in ("declare", "primaire", "pressenti")]),
                       "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/candidats/{c['id']}.html",
                                            "item": {"@type": "Person", "name": c["nom"], "affiliation": {"@type": "Organization", "name": c["parti"]}}}
                                           for i, c in enumerate(c for c in load(DATA / "candidats.json")["candidats"] if c["statut"] in ("declare", "primaire", "pressenti"))]})
    if page == "a-propos.html":
        jsonld.append({"@context": "https://schema.org", "@type": "AboutPage", "name": "Qui sommes-nous — 2027 et moi",
                       "url": url, "inLanguage": "fr-FR",
                       "description": "Qui édite le site, comment il est financé et tenu à jour, et ses mentions légales.",
                       "mainEntity": ORGANISATION})
    if page == "contact.html":
        jsonld.append({"@context": "https://schema.org", "@type": "ContactPage", "name": "Contact — 2027 et moi",
                       "url": url, "inLanguage": "fr-FR",
                       "description": "Comment signaler une erreur, proposer une source ou poser une question sur la méthode du site.",
                       "mainEntity": {"@type": "Organization", "name": NOM_SITE, "url": SITE + "/", "email": COURRIEL}})
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
ETATS_AFFAIRE_LIB = {"enquete": "Enquête en cours", "mise_en_examen": "Mise en examen", "renvoi_proces": "Renvoi devant le tribunal",
                     "condamnation_non_definitive": "Condamnation non définitive", "condamnation_definitive": "Condamnation définitive",
                     "relaxe": "Relaxe", "instruction_close": "Instruction close", "non_lieu": "Non-lieu", "classement": "Classement sans suite"}


def _source(src, prefixe="Source : "):
    if not src or not str(src.get("url", "")).startswith("http"):
        return ""
    return (f'<span class="source">{prefixe}<a href="{esc(src["url"])}" target="_blank" rel="noopener">{esc(src.get("titre") or "lien")}</a>'
            + (f', {esc(date_courte(src["date"]) or src["date"])}' if src.get("date") else "") + "</span>")


cands = load(DATA / "candidats.json")["candidats"]
sond = load(DATA / "sondages.json") if (DATA / "sondages.json").exists() else {"sondages": []}
moy = moyennes_sondages(sond)
fen = sond.get("fenetre") or {}
def _fenetre(debut, fin):
    """« du 1er août au 22 septembre 2026 » (l'année n'est écrite qu'une fois)."""
    d, f = date_courte(debut), date_courte(fin)
    if not d or not f:
        return ""
    if debut[:4] == fin[:4]:
        d = d.rsplit(" ", 1)[0]
    return f" (publiés du {d} au {f})"


fenetre_txt = _fenetre(fen.get("debut"), fen.get("fin"))

# Prises de parole : propos tenus par la personne, là où ils l'ont été (docs/methode-prises-de-parole.md)
pp = load(DATA / "prises-de-parole.json") if (DATA / "prises-de-parole.json").exists() else {"prises_de_parole": []}
TYPES_PAROLE = {"interview": ("Interview", "interview", "interviews"),
                "discours": ("Discours ou meeting", "discours ou meeting", "discours ou meetings"),
                "tribune": ("Tribune signée", "tribune signée", "tribunes signées"),
                "debat": ("Débat", "débat", "débats"),
                "conference": ("Conférence de presse", "conférence de presse", "conférences de presse"),
                "parlement": ("Intervention au Parlement", "intervention au Parlement", "interventions au Parlement"),
                "communique": ("Communiqué officiel", "communiqué officiel", "communiqués officiels")}
THEMES_PAROLE = {**THEMES, "campagne": "Campagne et candidature"}
D_PAROLE = maj("prises-de-parole.json")
par_cand_pp = {}
for _it in pp.get("prises_de_parole", []):
    par_cand_pp.setdefault(_it["id"], []).append(_it)
for _l in par_cand_pp.values():
    _l.sort(key=lambda i: i["date"], reverse=True)
# Ancre stable par prise de parole (p-<id>-<date>, suffixée si plusieurs le même jour) : cible des liens du flux RSS
_vus = {}
for _it in sorted(pp.get("prises_de_parole", []), key=lambda i: (i["date"], i["id"], i["url"])):
    _base = f'p-{_it["id"]}-{_it["date"]}'
    _vus[_base] = _vus.get(_base, 0) + 1
    _it["_ancre"] = _base if _vus[_base] == 1 else f"{_base}-{_vus[_base]}"


def en_bref(items):
    """« En bref » construit mécaniquement — même logique que enBrefParole() dans assets/common.js."""
    if not items:
        return ""
    dates = sorted(i["date"] for i in items)
    n = len(items)
    par_type = {}
    for i in items:
        par_type[i["type"]] = par_type.get(i["type"], 0) + 1
    types = [f"{k} {TYPES_PAROLE.get(t, (t, t, t))[2 if k > 1 else 1]}" for t, k in par_type.items()]
    medias = list(dict.fromkeys(i["media"] for i in items))
    themes = list(dict.fromkeys(THEMES_PAROLE.get(t, t) for i in items for t in (i.get("themes") or [])))
    periode = (f"le {date_courte(dates[0])}" if dates[0] == dates[-1]
               else f"entre le {date_courte(dates[0])} et le {date_courte(dates[-1])}")
    s = "s" if n > 1 else ""
    return (f"{n} prise{s} de parole recensée{s} {periode} : {', '.join(types)}. "
            f"Lieux et médias : {' · '.join(medias)}. Thèmes abordés : {', '.join(themes).lower()}.")


def parole_li(i, avec_nom=""):
    """Une prise de parole en HTML statique — même présentation que paroleItemHtml() côté JavaScript."""
    type_ = TYPES_PAROLE.get(i["type"], (i["type"],))[0]
    themes = "".join(f'<a href="/themes/{esc(t)}.html">{esc(THEMES[t])}</a>' if t in THEMES
                     else f"<span>{esc(THEMES_PAROLE.get(t, t))}</span>" for t in (i.get("themes") or []))
    nom = f'<a class="feed-cand" href="/candidats/{esc(i["id"])}.html">{esc(avec_nom)}</a> ·' if avec_nom else ""
    return (f'<li id="{esc(i.get("_ancre", ""))}" data-cand="{esc(i["id"])}" data-themes="{esc(" ".join(i.get("themes") or []))}">'
            f'<div class="feed-head"><strong>{esc(date_courte(i["date"]))}</strong> <span class="badge parole">{esc(type_)}</span> {nom} '
            f'<span>{esc(i["media"])}{" — " + esc(i["emission"]) if i.get("emission") else ""}</span></div>'
            f'<a class="titre" href="{esc(i["url"])}" target="_blank" rel="noopener">{esc(i["titre"])}</a>'
            f'<p class="declare">{" ".join(esc(d) for d in i.get("declare") or [])}</p>'
            + (f'<div class="themes">{themes}</div>' if themes else "") + "</li>")
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
    statut = (STATUTS.get(c["statut"]) or "{nom} ({parti}).").format(nom=c["nom"], parti=c["parti"])
    titre = f"{c['nom']} : programme 2027, parcours et sondages"
    base = (bio or {}).get("presentation", {}).get("texte") or statut
    desc = couper(f"{statut} Programme par thème, parcours, sondages, chaque information sourcée. {base}")
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
    # La fiche affiche le programme, la biographie, le statut vérifié et la moyenne des sondages
    _d = [d for d in [(prog or {}).get("mise_a_jour"), (bio or {}).get("mise_a_jour"),
                      c.get("verifie_le"), D_SOND] if d]
    _d += [i["verifie_le"] for i in par_cand_pp.get(cid, []) if i.get("verifie_le")]
    dates_cand[cid] = max(_d) if _d else D_CAND
    jsonld = [
        {"@context": "https://schema.org", "@type": "ProfilePage", "name": titre, "url": url, "inLanguage": "fr-FR",
         "dateModified": dates_cand[cid] or lastmod, "mainEntity": personne},
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
              f'<p class="lede">{esc(statut)} {esc(c.get("statut_detail"))}</p>']
    if base and base != statut:  # sans biographie, base reprend la phrase du chapô
        resume.append(f"<p>{esc(base)}</p>")
    # Intentions de vote : reprise du calcul affiché sur la page Sondages
    if c["statut"] in ("declare", "primaire", "pressenti"):
        m = moy.get(cid)
        if m:
            fourchette = (f", dans une fourchette de {pct(m['min'])} à {pct(m['max'])}"
                          if m["n"] > 1 and m["max"] - m["min"] > 0.05 else "")
            resume.append(
                f'<p><strong>Sondages :</strong> {esc(c["nom"])} apparaît dans {m["n"]} sondage'
                f'{"s" if m["n"] > 1 else ""} d\'intentions de vote au premier tour{esc(fenetre_txt)}, '
                f'avec une moyenne de {pct(m["moyenne"])}{fourchette}. Un sondage mesure une intention à une '
                f'date donnée : ce n\'est ni un pronostic ni un résultat. '
                f'<a href="/sondages.html#{cid}">Détail des sondages</a></p>')
        else:
            resume.append(
                f'<p><strong>Sondages :</strong> {esc(c["nom"])} ne figure dans aucune des hypothèses '
                f'des sondages retenus{esc(fenetre_txt)}. '
                f'<a href="/sondages.html">Voir les sondages</a></p>')
    if par_theme:
        resume.append(f"<h2>Programme de {esc(c['nom'])} pour 2027</h2>")
        for t, label in THEMES.items():
            if t in par_theme:
                resume.append(f'<h3><a href="/themes/{t}.html">{esc(label)}</a></h3><ul>' + "".join(
                    f'<li>{esc(m["texte"])} (<a href="{esc(m["source"]["url"])}" rel="noopener">source</a>)</li>' for m in par_theme[t]) + "</ul>")
    miens = par_cand_pp.get(cid, [])[:5]
    if miens:
        resume.append(f'<h2>Prises de parole récentes</h2><p class="enbref">{esc(en_bref(miens))}</p><ul class="measures feed">'
                      + "".join(parole_li(i) for i in miens) + "</ul>"
                      f'<p class="notice">Propos tenus par la personne, là où ils l\'ont été ; jamais les articles à son sujet. '
                      f'<a href="/actualite.html#{esc(cid)}">Toute l\'actualité de la campagne</a></p>')
    # Parcours et procédures judiciaires : mêmes informations que la fiche complète, lisibles sans JavaScript
    if bio:
        nais = bio.get("naissance") or {}
        if nais.get("date"):
            resume.append(f'<p>Naissance : {esc(date_courte(nais["date"]) or nais["date"])}'
                          + (f', {esc(nais["lieu"])}' if nais.get("lieu") else "") + ".</p>")
        for cle, intitule in (("parcours_politique", "Parcours politique"),
                              ("parcours_professionnel", "Formation et parcours professionnel")):
            if bio.get(cle):
                resume.append(f"<h2>{intitule} de {esc(c['nom'])}</h2><ul>" + "".join(
                    f'<li><strong>{esc(e.get("periode", ""))}</strong> : {esc(e["texte"])}</li>' for e in bio[cle]) + "</ul>")
        if bio.get("affaires"):
            resume.append("<h2>Procédures judiciaires</h2>" + "".join(
                f'<h3>{esc(a["titre"])}</h3><p>{esc(a["texte"])}</p>'
                f'<p><strong>{esc(ETATS_AFFAIRE_LIB.get(a["etat"], a["etat"]))}</strong>'
                + (f' (état au {esc(date_courte(a["date_etat"]) or a["date_etat"])})' if a.get("date_etat") else "")
                + (f' : {esc(a["etat_detail"])}' if a.get("etat_detail") else "") + "</p>"
                + "".join(_source(x) for x in a.get("sources") or [])
                for a in bio["affaires"])
                + '<p class="notice">Toute personne qui n\'a pas été définitivement condamnée est présumée innocente. '
                  'Seules les procédures dont l\'état a pu être vérifié sur une source ouverte sont mentionnées.</p>')
    resume.append("</article>")

    s = set_title_desc(gabarit, f"{titre} | {NOM_SITE}", desc)
    s = s.replace('<p class="notice" id="loading">Chargement…</p>', "\n".join(resume))
    s = inject(s, seo_block(titre, desc, url, image=photo or OG_DEFAUT, type_="profile", jsonld=jsonld))
    (out / f"{cid}.html").write_text(s, encoding="utf-8")

# --- 3 a. pages Sondages et Candidats : contenu lisible sans JavaScript
# Ces deux pages sont construites par script dans le navigateur. Les robots des assistants
# conversationnels, et certains moteurs, n'exécutent pas JavaScript : sans ce pré-remplissage,
# ils n'y lisent ni un chiffre ni un nom. Le script remplace ce contenu au chargement.
_par_id = {c["id"]: c for c in cands}
_hors = sond.get("noms_hors_liste") or {}
LIENS = {"campagne": "Site de campagne", "parti": "Parti", "programme": "Programme", "x": "X",
         "instagram": "Instagram", "youtube": "YouTube", "wikipedia": "Wikipédia"}
BLOCS_LIB = {"gauche": "Gauche", "ecolo": "Écologistes", "centre": "Centre", "droite": "Droite",
             "extdroite": "Droite nationaliste", "autre": "Autres"}
# Libellés sans accord de genre (le script affiche ensuite ses propres badges)
STATUTS_COURTS = {"declare": "Candidature déclarée", "primaire": "En primaire", "pressenti": "Candidature pressentie",
                  "empeche": "Candidature empêchée", "renonce": "Ne se présente pas"}


def _nom(i):
    return _par_id[i]["nom"] if i in _par_id else _hors.get(i, i)


def _remplir(page, cible_ouvre, cible_ferme, contenu):
    """Place le contenu statique entre deux balises d'une page, de façon répétable."""
    f = ROOT / page
    if not f.exists():
        return
    t = f.read_text(encoding="utf-8")
    motif = re.escape(cible_ouvre) + r"(?:<!--STATIQUE-->.*?<!--/STATIQUE-->)?" + re.escape(cible_ferme)
    t2, n = re.subn(motif, lambda _: f"{cible_ouvre}<!--STATIQUE-->{contenu}<!--/STATIQUE-->{cible_ferme}", t, count=1, flags=re.S)
    if n != 1:
        sys.exit(f"build : zone statique introuvable dans {page} ({cible_ouvre})")
    f.write_text(t2, encoding="utf-8")


_rangs = sorted(moy.items(), key=lambda kv: -kv[1]["moyenne"])
_top = _rangs[0][1]["moyenne"] if _rangs else 1
_remplir("sondages.html", '<tbody id="avg">', "</tbody>", "".join(
    f'<tr id="{esc(i)}"><td>'
    + (f'<span class="bloc"><span class="dot {esc(_par_id[i]["bloc"])}"></span><a class="name" href="/candidats/{esc(i)}.html">{esc(_nom(i))}</a></span>'
       if i in _par_id else esc(_nom(i)))
    + f'</td><td class="num"><strong>{pct(m["moyenne"])}</strong></td>'
      f'<td class="num">{pct(m["min"]) + " – " + pct(m["max"]) if m["n"] > 1 else "—"}</td>'
      f'<td class="num">{m["n"]}</td>'
      f'<td class="bar-cell"><div class="bar" style="width:{m["moyenne"] / _top * 100:.1f}%"></div></td></tr>'
    for i, m in _rangs))
_remplir("sondages.html", '<div id="polls">', "</div>\n    </section>", "".join(
    f'<div class="card poll-card"><h3>{esc(s["institut"])}{" pour " + esc(s["commanditaire"]) if s.get("commanditaire") else ""}</h3>'
    f'<div class="notice">Terrain du {esc(date_courte(s["terrain_debut"]))} au {esc(date_courte(s["terrain_fin"]))}'
    + (f' · {s["echantillon"]:,} personnes interrogées'.replace(",", " ") if s.get("echantillon") else "") + "</div>"
    + _source(s.get("source"))
    + "".join(f'<div class="hyp"><strong>{esc(h.get("label") or "Hypothèse")}</strong> '
              + " · ".join(f"{esc(_nom(i))} {pct(v)}" for i, v in sorted((h.get("scores") or {}).items(), key=lambda kv: -kv[1]))
              + "</div>" for h in s.get("hypotheses", []))
    + "</div>" for s in sond.get("sondages", [])))


def _ligne_candidat(c):
    m = moy.get(c["id"])
    sondage = (f'<a class="poll" href="/sondages.html#{esc(c["id"])}">{pct(m["moyenne"])}</a> '
               f'<span class="poll-n">{m["n"]} sondage{"s" if m["n"] > 1 else ""}</span>' if m
               else '<span class="props-empty">Non testé</span>')
    props = ("<ul class=\"props\">" + "".join(f"<li>{esc(x)}</li>" for x in c["propositions"]) + "</ul>" if c.get("propositions")
             else '<span class="props-empty">Pas encore de programme publié</span>')
    liens = "".join(f'<a href="{esc(u)}" target="_blank" rel="noopener">{lib}</a>' for k, lib in LIENS.items()
                    if str((u := (c.get("liens") or {}).get(k)) or "").startswith("http"))
    return (f'<tr class="{"retire" if c["statut"] == "renonce" else ""}">'
            f'<td data-label="Candidat"><a class="name" href="/candidats/{esc(c["id"])}.html">{esc(c["nom"])}</a><div class="party">{esc(c["parti"])}</div></td>'
            f'<td data-label="Famille"><span class="bloc"><span class="dot {esc(c["bloc"])}"></span>{esc(BLOCS_LIB.get(c["bloc"], c["bloc"]))}</span></td>'
            f'<td data-label="Statut"><span class="badge {esc(c["statut"])}">{esc(STATUTS_COURTS.get(c["statut"], c["statut"]))}</span>'
            + (f'<div class="status-note">{esc(c["statut_detail"])}</div>' if c.get("statut_detail") else "") + _source(c.get("source")) + "</td>"
            f'<td data-label="Sondages (moyenne)">{sondage}</td>'
            f'<td data-label="Propositions phares">{props}</td>'
            f'<td data-label="Liens"><div class="links">{liens or "<span class=props-empty>—</span>"}</div></td></tr>')


_remplir("candidats.html", '<tbody id="rows">', "</tbody>", "".join(_ligne_candidat(c) for c in cands))

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


# --- 3 ter. pages thématiques et page calendrier (HTML statique, lisible sans JavaScript)
NAV = re.search(r'<nav class="site-nav">.*?</nav>', (ROOT / "index.html").read_text(encoding="utf-8"), re.S).group(0).replace(' aria-current="page"', "")
FOOTER = re.search(r'<footer class="site-footer">.*?</footer>', (ROOT / "index.html").read_text(encoding="utf-8"), re.S).group(0)


def page_html(titre_seo, desc, url, kicker, h1, lede, corps, jsonld=None, scripts=()):
    """Page statique complète, au gabarit du site."""
    return versionner(f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(titre_seo)} | {NOM_SITE}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
  <meta name="theme-color" content="#faf8f4">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap">
  <link rel="stylesheet" href="/assets/style.css">
  <link rel="alternate" type="application/rss+xml" title="2027 et moi — Actualité de la campagne" href="/actualite.xml">
  {seo_block(titre_seo, desc, url, jsonld=jsonld)}
</head>
<body>
  {NAV}

  <header class="site-header">
    <div class="wrap">
      <p class="kicker">{esc(kicker)}</p>
      <h1>{h1}</h1>
      <p class="lede">{lede}</p>
    </div>
  </header>

  <main class="wrap">
{corps}
  </main>

  {FOOTER}

  <script src="/assets/common.js"></script>
{"".join(f'  <script src="{s}"></script>' + chr(10) for s in scripts)}</body>
</html>
""")


def fil_ariane(niveaux):
    """JSON-LD BreadcrumbList + fil d'Ariane visible."""
    items = [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(niveaux)]
    visible = ' <span aria-hidden="true">›</span> '.join(
        f'<a href="{esc(u.replace(SITE, "") or "/")}">{esc(n)}</a>' if i < len(niveaux) - 1 else esc(n)
        for i, (n, u) in enumerate(niveaux))
    return ({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items},
            f'<nav class="fil" aria-label="Fil d\'Ariane">{visible}</nav>')


# Mesures et questions par thème
progs = {}
for c in cands:
    f = DATA / "programmes" / f"{c['id']}.json"
    if f.exists():
        progs[c["id"]] = load(f)
qdata = load(DATA / "questions.json") if (DATA / "questions.json").exists() else {"questions": [], "positions": {}}
noms = {c["id"]: c for c in cands}
LIBELLES_POS = {"pour": "Pour", "plutot_pour": "Plutôt pour", "nuance": "Nuancé",
                "plutot_contre": "Plutôt contre", "contre": "Contre"}

themes_dir = ROOT / "themes"
themes_dir.mkdir(exist_ok=True)
for old in themes_dir.glob("*.html"):
    old.unlink()

liens_themes = []
for theme, label in THEMES.items():
    url = f"{SITE}/themes/{theme}.html"
    liens_themes.append((theme, label))
    par_cand = []
    for c in sorted(en_lice, key=lambda c: c["id"]):
        ms = [m for m in (progs.get(c["id"], {}).get("mesures") or []) if m["theme"] == theme]
        if ms:
            par_cand.append((c, ms))
    total = sum(len(ms) for _, ms in par_cand)
    questions = [q for q in qdata["questions"] if q["theme"] == theme]

    sections = []
    if par_cand:
        sections.append('<section class="section"><h2>Ce que proposent les candidats</h2>'
                        + "".join(
                            f'<div class="card theme-block th-{theme}"><h3><a href="/candidats/{c["id"]}.html">{esc(c["nom"])}</a> '
                            f'<span class="party">{esc(c["parti"])}</span></h3><ul class="measures">'
                            + "".join(f'<li>{esc(m["texte"])} <span class="tag {esc(m["nature"])}">{esc({"programme": "Programme", "declaration": "Déclaration", "presse": "Presse"}.get(m["nature"], m["nature"]))}</span>'
                                      f'<span class="source">Source : <a href="{esc(m["source"]["url"])}" target="_blank" rel="noopener">{esc(m["source"].get("titre", "lien"))}</a>'
                                      f'{", " + esc(m["source"]["date"]) if m["source"].get("date") else ""}</span></li>' for m in ms)
                            + "</ul></div>" for c, ms in par_cand)
                        + "</section>")
    else:
        sections.append('<section class="section"><p class="notice">Aucune mesure sourcée n\'a encore été recensée sur ce thème.</p></section>')

    if questions:
        blocs_q = []
        for q in questions:
            pos = [(cid, qdata["positions"][cid][q["id"]]) for cid in qdata["positions"]
                   if q["id"] in qdata["positions"][cid] and cid in noms]
            pos.sort(key=lambda x: (list(LIBELLES_POS).index(x[1]["position"]), x[0]))
            blocs_q.append(
                f'<details class="card theme-block th-{theme}"><summary><h3>{esc(q["texte"])}</h3>'
                f'<span class="fold-count">{len(pos)}</span></summary>'
                + (f'<p class="notice">{esc(q["contexte"]["texte"])}</p>' if q.get("contexte") else "")
                + (f'<ul class="measures">' + "".join(
                    f'<li><span class="answer-tag {"oui" if p["position"] in ("pour", "plutot_pour") else "non" if p["position"] in ("contre", "plutot_contre") else "none"}">{esc(LIBELLES_POS[p["position"]])}</span> '
                    f'<strong><a href="/candidats/{cid}.html">{esc(noms[cid]["nom"])}</a></strong> — {esc(p["resume"])}'
                    f'<span class="source">Source : <a href="{esc(p["source"]["url"])}" target="_blank" rel="noopener">{esc(p["source"].get("titre", "lien"))}</a>'
                    f'{", " + esc(p["source"]["date"]) if p["source"].get("date") else ""}</span></li>' for cid, p in pos) + "</ul>"
                   if pos else '<p class="props-empty">Aucune position sourcée pour l\'instant.</p>')
                + "</details>")
        sections.append('<section class="section"><h2>Les questions clés sur ce thème</h2>'
                        + "".join(blocs_q)
                        + f'<p class="notice">Répondez-y vous-même et comparez vos réponses à celles des candidats : <a href="/mes-priorites.html">Mes priorités</a>.</p></section>')

    autres = "".join(f'<li><a href="/themes/{t}.html">{esc(l)}</a></li>' for t, l in THEMES.items() if t != theme)
    sections.append(f'<section class="section"><h2>Les autres thèmes</h2><ul class="cand-links cols">{autres}</ul>'
                    f'<p class="notice"><a href="/comparateur.html?t={theme}">Comparer les candidats sur ce thème</a> · '
                    f'<a href="/candidats.html">Tous les candidats</a></p></section>')

    jl, fil = fil_ariane([("Présidentielle 2027", SITE + "/"), ("Thèmes", SITE + "/themes/"), (label, url)])
    collection = {"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{label} — Présidentielle 2027",
                  "url": url, "inLanguage": "fr-FR", "dateModified": D_THEMES or lastmod,
                  "description": f"Propositions des candidats à la présidentielle 2027 sur le thème « {label} », avec leurs sources."}
    sections.append(f'<p class="meta">Page mise à jour le {esc(D_THEMES or lastmod)} · les mesures et positions proviennent des fiches candidats, chacune sourcée.</p>')
    corps = fil + "\n" + "\n".join(sections)
    titre_court = label.split(",")[0]
    (themes_dir / f"{theme}.html").write_text(page_html(
        f"{titre_court} : que proposent les candidats à la présidentielle 2027 ?",
        couper(f"Toutes les propositions sourcées des candidats à l'élection présidentielle 2027 sur {titre_court.lower()} : {total} mesures et leurs sources, plus les positions sur les questions clés du thème."),
        url, "Présidentielle 2027", esc(label), f"{total} mesures sourcées, candidat par candidat, et les positions sur les questions clés de ce thème.",
        corps, [collection, jl]), encoding="utf-8")

# Sommaire des thèmes : /themes/index.html
cartes = "".join(
    f'<a class="entry card th-{t}" href="/themes/{t}.html"><span class="entry-t">{esc(l)}</span>'
    f'<span>{sum(1 for c in en_lice for m in (progs.get(c["id"], {}).get("mesures") or []) if m["theme"] == t)} mesures sourcées</span></a>'
    for t, l in THEMES.items())
jl_t, fil_t = fil_ariane([("Présidentielle 2027", SITE + "/"), ("Thèmes", SITE + "/themes/")])
(themes_dir / "index.html").write_text(page_html(
    "Programmes 2027 par thème : retraites, santé, immigration, écologie…",
    "Les propositions des candidats à la présidentielle 2027, thème par thème : économie, travail, retraites, santé, éducation, écologie, immigration, sécurité, Europe, institutions, logement, agriculture, société. Chaque mesure est sourcée.",
    f"{SITE}/themes/", "Présidentielle 2027", "Les programmes thème par thème",
    "Choisissez un thème pour voir toutes les propositions sourcées des candidats et leurs positions sur les questions clés.",
    fil_t + '\n    <section class="section"><div class="entry-grid entry-grid-13">' + cartes + "</div></section>", [jl_t]), encoding="utf-8")

# Page Actualité de la campagne : toutes les prises de parole, en ordre chronologique inverse
paroles = sorted(pp.get("prises_de_parole", []), key=lambda i: (i["date"], i["id"]), reverse=True)
paroles = [i for i in paroles if i["id"] in noms]
mois_fr = {}
for i in paroles:
    mois_fr.setdefault(i["date"][:7], []).append(i)
cands_pp = sorted({i["id"] for i in paroles}, key=lambda k: noms[k]["nom"].split()[-1])
themes_pp = [t for t in THEMES_PAROLE if any(t in (i.get("themes") or []) for i in paroles)]
filtres = ('<div class="filters needs-js" id="filtres"><label>Candidat <select>'
           '<option value="">Tous</option>'
           + "".join(f'<option value="{esc(k)}">{esc(noms[k]["nom"])}</option>' for k in cands_pp)
           + '</select></label><div class="chips" role="group" aria-label="Thème">'
           + "".join(f'<button type="button" class="chip" data-theme="{esc(t)}" aria-pressed="false">{esc(THEMES_PAROLE[t])}</button>'
                     for t in themes_pp)
           + f'</div><span class="notice" id="feed-count"></span></div>')
corps_feed = "".join(
    f'<h2 class="feed-month">{esc(MOIS_FR[int(m[5:7]) - 1].capitalize())} {m[:4]}</h2><ul class="measures feed">'
    + "".join(parole_li(i, avec_nom=noms[i["id"]]["nom"]) for i in its) + "</ul>"
    for m, its in mois_fr.items())
if not paroles:
    corps_feed = '<p class="notice">Aucune prise de parole recensée pour le moment.</p>'
jl_a, fil_a = fil_ariane([("Présidentielle 2027", SITE + "/"), ("Actualité de la campagne", SITE + "/actualite.html")])
jl_a2 = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Actualité de la campagne présidentielle 2027",
         "url": f"{SITE}/actualite.html", "inLanguage": "fr-FR", "dateModified": D_PAROLE or lastmod,
         "description": "Prises de parole des candidats à l'élection présidentielle 2027, jour par jour, avec ce qui a été déclaré et la source."}
(ROOT / "actualite.html").write_text(page_html(
    "Actualité de la présidentielle 2027 : ce que déclarent les candidats, jour par jour",
    "Interviews, discours, tribunes et débats des candidats à la présidentielle 2027, en ordre chronologique : ce qui a été déclaré, où, avec la source. Sans commentaire, sélection identique pour tous.",
    f"{SITE}/actualite.html", "Présidentielle 2027", "Actualité de la campagne",
    "Ce que les candidats ont déclaré, là où ils l'ont dit : interviews, discours, tribunes, débats, interventions au Parlement. Chaque ligne renvoie à sa source. Aucun article <em>sur</em> les candidats, aucun commentaire.",
    fil_a + f"""
    <section class="section" id="feed">
      {filtres}
      <p class="notice">Suivre cette page : <a href="/actualite.xml">flux RSS</a>.</p>
      {corps_feed}
    </section>
    <section class="section prose">
      <h2>Comment cette page est construite</h2>
      <p>Une « revue de presse » choisit des articles sur un candidat, et chaque choix est une opinion. Ici, l'unité recensée est une <strong>prise de parole publique</strong> : un fait daté. On note où le candidat s'est exprimé et ce qu'il a déclaré, reformulé sans qualificatif, avec la source ouverte avant publication. Portraits, enquêtes, éditoriaux et propos rapportés par des sources anonymes ne sont jamais repris. La sélection obéit à la même règle pour tous ; l'inégalité d'exposition entre candidats est un fait du paysage médiatique, que le site affiche sans le corriger. <a href="https://github.com/2027etmoi/2027etmoi/blob/main/docs/methode-prises-de-parole.md" target="_blank" rel="noopener">Méthode détaillée</a> · <a href="/contact.html">Signaler une prise de parole manquante</a>.</p>
      <p>Voir aussi : <a href="/candidats.html">les candidats</a>, <a href="/themes/">les programmes par thème</a>, <a href="/sondages.html">les sondages</a>, <a href="/donnees.html">le temps de parole relevé par l'Arcom</a>.</p>
    </section>""", [jl_a, jl_a2], scripts=("/assets/actualite.js",)), encoding="utf-8")

# Flux RSS des prises de parole (les 60 plus récentes) : chaque entrée renvoie à son ancre sur la page Actualité
from datetime import datetime, timezone
from email.utils import format_datetime


def _rfc822(iso):
    return format_datetime(datetime(*(int(x) for x in iso.split("-")), 12, 0, tzinfo=timezone.utc))


_items = "".join(
    f"""    <item>
      <title>{esc(noms[i["id"]]["nom"])} — {esc(TYPES_PAROLE.get(i["type"], (i["type"],))[0])}, {esc(i["media"])}</title>
      <link>{SITE}/actualite.html#{esc(i["_ancre"])}</link>
      <guid isPermaLink="true">{SITE}/actualite.html#{esc(i["_ancre"])}</guid>
      <pubDate>{_rfc822(i["date"])}</pubDate>
      <description><![CDATA[<p>{" ".join(esc(d) for d in i.get("declare") or [])}</p><p>Source : <a href="{esc(i["url"])}">{esc(i["titre"])}</a></p>]]></description>
    </item>
""" for i in paroles[:60])
(ROOT / "actualite.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>2027 et moi — Actualité de la campagne</title>
    <link>{SITE}/actualite.html</link>
    <atom:link href="{SITE}/actualite.xml" rel="self" type="application/rss+xml"/>
    <description>Ce que déclarent les candidats à la présidentielle 2027 : interviews, discours, débats, tribunes. Chaque entrée renvoie à sa source, sans commentaire.</description>
    <language>fr-FR</language>
    <lastBuildDate>{_rfc822(D_PAROLE or lastmod)}</lastBuildDate>
{_items}  </channel>
</rss>
""", encoding="utf-8")

# Page calendrier
cal = load(DATA / "calendrier.json") if (DATA / "calendrier.json").exists() else {"etapes": []}
STATUTS_CAL = {"officielle": "Date officielle", "prevue": "Prévue", "estimee": "Estimée"}
lignes_cal = "".join(
    f'<li class="step card"><span class="step-date">{esc(e["date"])}{" – " + esc(e["fin"]) if e.get("fin") and e["fin"] != e["date"] else ""}</span>'
    f'<span class="step-t">{esc(e["titre"])}</span>'
    f'<span class="badge {"declare" if e.get("statut") == "officielle" else "primaire" if e.get("statut") == "prevue" else "pressenti"}">{esc(STATUTS_CAL.get(e.get("statut"), ""))}</span>'
    f'<span class="source">Source : <a href="{esc(e["source"]["url"])}" target="_blank" rel="noopener">{esc(e["source"].get("titre", "lien"))}</a>, {esc(e["source"].get("date", ""))}</span></li>'
    for e in cal.get("etapes", []))



def event_jsonld(e):
    """Données structurées d'une étape du calendrier dont la date est officielle.

    Les champs recommandés par Google sont renseignés à partir des données du
    fichier calendrier.json, sans rien ajouter qui n'y figure pas. Le champ
    « performer » est volontairement absent : une élection n'a pas d'interprète,
    et y inscrire des candidats serait faux (et contraire à la neutralité du site).
    """
    src = e.get("source") or {}
    quand = date_fr(e["date"])
    desc = (f"{e['titre']}" + (f", le {quand}" if quand else "") + ". "
            "Le président de la République française est élu au suffrage universel direct, à deux tours. "
            "Date officielle" + (f", source : {src['titre']}" if src.get("titre") else "")
            + (f", {date_fr(src['date']) or src['date']}" if src.get("date") else "") + ".")
    return {"@context": "https://schema.org", "@type": "Event", "name": e["titre"],
            "description": desc, "image": [OG_DEFAUT], "url": f"{SITE}/calendrier.html",
            "startDate": e["date"], "endDate": e.get("fin") or e["date"],
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "location": {"@type": "Place", "name": "France",
                         "address": {"@type": "PostalAddress", "addressCountry": "FR"}},
            "organizer": {"@type": "GovernmentOrganization", "name": "Ministère de l'Intérieur",
                          "url": "https://www.interieur.gouv.fr/"},
            "about": {"@type": "Thing", "name": "Élection présidentielle française de 2027"},
            "inLanguage": "fr-FR"}


events = [event_jsonld(e) for e in cal.get("etapes", []) if e.get("statut") == "officielle"]
jl_c, fil_c = fil_ariane([("Présidentielle 2027", SITE + "/"), ("Calendrier", SITE + "/calendrier.html")])
(ROOT / "calendrier.html").write_text(page_html(
    "Date de la présidentielle 2027 : 18 avril et 2 mai, calendrier complet",
    "Quand a lieu l'élection présidentielle 2027 ? Premier tour le dimanche 18 avril 2027, second tour le dimanche 2 mai. Calendrier complet : primaires, parrainages, liste officielle des candidats, campagne officielle. Dates sourcées.",
    f"{SITE}/calendrier.html", "Présidentielle 2027", "Calendrier de l'élection présidentielle 2027",
    "Premier tour le <strong>dimanche 18 avril 2027</strong>, second tour le <strong>dimanche 2 mai 2027</strong>. Toutes les étapes, avec leur source et leur degré de certitude.",
    fil_c + f"""
    <section class="section">
      <ol class="steps steps-col">{lignes_cal}</ol>
      <p class="notice">Les dates « estimées » découlent des règles électorales : elles seront fixées par le décret de convocation des électeurs, attendu au plus tard début février 2027. Les dates « prévues » sont annoncées par les organisateurs (primaires, consultations internes).</p>
    </section>
    <section class="section prose">
      <h2>Comment se déroule l'élection</h2>
      <p>Le président de la République est élu au suffrage universel direct, à deux tours. Pour se présenter, un candidat doit réunir au moins <strong>500 parrainages</strong> d'élus venant d'au moins 30 départements ou collectivités d'outre-mer, sans que plus d'un dixième proviennent d'un même département. Le Conseil constitutionnel vérifie ces parrainages et arrête la liste officielle des candidats, attendue vers la mi-mars 2027.</p>
      <p>Dans certains territoires d'outre-mer (Guadeloupe, Martinique, Guyane, Saint-Pierre-et-Miquelon, Saint-Barthélemy, Saint-Martin, Polynésie française), le vote a lieu la veille, samedi 17 avril et samedi 1er mai.</p>
      <p><a href="/faq.html">Questions fréquentes sur l'élection</a> · <a href="/candidats.html">Qui se présente</a> · <a href="/sondages.html">Sondages</a></p>
    </section>""", [jl_c] + events), encoding="utf-8")


# --- 3 quater. llms.txt : présentation du site à l'intention des assistants conversationnels
# Convention récente (llmstxt.org), sans garantie d'être lue ; elle ne coûte rien et ne contient
# que ce que le site affiche déjà.
_gh = "https://github.com/2027etmoi/2027etmoi/blob/main"
(ROOT / "llms.txt").write_text(f"""# 2027 et moi

> Site d'information indépendant et non partisan sur l'élection présidentielle française de 2027 (premier tour le 18 avril 2027, second tour le 2 mai 2027). Chaque information renvoie à une source datée. Le site n'attribue ni note ni classement et ne donne aucune consigne de vote.

Données mises à jour le {date_courte(lastmod)}. Les données sont réutilisables sous Licence Ouverte 2.0, en citant « 2027 et moi » ({SITE}) et la date de mise à jour. Tant que le Conseil constitutionnel n'a pas arrêté la liste officielle, attendue vers la mi-mars 2027, les candidatures recensées sont des candidatures annoncées.

## Pages principales

- [Candidats]({SITE}/candidats.html) : candidatures déclarées, en primaire ou pressenties, avec parti, statut sourcé et moyenne des sondages
- [Actualité de la campagne]({SITE}/actualite.html) : ce que les candidats ont déclaré, jour par jour, avec la source
- [Programmes par thème]({SITE}/themes/) : mesures sourcées classées en treize thèmes
- [Sondages]({SITE}/sondages.html) : intentions de vote au premier tour, recopiées des notices de la Commission des sondages
- [Calendrier]({SITE}/calendrier.html) : étapes de l'élection, avec leur degré de certitude
- [La campagne en données]({SITE}/donnees.html) : programmes publiés, chiffrages, temps de parole relevé par l'Arcom
- [Questions fréquentes]({SITE}/faq.html) : règles de l'élection et méthode du site
- [Qui sommes-nous]({SITE}/a-propos.html) : éditeur, financement, mentions légales

## Fiches candidats

"""
    + "".join(f"- [{c['nom']}]({SITE}/candidats/{c['id']}.html) : {c['parti']} — {STATUTS_COURTS.get(c['statut'], c['statut']).lower()}\n"
              for c in cands if c["statut"] in ("declare", "primaire", "pressenti"))
    + f"""
## Données ouvertes (JSON)

- [candidats.json]({SITE}/data/candidats.json) : candidatures et statuts sourcés
- [votes.json]({SITE}/data/votes.json) : votes nominatifs des candidats au Parlement
- [prises-de-parole.json]({SITE}/data/prises-de-parole.json) : interviews, discours et débats, avec ce qui a été déclaré
- [sondages.json]({SITE}/data/sondages.json) : sondages par hypothèse, avec les notices officielles
- [calendrier.json]({SITE}/data/calendrier.json) : calendrier de l'élection
- Programmes : {SITE}/data/programmes/<identifiant>.json — biographies : {SITE}/data/biographies/<identifiant>.json

## Méthode

- [Programmes et mesures]({_gh}/docs/methode-sources.md)
- [Biographies et affaires judiciaires]({_gh}/docs/methode-biographies.md)
- [Votes au Parlement]({_gh}/docs/methode-votes.md)
- [Prises de parole]({_gh}/docs/methode-prises-de-parole.md)
- [Licence des données]({_gh}/LICENCE-DONNEES.md)
""", encoding="utf-8")

# --- 4. sitemap.xml et robots.txt
urls = [(SITE + "/", "1.0", DATES_PAGES["index.html"]),
        *[(f"{SITE}/{p}", "0.8", DATES_PAGES.get(p)) for p in PAGES if p != "index.html"],
        (f"{SITE}/calendrier.html", "0.9", D_CAL), (f"{SITE}/actualite.html", "0.9", D_PAROLE),
        (f"{SITE}/themes/", "0.8", D_THEMES),
        *[(f"{SITE}/themes/{t}.html", "0.8", D_THEMES) for t in THEMES],
        *[(f"{SITE}/candidats/{c['id']}.html", "0.7" if c["statut"] != "renonce" else "0.4", dates_cand.get(c["id"]))
          for c in cands]]
(ROOT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{esc(u)}</loc>" + (f"<lastmod>{d}</lastmod>" if d else "")
              + f"<priority>{pr}</priority></url>\n" for u, pr, d in urls)
    + "</urlset>\n", encoding="utf-8")
# Redirections des adresses sans extension (« /faq ») vers l'adresse déclarée
# (« /faq.html »). Netlify a longtemps servi les deux avec un code 200 : ces règles
# ramènent chaque page à une seule adresse, quelle que soit celle déjà connue des moteurs.
# Le « ! » force la redirection même si un fichier correspond au chemin demandé.
sans_ext = sorted({u[len(SITE):].removesuffix(".html") for u, _, _ in urls
                   if u.endswith(".html")} - {""})
(ROOT / "_redirects").write_text(
    "# Généré par scripts/build.py — ne pas modifier à la main\n"
    + "".join(f"{c}  {c}.html  301!\n" for c in sans_ext), encoding="utf-8")
(ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /candidat.html\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

print(f"build : {len(cands)} pages candidats, {len(urls)} URL dans le sitemap, site = {SITE}")
