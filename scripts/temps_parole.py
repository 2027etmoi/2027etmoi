#!/usr/bin/env python3
"""Temps de parole Arcom (hors périodes électorales) des candidats de data/candidats.json.

Source : Arcom, « Fichiers sources des temps de parole hors période électorale »
https://www.arcom.fr/temps-parole/hors-elections/recherche/source/2026
(page liée depuis https://www.arcom.fr/temps-parole/hors-elections, bouton « Accéder à la liste des fichiers »).

Fichiers utilisés : « Temps de parole des personnalités politiques - <mois> »
(Export_web_Personnalites_avec_seuil_<début>_<fin>.csv), un par mois.

Structure d'un fichier (CSV, séparateur « ; », UTF-8 avec BOM, 74 colonnes) :
  ligne 1 : "" ; "Appartenance" ; puis le nom du service, répété 3 fois (24 services)
  ligne 2 : "Type de service" ; "-" ; « Chaîne généraliste » | « Chaîne d'information » | « Radio »
  ligne 3 : "Type d'émission" ; "-" ; JTF | MAG | PROG (pour chaque service)
  lignes suivantes : personnalité ("NOM Prénom", casse variable) ; appartenance ; durées HH:MM:SS ou "-"
Services : TF1, France 2, France 3, France 5, M6, TMC, T18, Novo19, RMC Life, RMC Decouverte,
RMC Story (généralistes) ; BFMTV, CNews, LCI, franceinfo: (information) ; France Info, France Culture,
France Inter, Radio Classique, BFM Business, RMC, RTL, Europe 1, Sud Radio (radio).

Agrégation : pour chaque candidat et chaque mois, somme de toutes les cellules chiffrées
(tous services, JTF + MAG + PROG) de toutes les lignes rattachées au candidat (ALIAS ci-dessous).
TV = « Chaîne généraliste » + « Chaîne d'information » ; radio = « Radio ». Minutes, 1 décimale.
Un candidat sans aucune cellule chiffrée dans un mois n'a pas d'entrée pour ce mois ; une composante
(tv ou radio) sans cellule chiffrée vaut null (le fichier n'affiche aucune valeur, ce n'est pas un 0).

Usage : python3 scripts/temps_parole.py [--cache DOSSIER]
Les CSV sont téléchargés dans --cache (par défaut un dossier temporaire du système), jamais dans le dépôt.
"""
import argparse
import csv
import json
import sys
import tempfile
import unicodedata
import urllib.request
from collections import defaultdict
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path

BASE = "https://www.arcom.fr/sites/default/files/tphe/files/speaking_time_files/"
FICHIERS = [  # (mois, url) — 6 derniers mois publiés au 2026-09-22
    ("2026-01", BASE + "Export_web_Personnalites_avec_seuil_01-01-2026_31-01-2026.csv"),
    ("2026-02", BASE + "Export_web_Personnalites_avec_seuil_01-02-2026_28-02-2026.csv"),
    ("2026-03", BASE + "Export_web_Personnalites_avec_seuil_01-03-2026_31-03-2026.csv"),
    ("2026-04", BASE + "Export_web_Personnalites_avec_seuil_01-04-2026_30-04-2026.csv"),
    ("2026-05", BASE + "Export_web_Personnalites_avec_seuil_01-05-2026_31-05-2026.csv"),
    ("2026-06", BASE + "Export_web_Personnalites_avec_seuil_01-06-2026_30-06-2026.csv"),
]
SOURCE = {
    "titre": "Arcom — relevés des temps de parole hors périodes électorales",
    "url": "https://www.arcom.fr/temps-parole/hors-elections/recherche/source/2026",
}
STATUTS = {"declare", "primaire", "pressenti"}

# Libellés Arcom (normalisés : majuscules, sans accents, tirets -> espaces) rattachés à chaque id.
# Vérifiés à la main sur les 6 fichiers : homonymes écartés (ex. CAZENEUVE Jean-René / Pierre,
# ROUSSEL Benoît / David / Jeanne, RUFFIN Laurence, FAURE Bruno / Cécile, LE PEN Marie-Caroline,
# DE VILLEPIN Hervé, BERTRAND Dorothée). Les variantes de casse d'une même personne sont additionnées.
# Une contrainte d'appartenance est ajoutée quand le libellé seul est ambigu.
ALIAS = {
    "melenchon": [("MELENCHON JEAN LUC", None)],
    "faure": [("FAURE OLIVIER", None)],
    "glucksmann": [("GLUCKSMANN RAPHAEL", None)],
    "guedj": [("GUEDJ JEROME", None)],
    "royal": [("ROYAL SEGOLENE", None)],
    "maurel": [("MAUREL EMMANUEL", None)],
    "roussel": [("ROUSSEL FABIEN", None)],
    "ruffin": [("RUFFIN FRANCOIS", None)],
    "cazeneuve": [("CAZENEUVE BERNARD", None)],
    "bouamrane": [("BOUAMRANE KARIM", None)],
    "hollande": [("HOLLANDE FRANCOIS", None)],
    "arthaud": [("ARTHAUD NATHALIE", None)],
    "tondelier": [("TONDELIER MARINE", None)],
    "batho": [("BATHO DELPHINE", None)],
    # « EDOUARD PHILIPPE » (Horizons, mars 2026) : ordre prénom/nom inversé, ligne sans valeur chiffrée.
    "philippe": [("PHILIPPE EDOUARD", None), ("EDOUARD PHILIPPE", "Horizons")],
    "attal": [("ATTAL GABRIEL", None)],
    "villepin": [("DE VILLEPIN DOMINIQUE", None)],
    "le-maire": [("LE MAIRE BRUNO", None)],
    "retailleau": [("RETAILLEAU BRUNO", None)],
    "lisnard": [("LISNARD DAVID", None)],  # appartenance « Les Républicains » puis « Nouvelle Energie »
    "bertrand": [("BERTRAND XAVIER", None)],
    "le-pen": [("LE PEN MARINE", None)],
    "zemmour": [("ZEMMOUR ERIC", None)],
    "dupont-aignan": [("DUPONT AIGNAN NICOLAS", None)],
    "philippot": [("PHILIPPOT FLORIAN", None)],
}

ROOT = Path(__file__).resolve().parent.parent
TV_TYPES = {"Chaîne généraliste", "Chaîne d'information"}
RADIO_TYPES = {"Radio"}


def norm(s):
    s = unicodedata.normalize("NFD", s.upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.replace("-", " ").split())


def secondes(v):
    h, m, s = (int(x) for x in v.split(":"))
    return h * 3600 + m * 60 + s


def telecharger(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (2027etmoi; script open data)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        dest.write_bytes(r.read())
        lm = r.headers.get("Last-Modified")
    return parsedate_to_datetime(lm).date().isoformat() if lm else None


def lire(path):
    rows = list(csv.reader(path.open(encoding="utf-8-sig", newline=""), delimiter=";"))
    services, types_service, types_emission = rows[0], rows[1], rows[2]
    assert types_service[0] == "Type de service" and types_emission[0] == "Type d'émission", path
    inconnus = set(types_service[2:]) - TV_TYPES - RADIO_TYPES
    assert not inconnus, f"type de service inconnu : {inconnus}"
    assert set(types_emission[2:]) <= {"JTF", "MAG", "PROG"}, set(types_emission[2:])
    lignes = []
    for r in rows[3:]:
        if not r or not r[0].strip():
            continue
        assert len(r) == len(services), (path, r[:2])
        tv = radio = 0
        n_tv = n_radio = 0
        for i in range(2, len(r)):
            v = r[i].strip()
            if v in ("-", ""):
                continue
            s = secondes(v)
            if types_service[i] in TV_TYPES:
                tv += s
                n_tv += 1
            else:
                radio += s
                n_radio += 1
        lignes.append({"nom": r[0].strip(), "appartenance": r[1].strip(),
                       "tv": tv if n_tv else None, "radio": radio if n_radio else None})
    return lignes


def minutes(s):
    return None if s is None else round(s / 60, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(Path(tempfile.gettempdir()) / "arcom-temps-parole"))
    args = ap.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)

    cands = json.loads((ROOT / "data" / "candidats.json").read_text(encoding="utf-8"))["candidats"]
    retenus = [c for c in cands if c["statut"] in STATUTS]
    inconnus = set(ALIAS) - {c["id"] for c in retenus}
    assert not inconnus, f"ALIAS pour des ids non retenus : {inconnus}"

    fichiers, resultat, noms_arcom = [], defaultdict(dict), defaultdict(list)
    for mois, url in FICHIERS:
        dest = cache / url.rsplit("/", 1)[1]
        publie = telecharger(url, dest)
        fichiers.append({"mois": mois, "url": url, "publie_le": publie})
        lignes = lire(dest)
        for cid, alias in ALIAS.items():
            tv = radio = None
            for l in lignes:
                if any(norm(l["nom"]) == a and (p is None or l["appartenance"] == p) for a, p in alias):
                    if l["nom"] not in noms_arcom[cid]:
                        noms_arcom[cid].append(l["nom"])
                    if l["tv"] is not None:
                        tv = (tv or 0) + l["tv"]
                    if l["radio"] is not None:
                        radio = (radio or 0) + l["radio"]
            if tv is None and radio is None:
                continue  # absent du fichier, ou aucune cellule chiffrée : pas d'entrée
            resultat[cid][mois] = {"tv": minutes(tv), "radio": minutes(radio),
                                   "total": minutes((tv or 0) + (radio or 0))}
        # Contrôle : lignes portant le nom de famille d'un candidat mais non rattachées (homonymes à revoir)
        for c in retenus:
            nom_famille = norm(c["nom"].split(" ", 1)[1] if c["id"] != "villepin" else "de Villepin")
            for l in lignes:
                n = norm(l["nom"])
                rattache = any(n == a for a, _ in ALIAS.get(c["id"], []))
                if not rattache and n.startswith(nom_famille + " ") and (l["tv"] or l["radio"]):
                    print(f"[contrôle {mois}] {c['id']} : ligne non rattachée « {l['nom']} » ({l['appartenance']})",
                          file=sys.stderr)

    mois = [m for m, _ in FICHIERS]
    out = {
        "mise_a_jour": date.today().isoformat(),
        "source": {**SOURCE, "date": max(f["publie_le"] for f in fichiers if f["publie_le"])},
        "fichiers": fichiers,
        "mesure": (
            "Temps de parole (seule mesure des fichiers Arcom hors période électorale), en minutes : "
            "somme de toutes les durées affichées pour la personnalité dans le fichier « Temps de parole "
            "des personnalités politiques » du mois, sur les 24 services relevés (TV : TF1, France 2, "
            "France 3, France 5, M6, TMC, T18, Novo19, RMC Life, RMC Découverte, RMC Story, BFMTV, CNews, "
            "LCI, franceinfo: ; radio : France Info, France Culture, France Inter, Radio Classique, "
            "BFM Business, RMC, RTL, Europe 1, Sud Radio) et les trois types d'émission (JTF, MAG, PROG). "
            "tv = chaînes généralistes + chaînes d'information ; radio = radios ; total = tv + radio."
        ),
        "mois": mois,
        "candidats": {
            c["id"]: {"nom_arcom": " / ".join(noms_arcom[c["id"]]), "par_mois": resultat[c["id"]]}
            for c in retenus if resultat.get(c["id"])
        },
        "limites": [
            "Fichiers « avec seuil » : dans les 6 fichiers, aucune durée affichée n'est inférieure à 1 min "
            "(00:01:00) ; une cellule « - » signifie donc « pas de temps relevé » ou « moins de 1 min sur ce "
            "service et ce type d'émission ». Les totaux sont des minorants : la somme des personnalités d'un "
            "parti est inférieure de quelques pourcents au total du même parti dans le fichier « Temps de "
            "parole des partis politiques » du même mois.",
            "Seul le temps de parole est publié hors période électorale : pas de temps d'antenne, ni de "
            "distinction entre fonctions (un ministre ou un élu local est compté comme toute personnalité).",
            "Les chaînes et radios non relevées par l'Arcom (chaînes locales, parlementaires, web, réseaux "
            "sociaux) ne sont pas comptées.",
            "Candidats sans entrée : absents des 6 fichiers ou sans aucune durée affichée (Anasse Kazib, "
            "Selma Labib, François Asselineau, Jean Lassalle, Manolo Mlekuz, Clara Egger, Benoît Mathieu, "
            "Francis Lalanne, Juan Branco, Sylvain Durif, Antoine Mikolajczak, Lydie Massard). Un mois "
            "manquant pour un candidat présent ailleurs signifie de même « rien d'affiché », pas 0.",
            "tv ou radio = null : aucune durée affichée pour ce type de média ce mois-là (pas un zéro).",
            "Arrondis : chaque valeur est arrondie séparément à 0,1 min ; total peut différer de tv + radio "
            "de 0,1.",
            "publie_le = date « Last-Modified » renvoyée par le serveur de l'Arcom pour le fichier ; la page "
            "de l'Arcom n'affiche pas de date de publication.",
            "Mars 2026 inclut la campagne des municipales (15 et 22 mars), période pour laquelle l'Arcom "
            "publie aussi des relevés électoraux distincts ; les fichiers utilisés ici sont ceux « hors "
            "périodes électorales ».",
        ],
        "a_verifier": [
            "Seuil de 1 min : déduit des fichiers (nom « avec_seuil », minimum observé 00:01:00), non "
            "documenté sur la page de l'Arcom consultée.",
            "Signification exacte des types d'émission JTF, MAG, PROG : non documentée dans les fichiers.",
            "Philippe (id philippe) : la ligne « EDOUARD PHILIPPE » (Horizons, mars 2026, sans durée "
            "affichée) est supposée être Édouard Philippe avec prénom et nom inversés ; elle ne change "
            "aucun total.",
            "Doublons de casse (ex. « MELENCHON JEAN LUC » et « MELENCHON Jean-Luc », « RETAILLEAU BRUNO » "
            "et « RETAILLEAU Bruno ») additionnés comme une même personne.",
            "David Lisnard apparaît sous deux appartenances en mars 2026 (Les Républicains et Nouvelle "
            "Energie) : les deux lignes sont additionnées.",
            "Bruno Le Maire est classé « Renaissance » par l'Arcom (« Ex-Renaissance » dans candidats.json) : "
            "rattaché par le nom, sans homonyme dans les fichiers.",
            "Le fichier personnalités de février 2026 porte une date Last-Modified du 2026-09-09, bien après "
            "les autres fichiers de ce mois : il a pu être remplacé (révision non signalée sur la page).",
            "Mars 2026, Reconquête : la somme des personnalités (90,9 min) dépasse le total du parti dans le "
            "fichier des partis (90,0 min), incohérence mineure entre les deux fichiers de l'Arcom.",
        ],
    }
    dest = ROOT / "data" / "temps-parole.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{dest} écrit : {len(out['candidats'])} candidats, mois {mois[0]} à {mois[-1]}")


if __name__ == "__main__":
    main()
