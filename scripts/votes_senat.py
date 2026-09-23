#!/usr/bin/env python3
"""Votes nominatifs au Sénat des candidats de data/candidats.json (data/votes-senat.json).

Méthode : docs/methode-votes.md. Seuls les scrutins publics (nominatifs) sont repris ;
aucun score, aucun taux de présence n'est calculé.

Sources (licence : « licence ouverte » du Sénat, reprenant les termes de la Licence Ouverte
de data.gouv.fr — https://data.senat.fr/licence/) :

1. Répertoire des sénateurs (data.senat.fr, base « Sénateurs ») :
   - https://data.senat.fr/data/senateurs/ODSEN_GENERAL.json  (état civil, matricule, circonscription)
   - https://data.senat.fr/data/senateurs/ODSEN_ELUSEN.json   (mandats sénatoriaux, actuels et historiques)
   La base couvre les sénateurs depuis 1875 : elle sert aussi à établir, par recherche sur le
   nom et le prénom, que les 47 autres personnalités n'ont jamais été sénatrices.
2. Scrutins publics (senat.fr) :
   - liste d'une session : https://www.senat.fr/scrutin-public/scr<AAAA>.html
   - page d'un scrutin   : https://www.senat.fr/scrutin-public/<AAAA>/scr<AAAA>-<N>.html
   - votes nominatifs    : https://www.senat.fr/scrutin-public/<AAAA>/scr<AAAA>-<N>.json
     (fichier utilisé par le plan de l'hémicycle de la page du scrutin ; une entrée par siège,
     {"matricule", "vote", "siege"} avec vote = p | c | a | n).

Sénateurs parmi les 50 personnalités (voir SENATEURS_CANDIDATS) : Bruno Retailleau (Vendée, 2004 →,
mandat suspendu du 21 octobre 2024 au 13 novembre 2025 pendant ses fonctions ministérielles),
Jean-Luc Mélenchon (Essonne, 1986-2000 puis 2004-2010) et Michel Barnier (Savoie, 1995 puis
1997-1999). Les scrutins publics ne sont publiés en ligne qu'à partir de la session 2006-2007 :
Michel Barnier n'a donc aucun scrutin couvert, ce qui est dit dans « a_verifier ».

Choix des scrutins (SCRUTINS ci-dessous) : votes sur l'ensemble d'un texte (ou, à défaut de
scrutin sur l'ensemble, sur l'article qui porte la mesure) pour les textes marquants énumérés
par la méthode — retraites, lois de finances, immigration, énergie, sécurité, fin de vie, santé,
agriculture, libertés publiques — et pour les textes qui portent sur une question clé de
data/questions.json. Le Sénat ne connaît ni scrutin solennel ni motion de censure.
La sélection ne dépend jamais du vote d'un candidat ; elle est en revanche limitée aux périodes
où l'un des trois siégeait (rien n'est retenu entre le 21 octobre 2024 et le 13 novembre 2025,
où aucun des trois n'était membre du Sénat).

Usage : python3 scripts/votes_senat.py [--cache DOSSIER]
Les fichiers du Sénat sont téléchargés dans --cache (par défaut un dossier temporaire du
système), jamais dans le dépôt.
"""
import argparse
import html
import json
import re
import sys
import tempfile
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUJ = date.today().isoformat()

SENATEURS = "https://data.senat.fr/data/senateurs/"
SCRUTIN = "https://www.senat.fr/scrutin-public/"

# Personnalités ayant été sénatrices : matricule Sénat (identifiant du répertoire et des
# fichiers de scrutins), circonscription attendue et libellé du mandat.
# Vérifié dans ODSEN_GENERAL.json (nom, prénom, date de naissance).
SENATEURS_CANDIDATS = {
    "retailleau": ("04033B", "Vendée", "Sénateur de la Vendée"),    # né le 20/11/1960
    "melenchon": ("86039K", "Essonne", "Sénateur de l'Essonne"),    # né le 19/08/1951
    "barnier": ("95008D", "Savoie", "Sénateur de la Savoie"),       # né le 09/01/1951
}
MATRICULES = {cid: v[0] for cid, v in SENATEURS_CANDIDATS.items()}

# Page « sénateur » de senat.fr, qui porte les reprises de mandat après des fonctions
# ministérielles (absentes de ODSEN_ELUSEN.json).
FICHES = {
    "retailleau": "https://www.senat.fr/senateur/retailleau_bruno04033b.html",
    "melenchon": "https://www.senat.fr/senateur/melenchon_jean_luc86039k.html",
    "barnier": "https://www.senat.fr/senateur/barnier_michel95008d.html",
}

# (session, numéro, questions clés liées, motif de sélection)
# « session » est l'année d'ouverture de la session parlementaire (2025 = session 2025-2026).
SCRUTINS = [
    ("2006", 40, [], "texte marquant : énergie (ouverture du capital de Gaz de France)"),
    ("2006", 122, ["q04"], "exonération fiscale et sociale des heures supplémentaires (loi TEPA)"),
    ("2007", 10, [], "texte marquant : immigration (maîtrise de l'immigration, intégration, asile)"),
    ("2007", 85, [], "texte marquant : ratification du traité de Lisbonne"),
    ("2008", 56, [], "texte marquant : loi de finances pour 2009"),
    ("2008", 109, [], "texte marquant : écologie (Grenelle de l'environnement)"),
    ("2009", 276, [], "texte marquant : libertés publiques (dissimulation du visage dans l'espace public)"),
    ("2010", 82, ["q05"], "réforme des retraites de 2010 (âge légal porté à 62 ans)"),
    ("2010", 195, [], "texte marquant : immigration, intégration et nationalité"),
    ("2011", 66, ["q30"], "droit de vote et d'éligibilité des étrangers non européens aux municipales"),
    ("2012", 148, ["q25"], "mariage des couples de personnes de même sexe (article 1er ; "
                           "le vote sur l'ensemble du texte n'a pas donné lieu à scrutin public en ligne)"),
    ("2013", 42, ["q05"], "réforme des retraites de 2013"),
    ("2014", 215, [], "texte marquant : fin de vie (nouveaux droits des malades en fin de vie)"),
    ("2015", 13, [], "texte marquant : immigration (droit des étrangers en France)"),
    ("2016", 123, [], "texte marquant : sécurité intérieure et lutte contre le terrorisme"),
    ("2017", 6, [], "texte marquant : énergie (fin de la recherche et de l'exploitation des hydrocarbures)"),
    ("2017", 171, [], "texte marquant : immigration maîtrisée et droit d'asile effectif"),
    ("2018", 170, [], "texte marquant : énergie et climat"),
    ("2020", 148, [], "texte marquant : climat et résilience"),
    ("2022", 8, [], "texte marquant : libertés publiques (constitutionnalisation de l'IVG, "
                    "proposition de loi constitutionnelle d'origine sénatoriale)"),
    ("2022", 110, ["q11"], "construction de nouveaux réacteurs nucléaires"),
    ("2022", 124, ["q17"], "soutien à l'Ukraine et renforcement de l'aide fournie"),
    ("2022", 249, ["q05"], "réforme des retraites de 2023 (âge légal porté à 64 ans), vote sur le texte"),
    ("2022", 251, ["q05"], "réforme des retraites de 2023, texte de la commission mixte paritaire"),
    ("2022", 332, ["q23"], "objectif « zéro artificialisation nette » (ZAN)"),
    ("2023", 43, ["q13", "q14"], "loi immigration 2023, première lecture au Sénat"),
    ("2023", 109, ["q13", "q14"], "loi immigration 2023, texte de la commission mixte paritaire"),
    ("2023", 136, [], "texte marquant : libertés publiques (loi constitutionnelle sur la liberté "
                      "de recourir à l'IVG)"),
    ("2025", 61, [], "texte marquant : loi de financement de la sécurité sociale pour 2026"),
    ("2025", 125, [], "texte marquant : loi de finances pour 2026"),
    ("2025", 169, ["q08"], "droit à l'aide à mourir"),
    ("2025", 307, ["q07"], "régulation de l'installation des médecins (article 1er de la proposition "
                           "de loi contre les déserts médicaux)"),
    ("2025", 337, ["q33"], "protection des mineurs face aux réseaux sociaux"),
    ("2025", 338, [], "texte marquant : sécurité (réponses immédiates aux troubles à l'ordre public)"),
    ("2025", 340, [], "texte marquant : agriculture (protection et souveraineté agricoles)"),
]

VOTE = {"p": "pour", "c": "contre", "a": "abstention", "n": "non_votant"}
MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}


def sans_accents(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def cle(s):
    return re.sub(r"[^a-z]", "", sans_accents(s).lower())


def telecharger(url, cache, binaire=False):
    """Télécharge url dans cache (une seule fois) et renvoie son contenu."""
    nom = re.sub(r"[^A-Za-z0-9._-]", "_", url.split("//", 1)[-1])[-180:]
    f = cache / nom
    if not f.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "2027etmoi (données ouvertes)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            f.write_bytes(r.read())
    return f.read_bytes() if binaire else f.read_text(encoding="utf-8", errors="replace")


def texte(fragment):
    """HTML -> texte lisible."""
    fragment = re.sub(r"<script.*?</script>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def jour(s):
    """« 21 juillet 2026 » -> « 2026-07-21 »."""
    m = re.match(r"\s*(\d{1,2})(?:er)?\s+(\S+)\s+(\d{4})", s)
    if not m or sans_accents(m.group(2)).lower() not in MOIS:
        return None
    return "%s-%02d-%02d" % (m.group(3), MOIS[sans_accents(m.group(2)).lower()], int(m.group(1)))


def iso(d):
    """« 2004/10/01 00:00:00 » -> « 2004-10-01 »."""
    return d[:10].replace("/", "-") if d else None


# --- mandats ---------------------------------------------------------------

def mandats(cache, candidats):
    """Mandats sénatoriaux de chaque candidat ; [] pour ceux qui n'ont jamais siégé."""
    general = json.loads(telecharger(SENATEURS + "ODSEN_GENERAL.json", cache))["results"]
    elus = json.loads(telecharger(SENATEURS + "ODSEN_ELUSEN.json", cache))["results"]
    par_matricule = {s["Matricule"]: s for s in general}

    out = {c["id"]: [] for c in candidats}
    for cid, (mat, circo, detail) in SENATEURS_CANDIDATS.items():
        fiche = par_matricule[mat]
        if fiche["Circonscription"] != circo:
            sys.exit("%s (%s) : circonscription « %s » dans ODSEN_GENERAL, « %s » attendue."
                     % (cid, mat, fiche["Circonscription"], circo))
        source = {"titre": "Sénat — répertoire des sénateurs (données ouvertes)",
                  "url": SENATEURS + "ODSEN_ELUSEN.json", "date": AUJ}
        lignes = sorted((r for r in elus if r["Matricule"] == mat),
                        key=lambda r: r["Date_de_debut_de_mandat"] or "")
        for r in lignes:
            out[cid].append({"chambre": "SENAT", "detail": detail,
                             "debut": iso(r["Date_de_debut_de_mandat"]),
                             "fin": iso(r["Date_de_fin_de_mandat"]), "source": dict(source)})
        # Reprise de mandat après des fonctions ministérielles : absente de ODSEN_ELUSEN,
        # lue sur la fiche du sénateur.
        page = texte(telecharger(FICHES[cid], cache))
        m = re.search(r"Redevenu S[ée]nat(?:eur|rice) le (\d{1,2}\s+\S+\s+\d{4})", page)
        if m and jour(m.group(1)):
            out[cid].append({"chambre": "SENAT", "detail": detail, "debut": jour(m.group(1)),
                             "fin": None,
                             "source": {"titre": "Sénat — fiche de %s %s" % (fiche["Prenom_usuel"],
                                                                             fiche["Nom_usuel"]),
                                        "url": FICHES[cid], "date": AUJ}})
    return out, general


def jamais_senateur(candidats, general):
    """Contrôle : aucun autre candidat ne porte le nom d'un sénateur (alerte à vérifier)."""
    noms = {}
    for s in general:
        noms.setdefault(cle(s["Nom_usuel"]), []).append(s)
    alertes = []
    for c in candidats:
        if c["id"] in MATRICULES:
            continue
        parts = c["nom"].split()
        nom, prenom = cle(" ".join(parts[1:])), cle(parts[0])
        for s in noms.get(nom, []):
            if cle(s["Prenom_usuel"]) == prenom:
                alertes.append("%s (%s) porte le nom et le prénom du sénateur %s %s "
                               "(matricule %s) : vérifier s'il s'agit de la même personne."
                               % (c["nom"], c["id"], s["Prenom_usuel"], s["Nom_usuel"], s["Matricule"]))
    return alertes


# --- scrutins --------------------------------------------------------------

def scrutin(session, num, cache):
    """Objet, date, résultat et votes nominatifs d'un scrutin public."""
    base = "%s%s/scr%s-%d" % (SCRUTIN, session, session, num)
    page = telecharger(base + ".html", cache)
    # Le fil d'Ariane, juste avant le contenu central, porte l'objet officiel et le résultat :
    # « … Scrutins  Scrutin n°N - séance du <date>  <objet>  Adopté|Rejeté ».
    fil = texte(page[:page.find("CONTENU CENTRAL")])
    m = re.search(r"Scrutins\s+Scrutin n°\s*%d\s*-\s*séance du (\d{1,2}\s+\S+\s+\d{4})\s+(.+?)\s+"
                  r"(Adopté|Rejeté|Non adopté)\b" % num, fil)
    if not m:
        sys.exit("Scrutin %s-%d : objet introuvable sur %s.html" % (session, num, base))
    objet, resultat = m.group(2).strip(" .-"), m.group(3)
    votes = json.loads(telecharger(base + ".json", cache))["votes"]
    return {
        "id": "senat-%s-%d" % (session, num),
        "chambre": "SENAT",
        "date": jour(m.group(1)),
        "titre": objet[0].upper() + objet[1:],
        # « article » : vote sur un article isolé ; « ensemble » : vote sur l'ensemble du texte
        # (y compris « article unique constituant l'ensemble »).
        "type": "article" if (re.match(r"(?i)sur l'article", objet)
                              and not re.search(r"(?i)constituant l'ensemble", objet)) else "ensemble",
        "resultat": {"Adopté": "adopté", "Rejeté": "rejeté", "Non adopté": "rejeté"}[resultat],
        "url": base + ".html",
        "votes_bruts": {v["matricule"]: v["vote"] for v in votes},
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", help="dossier de téléchargement (hors dépôt)")
    args = p.parse_args()
    cache = Path(args.cache) if args.cache else Path(tempfile.gettempdir()) / "votes-senat"
    cache.mkdir(parents=True, exist_ok=True)

    candidats = json.loads((ROOT / "data/candidats.json").read_text(encoding="utf-8"))["candidats"]
    questions = {q["id"] for q in json.loads((ROOT / "data/questions.json").read_text(encoding="utf-8"))["questions"]}

    mand, general = mandats(cache, candidats)
    a_verifier = jamais_senateur(candidats, general)

    scrutins = []
    for session, num, liens, motif in SCRUTINS:
        inconnues = [q for q in liens if q not in questions]
        if inconnues:
            sys.exit("Scrutin %s-%d : question(s) inconnue(s) %s" % (session, num, inconnues))
        s = scrutin(session, num, cache)
        bruts = s.pop("votes_bruts")
        s["questions"] = liens
        votes = {}
        for cid, mat in MATRICULES.items():
            if mat in bruts:  # absent du fichier = non membre du Sénat à cette date
                votes[cid] = VOTE[bruts[mat]]
        s["votes"] = votes
        if not votes:
            sys.exit("Scrutin %s-%d : aucun candidat n'était sénateur à cette date." % (session, num))
        scrutins.append(s)
    scrutins.sort(key=lambda s: (s["date"], s["id"]))

    a_verifier.append(
        "Michel Barnier a été sénateur de la Savoie (1995, puis 1997-1999) : les scrutins publics "
        "du Sénat n'étant publiés en ligne qu'à partir de la session 2006-2007, aucun de ses votes "
        "n'est repris ici.")
    a_verifier.append(
        "Aucun scrutin n'est retenu entre le 21 octobre 2024 et le 13 novembre 2025 : Bruno "
        "Retailleau, seul sénateur en exercice parmi les candidats, n'était alors pas membre du "
        "Sénat (fonctions gouvernementales).")

    sortie = {
        "mise_a_jour": AUJ,
        "sources": [
            {"titre": "Sénat — données ouvertes, répertoire des sénateurs",
             "url": "https://data.senat.fr/les-senateurs/",
             "licence": "Licence ouverte du Sénat (termes de la Licence Ouverte de data.gouv.fr)"},
            {"titre": "Sénat — scrutins publics",
             "url": "https://www.senat.fr/scrutin-public/scr2025.html",
             "licence": "Licence ouverte du Sénat (termes de la Licence Ouverte de data.gouv.fr)"},
        ],
        "mandats": mand,
        "scrutins": scrutins,
        "a_verifier": a_verifier,
    }
    f = ROOT / "data/votes-senat.json"
    f.write_text(json.dumps(sortie, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("%s : %d scrutins, %d candidats sénateurs, %d points à vérifier."
          % (f.relative_to(ROOT), len(scrutins), sum(1 for v in mand.values() if v), len(a_verifier)))


if __name__ == "__main__":
    main()
