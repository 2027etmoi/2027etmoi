#!/usr/bin/env python3
"""Régénère les « propositions phares » de data/candidats.json à partir des fiches programme.

Pour chaque candidat ayant une fiche data/programmes/<id>.json, on retient jusqu'à 4 mesures
vérifiées, de thèmes différents, en privilégiant la nature « programme », dans l'ordre de la fiche.
Les candidats sans fiche gardent leurs propositions (qui doivent alors être sourcées à la main).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX = 4

cands_path = ROOT / "data" / "candidats.json"
data = json.loads(cands_path.read_text(encoding="utf-8"))

for c in data["candidats"]:
    f = ROOT / "data" / "programmes" / f"{c['id']}.json"
    if not f.exists():
        continue
    mesures = json.loads(f.read_text(encoding="utf-8")).get("mesures", [])
    choix, themes = [], set()
    for nature_ok in (lambda m: m.get("nature") == "programme", lambda m: True):
        for m in mesures:
            if len(choix) >= MAX:
                break
            if m["theme"] in themes or not nature_ok(m):
                continue
            choix.append(m["texte"])
            themes.add(m["theme"])
    c["propositions"] = choix

cands_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("propositions régénérées")
