# 2027 et moi

Site d'information indépendant et non partisan sur l'élection présidentielle française de 2027 : qui se présente, avec quel parti et quelles propositions, avec des liens vers les sources.

## Structure

```
index.html            page d'accueil : tableau des candidats
assets/style.css      styles (clair / sombre, cartes sur mobile)
assets/app.js         chargement, filtres, tri
data/candidats.json   données des candidats (source unique)
docs/                 notes de recherche
```

Site statique, sans étape de build. Il peut être publié tel quel sur GitHub Pages.

## Lancer en local

La page charge `data/candidats.json` avec `fetch`. Il faut donc un serveur local : ouvrir le fichier directement ne suffit pas.

```bash
python3 -m http.server 8027
```

Puis ouvrir http://localhost:8027.

## Mettre à jour les données

Chaque entrée de `data/candidats.json` contient :

| Champ | Valeurs |
|---|---|
| `bloc` | `gauche`, `ecolo`, `centre`, `droite`, `extdroite`, `autre` |
| `statut` | `declare`, `primaire`, `pressenti`, `empeche`, `renonce` (affiché « Pas candidat ») |
| `source` | `{ titre, url, date }` — **obligatoire** pour tout statut |
| `propositions` | liste courte de mesures phares, reprises de sources vérifiées |
| `liens` | `campagne`, `programme`, `parti`, `x`, `instagram`, `youtube`, `wikipedia` |

Règles : ne publier que des liens vérifiés, dater chaque source et penser à mettre à jour `mise_a_jour`.
