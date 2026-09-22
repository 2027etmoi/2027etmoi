#!/usr/bin/env python3
"""Écrit data/meta.json : date de la dernière publication (dernier commit) et
date de mise à jour la plus récente des données. Lancé à chaque déploiement
(voir netlify.toml) ; peut aussi être lancé à la main avant un commit.
"""
import json
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

try:
    publication = subprocess.run(["git", "log", "-1", "--format=%cs"], cwd=ROOT,
                                 capture_output=True, text=True, check=True).stdout.strip()
except Exception:  # noqa: BLE001 — pas de git disponible
    publication = ""

dates = []
for f in DATA.rglob("*.json"):
    if f.name == "meta.json":
        continue
    try:
        d = json.loads(f.read_text(encoding="utf-8")).get("mise_a_jour")
    except Exception:  # noqa: BLE001
        continue
    if isinstance(d, str) and len(d) >= 10:
        dates.append(d[:10])

meta = {
    "publication": publication or date.today().isoformat(),
    "donnees": max(dates) if dates else None,
}
(DATA / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(meta)
