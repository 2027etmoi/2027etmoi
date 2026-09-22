# Méthode : programmes et mesures

Règle absolue : **rien n'est inventé, tout est sourcé.** Une mesure sans source vérifiée n'est pas publiée.

## Fichiers

Un fichier par candidat : `data/programmes/<id>.json`. L'`id` est celui de `data/candidats.json`.

```json
{
  "id": "melenchon",
  "mise_a_jour": "2026-09-22",
  "programme": {
    "titre": "L'Avenir en commun (édition 2025)",
    "url": "https://…",
    "etat": "complet | partiel | aucun",
    "note": "Une phrase factuelle sur l'état du programme (ex. « Pas de programme complet publié au 22/09/2026 ; mesures annoncées dans la presse. »)"
  },
  "reperes": [
    { "texte": "Député des Bouches-du-Rhône de 2017 à 2022.", "source": { "titre": "Wikipédia", "url": "https://…", "date": "2026-09-22" } }
  ],
  "mesures": [
    {
      "theme": "retraites",
      "texte": "Retour de l'âge légal de départ à 60 ans.",
      "nature": "programme",
      "source": { "titre": "L'Avenir en commun, chap. 4", "url": "https://…", "date": "2025-10-01" }
    }
  ],
  "ressources": [
    { "titre": "Entretien au 20 h de TF1", "url": "https://…", "type": "video", "date": "2026-05-03" }
  ],
  "a_verifier": [
    "Notes internes, non affichées : mesures entendues mais non confirmées par une source ouverte."
  ]
}
```

## Thèmes (`theme`)

| id | Libellé |
|---|---|
| `economie` | Économie, fiscalité et finances publiques |
| `travail` | Travail, salaires et pouvoir d'achat |
| `retraites` | Retraites et protection sociale |
| `sante` | Santé |
| `education` | Éducation, jeunesse et recherche |
| `ecologie` | Écologie, climat et énergie |
| `immigration` | Immigration et intégration |
| `securite` | Sécurité et justice |
| `international` | Europe, international et défense |
| `institutions` | Institutions et démocratie |
| `logement` | Logement |
| `territoires` | Agriculture, ruralité et services publics locaux |

## Nature de la source (`nature`)

- `programme` : programme officiel, site de campagne, site du parti, livre-programme ou document de campagne.
- `declaration` : propos du candidat lui-même, dans un entretien, un discours ou un post officiel, rapportés par un média.
- `presse` : mesure décrite par un média reconnu, sans citation directe du candidat.

## Règles

1. **Vérification** : la page source a été ouverte, et la mesure y figure. Si la page ne peut pas être ouverte (erreur 403, paywall), la mesure va dans `a_verifier` et n'est pas publiée.
2. **Sources acceptées** : sites officiels des candidats et des partis ; médias reconnus (AFP, franceinfo, Le Monde, Libération, Le Figaro, Les Échos, Le Parisien, Ouest-France, Public Sénat, LCP, France 24, BFM, TF1, RTL, Europe 1, Mediapart, L'Opinion, JDD, CNews, etc.).
3. **Sources refusées** :
   - agrégateurs et comparateurs non officiels (elyseescope, monvote2027, candidatspresidentielles2027, repere2027, polradar, sondages-presidentielle2027…) ;
   - Wikipédia pour une mesure. Wikipédia n'est admis que pour les `reperes` biographiques.
4. **Rédaction** : reformulation fidèle, courte (au plus 25 mots), neutre, sans adjectif évaluatif. On garde les chiffres exacts de la source. Pas de citation longue ; un court extrait entre guillemets est possible s'il est indispensable.
5. **Pas d'extrapolation** : on ne déduit pas une mesure d'une orientation générale. « Veut réduire l'immigration » n'est pas une mesure. « Quotas annuels d'immigration économique votés par le Parlement » en est une.
6. **Datation** : chaque source a une date au format `AAAA-MM-JJ` (ou `AAAA-MM` à défaut). Les programmes antérieurs à 2025 ne sont retenus que si le candidat s'en réclame explicitement pour 2027, et la `note` du programme le précise.
7. **Pas de doublon** : une mesure n'apparaît qu'une fois, dans le thème le plus pertinent.
8. **Archives** : si une source officielle a été retirée ou déplacée, une copie archivée (web.archive.org) du document officiel est admise. Le titre de la source le précise, par exemple « L'Avenir en commun (PDF officiel, copie archivée du 9 mars 2026) ».

## Propositions phares du tableau d'accueil

Les `propositions` de `data/candidats.json` ne sont pas saisies à la main quand une fiche programme existe. Le script `python3 scripts/propositions_phares.py` les régénère : il prend jusqu'à 4 mesures vérifiées de la fiche, de thèmes différents, en privilégiant la nature `programme`.
