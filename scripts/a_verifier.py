#!/usr/bin/env python3
"""Rassemble les champs « a_verifier » de toutes les fiches dans docs/a-verifier.md.

Usage : python3 scripts/a_verifier.py
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
noms = {c["id"]: c["nom"] for c in json.loads((ROOT / "data/candidats.json").read_text(encoding="utf-8"))["candidats"]}

sections = []
total = 0
for kind, label in (("biographies", "Biographies et affaires judiciaires"), ("programmes", "Programmes et mesures")):
    lines = []
    for f in sorted((ROOT / "data" / kind).glob("*.json")):
        items = json.loads(f.read_text(encoding="utf-8")).get("a_verifier") or []
        if not items:
            continue
        total += len(items)
        lines.append(f"\n### {noms.get(f.stem, f.stem)} (`data/{kind}/{f.stem}.json`)\n")
        lines += [f"- [ ] {str(i).strip()}" for i in items]
    sections.append(f"\n## {label}\n" + ("\n".join(lines) if lines else "\nRien à vérifier.\n"))

out = ROOT / "docs" / "a-verifier.md"
out.write_text(
    "# Points à vérifier (généré)\n\n"
    f"Généré le {date.today().isoformat()} par `python3 scripts/a_verifier.py` à partir des champs `a_verifier` "
    f"des fiches : {total} points. Ne pas éditer à la main. Une fois un point tranché, mettre à jour la fiche "
    "(publier la donnée sourcée ou supprimer la note) puis relancer le script.\n"
    + "".join(sections) + "\n",
    encoding="utf-8",
)
print(f"{total} points → {out.relative_to(ROOT)}")
