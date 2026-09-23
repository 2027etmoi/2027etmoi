# Méthode : votes au Parlement

Objectif : montrer, pour chaque candidat qui a été parlementaire, **ce qu'il a voté**, fait daté et vérifiable, et le relier aux questions clés. Les votes complètent les déclarations : ils ne les remplacent pas.

## Principes

1. **Seuls les votes nominatifs comptent.** Un vote de groupe n'est jamais attribué à un candidat. Les scrutins publics (Assemblée, Sénat) et les votes par appel nominal (Parlement européen) sont nominatifs ; les votes à main levée ne le sont pas et ne sont pas repris.
2. **Aucun score d'orientation.** On ne calcule ni pourcentage de votes « à gauche », ni indice de proximité entre candidats, ni note. Ce serait un classement déguisé.
3. **Pas de taux de participation ni d'absentéisme.** Ces chiffres sont trompeurs : un ministre ne vote pas, un candidat en campagne non plus, et les scrutins publics ne couvrent qu'une partie du travail parlementaire. Une absence isolée est affichée telle quelle, sans en tirer de conclusion.
4. **Couverture inégale, dite explicitement.** Beaucoup de candidats n'ont jamais été parlementaires : leur fiche affiche « Jamais élu au Parlement », et non une rubrique vide. L'absence de votes n'est pas un défaut.
5. **Source officielle obligatoire** : données ouvertes de l'Assemblée nationale, du Sénat ou du Parlement européen, avec un lien vers la page officielle du scrutin.
6. **Intitulé neutre.** On reprend l'objet officiel du scrutin, éventuellement raccourci, sans qualificatif ajouté.

## Quels scrutins retenir

- **Tous les scrutins solennels** et les **motions de censure** de la législature en cours ;
- **les scrutins liés à nos questions clés** (`data/questions.json`), qui portent sur le même sujet ;
- **les textes marquants** du mandat, choisis sur des critères explicites : réforme des retraites, lois de finances, lois sur l'immigration, l'énergie, la sécurité, la fin de vie, la santé, l'agriculture, les libertés publiques ;
- au Parlement européen : les votes finaux sur les textes équivalents et les résolutions notables (Ukraine, Israël, climat, migration, budget).

Un scrutin retenu est **le même pour tous les candidats** : on ne sélectionne jamais un vote candidat par candidat.

## `data/votes.json`

```json
{
  "mise_a_jour": "2026-09-23",
  "sources": [
    { "titre": "Assemblée nationale — données ouvertes, scrutins", "url": "https://data.assemblee-nationale.fr/", "licence": "Licence Ouverte 2.0" }
  ],
  "mandats": {
    "attal": [
      { "chambre": "AN", "detail": "Député des Hauts-de-Seine", "debut": "2022-06-22", "fin": null,
        "source": { "titre": "Assemblée nationale", "url": "https://…", "date": "2026-09-23" } }
    ],
    "philippe": []
  },
  "scrutins": [
    {
      "id": "an-17-8431",
      "chambre": "AN",
      "date": "2026-07-21",
      "titre": "Proposition de loi visant à interdire les réseaux sociaux aux moins de 15 ans (lecture définitive)",
      "type": "solennel",
      "resultat": "adopté",
      "url": "https://www2.assemblee-nationale.fr/scrutins/detail/(legislature)/17/(num)/8431",
      "questions": ["q33"],
      "votes": { "faure": "abstention", "guedj": "pour", "batho": "pour" }
    }
  ],
  "a_verifier": []
}
```

Valeurs de `votes` : `pour`, `contre`, `abstention`, `non_votant` (présent mais ne prenant pas part au vote), `absent` (non inscrit au scrutin). Un candidat qui n'était pas membre de la chambre à cette date **n'apparaît pas** dans `votes` : la page affiche alors « non membre ».

`chambre` : `AN` (Assemblée nationale), `SENAT`, `PE` (Parlement européen).

## Affichage

- **Fiche candidat** : bloc replié « Votes au Parlement », scrutins du plus récent au plus ancien, avec la date, l'objet, le vote et le lien officiel. Si `mandats` est vide : « Jamais élu au Parlement (Assemblée nationale, Sénat ou Parlement européen) ».
- **Questions clés** : quand un scrutin est relié à une question, le vote est affiché à côté de la position déclarée. Si les deux diffèrent, les deux sont montrés avec leur date, sans commentaire.
