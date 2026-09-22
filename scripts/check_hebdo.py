#!/usr/bin/env python3
"""Contrôle hebdomadaire des données du site : cohérence, liens, calendrier, fraîcheur.

Usage : python3 scripts/check_hebdo.py [--sans-liens] > rapport.md
Écrit un rapport Markdown sur la sortie standard. Ne modifie aucune donnée.
Lancé chaque semaine par .github/workflows/veille-hebdo.yml, qui publie le rapport en issue GitHub.
"""
import json
import re
import subprocess
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AUJ = date.today()
UA = "Mozilla/5.0 (compatible; 2027etmoi-veille/1.0; +https://github.com/2027etmoi/2027etmoi)"

SEUIL_STATUT = 30      # jours depuis la dernière vérification d'un statut (champ verifie_le)
SEUIL_SONDAGES = 21    # jours : dernier sondage trop ancien
EN_LICE = {"declare", "primaire", "pressenti"}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def d(s):
    """« AAAA-MM-JJ » ou « AAAA-MM » → date (1er du mois si le jour manque)."""
    try:
        return date.fromisoformat(s if len(s) == 10 else f"{s[:7]}-01")
    except (TypeError, ValueError):
        return None


def run(cmd):
    r = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


sections = []
alertes = 0

# 1. Cohérence des données
code, out = run(["scripts/verifier.py"])
erreurs = [l for l in out.splitlines() if "ERREUR" in l]
alertes += len(erreurs)
sections.append("## 1. Cohérence des données\n\n" + (
    "✅ `verifier.py` : aucune erreur.\n" if code == 0 else f"❌ `verifier.py` : {len(erreurs)} erreur(s).\n\n```\n" + "\n".join(erreurs[:40]) + "\n```\n"))

# 2. Liens
if "--sans-liens" not in sys.argv:
    code, out = run(["scripts/verifier_liens.py"])
    morts = [l for l in out.splitlines() if "MORT" in l]
    alertes += len(morts)
    resume = out.splitlines()[0] if out else ""
    sections.append("## 2. Liens\n\n" + (f"✅ {resume}\n" if not morts else f"❌ {resume}\n\n" + "\n".join(f"- {l.strip()}" for l in morts[:40]) + "\n"))

# 3. Calendrier
cal = load(DATA / "calendrier.json") if (DATA / "calendrier.json").exists() else {"etapes": []}
passees = [e for e in cal["etapes"] if AUJ - timedelta(days=8) <= d(e.get("fin") or e["date"]) < AUJ]
a_venir = [e for e in cal["etapes"] if AUJ <= d(e["date"]) <= AUJ + timedelta(days=15)]
lignes = []
if passees:
    alertes += len(passees)
    lignes.append("**Étapes passées cette semaine : mettre à jour les statuts, les résultats et le calendrier.**\n")
    lignes += [f"- [ ] {e['date']} — {e['titre']}" for e in passees]
if a_venir:
    lignes.append("\n**Dans les 15 prochains jours :**\n")
    lignes += [f"- {e['date']} — {e['titre']} ({e.get('statut', '')})" for e in a_venir]
estimees = [e for e in cal["etapes"] if e.get("statut") == "estimee" and d(e["date"]) >= AUJ]
if estimees:
    lignes.append(f"\n{len(estimees)} date(s) encore « estimée(s) » : à confirmer dès la publication du décret de convocation.")
sections.append("## 3. Calendrier\n\n" + ("\n".join(lignes) if lignes else "Rien à signaler.") + "\n")

# 4. Fraîcheur des statuts de candidature
cands = load(DATA / "candidats.json")["candidats"]
def verifie(c):
    return d(c.get("verifie_le") or c["source"].get("date"))


vieux = sorted(((AUJ - verifie(c)).days, c["nom"], c["statut"]) for c in cands
               if c["statut"] in EN_LICE and verifie(c) and (AUJ - verifie(c)).days > SEUIL_STATUT)
alertes += len(vieux)
sections.append(f"## 4. Statuts de candidature\n\n" + (
    f"{len(vieux)} statut(s) non revérifié(s) depuis plus de {SEUIL_STATUT} jours : vérifier qu'ils sont toujours exacts, puis mettre à jour `verifie_le`.\n\n"
    + "\n".join(f"- [ ] {nom} ({statut}) — vérifié il y a {j} jours" for j, nom, statut in reversed(vieux)) if vieux
    else f"✅ Tous les statuts ont été vérifiés il y a moins de {SEUIL_STATUT} jours.") + "\n")

# 5. Sondages
sd = load(DATA / "sondages.json") if (DATA / "sondages.json").exists() else {"sondages": []}
fins = [d(s["terrain_fin"]) for s in sd.get("sondages", []) if d(s.get("terrain_fin"))]
dernier = max(fins) if fins else None
age = (AUJ - dernier).days if dernier else None
if age is None or age > SEUIL_SONDAGES:
    alertes += 1
sections.append("## 5. Sondages\n\n" + (
    f"⚠️ Dernier sondage : terrain achevé le {dernier} ({age} jours). Rechercher les nouvelles notices de la "
    "[Commission des sondages](https://www.commission-des-sondages.fr/notices/medias/fichiers/bytag/14/Presidentielle-2027) "
    "et mettre à jour `data/sondages.json` (et la fenêtre de calcul)." if age is None or age > SEUIL_SONDAGES
    else f"✅ Dernier sondage : terrain achevé le {dernier} ({age} jours).") + "\n")

# 6. Temps de parole (nouveaux fichiers Arcom)
tp = load(DATA / "temps-parole.json") if (DATA / "temps-parole.json").exists() else {"fichiers": []}
connus = {f["url"] for f in tp.get("fichiers", [])}
dernier_mois = max(tp.get("mois") or ["?"])
try:
    req = urllib.request.Request(f"https://www.arcom.fr/temps-parole/hors-elections/recherche/source/{AUJ.year}", headers={"User-Agent": UA})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    liens = set(re.findall(r'https?://www\.arcom\.fr/sites/default/files/tphe/files/speaking_time_files/Export_web_Personnalites_avec_seuil_[^"\']+\.csv', page))
    liens |= {"https://www.arcom.fr" + l for l in re.findall(r'"(/sites/default/files/tphe/files/speaking_time_files/Export_web_Personnalites_avec_seuil_[^"]+\.csv)"', page)}
    nouveaux = sorted(liens - connus)
    if not liens:
        raise ValueError("aucun fichier détecté sur la page")
    if nouveaux:
        alertes += 1
    texte = (f"⚠️ {len(nouveaux)} nouveau(x) fichier(s) Arcom non intégré(s) (dernier mois intégré : {dernier_mois}). "
             "Ajouter les URL en tête de `scripts/temps_parole.py` puis le relancer :\n\n" + "\n".join(f"- {u}" for u in nouveaux)
             if nouveaux else f"✅ Aucun nouveau fichier Arcom (dernier mois intégré : {dernier_mois}).")
except Exception as e:  # noqa: BLE001
    texte = f"ℹ️ Page Arcom non exploitable automatiquement ({e}) : vérifier à la main (dernier mois intégré : {dernier_mois})."
sections.append("## 6. Temps de parole (Arcom)\n\n" + texte + "\n")

# 7. Points en attente
code, out = run(["scripts/a_verifier.py"])
m = re.search(r"(\d+) points", out)
sections.append("## 7. Points à vérifier\n\n" + (f"{m.group(1)} point(s) en attente dans `docs/a-verifier.md` (liste régénérée)." if m else out) + "\n")

print(f"# Veille hebdomadaire — {AUJ.isoformat()}\n")
print(f"**{alertes} point(s) d'attention.** Rapport généré automatiquement par `scripts/check_hebdo.py` ; aucune donnée n'a été modifiée.\n")
print("\n".join(sections))
