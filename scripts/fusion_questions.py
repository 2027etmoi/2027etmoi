#!/usr/bin/env python3
"""Fusionne data/questions-lots/*.json (positions recherchées par lots) dans data/questions.json."""
import json
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
cible = DATA / "questions.json"
q = json.loads(cible.read_text(encoding="utf-8"))
q.setdefault("positions", {})
q.setdefault("a_verifier", [])
for f in sorted((DATA / "questions-lots").glob("*.json")):
    lot = json.loads(f.read_text(encoding="utf-8"))
    for cid, pos in (lot.get("positions") or {}).items():
        q["positions"].setdefault(cid, {}).update(pos)
    q["a_verifier"] += lot.get("a_verifier") or []
    f.unlink()
    print("fusionné :", f.name)
q["a_verifier"] = list(dict.fromkeys(q["a_verifier"]))
q["mise_a_jour"] = date.today().isoformat()
cible.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(sum(len(p) for p in q["positions"].values()), "positions pour", len(q["positions"]), "candidats")
