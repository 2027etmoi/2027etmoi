#!/usr/bin/env python3
"""Fusionne data/candidatures-*.json (produits par lots) dans data/candidatures.json."""
import json
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
out = {"mise_a_jour": date.today().isoformat(), "candidatures": {}, "a_verifier": []}
target = DATA / "candidatures.json"
if target.exists():
    prev = json.loads(target.read_text(encoding="utf-8"))
    out["candidatures"].update(prev.get("candidatures", {}))
    out["a_verifier"] += prev.get("a_verifier", [])
for f in sorted(DATA.glob("candidatures-*.json")):
    part = json.loads(f.read_text(encoding="utf-8"))
    out["candidatures"].update(part.get("candidatures", {}))
    out["a_verifier"] += part.get("a_verifier", [])
    f.unlink()
    print("fusionné :", f.name)
out["a_verifier"] = list(dict.fromkeys(out["a_verifier"]))
target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(len(out["candidatures"]), "candidatures dans", target.name)
