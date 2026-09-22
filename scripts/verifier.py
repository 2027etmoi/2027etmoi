#!/usr/bin/env python3
"""Contrôle la cohérence et le sourçage des données du site.

Usage : python3 scripts/verifier.py
Code de sortie 1 s'il y a au moins une erreur.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

BLOCS = {"gauche", "ecolo", "centre", "droite", "extdroite", "autre"}
STATUTS = {"declare", "primaire", "pressenti", "empeche", "renonce"}
THEMES = {"economie", "travail", "retraites", "sante", "education", "ecologie", "immigration",
          "securite", "international", "institutions", "logement", "territoires"}
NATURES = {"programme", "declaration", "presse"}
ETATS_PROG = {"complet", "partiel", "aucun"}
ETATS_AFFAIRE = {"enquete", "mise_en_examen", "renvoi_proces", "condamnation_non_definitive",
                 "condamnation_definitive", "relaxe", "non_lieu", "classement", "instruction_close"}
# Agrégateurs non officiels refusés comme source (docs/methode-sources.md)
INTERDITS = ["elyseescope", "monvote2027", "candidatspresidentielles2027", "repere2027", "polradar",
             "sondages-presidentielle2027", "komunemedia", "objectif2027", "comparateurpresident",
             "pourquituvotes", "candidator", "france-presidentielle", "xn--lection-9xa", "élection.fr"]
DATE_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")

erreurs, avertissements = [], []


def err(where, msg):
    erreurs.append(f"{where}: {msg}")


def warn(where, msg):
    avertissements.append(f"{where}: {msg}")


def check_source(where, src, allow_wikipedia=True):
    if not isinstance(src, dict):
        return err(where, "source manquante")
    url = src.get("url", "")
    if not url.startswith("https://") and not url.startswith("http://"):
        err(where, f"URL de source invalide : {url!r}")
    if any(d in url for d in INTERDITS):
        err(where, f"source interdite (agrégateur) : {url}")
    if not allow_wikipedia and "wikipedia.org" in url:
        err(where, "Wikipédia n'est pas admis comme source ici")
    if not src.get("titre"):
        warn(where, "source sans titre")
    if not DATE_RE.match(str(src.get("date", ""))):
        err(where, f"date de source absente ou mal formée : {src.get('date')!r}")


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        err(path.name, f"JSON illisible : {e}")
        return None


# --- candidats.json
cands = load(DATA / "candidats.json") or {"candidats": []}
ids = set()
for c in cands["candidats"]:
    w = f"candidats/{c.get('id')}"
    if not c.get("id") or c["id"] in ids:
        err(w, "id manquant ou dupliqué")
    ids.add(c.get("id"))
    if c.get("bloc") not in BLOCS:
        err(w, f"bloc inconnu {c.get('bloc')!r}")
    if c.get("statut") not in STATUTS:
        err(w, f"statut inconnu {c.get('statut')!r}")
    check_source(w, c.get("source"))
    for k, u in (c.get("liens") or {}).items():
        if not str(u).startswith("https://"):
            err(w, f"lien {k} non https : {u}")
en_lice = {c["id"] for c in cands["candidats"] if c.get("statut") in {"declare", "primaire", "pressenti"}}

# --- programmes
progs = {}
for f in sorted((DATA / "programmes").glob("*.json")):
    p = load(f)
    if p is None:
        continue
    w = f"programmes/{f.stem}"
    progs[f.stem] = p
    if p.get("id") != f.stem:
        err(w, f"id {p.get('id')!r} ≠ nom de fichier")
    if f.stem not in ids:
        err(w, "id absent de candidats.json")
    if (p.get("programme") or {}).get("etat") not in ETATS_PROG:
        err(w, "programme.etat invalide")
    for i, r in enumerate(p.get("reperes", [])):
        check_source(f"{w} repère {i + 1}", r.get("source"))
    for i, m in enumerate(p.get("mesures", [])):
        wm = f"{w} mesure {i + 1}"
        if m.get("theme") not in THEMES:
            err(wm, f"thème inconnu {m.get('theme')!r}")
        if m.get("nature") not in NATURES:
            err(wm, f"nature inconnue {m.get('nature')!r}")
        if not m.get("texte"):
            err(wm, "texte vide")
        elif len(m["texte"].split()) > 35:
            warn(wm, f"texte long ({len(m['texte'].split())} mots)")
        check_source(wm, m.get("source"), allow_wikipedia=False)
    for i, r in enumerate(p.get("ressources", [])):
        if not str(r.get("url", "")).startswith("http"):
            err(f"{w} ressource {i + 1}", "URL invalide")

# --- biographies
bios = {}
for f in sorted((DATA / "biographies").glob("*.json")):
    b = load(f)
    if b is None:
        continue
    w = f"biographies/{f.stem}"
    bios[f.stem] = b
    if b.get("id") != f.stem:
        err(w, f"id {b.get('id')!r} ≠ nom de fichier")
    if f.stem not in ids:
        err(w, "id absent de candidats.json")
    ph = b.get("photo")
    if ph:
        if not str(ph.get("url", "")).startswith("https://upload.wikimedia.org/"):
            err(w, "photo hors Wikimedia Commons")
        if not ph.get("licence") or not ph.get("auteur"):
            err(w, "photo sans auteur ou licence")
    for s in (b.get("presentation") or {}).get("sources", []):
        check_source(f"{w} présentation", s)
    for key in ("parcours_politique", "parcours_professionnel"):
        for i, e in enumerate(b.get(key, [])):
            check_source(f"{w} {key} {i + 1}", e.get("source"))
    if "affaires" not in b:
        warn(w, "champ affaires absent (mettre [] si aucune)")
    for i, a in enumerate(b.get("affaires", [])):
        wa = f"{w} affaire {i + 1}"
        if a.get("etat") not in ETATS_AFFAIRE:
            err(wa, f"état inconnu {a.get('etat')!r}")
        srcs = a.get("sources") or []
        if not srcs:
            err(wa, "aucune source")
        if srcs and all("wikipedia.org" in s.get("url", "") for s in srcs):
            err(wa, "sourcée uniquement par Wikipédia")
        for s in srcs:
            check_source(wa, s)

# --- sondages
sd = load(DATA / "sondages.json") if (DATA / "sondages.json").exists() else None
if sd:
    hors = set((sd.get("noms_hors_liste") or {}).keys())
    for i, s in enumerate(sd.get("sondages", [])):
        w = f"sondages/{s.get('institut')} {s.get('terrain_fin')}"
        check_source(w, s.get("source"))
        for h in s.get("hypotheses", []):
            for pid, v in (h.get("scores") or {}).items():
                if pid not in ids and pid not in hors:
                    err(w, f"id inconnu dans les scores : {pid}")
                if not isinstance(v, (int, float)) or not 0 <= v <= 100:
                    err(w, f"score invalide pour {pid} : {v!r}")
            total = sum(v for v in (h.get("scores") or {}).values() if isinstance(v, (int, float)))
            if total > 102:
                warn(w, f"total des scores > 100 ({total:.1f}) dans « {h.get('label')} »")

# --- couverture
manque_prog = sorted(en_lice - set(progs))
manque_bio = sorted(en_lice - set(bios))
if manque_prog:
    warn("couverture", "sans fiche programme : " + ", ".join(manque_prog))
if manque_bio:
    warn("couverture", "sans biographie : " + ", ".join(manque_bio))

nb_mesures = sum(len(p.get("mesures", [])) for p in progs.values())
print(f"{len(ids)} personnalités · {len(progs)} fiches programme ({nb_mesures} mesures) · "
      f"{len(bios)} biographies · {len((sd or {}).get('sondages', []))} sondages")
for a in avertissements:
    print("  avertissement –", a)
for e in erreurs:
    print("  ERREUR –", e)
print("OK" if not erreurs else f"{len(erreurs)} erreur(s)")
sys.exit(1 if erreurs else 0)
