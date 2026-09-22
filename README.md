# 2027 et moi

Site d'information indépendant et non partisan sur l'élection présidentielle française de 2027 : qui se présente, avec quel parti, quel parcours et quelles propositions. Chaque élément renvoie à sa source.

## Pages

| Page | Contenu |
|---|---|
| `index.html` | Tableau des candidats : statut, moyenne des sondages, propositions phares, liens |
| `candidat.html?id=<id>` | Fiche candidat : photo, présentation, parcours, affaires judiciaires, programme et propositions par thème |
| `comparateur.html?c=<id>,<id>&t=<theme>` | Propositions de 1 à 4 candidats, thème par thème |
| `sondages.html` | Moyenne des intentions de vote et détail de chaque sondage |
| `donnees.html` | Candidatures en données : déclaration, désignation, programme, chiffrage, sondages, temps de parole, évaluations externes — sans note ni classement |
| `faq.html` | Questions fréquentes sourcées : règles de l'élection, sondages, programmes, méthode du site |

## Données

```
data/candidats.json          liste des personnalités, statut et source (fichier de référence)
data/programmes/<id>.json    programme, repères, mesures par thème, ressources
data/biographies/<id>.json   photo (Wikimedia Commons), présentation, parcours, affaires judiciaires
data/sondages.json           sondages bruts ; la moyenne est calculée par le site
data/candidatures.json       déclaration, désignation, présidentielles passées, chiffrage
data/evaluations.json        évaluations multi-candidats d'institutions, avec leur orientation
data/temps-parole.json       temps de parole TV/radio par mois (Arcom), produit par scripts/temps_parole.py
```

Méthode des données de candidature et des évaluations : [docs/methode-candidatures.md](docs/methode-candidatures.md). Recherches à reprendre : [docs/TODO-recherches.md](docs/TODO-recherches.md) et [docs/a-verifier.md](docs/a-verifier.md) (généré par `python3 scripts/a_verifier.py`).

Mise à jour des temps de parole (nouveaux mois publiés par l'Arcom) : ajouter les URL en tête de `scripts/temps_parole.py`, puis `python3 scripts/temps_parole.py`.

Les règles de sourçage sont dans [docs/methode-sources.md](docs/methode-sources.md) (programmes) et [docs/methode-biographies.md](docs/methode-biographies.md) (biographies, photos, affaires). Le principe : **rien n'est inventé, tout est sourcé et daté ; en cas de doute, on ne publie pas.**

## Contrôles

```bash
python3 scripts/verifier.py
```

`verifier.py` contrôle la structure et le sourçage : sources datées, agrégateurs interdits, thèmes valides, photos libres, affaires sourcées par la presse. Il est à lancer avant chaque commit.

```bash
python3 scripts/verifier_liens.py
```

`verifier_liens.py` teste toutes les URL et signale les liens morts.

## Lancer en local

```bash
python3 -m http.server 8027
```

Puis ouvrir http://localhost:8027. Un serveur local est nécessaire : les pages chargent les données JSON avec `fetch`.

## Déploiement

Site statique sans build. Netlify publie la racine du dépôt (voir `netlify.toml`).
