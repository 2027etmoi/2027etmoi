#!/usr/bin/env python3
"""Produit data/votes-an-historique.json : votes nominatifs des candidats à l'Assemblée
nationale AVANT la 17e législature (législatures XII à XVI, 2002-2024).

Complément de scripts/votes_an.py, qui ne couvre que la 17e législature : les scrutins
publics nominatifs mis en ligne en données ouvertes par l'Assemblée ne commencent qu'en
octobre 2024, si bien que les candidats dont le mandat de député est antérieur
(Xavier Bertrand, Ségolène Royal, François Hollande, François Bayrou, Édouard Philippe…)
n'y ont aucun vote. Ce script va chercher les législatures antérieures.

    python3 scripts/votes_an_historique.py [--cache DOSSIER] [--out FICHIER] [--offline]

Ne modifie aucun autre fichier de données. Voir docs/methode-votes.md.

--------------------------------------------------------------------------------
Disponibilité réelle des scrutins nominatifs, législature par législature
--------------------------------------------------------------------------------
- XVIe (2022-2024), XVe (2017-2022), XIVe (2012-2017) : jeux de données ouvertes
  « Scrutins » de data.assemblee-nationale.fr, avec décompte nominatif et identifiant
  d'acteur (PAxxxx). Même format que la 17e législature.
- XIIIe (2007-2012) et XIIe (2002-2007) : aucun jeu de données ouvertes. Les votes
  nominatifs ne sont publiés que dans les pages HTML « analyse du scrutin » des sites
  archivés (www.assemblee-nationale.fr/13/scrutins/joNNNN.asp et /12/scrutins/joNNNN.asp),
  qui listent les députés par groupe et par position. L'identification s'y fait par
  prénom + nom, sans identifiant.
- XIe législature et antérieures : les tables de la XIe législature ne comportent pas de
  pages « analyse du scrutin » nominatives ; rien n'est repris ici.

Attention : une partie des pages des XIIe et XIIIe législatures ne sont PAS nominatives.
Quand un groupe vote en bloc, la page écrit « membres du groupe, présents ou ayant délégué
leur droit de vote » sans nommer personne, et seuls les dissidents sont cités. Le script
rejette ces scrutins (contrôle : pour chaque groupe et chaque position, le nombre de noms
lus doit égaler le décompte annoncé).

--------------------------------------------------------------------------------
Sources
--------------------------------------------------------------------------------
- Scrutins XIVe : .../repository/14/loi/scrutins/Scrutins_XIV.json.zip
- Scrutins XVe  : .../repository/15/loi/scrutins/Scrutins_XV.json.zip
- Scrutins XVIe : .../repository/16/loi/scrutins/Scrutins.json.zip
- Acteurs / mandats / organes (historique, législatures 12 à 17) : AMO30
- Tables chronologiques des scrutins publics des XIIe et XIIIe législatures :
  https://www.assemblee-nationale.fr/1{2,3}/scrutins/table-AAAA-AAAA.asp
- Analyses nominatives des scrutins des XIIe et XIIIe législatures :
  https://www.assemblee-nationale.fr/1{2,3}/scrutins/joNNNN.asp
- Mandats de député d'un candidat, y compris antérieurs à 2002 :
  https://www.assemblee-nationale.fr/dyn/deputes/PAxxxx/fonctions?archive=oui

--------------------------------------------------------------------------------
Critères de sélection des scrutins (les mêmes pour tous les candidats)
--------------------------------------------------------------------------------
60 scrutins, répartis sur les cinq législatures (11 + 13 + 12 + 13 + 11), choisis parmi
les scrutins nominatifs disponibles selon docs/methode-votes.md :
motions de censure et déclarations de politique générale ; retraites (2003, 2010, 2013,
2020, 2023) ; mariage et adoption pour les couples de même sexe (2013) ; immigration et
asile (2006, 2007, 2011, 2018, 2023) ; travail et emploi (2003, 2006, 2017, 2018, 2022) ;
énergie, climat et environnement (2004, 2009, 2010, 2019, 2021, 2023) ; sécurité, justice
et libertés publiques (2003, 2009, 2010, 2015, 2016, 2020, 2021) ; santé et fin de vie
(2004, 2009, 2015) ; bioéthique et IVG (2011, 2019, 2021, 2022, 2024) ; agriculture (2024) ;
défense et international (2008, 2011, 2019, 2022, 2023, 2024) ; laïcité et société.
Ne sont retenus ni les votes sur amendements ou sur articles, ni les motions de rejet, ni
les scrutins de portée locale ou purement technique.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

URL_ACTEURS = (
    "https://data.assemblee-nationale.fr/static/openData/repository/17/amo/"
    "tous_acteurs_mandats_organes_xi_legislature/"
    "AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip"
)
URL_SCRUTINS = {
    "14": "https://data.assemblee-nationale.fr/static/openData/repository/14/loi/"
          "scrutins/Scrutins_XIV.json.zip",
    "15": "https://data.assemblee-nationale.fr/static/openData/repository/15/loi/"
          "scrutins/Scrutins_XV.json.zip",
    "16": "https://data.assemblee-nationale.fr/static/openData/repository/16/loi/"
          "scrutins/Scrutins.json.zip",
}
URL_SCRUTIN_PAGE = "https://www.assemblee-nationale.fr/dyn/{leg}/scrutins/{num}"
URL_ANALYSE = "https://www.assemblee-nationale.fr/{leg}/scrutins/jo{num:04d}.asp"
URL_TABLE = "https://www.assemblee-nationale.fr/{leg}/scrutins/table-{annees}.asp"
URL_DEPUTE_PAGE = "https://www.assemblee-nationale.fr/dyn/deputes/{uid}"
URL_DEPUTE_MANDATS = "https://www.assemblee-nationale.fr/dyn/deputes/{uid}/fonctions?archive=oui"

TABLES = {
    "12": ["2002-2003", "2003-2004", "2004-2005", "2005-2006", "2006-2007"],
    "13": ["2007-2008", "2008-2009", "2009-2010", "2010-2011", "2011-2012"],
}

SOURCES = [
    {
        "titre": "Assemblée nationale — données ouvertes, scrutins des 14e, 15e et 16e législatures",
        "url": "https://data.assemblee-nationale.fr/travaux-parlementaires/votes",
        "licence": "Licence Ouverte / Open Licence (Etalab)",
    },
    {
        "titre": "Assemblée nationale — données ouvertes, historique des députés (acteurs, mandats, organes)",
        "url": "https://data.assemblee-nationale.fr/acteurs/historique-des-deputes",
        "licence": "Licence Ouverte / Open Licence (Etalab)",
    },
    {
        "titre": "Assemblée nationale — analyses des scrutins publics de la 13e législature (archives)",
        "url": "https://www.assemblee-nationale.fr/13/scrutins/table-2011-2012.asp",
        "licence": "Site officiel de l'Assemblée nationale",
    },
    {
        "titre": "Assemblée nationale — analyses des scrutins publics de la 12e législature (archives)",
        "url": "https://www.assemblee-nationale.fr/12/scrutins/table-2006-2007.asp",
        "licence": "Site officiel de l'Assemblée nationale",
    },
    {
        "titre": "Assemblée nationale — fiches des députés, anciens mandats et fonctions",
        "url": "https://www.assemblee-nationale.fr/dyn/deputes",
        "licence": "Site officiel de l'Assemblée nationale",
    },
]

# ------------------------------------------------------------------------------
# Candidats identifiés comme députés (actuels ou anciens) dans le référentiel AMO30.
# Liste et identifiants strictement identiques à scripts/votes_an.py ; le triplet
# prénom / nom / date de naissance sert de garde-fou contre les homonymes.
# ------------------------------------------------------------------------------
CANDIDATS_DEPUTES = {
    "melenchon": ("PA2150", "Jean-Luc", "Mélenchon", "1951-08-19"),
    "faure": ("PA609332", "Olivier", "Faure", "1968-08-18"),
    "guedj": ("PA1567", "Jérôme", "Guedj", "1972-01-23"),
    "royal": ("PA2650", "Ségolène", "Royal", "1953-09-22"),
    "maurel": ("PA842271", "Emmanuel", "Maurel", "1973-05-10"),
    "roussel": ("PA720692", "Fabien", "Roussel", "1969-04-16"),
    "ruffin": ("PA722142", "François", "Ruffin", "1975-10-18"),
    "cazeneuve": ("PA785", "Bernard", "Cazeneuve", "1963-06-02"),
    "hollande": ("PA1654", "François", "Hollande", "1954-08-12"),
    "batho": ("PA335999", "Delphine", "Batho", "1973-03-23"),
    "vallaud": ("PA719930", "Boris", "Vallaud", "1975-07-25"),
    "autain": ("PA588884", "Clémentine", "Autain", "1973-05-26"),
    "philippe": ("PA345619", "Édouard", "Philippe", "1970-11-28"),
    "attal": ("PA722190", "Gabriel", "Attal", "1989-03-16"),
    "becht": ("PA642935", "Olivier", "Becht", "1976-04-28"),
    "le-maire": ("PA331481", "Bruno", "Le Maire", "1969-04-15"),
    "darmanin": ("PA607846", "Gérald", "Darmanin", "1982-10-11"),
    "bayrou": ("PA410", "François", "Bayrou", "1951-05-25"),
    "bertrand": ("PA267080", "Xavier", "Bertrand", "1965-03-21"),
    "wauquiez": ("PA267285", "Laurent", "Wauquiez", "1975-04-12"),
    "barnier": ("PA368", "Michel", "Barnier", "1951-01-09"),
    "le-pen": ("PA720614", "Marine", "Le Pen", "1968-08-05"),
    "marechal": ("PA609709", "Marion", "Maréchal-Le Pen", "1989-12-10"),
    "dupont-aignan": ("PA1206", "Nicolas", "Dupont-Aignan", "1961-03-07"),
    "lassalle": ("PA1838", "Jean", "Lassalle", "1955-05-03"),
    "lucas-lundy": ("PA795636", "Benjamin", "Lucas-Lundy", "1990-10-08"),
    "brun": ("PA793624", "Philippe", "Brun", "1991-10-16"),
}

# ------------------------------------------------------------------------------
# Scrutins retenus. numéro -> questions clés dont le scrutin traite exactement le même
# sujet (liste vide sinon). Les commentaires reprennent l'objet officiel, raccourci.
# ------------------------------------------------------------------------------
# Législatures publiées en données ouvertes (décompte nominatif, identifiant d'acteur).
SCRUTINS_OPENDATA: dict[str, dict[int, list[str]]] = {
    "14": {
        1: [],          # déclaration de politique générale de Jean-Marc Ayrault (49-1)
        259: ["q25"],   # mariage aux couples de personnes de même sexe (1re lecture)
        511: ["q25"],   # mariage aux couples de personnes de même sexe (2e lecture)
        647: [],        # avenir et justice du système de retraites (1re lecture)
        914: [],        # transition énergétique pour la croissance verte (1re lecture)
        994: [],        # réforme de l'asile (1re lecture)
        1044: [],       # motion de censure (49-3, loi « Macron »)
        1070: [],       # nouveaux droits des malades et des personnes en fin de vie
        1106: [],       # modernisation de notre système de santé (1re lecture)
        1109: [],       # renseignement (1re lecture)
        1237: [],       # loi constitutionnelle de protection de la Nation (déchéance)
        1270: [],       # motion de censure (49-3, loi « travail »)
    },
    "15": {
        1: [],          # déclaration de politique générale d'Édouard Philippe (49-1)
        49: [],         # ordonnances pour le renforcement du dialogue social (1re lecture)
        351: ["q10"],   # orientation et réussite des étudiants (Parcoursup)
        578: [],        # immigration maîtrisée, droit d'asile effectif (1re lecture)
        2059: [],       # ratification de l'accord économique UE-Canada (CETA)
        2065: [],       # énergie et climat (CMP)
        2146: [],       # bioéthique (1re lecture)
        2706: [],       # motion de censure (49-3, système universel de retraite)
        3254: [],       # sécurité globale (1re lecture)
        3421: [],       # respect des principes de la République (1re lecture)
        3738: [],       # dérèglement climatique et résilience (1re lecture)
        3943: [],       # gestion de la crise sanitaire (1re lecture, passe sanitaire)
        4414: [],       # renforcement du droit à l'avortement (lecture définitive)
    },
    "16": {
        652: ["q17"],   # résolution de soutien à l'Ukraine
        823: [],        # accélération de la production d'énergies renouvelables
        1108: ["q33"],  # majorité numérique et lutte contre la haine en ligne
        1240: ["q05"],  # motion de censure (49-3, retraites : recul à 64 ans)
        1241: ["q05"],  # motion de censure (49-3, retraites : recul à 64 ans)
        1533: ["q11"],  # nouvelles installations nucléaires (nouvelle lecture)
        1778: [],       # loi de programmation militaire 2024-2030 (1re lecture)
        3213: [],       # contrôler l'immigration, améliorer l'intégration (CMP)
        3289: [],       # loi constitutionnelle, liberté de recourir à l'IVG
        3461: ["q17"],  # déclaration sur l'accord de sécurité franco-ukrainien (50-1)
        3966: [],       # souveraineté alimentaire et agricole (1re lecture)
    },
}

# Législatures disponibles seulement en pages HTML « analyse du scrutin » (archives).
SCRUTINS_ARCHIVE: dict[str, dict[int, list[str]]] = {
    "12": {
        1: [],          # déclaration de politique générale de Jean-Pierre Raffarin (49-1)
        114: [],        # loi pour la sécurité intérieure
        310: [],        # réforme des retraites (1re lecture)
        313: [],        # réforme des retraites (CMP)
        436: [],        # laïcité : signes religieux dans les écoles, collèges et lycées
        479: [],        # loi constitutionnelle, Charte de l'environnement
        642: [],        # assurance maladie
        678: [],        # droits des malades et fin de vie
        803: [],        # motion de censure (49-2)
        945: [],        # égalité des chances (contrat première embauche, CMP)
        979: [],        # immigration et intégration
    },
    "13": {
        33: [],         # maîtrise de l'immigration, intégration et asile (CMP)
        83: [],         # ratification du traité de Lisbonne
        323: [],        # motion de censure (49-2)
        360: [],        # hôpital, patients, santé et territoires (1re lecture)
        397: [],        # Grenelle de l'environnement (2e lecture)
        482: ["q30"],   # droit de vote et d'éligibilité des étrangers aux municipales
        564: [],        # engagement national pour l'environnement (Grenelle 2)
        595: [],        # interdiction de la dissimulation du visage dans l'espace public
        601: ["q05"],   # réforme des retraites (1re lecture, âge légal 60 → 62 ans)
        646: ["q05"],   # réforme des retraites (CMP, âge légal 60 → 62 ans)
        728: [],        # immigration, intégration et nationalité (CMP)
        737: [],        # bioéthique (2e lecture)
        786: [],        # déclaration sur l'intervention des forces armées en Libye
    },
}

TYPE_SCRUTIN = {"SPS": "solennel", "SAT": "solennel", "MOC": "motion_censure",
                "SPO": "ordinaire"}
# La 14e législature écrit « pour » et « contre » là où les 15e, 16e et 17e écrivent
# « pours » et « contres » : les deux graphies sont acceptées.
POSITION = {"pour": "pour", "pours": "pour", "contre": "contre", "contres": "contre",
            "abstention": "abstention", "abstentions": "abstention",
            "nonVotant": "non_votant", "nonVotants": "non_votant"}
# Le décompte de voix connaît les mêmes variantes ; « nonVotantsVolontaires » est un
# sous-ensemble des abstentions et n'est pas une position à part.
DECOMPTE = dict(POSITION)

A_VERIFIER = [
    "Périmètre : ce fichier ne couvre que l'Assemblée nationale, et uniquement les "
    "législatures XII à XVI (2002-2024). Les scrutins de la 17e législature sont dans "
    "data/votes-an.json ; le Sénat et le Parlement européen sont traités ailleurs.",
    "Disponibilité par législature : les 14e, 15e et 16e législatures sont publiées en "
    "données ouvertes avec décompte nominatif ; les 12e et 13e ne le sont pas et n'ont "
    "été lues que dans les pages HTML « analyse du scrutin » du site archivé de "
    "l'Assemblée. Pour la 11e législature (1997-2002) et les précédentes, aucune liste "
    "nominative n'est publiée en ligne : aucun vote antérieur à juin 2002 ne figure ici.",
    "Pages « analyse du scrutin » des 12e et 13e législatures : l'identification des "
    "votants s'y fait par prénom + nom, sans identifiant de député. Un vote n'est "
    "attribué à un candidat que si le prénom ET le nom correspondent exactement (accents "
    "et tirets normalisés) et si le candidat exerçait son mandat à la date du scrutin ; "
    "toute correspondance multiple ou hors mandat arrête le script.",
    "Scrutins non nominatifs écartés : quand un groupe vote en bloc, les pages des 12e et "
    "13e législatures écrivent « membres du groupe, présents ou ayant délégué leur droit "
    "de vote » sans nommer personne et ne citent que les dissidents. Ces scrutins sont "
    "rejetés par le script (contrôle nom à nom contre les décomptes annoncés) : c'est le "
    "cas, par exemple, du scrutin n° 779 du 21 juin 2011 sur la loi de bioéthique (CMP).",
    "Type de scrutin des 12e et 13e législatures : la distinction solennel / ordinaire "
    "n'est pas publiée telle quelle. Elle est déduite de l'entête de la page (« scrutin "
    "public à la tribune », « dans les salles voisines de la salle des séances ») et des "
    "tables chronologiques (section « salles voisines », astérisque « scrutin décidé en "
    "Conférence des Présidents en application de l'article 65-1 »). Avant la session "
    "2003-2004, les tables ne portent pas l'astérisque : les scrutins concernés sont donc "
    "rangés en « ordinaire » faute de mention contraire dans la source.",
    "Le jeu de données ouvertes de la 14e législature s'arrête au scrutin n° 1354 du "
    "24 novembre 2016 et celui de la 15e au scrutin n° 4417 du 24 février 2022, alors que "
    "ces législatures se sont achevées en juin 2017 et juin 2022 : les derniers mois n'y "
    "figurent pas. Aucun scrutin retenu ici n'est concerné.",
    "Mandats : le jeu « historique des députés » (AMO30) ne remonte qu'à la 12e "
    "législature (2002) et ignore le mandat de Xavier Bertrand de 2002 à 2004. Les "
    "mandats manquants — antérieurs à 2002 et celui-là — sont repris de la fiche "
    "officielle du député sur assemblee-nationale.fr (rubrique « Anciens mandats et "
    "fonctions »), qui remonte à la 6e législature pour Michel Barnier. Ces mandats "
    "anciens n'indiquent pas la circonscription.",
    "Les dates de mandat retenues sont les dates d'exercice effectif (prise de fonction "
    "et fin), et non les dates d'ouverture et de clôture de la législature : un député "
    "entré au Gouvernement puis revenu au Palais-Bourbon apparaît donc avec plusieurs "
    "périodes, et il n'est pas compté comme membre entre les deux.",
    "Les « mises au point au sujet du présent scrutin » (corrections déclarées après coup "
    "par des députés) ne sont pas appliquées : le vote publié dans le décompte nominatif "
    "officiel est repris tel quel.",
    "« absent » signifie : député en exercice à cette date mais ne figurant dans aucune "
    "des listes nominatives du scrutin. « non_votant » reprend la catégorie officielle "
    "des non-votants (présidence de séance, membres du Gouvernement, etc.).",
    "Motions de censure : seuls les votes « pour » sont recensés, une motion n'étant "
    "adoptée que si elle réunit la majorité des membres de l'Assemblée. « absent » y "
    "signifie donc « n'a pas voté la censure » et non « était absent de l'hémicycle ».",
    "60 scrutins retenus sur les quelque 11 000 scrutins publics de ces cinq "
    "législatures, dont une minorité seulement est nominative pour les 12e et 13e. Les "
    "critères de sélection, identiques pour tous les candidats, sont détaillés en tête de "
    "scripts/votes_an_historique.py.",
    "Un scrutin n'est relié à une question clé que lorsqu'il porte exactement sur le même "
    "objet. Les lois de 2005 et 2016 sur la fin de vie ne sont donc pas reliées à la "
    "question sur l'aide à mourir : elles écartaient explicitement l'aide active à mourir. "
    "De même, la loi de 2010 interdisant la dissimulation du visage dans l'espace public "
    "n'est pas reliée à la question sur le port du voile.",
    "Les intitulés reprennent l'objet officiel du scrutin tel qu'il est publié, sans "
    "retouche : quelques libellés de la 15e législature figurent sans accents dans la "
    "source (« la declaration de politique generale du Gouvernement de M. Edouard "
    "Philippe »).",
    "La page de licence de data.assemblee-nationale.fr renvoie à la « Licence Ouverte / "
    "Open Licence » d'Etalab sans en indiquer le numéro de version. Les pages archivées "
    "des 12e et 13e législatures ne portent pas de mention de licence.",
]


# ------------------------------------------------------------------------------
# Téléchargement / cache
# ------------------------------------------------------------------------------
def telecharger(url: str, dest: Path, offline: bool) -> Path:
    if dest.exists() and dest.stat().st_size:
        return dest
    if offline:
        sys.exit(f"Fichier absent du cache et mode --offline : {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"téléchargement {url}", file=sys.stderr)
    with urllib.request.urlopen(url, timeout=120) as reponse:
        dest.write_bytes(reponse.read())
    return dest


def decompresser(zip_path: Path, dossier: Path) -> Path:
    if not dossier.exists():
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(dossier)
    return dossier


# ------------------------------------------------------------------------------
# Utilitaires
# ------------------------------------------------------------------------------
def texte(v):
    """Les champs XML convertis en JSON sont tantôt une chaîne, tantôt {'#text': ...}."""
    return v.get("#text") if isinstance(v, dict) else v


def liste(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def sans_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("-", " ")).strip()


def cle_nom(prenom: str, nom: str) -> str:
    """Clé de comparaison : accents, tirets, ponctuation et n° de département ôtés."""
    s = sans_accents(f"{prenom} {nom}")
    s = re.sub(r"\(\s*\d+\s*\)", " ", s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z' ]", " ", s)).strip()


def capitaliser(s: str) -> str:
    s = (s or "").strip()
    return s[:1].upper() + s[1:] if s else s


def ordinal(n: str) -> str:
    return f"{n}re" if n == "1" else f"{n}e"


def nettoyer(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s).replace("\xa0", " ")).strip()


# ------------------------------------------------------------------------------
# Mandats : référentiel AMO30 complété par la fiche officielle du député
# ------------------------------------------------------------------------------
MOIS = {"janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11,
        "décembre": 12}
RE_MANDAT_FICHE = re.compile(
    r"(\d{1,2})\s*e?\s*l[ée]gislature\s*:\s*(?:R[ée][ée]lu|[ÉE]lu)e?\s*le\s*[^-]{0,40}-\s*"
    r"Mandat du\s+(\d{1,2}(?:er)?\s+[^\s]+\s+\d{4})\s*\(([^)]*)\)\s*"
    r"(?:au\s+(\d{1,2}(?:er)?\s+[^\s]+\s+\d{4})\s*\(([^)]*)\))?", re.I)


def jour_francais(s: str) -> str:
    j, m, a = s.replace("1er", "1").split()
    if m.lower() not in MOIS:
        raise ValueError(f"mois inconnu : {m}")
    return f"{int(a):04d}-{MOIS[m.lower()]:02d}-{int(j):02d}"


def mandats_fiche(octets: bytes) -> list[dict]:
    """Mandats de député lus sur la fiche officielle (rubrique « Anciens mandats »)."""
    t = octets.decode("utf-8", errors="replace")
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = nettoyer(t)
    depart = t.find("Fonctions à l'Assemblée nationale")
    sortie = []
    for m in RE_MANDAT_FICHE.finditer(t[depart if depart > 0 else 0:]):
        sortie.append({
            "legislature": m.group(1),
            "debut": jour_francais(m.group(2)),
            "fin": jour_francais(m.group(4)) if m.group(4) else None,
            "cause_fin": (m.group(5) or "").strip() or None,
        })
    return sortie


def lire_mandats(dossier_acteurs: Path, cache: Path, offline: bool,
                 aujourdhui: str) -> dict[str, list[dict]]:
    mandats: dict[str, list[dict]] = {}
    for cid, (uid, prenom, nom, naissance) in CANDIDATS_DEPUTES.items():
        chemin = dossier_acteurs / "json" / "acteur" / f"{uid}.json"
        if not chemin.exists():
            sys.exit(f"Acteur introuvable dans le référentiel : {uid} ({cid})")
        acteur = json.loads(chemin.read_text(encoding="utf-8"))["acteur"]
        ident = acteur["etatCivil"]["ident"]
        vu = (texte(ident.get("prenom")), texte(ident.get("nom")),
              texte((acteur["etatCivil"].get("infoNaissance") or {}).get("dateNais")))
        if vu != (prenom, nom, naissance):
            sys.exit(f"Homonyme probable pour {cid} ({uid}) : attendu "
                     f"{(prenom, nom, naissance)}, trouvé {vu}")
        civ = texte(ident.get("civ")) or ""
        titre = "Députée" if civ.startswith("Mme") else "Député"

        # 1. référentiel de données ouvertes : législatures 12 à 17, avec circonscription
        ouvert, vus = {}, set()
        for m in liste(acteur.get("mandats", {}).get("mandat")):
            if m.get("typeOrgane") != "ASSEMBLEE":
                continue
            mandature = m.get("mandature") or {}
            debut = mandature.get("datePriseFonction") or m.get("dateDebut")
            cle = (m.get("legislature"), debut, m.get("dateFin"))
            if cle in vus:
                continue
            vus.add(cle)
            lieu = (m.get("election") or {}).get("lieu") or {}
            circo = (f" ({lieu.get('departement')}, "
                     f"{ordinal(lieu.get('numCirco') or '')} circonscription)"
                     if lieu.get("departement") else "")
            ouvert[cle] = {
                "chambre": "AN",
                "detail": f"{titre}{circo} — {ordinal(m.get('legislature'))} législature",
                "debut": debut,
                "fin": m.get("dateFin"),
                "source": {
                    "titre": f"Assemblée nationale — fiche de {prenom} {nom}",
                    "url": URL_DEPUTE_PAGE.format(uid=uid),
                    "date": aujourdhui,
                },
            }

        # 2. fiche officielle : mandats absents du référentiel (avant 2002, et Bertrand 2002)
        page = telecharger(URL_DEPUTE_MANDATS.format(uid=uid),
                           cache / "fiches" / f"{uid}.html", offline)
        for m in mandats_fiche(page.read_bytes()):
            cle = (m["legislature"], m["debut"], m["fin"])
            if cle in ouvert:
                continue
            ouvert[cle] = {
                "chambre": "AN",
                "detail": f"{titre} — {ordinal(m['legislature'])} législature",
                "debut": m["debut"],
                "fin": m["fin"],
                "source": {
                    "titre": f"Assemblée nationale — anciens mandats de {prenom} {nom}",
                    "url": URL_DEPUTE_MANDATS.format(uid=uid),
                    "date": aujourdhui,
                },
            }

        lignes = sorted(ouvert.values(),
                        key=lambda x: (x["debut"] or "", x["fin"] or "9999"), reverse=True)
        mandats[cid] = lignes
    return mandats


def membre_le(mandats: list[dict], jour: str) -> bool:
    return any(m["debut"] and m["debut"] <= jour and (m["fin"] is None or jour <= m["fin"])
               for m in mandats)


# ------------------------------------------------------------------------------
# Scrutins publiés en données ouvertes (14e, 15e, 16e législatures)
# ------------------------------------------------------------------------------
def votes_par_acteur(scrutin: dict, etiquette: str) -> dict[str, str]:
    """acteurRef -> pour / contre / abstention / non_votant.

    Contrôle, groupe par groupe et position par position, que le nombre de noms lus
    égale le décompte de voix annoncé : sans cela, un scrutin dont les listes
    nominatives seraient incomplètes ferait passer des votants pour des absents.
    """
    resultat = {}
    for groupe in liste(scrutin["ventilationVotes"]["organe"]["groupes"]["groupe"]):
        vote = groupe.get("vote") or {}
        decompte = vote.get("decompteNominatif") or {}
        lus: dict[str, int] = {}
        for cle, bloc in decompte.items():
            position = POSITION.get(cle)
            if position is None or not isinstance(bloc, dict):
                continue
            for votant in liste(bloc.get("votant")):
                if isinstance(votant, dict) and votant.get("acteurRef"):
                    resultat[votant["acteurRef"]] = position
                    lus[position] = lus.get(position, 0) + 1
        annonces = {"pour": 0, "contre": 0, "abstention": 0, "non_votant": 0}
        for cle, valeur in (vote.get("decompteVoix") or {}).items():
            if cle == "nonVotantsVolontaires" or cle not in DECOMPTE:
                continue
            annonces[DECOMPTE[cle]] += int(valeur or 0)
        for position, annonce in annonces.items():
            if lus.get(position, 0) != annonce:
                sys.exit(f"{etiquette} : groupe {groupe.get('organeRef')}, "
                         f"{annonce} voix « {position} » annoncées mais "
                         f"{lus.get(position, 0)} noms publiés")
    return resultat


def charger_scrutins_ouverts(cache: Path, offline: bool) -> dict[str, dict[int, dict]]:
    """{législature: {numéro: scrutin}} pour les seuls scrutins retenus."""
    sortie: dict[str, dict[int, dict]] = {}
    for leg, url in URL_SCRUTINS.items():
        zip_path = telecharger(url, cache / f"Scrutins_{leg}.zip", offline)
        dossier = decompresser(zip_path, cache / f"scrutins_{leg}")
        voulus = SCRUTINS_OPENDATA[leg]
        trouves: dict[int, dict] = {}
        unique = list(dossier.rglob("Scrutins_*.json"))
        if unique:                                   # 14e : un seul fichier global
            for s in json.loads(unique[0].read_text(encoding="utf-8"))["scrutins"]["scrutin"]:
                if int(s["numero"]) in voulus:
                    trouves[int(s["numero"])] = s
        else:                                        # 15e et 16e : un fichier par scrutin
            for numero in voulus:
                chemin = dossier / "json" / f"VTANR5L{leg}V{numero}.json"
                if chemin.exists():
                    trouves[numero] = json.loads(chemin.read_text(encoding="utf-8"))["scrutin"]
        manquants = sorted(set(voulus) - set(trouves))
        if manquants:
            sys.exit(f"Scrutins introuvables pour la {leg}e législature : {manquants}")
        sortie[leg] = trouves
    return sortie


def scrutins_ouverts(cache: Path, offline: bool,
                     mandats: dict[str, list[dict]]) -> list[dict]:
    sortie = []
    for leg, scrutins in charger_scrutins_ouverts(cache, offline).items():
        for numero, questions in SCRUTINS_OPENDATA[leg].items():
            s = scrutins[numero]
            if s.get("legislature") != leg:
                sys.exit(f"Scrutin {leg}/{numero} : législature inattendue "
                         f"{s.get('legislature')}")
            if s.get("modePublicationDesVotes") != "DecompteNominatif":
                sys.exit(f"Scrutin {leg}/{numero} : vote non nominatif "
                         f"({s.get('modePublicationDesVotes')})")
            jour = s["dateScrutin"]
            positions = votes_par_acteur(s, f"Scrutin {leg}/{numero}")
            votes = {}
            for cid, (uid, *_reste) in CANDIDATS_DEPUTES.items():
                if not membre_le(mandats[cid], jour):
                    continue        # non membre à cette date : absent du champ « votes »
                votes[cid] = positions.get(uid, "absent")
            sortie.append({
                "id": f"an-{leg}-{numero}",
                "chambre": "AN",
                "date": jour,
                "titre": capitaliser(s.get("titre") or (s.get("objet") or {}).get("libelle")),
                "type": TYPE_SCRUTIN.get(s["typeVote"]["codeTypeVote"], "ordinaire"),
                "resultat": (s.get("sort") or {}).get("code"),
                "url": URL_SCRUTIN_PAGE.format(leg=leg, num=numero),
                "questions": questions,
                "votes": dict(sorted(votes.items())),
            })
    return sortie


# ------------------------------------------------------------------------------
# Scrutins des 12e et 13e législatures : pages HTML « analyse du scrutin »
# ------------------------------------------------------------------------------
RE_P = re.compile(r"<p\b[^>]*>(.*?)</p\s*>", re.I | re.S)
RE_B = re.compile(r"<b\b[^>]*>(.*?)</b\s*>", re.I | re.S)
RE_VOTE = re.compile(r"^(?:\s|<[^>]+>)*(pour|contre|abstentions?|non[- ]votants?)(?:\(s\))?"
                     r"\s*:?[.\s]*(?:(?:\s|<[^>]+>)*(\d+))?", re.I)
RE_GROUPE = re.compile(r"^(groupe\b|(?:d[ée]put[ée]e?s?\s+)?non[- ]inscrits?\b"
                       r"|d[ée]put[ée]e?s?\s+n'appartenant)", re.I)
POSITIONS_HTML = {"pour": "pour", "contre": "contre", "abstention": "abstention",
                  "abstentions": "abstention", "non-votant": "non_votant",
                  "non-votants": "non_votant", "non votant": "non_votant",
                  "non votants": "non_votant"}
RE_SECTION = re.compile(r"Scrutins\s+publics\s+[àa]\s+la\s+tribune"
                        r"|salles\s+voisines\s+de\s+la\s+salle\s+des\s+s[ée]ances"
                        r"|Scrutins\s+publics\s+ordinaires", re.I)


def decoder(octets: bytes) -> str:
    """Les archives mélangent iso-8859-1 (12e) et utf-8 (13e) : on lit le meta charset."""
    m = re.search(rb"charset=([\w-]+)", octets[:4000])
    enc = m.group(1).decode("ascii").lower() if m else "iso-8859-1"
    return octets.decode(enc, errors="replace")


def noms_du_paragraphe(par: str) -> list[tuple[str, str]]:
    """[(prénom éventuellement suivi d'une particule, nom)] pour chaque <b> du paragraphe."""
    sortie, pos = [], 0
    for m in RE_B.finditer(par):
        avant = nettoyer(par[pos:m.start()])
        pos = m.end()
        avant = re.sub(r"^\s*\([^)]*\)", "", avant)          # (Président de l'Assemblée…)
        avant = re.sub(r"^[\s,;.]*(?:et|puis)?\s*", "", avant, flags=re.I)
        avant = re.sub(r"^(MM\.|M\.|Mmes|Mme|Mlles?)\s*", "", avant)
        sortie.append((re.sub(r"^[\s,;.]*", "", avant).strip(), nettoyer(m.group(1))))
    return sortie


def analyser_page(octets: bytes) -> dict:
    """Entête, groupes et listes nominatives d'une page « analyse du scrutin »."""
    t = decoder(octets)
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    apres_menu = t.lower().find("</header>")
    debut = t.lower().find("analyse du scrutin", apres_menu if apres_menu > 0 else 0)
    corps = t[debut:] if debut > 0 else t
    coupe = re.search(r"MISES?\s+AU\s+POINT\s+AU\s+SUJET", corps, re.I)
    if coupe:                                   # corrections postérieures : non reprises
        corps = corps[:coupe.start()]

    groupes, courant, position, nominatif = [], None, None, True
    for m in RE_P.finditer(corps):
        par = m.group(1)
        if not nettoyer(par):
            continue
        mv = RE_VOTE.match(par)
        if mv:
            position = POSITIONS_HTML[mv.group(1).lower()]
            if courant is not None:
                courant["annonces"][position] = int(mv.group(2)) if mv.group(2) else None
            par = mv.string[mv.end():]          # « ABSTENTION : 1 M. Joël <b>Sarlot</b> »
            if not nettoyer(par):
                continue
        elif RE_GROUPE.match(nettoyer(par)):
            courant = {"nom": nettoyer(par), "annonces": {}, "noms": {}}
            groupes.append(courant)
            position = None
            continue
        if courant is None or position is None:
            continue
        noms = [n for n in noms_du_paragraphe(par)
                if not n[1].strip().isdigit() and re.search(r"[^\W\d_]", n[1])]
        if noms:
            courant["noms"].setdefault(position, []).extend(noms)
        elif re.search(r"membres?\s+du\s+groupe", nettoyer(par), re.I):
            nominatif = False                   # vote de groupe : aucun nom publié
            courant["noms"].setdefault(position, [])
    for g in groupes:
        for pos, annonce in g["annonces"].items():
            if annonce is not None and len(g["noms"].get(pos, [])) != annonce:
                nominatif = False
    return {"groupes": groupes, "nominatif": nominatif, "corps": nettoyer(corps[:4000])}


def entete_page(octets: bytes) -> dict:
    """Numéro, date, objet, résultat et caractère solennel lus sur la page."""
    brut = decoder(octets)
    brut = re.sub(r"<script.*?</script>", " ", brut, flags=re.S | re.I)
    brut = re.sub(r"<style.*?</style>", " ", brut, flags=re.S | re.I)
    brut = re.sub(r"<head\b.*?</head\s*>", " ", brut, flags=re.S | re.I)   # le <title>
    t = nettoyer(brut)                                                      # reprend l'objet
    m = re.search(r"analyse du scrutin n[°o]\s*(\d+)\s*-\s*(.*?)s[ée]ances? du\s*:?\s*"
                  r"(\d{1,2})\s*(?:er|ère|re)?[/\s]+([^\s/]+)[/\s]+(\d{4})", t, re.I)
    if not m:
        raise ValueError("entête de scrutin illisible")
    brut = sans_accents(m.group(4))
    mois = {sans_accents(k): v for k, v in MOIS.items()}
    numero_mois = mois[brut] if brut in mois else int(m.group(4))
    jour = f"{m.group(5)}-{numero_mois:02d}-{int(m.group(3)):02d}"

    objet = re.search(r"SCRUTIN PUBLIC\s*(.*?)\s*SUR\s*:?\s*(.*?)\s*"
                      r"(?=Nombre de votants|Majorit[ée]\s|Pour l'adoption|"
                      r"L'Assembl[ée]e nationale)", t, re.I | re.S)
    if not objet:
        raise ValueError("objet du scrutin illisible")
    solennel = bool(re.search(r"tribune|salles voisines", objet.group(1), re.I))
    adopte = re.search(r"L'Assembl[ée]e nationale (n'a pas adopt[ée]|a adopt[ée])", t, re.I)
    return {
        "numero": m.group(1),
        "date": jour,
        "objet": objet.group(2).strip(" .:"),
        "solennel": solennel,
        "resultat": ("rejeté" if adopte and adopte.group(1).lower().startswith("n'a")
                     else "adopté" if adopte else None),
    }


def types_des_tables(cache: Path, offline: bool, leg: str) -> dict[str, str]:
    """{numéro: 'solennel'|'ordinaire'} d'après les tables chronologiques de la législature.

    Les tables rangent les scrutins en trois blocs (« à la tribune », « dans les salles
    voisines de la salle des séances », « ordinaires ») et marquent d'un astérisque les
    scrutins décidés en Conférence des Présidents en application de l'article 65-1.
    """
    resultat: dict[str, str] = {}
    for annees in TABLES[leg]:
        page = telecharger(URL_TABLE.format(leg=leg, annees=annees),
                           cache / "tables" / f"{leg}-{annees}.html", offline)
        t = re.sub(r"\s+", " ", page.read_bytes().decode("iso-8859-1", errors="replace"))
        depart = re.search(r"TABLE\s+CHRONOLOGIQUE", t, re.I)  # ignorer le menu du site
        t = t[depart.start():] if depart else t
        bornes = [(m.start(), "ordinaire" if "ordinaires" in m.group(0).lower()
                   else "solennel") for m in RE_SECTION.finditer(t)]
        for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I):
            tr = m.group(1)
            if "analyse" not in tr.lower():
                continue
            cellules = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)
            if not cellules:
                continue
            brut = nettoyer(cellules[0])
            numero = re.match(r"\s*(\d+)", brut)
            if not numero:
                continue
            section = None
            for pos, nom in bornes:
                if pos < m.start():
                    section = nom
            resultat[numero.group(1)] = ("solennel" if "*" in brut or section == "solennel"
                                         else "ordinaire")
    return resultat


def scrutins_archives(cache: Path, offline: bool,
                      mandats: dict[str, list[dict]]) -> tuple[list[dict], list[str]]:
    sortie, avertissements = [], []
    cles = {cle_nom(p, n): cid for cid, (_u, p, n, _d) in CANDIDATS_DEPUTES.items()}
    for leg, voulus in SCRUTINS_ARCHIVE.items():
        types = types_des_tables(cache, offline, leg)
        for numero, questions in voulus.items():
            page = telecharger(URL_ANALYSE.format(leg=leg, num=numero),
                               cache / "analyses" / f"{leg}-{numero:04d}.html", offline)
            octets = page.read_bytes()
            entete = entete_page(octets)
            if entete["numero"] != str(numero):
                sys.exit(f"Scrutin {leg}/{numero} : la page annonce le n° {entete['numero']}")
            lu = analyser_page(octets)
            if not lu["nominatif"]:
                avertissements.append(
                    f"Scrutin n° {numero} du {entete['date']} ({ordinal(leg)} législature) : "
                    f"la page officielle ne publie pas tous les votes nom par nom "
                    f"(vote de groupe) ; il n'est donc pas repris.")
                continue

            jour = entete["date"]
            positions: dict[str, str] = {}
            for groupe in lu["groupes"]:
                for position, noms in groupe["noms"].items():
                    for prenom, nom in noms:
                        cid = cles.get(cle_nom(prenom, nom))
                        if cid is None:
                            continue
                        if cid in positions:
                            sys.exit(f"Scrutin {leg}/{numero} : {cid} figure deux fois "
                                     f"dans les listes nominatives (homonyme ?)")
                        if not membre_le(mandats[cid], jour):
                            sys.exit(f"Scrutin {leg}/{numero} : « {prenom} {nom} » "
                                     f"correspond à {cid}, qui n'exerçait pas de mandat "
                                     f"le {jour} (homonyme)")
                        positions[cid] = position

            votes = {cid: positions.get(cid, "absent")
                     for cid in CANDIDATS_DEPUTES if membre_le(mandats[cid], jour)}
            objet = entete["objet"]
            type_scrutin = ("motion_censure" if re.search(r"motion de censure", objet, re.I)
                            else "solennel" if entete["solennel"]
                            or types.get(str(numero)) == "solennel"
                            else "ordinaire")
            sortie.append({
                "id": f"an-{leg}-{numero}",
                "chambre": "AN",
                "date": jour,
                "titre": capitaliser(objet),
                "type": type_scrutin,
                "resultat": entete["resultat"],
                "url": URL_ANALYSE.format(leg=leg, num=numero),
                "questions": questions,
                "votes": dict(sorted(votes.items())),
            })
    return sortie, avertissements


# ------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default=None,
                        help="dossier de travail pour les jeux de données (hors dépôt)")
    parser.add_argument("--out", default=str(ROOT / "data" / "votes-an-historique.json"))
    parser.add_argument("--offline", action="store_true",
                        help="échouer plutôt que télécharger si le cache est vide")
    args = parser.parse_args()

    import tempfile
    cache = Path(args.cache or Path(tempfile.gettempdir()) / "votes_an_historique_cache")
    cache.mkdir(parents=True, exist_ok=True)

    acteurs = decompresser(telecharger(URL_ACTEURS, cache / "AMO30.json.zip", args.offline),
                           cache / "amo30")

    aujourdhui = date.today().isoformat()
    tous = [c["id"] for c in json.loads(
        (ROOT / "data" / "candidats.json").read_text(encoding="utf-8"))["candidats"]]
    inconnus = set(CANDIDATS_DEPUTES) - set(tous)
    if inconnus:
        sys.exit(f"Identifiants absents de data/candidats.json : {sorted(inconnus)}")

    trouves = lire_mandats(acteurs, cache, args.offline, aujourdhui)
    mandats = {cid: trouves.get(cid, []) for cid in tous}

    scrutins = scrutins_ouverts(cache, args.offline, mandats)
    archives, avertissements = scrutins_archives(cache, args.offline, mandats)
    scrutins += archives
    scrutins.sort(key=lambda r: (r["date"], r["id"]), reverse=True)

    document = {
        "mise_a_jour": aujourdhui,
        "sources": SOURCES,
        "mandats": mandats,
        "scrutins": scrutins,
        "a_verifier": A_VERIFIER + avertissements,
    }
    out = Path(args.out)
    out.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    votes = sum(len(s["votes"]) for s in scrutins)
    couverts = sorted({cid for s in scrutins for cid in s["votes"]})
    print(f"{len(scrutins)} scrutins, {votes} votes nominatifs, "
          f"{len(couverts)} candidats couverts → {out}")


if __name__ == "__main__":
    main()
