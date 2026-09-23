#!/usr/bin/env python3
"""Produit data/votes-pe.json : mandats de député européen et votes nominatifs des candidats.

Reproductible : le script interroge lui-même l'API v2 du portail de données ouvertes du
Parlement européen (data.europarl.europa.eu) et met les réponses en cache hors du dépôt.

    python3 scripts/votes_pe.py [--cache DOSSIER] [--out FICHIER] [--offline]

Voir docs/methode-votes.md. Ce fichier ne couvre QUE le Parlement européen
(chambre « PE ») ; l'Assemblée nationale et le Sénat sont traités ailleurs.

--------------------------------------------------------------------------------
Sources et licence
--------------------------------------------------------------------------------
- Portail de données ouvertes du Parlement européen, API v2 :
  https://data.europarl.europa.eu/en/developer-corner/opendata-api
  · liste des députés d'une législature : /api/v2/meps?parliamentary-term=N
  · fiche d'un député (mandats)        : /api/v2/meps/<id>
  · décisions d'une séance (votes)     : /api/v2/meetings/MTG-PL-<date>/decisions
  · objets mis aux voix d'une séance   : /api/v2/meetings/MTG-PL-<date>/vote-results
  Chaque décision issue d'un vote par appel nominal porte la liste nominative des
  députés ayant voté pour (had_voter_favor), contre (had_voter_against) et s'étant
  abstenus (had_voter_abstention).
- Licence : avis juridique du Parlement européen
  (https://www.europarl.europa.eu/legal-notice/fr/home). La réutilisation des données
  textuelles dont l'Union européenne est propriétaire est autorisée, pour un usage
  personnel comme pour une diffusion non commerciale ou commerciale, à condition de
  reproduire l'élément dans son intégralité et d'en citer la source :
  « © Union européenne, <année> – Source : Parlement européen ».
  Aucune donnée d'un agrégateur tiers (HowTheyVote.eu, Parltrack, VoteWatch…) n'est
  reprise ici : tous les votes proviennent de l'API officielle ci-dessus.
- Page officielle d'un scrutin (annexe « Résultat des votes par appel nominal » du
  procès-verbal de la séance) :
  https://www.europarl.europa.eu/doceo/document/PV-<législature>-<date>-RCV_FR.html
- Page officielle d'un député : https://www.europarl.europa.eu/meps/fr/<id>

--------------------------------------------------------------------------------
Périmètre
--------------------------------------------------------------------------------
L'API ne publie les décisions de séance plénière qu'à partir de la 9e législature
(séance du 2 juillet 2019). Les votes des législatures antérieures — ceux de
François Hollande et François Bayrou (1999), Michel Barnier (2009-2010),
Jean-Luc Mélenchon (2009-2017), Marine Le Pen (2004-2017) et Florian Philippot
(2014-2019) — ne sont donc pas couverts, bien que leurs mandats soient listés.

--------------------------------------------------------------------------------
Critères de sélection des scrutins (les mêmes pour tous les candidats)
--------------------------------------------------------------------------------
On retient 33 votes par appel nominal des 9e et 10e législatures, tous portant sur
l'ensemble d'un texte (proposition de résolution dans son ensemble, accord provisoire,
proposition de la Commission, projet d'acte du Conseil) :

1. les votes finaux sur les textes marquants des domaines listés par la méthode —
   climat et énergie, migration, budget, agriculture et commerce, libertés publiques,
   défense, social ;
2. les résolutions notables de politique étrangère sur l'Ukraine et sur le
   Proche-Orient ;
3. les votes dont l'objet recoupe exactement une question clé (data/questions.json)
   sont rattachés à cette question dans le champ « questions ».

Ne sont retenus ni les votes sur amendements, ni les votes par division (§ x/1, § x/2),
ni les votes de procédure (renvoi en commission, demande d'urgence, propositions de
rejet). Les votes à main levée ne sont pas nominatifs et n'existent pas dans ces
données.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

API = "https://data.europarl.europa.eu/api/v2"
URL_SCRUTIN_PAGE = "https://www.europarl.europa.eu/doceo/document/{pv}_FR.html"
URL_DEPUTE_PAGE = "https://www.europarl.europa.eu/meps/fr/{id}"

SOURCES = [
    {
        "titre": "Parlement européen — portail de données ouvertes, décisions de séance plénière (votes par appel nominal)",
        "url": "https://data.europarl.europa.eu/en/developer-corner/opendata-api",
        "licence": "Avis juridique du Parlement européen — réutilisation autorisée avec citation de la source (© Union européenne — Source : Parlement européen)",
    },
    {
        "titre": "Parlement européen — portail de données ouvertes, députés et mandats",
        "url": "https://data.europarl.europa.eu/en/dataset/meps",
        "licence": "Avis juridique du Parlement européen — réutilisation autorisée avec citation de la source (© Union européenne — Source : Parlement européen)",
    },
]

# ------------------------------------------------------------------------------
# Candidats identifiés comme députés européens (actuels ou anciens) dans le
# référentiel du Parlement. Le triplet prénom / nom / date de naissance sert de
# garde-fou contre les homonymes : le script s'arrête si la fiche ne correspond pas.
# La date de naissance de Sarah Knafo n'est pas publiée par le Parlement (None).
# ------------------------------------------------------------------------------
CANDIDATS_EURODEPUTES: dict[str, tuple[int, str, str, str | None]] = {
    "melenchon": (96742, "Jean-Luc", "Mélenchon", "1951-08-19"),
    "glucksmann": (197694, "Raphaël", "Glucksmann", "1979-10-15"),
    "maurel": (24505, "Emmanuel", "Maurel", "1973-05-10"),
    "hollande": (4285, "François", "Hollande", "1954-08-12"),
    "bayrou": (4324, "François", "Bayrou", "1951-05-25"),
    "barnier": (72776, "Michel", "Barnier", "1951-01-09"),
    "le-pen": (28210, "Marine", "Le Pen", "1968-08-05"),
    "bardella": (131580, "Jordan", "Bardella", "1995-09-13"),
    "knafo": (256924, "Sarah", "Knafo", None),
    "marechal": (256922, "Marion", "Maréchal", "1989-12-10"),
    "philippot": (110977, "Florian", "Philippot", "1981-10-24"),
    "massard": (249285, "Lydie", "Massard", "1978-08-24"),
}

# ------------------------------------------------------------------------------
# Scrutins retenus : identifiant officiel du vote (notation_votingId) -> date de la
# séance et questions clés dont le scrutin traite exactement le même sujet.
# Voir les critères en tête de fichier.
# ------------------------------------------------------------------------------
SCRUTINS_RETENUS: dict[int, tuple[str, list[str]]] = {
    # --- Ukraine --------------------------------------------------------------
    140111: ("2022-03-01", ["q17"]),  # agression russe contre l'Ukraine
    164536: ("2024-02-27", ["q17"]),  # facilité pour l'Ukraine
    169676: ("2024-09-19", ["q17"]),  # soutien financier et militaire à l'Ukraine
    169889: ("2024-10-22", ["q17"]),  # prêts et assistance macrofinancière à l'Ukraine
    172663: ("2025-03-12", ["q17"]),  # trois ans de guerre d'agression
    185885: ("2026-02-24", ["q17"]),  # quatre ans de guerre d'agression
    # --- Proche-Orient --------------------------------------------------------
    159664: ("2023-10-19", []),       # attentats du Hamas, droit d'Israël à se défendre
    166777: ("2024-03-14", []),       # risque de famine à Gaza
    # La résolution du 11 septembre 2025 soutient, à son paragraphe 23, la proposition
    # de suspension partielle de l'accord d'association UE-Israël : même objet que q34.
    179048: ("2025-09-11", ["q34"]),
    # --- climat, énergie, automobile ------------------------------------------
    152544: ("2023-02-14", ["q12"]),  # normes CO2 voitures et camionnettes (2035)
    154173: ("2023-04-18", []),       # révision du système d'échange de quotas
    164499: ("2024-02-27", []),       # restauration de la nature
    176302: ("2025-05-08", ["q12"]),  # normes CO2 voitures, années 2025 à 2027
    184178: ("2026-02-10", []),       # cadre pour parvenir à la neutralité climatique
    # --- migration et asile ---------------------------------------------------
    166904: ("2024-04-10", []),       # filtrage aux frontières extérieures
    167531: ("2024-04-10", []),       # gestion de l'asile et de la migration
    184172: ("2026-02-10", []),       # liste européenne des pays d'origine sûrs
    194134: ("2026-06-17", []),       # règlement sur le retour
    # --- budget ---------------------------------------------------------------
    164815: ("2024-02-27", []),       # cadre financier pluriannuel 2021-2027 (révision)
    180153: ("2025-10-22", []),       # budget général 2026
    190026: ("2026-04-28", []),       # cadre financier pluriannuel 2028-2034
    # --- agriculture et commerce ----------------------------------------------
    161821: ("2023-11-22", []),       # utilisation durable des produits phytopharmaceutiques
    182509: ("2025-12-16", []),       # PAC : conditionnalité et paiements directs
    183884: ("2026-01-21", []),       # avis de la Cour de justice sur l'accord UE-Mercosur
    184191: ("2026-02-10", []),       # clause de sauvegarde agricole UE-Mercosur
    # --- libertés publiques et état de droit ----------------------------------
    146649: ("2022-07-05", []),       # législation sur les services numériques
    147456: ("2022-09-15", []),       # risque de violation grave des valeurs par la Hongrie
    166051: ("2024-03-13", []),       # législation sur l'intelligence artificielle
    166183: ("2024-03-13", []),       # liberté des médias
    181511: ("2025-11-25", []),       # risque de violation grave des valeurs par la Hongrie
    # --- social ---------------------------------------------------------------
    147342: ("2022-09-14", []),       # salaires minimaux adéquats
    # --- défense --------------------------------------------------------------
    172867: ("2025-03-12", []),       # livre blanc sur l'avenir de la défense européenne
    182483: ("2025-12-16", []),       # investissements de défense, plan « ReArm Europe »
}

RESULTATS = {"ADOPTED": "adopté", "REJECTED": "rejeté", "LAPSED": "caduc"}

A_VERIFIER = [
    "Périmètre : ce fichier ne couvre que le Parlement européen. Un candidat dont la "
    "liste de mandats est vide n'a jamais été député européen ; il a pu être député ou "
    "sénateur, ce que ce fichier ne dit pas.",
    "L'API du portail de données ouvertes du Parlement européen ne publie les décisions "
    "de séance plénière qu'à partir de la 9e législature (2 juillet 2019). Les votes de "
    "François Hollande et François Bayrou (1999), de Michel Barnier (2009-2010), de "
    "Jean-Luc Mélenchon (2009-2017), de Marine Le Pen (2004-2017) et de Florian "
    "Philippot (2014-2019) ne sont donc pas repris, alors que leurs mandats le sont.",
    "L'annexe des votes par appel nominal ne publie que les listes « pour », « contre » "
    "et « abstention » : elle ne distingue pas un député absent d'un député présent "
    "n'ayant pas pris part au vote. Tout député en exercice à la date du scrutin et "
    "absent de ces trois listes est donc noté « non_votant », affiché « n'a pas pris "
    "part au vote », et jamais « absent ».",
    "Les intentions de vote déclarées après coup (had_voter_intended_favor / "
    "_against / _abstention) ne sont pas appliquées : le vote effectivement enregistré "
    "dans le décompte nominatif officiel est repris tel quel.",
    "Le champ decision_outcome (adopté / rejeté) n'est pas renseigné par l'API pour les "
    "scrutins les plus anciens de la 9e législature : « resultat » vaut alors null. "
    "Le sens du vote de chaque candidat, lui, est toujours issu des listes nominatives "
    "officielles.",
    "33 scrutins retenus sur plusieurs dizaines de milliers de votes par appel nominal "
    "des 9e et 10e législatures : uniquement des votes sur l'ensemble d'un texte, "
    "choisis selon les critères listés dans scripts/votes_pe.py. Tous les autres "
    "restent consultables dans le jeu de données source.",
    "Un scrutin sur l'ensemble d'une résolution porte sur un texte qui traite de "
    "plusieurs sujets : le rattachement à une question clé signale une correspondance "
    "d'objet, pas une réponse à la question.",
]


# ------------------------------------------------------------------------------
# Accès à l'API, avec cache sur disque hors du dépôt
# ------------------------------------------------------------------------------
def api(chemin: str, cache: Path, cle: str, offline: bool, essais: int = 5) -> dict:
    """Renvoie la réponse JSON-LD de l'API, en la mettant en cache hors du dépôt.

    L'API renvoie parfois une erreur transitoire (« Pending acquire queue... ») avec un
    code 200 : ces réponses sont réessayées et jamais mises en cache.
    """
    fichier = cache / f"{cle}.json"
    if fichier.exists():
        donnees = json.loads(fichier.read_text(encoding="utf-8"))
        if "data" in donnees:
            return donnees
        fichier.unlink()
    if offline:
        sys.exit(f"Réponse absente du cache et mode --offline : {fichier}")
    url = f"{API}/{chemin}"
    url += ("&" if "?" in url else "?") + urllib.parse.urlencode(
        {"format": "application/ld+json"})
    for essai in range(1, essais + 1):
        print(f"téléchargement {url}", file=sys.stderr)
        try:
            with urllib.request.urlopen(url, timeout=180) as reponse:
                brut = reponse.read()
            donnees = json.loads(brut)
        except Exception as erreur:              # noqa: BLE001 — réseau ou JSON illisible
            donnees = {"error": str(erreur)}
        if "data" in donnees:
            fichier.write_bytes(brut)
            return donnees
        print(f"  réessai {essai}/{essais} : {donnees.get('error')}", file=sys.stderr)
        time.sleep(5 * essai)
    sys.exit(f"L'API ne renvoie pas de données pour {url}")


# ------------------------------------------------------------------------------
# Mandats
# ------------------------------------------------------------------------------
def lire_mandats(cache: Path, offline: bool, aujourdhui: str) -> dict[str, list[dict]]:
    mandats: dict[str, list[dict]] = {}
    for cid, (pid, prenom, nom, naissance) in CANDIDATS_EURODEPUTES.items():
        fiche = api(f"meps/{pid}", cache, f"mep-{pid}", offline)["data"][0]
        vu = (fiche.get("givenName"), fiche.get("familyName"), fiche.get("bday"))
        if vu != (prenom, nom, naissance):
            sys.exit(f"Homonyme probable pour {cid} ({pid}) : attendu "
                     f"{(prenom, nom, naissance)}, trouvé {vu}")
        if not str(fiche.get("citizenship", "")).endswith("/FRA"):
            sys.exit(f"{cid} ({pid}) : nationalité inattendue {fiche.get('citizenship')} "
                     f"— le libellé « (France) » ne serait plus exact")
        feminin = str(fiche.get("hasGender", "")).endswith("FEMALE")
        titre = "Députée européenne" if feminin else "Député européen"

        lignes = []
        for m in fiche.get("hasMembership", []):
            organe = str(m.get("organization", ""))
            if (m.get("membershipClassification") != "def/ep-entities/EU_INSTITUTION"
                    or not organe.startswith("org/ep-")):
                continue
            legislature = organe.rsplit("-", 1)[1]
            periode = m.get("memberDuring") or {}
            lignes.append({
                "chambre": "PE",
                "detail": f"{titre} (France) — {legislature}e législature",
                "debut": periode.get("startDate"),
                "fin": periode.get("endDate"),
                "source": {
                    "titre": f"Parlement européen — fiche de {prenom} {nom}",
                    "url": URL_DEPUTE_PAGE.format(id=pid),
                    "date": aujourdhui,
                },
            })
        if not lignes:
            sys.exit(f"Aucun mandat de député européen trouvé pour {cid} ({pid})")
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
REFERENCE = re.compile(r"\b(RC-)?([ABC])(\d{1,2})-(\d{4})/(\d{4})")


def identifiants_eli(libelle: str) -> list[str]:
    """« A9-0150/2022 » -> [« A-9-2022-0150 »].

    Pour une proposition de résolution commune (« RC-B10-0372/2025 »), l'objet mis aux
    voix est rattaché soit à la proposition commune, soit aux propositions individuelles
    qu'elle remplace : les deux formes sont essayées.
    """
    m = REFERENCE.search(libelle or "")
    if not m:
        return []
    rc, lettre, legislature, numero, annee = m.groups()
    formes = [f"{lettre}-{legislature}-{annee}-{numero}"]
    if rc:
        formes.insert(0, f"RC-{legislature}-{annee}-{numero}")
    return formes


def sujet_officiel(decision: dict, objets: list[dict]) -> str:
    """Intitulé français de l'objet mis aux voix, tel que publié par le Parlement.

    Deux rattachements possibles selon l'ancienneté de la séance : le lien direct
    décision -> objet (inverse_consists_of), sinon la référence du document.
    """
    parents = {o["activity_id"]: o for o in objets}
    for lien in decision.get("inverse_consists_of", []):
        parent = parents.get(str(lien).rsplit("/", 1)[-1])
        if parent:
            return parent["activity_label"]["fr"]
    for eli in identifiants_eli(decision.get("activity_label", {}).get("fr", "")):
        for objet in objets:
            docs = [str(d).rsplit("/", 1)[-1] for d in objet.get("based_on_a_realization_of", [])]
            if eli in docs:
                return objet["activity_label"]["fr"]
    sys.exit(f"Objet mis aux voix introuvable pour {decision['activity_id']}")


def procede_verbal(decision: dict) -> str:
    """« eli/dl/doc/PV-9-2023-02-14-RCV-ITM-013 » -> « PV-9-2023-02-14-RCV »."""
    for doc in decision.get("recorded_in_a_realization_of", []):
        nom = str(doc).rsplit("/", 1)[-1]
        if "-RCV-" in nom:
            return nom.split("-RCV-")[0] + "-RCV"
    sys.exit(f"Procès-verbal des votes par appel nominal introuvable pour "
             f"{decision['activity_id']}")


def objet_du_vote(decision: dict, sujet: str) -> str:
    """Intitulé neutre : objet mis aux voix, suivi de la nature du vote."""
    libelle = decision.get("activity_label", {}).get("fr", "")
    nature = decision.get("referenceText", {}).get("fr")
    if not nature:
        # Séances anciennes : le champ referenceText n'est pas renseigné, la nature du
        # vote termine le libellé de la décision, éventuellement suivie du numéro de
        # l'amendement de compromis (« ... - Accord provisoire - Am 131 »).
        morceaux = [p.strip() for p in libelle.split(" - ") if p.strip()]
        while len(morceaux) > 1 and re.match(r"^Am\s", morceaux[-1]):
            morceaux.pop()
        nature = morceaux[-1]
    sujet = re.sub(r"\s*\*+I?\s*$", "", sujet).strip()   # marqueurs de procédure ***I
    return f"{sujet} — {nature[0].lower()}{nature[1:]}"


def lire_scrutins(cache: Path, offline: bool,
                  mandats: dict[str, list[dict]]) -> list[dict]:
    sortie = []
    objets_par_jour: dict[str, list[dict]] = {}
    for vote_id, (jour, questions) in SCRUTINS_RETENUS.items():
        reunion = f"MTG-PL-{jour}"
        decision = api(f"meetings/{reunion}/decisions/{reunion}-DEC-{vote_id}",
                       cache, f"dec-{vote_id}", offline)["data"][0]
        if decision.get("decision_method") != "def/ep-decision-methods/VOTE_ELECTRONIC_ROLLCALL":
            sys.exit(f"Le vote {vote_id} n'est pas un vote par appel nominal : "
                     f"{decision.get('decision_method')}")
        if jour not in objets_par_jour:
            objets_par_jour[jour] = api(f"meetings/{reunion}/vote-results",
                                        cache, f"vot-{jour}", offline)["data"]

        positions = {}
        for champ, position in (("had_voter_favor", "pour"),
                                ("had_voter_against", "contre"),
                                ("had_voter_abstention", "abstention")):
            for personne in decision.get(champ, []):
                positions[str(personne).rsplit("/", 1)[-1]] = position

        votes = {}
        for cid, (pid, *_reste) in CANDIDATS_EURODEPUTES.items():
            if not membre_le(mandats[cid], jour):
                continue           # non membre à cette date : absent du champ « votes »
            votes[cid] = positions.get(str(pid), "non_votant")

        pv = procede_verbal(decision)
        legislature = pv.split("-")[1]
        statut = str(decision.get("decision_outcome", "")).rsplit("/", 1)[-1]
        sortie.append({
            "id": f"pe-{legislature}-{vote_id}",
            "chambre": "PE",
            "date": jour,
            "titre": objet_du_vote(decision, sujet_officiel(decision, objets_par_jour[jour])),
            "type": "appel_nominal",
            "resultat": RESULTATS.get(statut),
            "url": URL_SCRUTIN_PAGE.format(pv=pv),
            "questions": questions,
            "votes": dict(sorted(votes.items())),
        })
    sortie.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    return sortie


# ------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default=None,
                        help="dossier de travail pour les réponses de l'API (hors dépôt)")
    parser.add_argument("--out", default=str(ROOT / "data" / "votes-pe.json"))
    parser.add_argument("--offline", action="store_true",
                        help="échouer plutôt qu'interroger l'API si le cache est vide")
    args = parser.parse_args()

    cache = Path(args.cache or Path(tempfile.gettempdir()) / "votes_pe_cache")
    cache.mkdir(parents=True, exist_ok=True)

    aujourdhui = date.today().isoformat()
    tous = [c["id"] for c in json.loads(
        (ROOT / "data" / "candidats.json").read_text(encoding="utf-8"))["candidats"]]
    inconnus = set(CANDIDATS_EURODEPUTES) - set(tous)
    if inconnus:
        sys.exit(f"Identifiants absents de data/candidats.json : {sorted(inconnus)}")

    trouves = lire_mandats(cache, args.offline, aujourdhui)
    mandats = {cid: trouves.get(cid, []) for cid in tous}
    liste_scrutins = lire_scrutins(cache, args.offline, mandats)

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
    eurodeputes = sum(1 for v in mandats.values() if v)
    print(f"{eurodeputes} candidats ayant été députés européens, "
          f"{len(liste_scrutins)} scrutins → {out}")


if __name__ == "__main__":
    main()
