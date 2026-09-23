#!/usr/bin/env python3
"""Produit data/votes-an.json : mandats de député et votes nominatifs des candidats.

Reproductible : le script télécharge lui-même les deux jeux de données ouvertes de
l'Assemblée nationale (Licence Ouverte / Open Licence, Etalab), les décompresse dans un
cache hors du dépôt, puis agrège.

    python3 scripts/votes_an.py [--cache DOSSIER] [--out FICHIER] [--offline]

Voir docs/methode-votes.md. Ce fichier ne couvre QUE l'Assemblée nationale
(chambre « AN ») ; le Sénat et le Parlement européen sont traités ailleurs.

--------------------------------------------------------------------------------
Sources
--------------------------------------------------------------------------------
- Acteurs / mandats / organes, historique (législatures 12 à 17) :
  https://data.assemblee-nationale.fr/static/openData/repository/17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip
- Scrutins publics de la 17e législature :
  https://data.assemblee-nationale.fr/static/openData/repository/17/loi/scrutins/Scrutins.json.zip
- Page officielle d'un scrutin :
  https://www.assemblee-nationale.fr/dyn/17/scrutins/<numero>
- Page officielle d'un député :
  https://www.assemblee-nationale.fr/dyn/deputes/<PAxxxx>

--------------------------------------------------------------------------------
Critères de sélection des scrutins (les mêmes pour tous les candidats)
--------------------------------------------------------------------------------
La 17e législature compte 8 434 scrutins publics, dont 72 solennels et 23 motions de
censure. On retient 60 scrutins :

1. les 23 motions de censure de la législature, sans exception ;
2. parmi les scrutins solennels, ceux qui portent sur les textes marquants listés par
   la méthode (retraites, lois de finances, immigration, énergie, fin de vie, santé,
   agriculture, sécurité et libertés publiques) ainsi que les déclarations de
   politique générale et de l'article 50-1 ; les votes de lecture définitive ou de
   commission mixte paritaire sont préférés aux lectures intermédiaires du même texte ;
3. quelques scrutins publics ordinaires portant sur le vote final d'un texte dont
   l'objet recoupe une question clé et qui n'a pas fait l'objet d'un scrutin solennel
   (retraites, ISF, déserts médicaux, Mercosur).

Ne sont retenus ni les votes sur amendements, ni les motions de rejet préalable, ni les
scrutins solennels purement techniques ou de portée locale (lois spéciales de fin
d'année, textes Mayotte / Nouvelle-Calédonie, JO 2030, sport professionnel...), afin de
tenir la cible de 25 à 60 scrutins. Tous les scrutins non retenus restent consultables
dans le jeu de données source.
"""

from __future__ import annotations

import argparse
import json
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
URL_SCRUTINS = (
    "https://data.assemblee-nationale.fr/static/openData/repository/17/loi/"
    "scrutins/Scrutins.json.zip"
)
URL_SCRUTIN_PAGE = "https://www.assemblee-nationale.fr/dyn/17/scrutins/{num}"
URL_DEPUTE_PAGE = "https://www.assemblee-nationale.fr/dyn/deputes/{uid}"
LEGISLATURE = "17"

SOURCES = [
    {
        "titre": "Assemblée nationale — données ouvertes, scrutins de la 17e législature",
        "url": "https://data.assemblee-nationale.fr/travaux-parlementaires/votes",
        "licence": "Licence Ouverte / Open Licence (Etalab)",
    },
    {
        "titre": "Assemblée nationale — données ouvertes, historique des députés (acteurs, mandats, organes)",
        "url": "https://data.assemblee-nationale.fr/acteurs/historique-des-deputes",
        "licence": "Licence Ouverte / Open Licence (Etalab)",
    },
]

# ------------------------------------------------------------------------------
# Candidats identifiés comme députés (actuels ou anciens) dans le référentiel AMO30.
# Le triplet prénom / nom / date de naissance sert de garde-fou contre les homonymes :
# le script s'arrête si l'acteur ne correspond pas.
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
# Scrutins retenus : numéro -> questions clés dont le scrutin traite exactement
# le même sujet (liste vide sinon). Voir les critères en tête de fichier.
# ------------------------------------------------------------------------------
SCRUTINS_RETENUS: dict[int, list[str]] = {
    # --- motions de censure (les 23 de la législature) -------------------------
    1: [], 519: [], 526: [], 693: [], 694: [], 739: [], 791: [], 842: [],
    2222: [], 2876: [], 3058: [], 3059: [], 4986: [], 4987: [], 5154: [],
    5155: [], 5193: [], 5194: [], 5284: [], 5285: [], 5730: [], 5731: [],
    7979: [],
    # --- budgets et fiscalité -------------------------------------------------
    438: [],    # PLF 2025, première partie (1re lecture)
    881: ["q01"],   # impôt plancher de 2 % sur le patrimoine des ultra-riches
    4241: [],   # PLF 2026, première partie (1re lecture)
    4442: [],   # loi de fin de gestion 2025 (CMP)
    4758: [],   # PLFSS 2026 (lecture définitive)
    # --- retraites ------------------------------------------------------------
    217: ["q05"],   # annulation des réformes sur l'âge de départ et les annuités
    # --- santé et fin de vie --------------------------------------------------
    1607: ["q07"],  # lutte contre les déserts médicaux (1re lecture)
    2107: ["q08"],  # droit à l'aide à mourir (1re lecture)
    8280: ["q08"],  # droit à l'aide à mourir (lecture définitive)
    # --- énergie et climat ----------------------------------------------------
    2653: [],   # programmation nationale pour l'énergie et le climat 2025-2035
    # --- agriculture et commerce ----------------------------------------------
    456: [],    # déclaration du Gouvernement sur l'accord UE-Mercosur (art. 50-1)
    691: [],    # résolution refusant la ratification de l'accord UE-Mercosur
    844: [],    # loi d'orientation pour la souveraineté alimentaire (CMP)
    2957: [],   # lever les contraintes à l'exercice du métier d'agriculteur (CMP)
    8427: [],   # urgence pour la protection et la souveraineté agricoles (CMP)
    # --- sécurité et justice --------------------------------------------------
    1041: [],   # renforcement de la sûreté dans les transports (CMP)
    1473: [],   # sortir la France du piège du narcotrafic (CMP)
    1624: [],   # autorité de la justice envers les mineurs délinquants (CMP)
    7987: [],   # présomption de légitime défense pour les forces de l'ordre
    8042: [],   # justice criminelle et respect des victimes (CMP)
    8433: [],   # réponses immédiates aux troubles à l'ordre public (CMP)
    # --- immigration et nationalité -------------------------------------------
    1308: [],   # accès à la nationalité française à Mayotte (CMP)
    2958: [],   # maintien en rétention de personnes condamnées (1re lecture)
    7405: [],   # sécurité, rétention administrative, risques d'attentat (CMP)
    # --- défense et international ---------------------------------------------
    988: ["q17"],   # résolution européenne : renforcement du soutien à l'Ukraine
    4698: [],   # déclaration sur la stratégie de défense nationale (art. 50-1)
    7905: [],   # actualisation de la loi de programmation militaire (CMP)
    # --- institutions et territoires ------------------------------------------
    1303: [],   # mode de scrutin aux élections municipales (2e lecture)
    3054: [],   # déclaration de politique générale de M. François Bayrou
    7454: [],   # loi constitutionnelle pour une Corse autonome (1re lecture)
    # --- société, éducation, numérique ----------------------------------------
    2880: [],   # antisémitisme dans l'enseignement supérieur (CMP)
    8430: [],   # protection des enfants (1re lecture)
    8431: ["q33"],  # protection des mineurs face aux réseaux sociaux (CMP)
    # --- économie, travail, logement ------------------------------------------
    6184: [],   # simplification de la vie économique (CMP)
    6319: [],   # lutte contre les fraudes sociales et fiscales (CMP)
    7260: [],   # transposition de l'accord d'assurance chômage (2e lecture)
    7408: [],   # accès au logement des travailleurs des services publics (CMP)
}

TYPE_SCRUTIN = {"SPS": "solennel", "MOC": "motion_censure", "SPO": "ordinaire"}
POSITION = {
    "pours": "pour",
    "contres": "contre",
    "abstentions": "abstention",
    "nonVotants": "non_votant",
}

A_VERIFIER = [
    "Périmètre : ce fichier ne couvre que l'Assemblée nationale. Un candidat dont la "
    "liste de mandats est vide n'a jamais été député ; il a pu être sénateur ou député "
    "européen, ce que ce fichier ne dit pas.",
    "Le jeu « historique des députés » de l'Assemblée (AMO30) ne remonte qu'à la 12e "
    "législature (2002). Les mandats de député antérieurs à 2002 — notamment ceux de "
    "François Bayrou, François Hollande et Ségolène Royal — n'y figurent pas et ne sont "
    "donc pas listés ici : à compléter avec une autre source officielle.",
    "Les scrutins publics mis en ligne pour la 17e législature commencent le 8 octobre "
    "2024 ; les séances de juillet et septembre 2024 ne donnent lieu à aucun scrutin "
    "public dans le jeu de données.",
    "60 scrutins retenus sur les 8 434 de la législature (dont 72 solennels et 23 "
    "motions de censure) : les 23 motions de censure et 34 des 72 scrutins solennels. "
    "Les solennels écartés sont soit des lectures intermédiaires d'un texte déjà retenu, "
    "soit des textes techniques ou de portée locale (voir les critères dans "
    "scripts/votes_an.py).",
    "Les « mises au point au sujet du présent scrutin » (corrections déclarées après "
    "coup par des députés) ne sont pas appliquées : le vote publié dans le décompte "
    "nominatif officiel est repris tel quel.",
    "« absent » signifie : député en exercice à cette date mais ne figurant dans aucune "
    "des listes nominatives du scrutin. « non_votant » reprend la catégorie officielle "
    "des non-votants (présidence de séance, membres du Gouvernement, etc.).",
    "Motions de censure : seuls les votes « pour » sont recensés, une motion n'étant "
    "adoptée que si elle réunit la majorité des membres de l'Assemblée. « absent » y "
    "signifie donc « n'a pas voté la censure » et non « était absent de l'hémicycle ».",
    "Scrutin n° 1 du 8 octobre 2024 : le décompte nominatif du fichier officiel "
    "comporte 21 non-votants alors que la synthèse du même fichier en annonce 10. "
    "Aucun candidat n'est concerné ; les 59 autres scrutins retenus sont cohérents "
    "entre décompte nominatif et synthèse.",
    "Les scrutins retenus appartiennent tous à la 17e législature (seule dont les "
    "scrutins soient publiés en données ouvertes) : les candidats dont le dernier "
    "mandat de député est antérieur à 2024 ont des mandats listés mais aucun vote.",
    "La page de licence de data.assemblee-nationale.fr renvoie à la « Licence Ouverte / "
    "Open Licence » d'Etalab sans en indiquer le numéro de version.",
    "Plusieurs mandats peuvent se chevaucher pour une même législature dans les données "
    "officielles (entrée au Gouvernement, remplacement par un suppléant, retour au "
    "Palais-Bourbon) : les périodes sont reprises telles quelles.",
]


# ------------------------------------------------------------------------------
# Téléchargement / décompression
# ------------------------------------------------------------------------------
def telecharger(url: str, dest: Path, offline: bool) -> Path:
    if dest.exists():
        return dest
    if offline:
        sys.exit(f"Fichier absent du cache et mode --offline : {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"téléchargement {url}", file=sys.stderr)
    urllib.request.urlretrieve(url, dest)
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
    if isinstance(v, dict):
        return v.get("#text")
    return v


def liste(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def sans_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def capitaliser(s: str) -> str:
    s = (s or "").strip()
    return s[:1].upper() + s[1:] if s else s


def ordinal(n: str) -> str:
    return f"{n}re" if n == "1" else f"{n}e"


# ------------------------------------------------------------------------------
# Mandats
# ------------------------------------------------------------------------------
def lire_mandats(dossier_acteurs: Path, aujourdhui: str) -> dict[str, list[dict]]:
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

        lignes, vus = [], set()
        for m in liste(acteur.get("mandats", {}).get("mandat")):
            if m.get("typeOrgane") != "ASSEMBLEE":
                continue
            lieu = (m.get("election") or {}).get("lieu") or {}
            cle = (m.get("legislature"), m.get("dateDebut"), m.get("dateFin"))
            if cle in vus:
                continue
            vus.add(cle)
            circo = f"{lieu.get('departement')}, {ordinal(lieu.get('numCirco') or '')} circonscription"
            lignes.append({
                "chambre": "AN",
                "detail": f"{titre} ({circo}) — {ordinal(m.get('legislature'))} législature",
                "debut": m.get("dateDebut"),
                "fin": m.get("dateFin"),
                "source": {
                    "titre": f"Assemblée nationale — fiche de {prenom} {nom}",
                    "url": URL_DEPUTE_PAGE.format(uid=uid),
                    "date": aujourdhui,
                },
            })
        lignes.sort(key=lambda x: (x["debut"] or "", x["fin"] or "9999"), reverse=True)
        mandats[cid] = lignes
    return mandats


def membre_le(mandats: list[dict], jour: str) -> bool:
    for m in mandats:
        if m["debut"] and m["debut"] <= jour and (m["fin"] is None or jour <= m["fin"]):
            return True
    return False


# ------------------------------------------------------------------------------
# Scrutins
# ------------------------------------------------------------------------------
def votes_par_acteur(scrutin: dict) -> dict[str, str]:
    """acteurRef -> pour / contre / abstention / non_votant."""
    resultat = {}
    ventilation = scrutin["ventilationVotes"]["organe"]["groupes"]["groupe"]
    for groupe in liste(ventilation):
        decompte = groupe.get("vote", {}).get("decompteNominatif") or {}
        for cle, position in POSITION.items():
            bloc = decompte.get(cle)
            if not isinstance(bloc, dict):
                continue
            for votant in liste(bloc.get("votant")):
                if isinstance(votant, dict) and votant.get("acteurRef"):
                    resultat[votant["acteurRef"]] = position
    return resultat


def lire_scrutins(dossier_scrutins: Path, mandats: dict[str, list[dict]]) -> list[dict]:
    sortie = []
    for numero, questions in SCRUTINS_RETENUS.items():
        chemin = dossier_scrutins / "json" / f"VTANR5L{LEGISLATURE}V{numero}.json"
        if not chemin.exists():
            sys.exit(f"Scrutin introuvable : {chemin}")
        s = json.loads(chemin.read_text(encoding="utf-8"))["scrutin"]
        if s.get("legislature") != LEGISLATURE:
            sys.exit(f"Scrutin {numero} : législature inattendue {s.get('legislature')}")
        jour = s["dateScrutin"]
        positions = votes_par_acteur(s)
        votes = {}
        for cid, (uid, *_rest) in CANDIDATS_DEPUTES.items():
            if not membre_le(mandats[cid], jour):
                continue           # non membre à cette date : absent du champ « votes »
            votes[cid] = positions.get(uid, "absent")
        sortie.append({
            "id": f"an-{LEGISLATURE}-{numero}",
            "chambre": "AN",
            "date": jour,
            "titre": capitaliser(s.get("titre") or (s.get("objet") or {}).get("libelle")),
            "type": TYPE_SCRUTIN.get(s["typeVote"]["codeTypeVote"], "ordinaire"),
            "resultat": (s.get("sort") or {}).get("code"),
            "url": URL_SCRUTIN_PAGE.format(num=numero),
            "questions": questions,
            "votes": dict(sorted(votes.items())),
        })
    sortie.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    return sortie


# ------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default=None,
                        help="dossier de travail pour les jeux de données (hors dépôt)")
    parser.add_argument("--out", default=str(ROOT / "data" / "votes-an.json"))
    parser.add_argument("--offline", action="store_true",
                        help="échouer plutôt que télécharger si le cache est vide")
    args = parser.parse_args()

    import tempfile
    cache = Path(args.cache or Path(tempfile.gettempdir()) / "votes_an_cache")
    cache.mkdir(parents=True, exist_ok=True)

    acteurs = decompresser(telecharger(URL_ACTEURS, cache / "AMO30.json.zip", args.offline),
                           cache / "amo30")
    scrutins = decompresser(telecharger(URL_SCRUTINS, cache / "Scrutins.json.zip", args.offline),
                            cache / "scrutins")

    aujourdhui = date.today().isoformat()
    tous = [c["id"] for c in json.loads(
        (ROOT / "data" / "candidats.json").read_text(encoding="utf-8"))["candidats"]]
    inconnus = set(CANDIDATS_DEPUTES) - set(tous)
    if inconnus:
        sys.exit(f"Identifiants absents de data/candidats.json : {sorted(inconnus)}")

    trouves = lire_mandats(acteurs, aujourdhui)
    mandats = {cid: trouves.get(cid, []) for cid in tous}
    liste_scrutins = lire_scrutins(scrutins, mandats)

    document = {
        "mise_a_jour": aujourdhui,
        "sources": SOURCES,
        "mandats": mandats,
        "scrutins": liste_scrutins,
        "a_verifier": A_VERIFIER,
    }
    out = Path(args.out)
    out.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    deputes = sum(1 for v in mandats.values() if v)
    print(f"{deputes} candidats ayant été députés, {len(liste_scrutins)} scrutins "
          f"→ {out}")


if __name__ == "__main__":
    main()
