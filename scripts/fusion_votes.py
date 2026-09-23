#!/usr/bin/env python3
"""Fusionne data/votes-an.json, votes-senat.json et votes-pe.json dans data/votes.json."""
import json
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
out = {"mise_a_jour": date.today().isoformat(), "sources": [], "mandats": {}, "scrutins": [], "a_verifier": []}
for nom in ("votes-an.json", "votes-senat.json", "votes-pe.json"):
    f = DATA / nom
    if not f.exists():
        continue
    part = json.loads(f.read_text(encoding="utf-8"))
    out["sources"] += part.get("sources", [])
    for cid, mandats in (part.get("mandats") or {}).items():
        out["mandats"].setdefault(cid, []).extend(mandats)
    out["scrutins"] += part.get("scrutins", [])
    out["a_verifier"] += part.get("a_verifier", [])
    print("fusionné :", nom)
out["scrutins"].sort(key=lambda s: (s.get("date", ""), s.get("id", "")), reverse=True)
for cid in out["mandats"]:
    out["mandats"][cid].sort(key=lambda m: m.get("debut") or "", reverse=True)
out["a_verifier"] = list(dict.fromkeys(out["a_verifier"]))
(DATA / "votes.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(len(out["scrutins"]), "scrutins ·", len(out["mandats"]), "personnalités avec un mandat renseigné")
