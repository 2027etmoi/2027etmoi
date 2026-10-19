# Méthode : données sur les candidatures et évaluations externes

Ces données alimentent la page « Candidatures en données » (`donnees.html`). Principe : **pas de note, pas de classement.** Chaque cellule présente un fait vérifiable, avec sa source et sa date. Quand l'information est inconnue, on met `null` et la page affiche « non connu ».

## Familles politiques (`bloc`)

Le champ `bloc` de `data/candidats.json` sert à regrouper les candidats sur le site. Il ne traduit aucune appréciation du site : il reprend la **grille des nuances politiques du ministère de l'Intérieur**, telle qu'elle est appliquée aux candidatures (instruction de nuançage des législatives de 2024, nuances publiées en données ouvertes avec les candidatures). On classe le **parti** du candidat, pas la personne.

| `bloc` | Libellé affiché | Nuances du ministère |
|---|---|---|
| `gauche` | Gauche | LFI, PS, PCF, DVG, UG, EXG… |
| `ecolo` | Écologistes | ECO |
| `centre` | Centre | ENS, REN, MDM, HOR, UDI, DVC… |
| `droite` | Droite | LR, DVD |
| `souverainiste` | Droite souverainiste | DSV (Debout la France, UPR, Les Patriotes) |
| `extdroite` | RN, Reconquête et alliés | RN, REC, et les partis qui leur sont alliés (Identité-Libertés) |
| `autre` | Autres | sans affiliation partisane, ou nuance DIV |

Règles :
- une personne sans parti va dans `autre`, même si son discours la rapproche d'une famille ; un maire « divers droite » (DVD) va dans `droite` ;
- le libellé affiché n'emploie aucun qualificatif absent de la grille du ministère (ni « extrême », ni « nationaliste ») ;
- tout changement de bloc est motivé par une source : nuance attribuée à une élection, adhésion ou départ d'un parti.

Vérification du 19 octobre 2026 : dans les candidatures aux législatives de 2024 publiées par le ministère (data.gouv.fr), Nicolas Dupont-Aignan et François Asselineau portent la nuance DSV « Droite souverainiste ».

## `data/candidatures.json`

```json
{
  "mise_a_jour": "2026-09-22",
  "candidatures": {
    "melenchon": {
      "declaration": { "date": "2026-05-03", "source": { "titre": "…", "url": "…", "date": "…" } },
      "designation": {
        "mode": "auto | vote_militants | instance_parti | primaire_fermee | primaire_ouverte | autre",
        "detail": "Ex. « Désigné par un vote des adhérents du PCF (72 %). »",
        "source": { "titre": "…", "url": "…", "date": "…" }
      },
      "precedentes": [
        { "annee": 2022, "resultat": "19,58 % au 1er tour (3e)", "source": { "titre": "…", "url": "…", "date": "…" } }
      ],
      "chiffrage": {
        "publie": true,
        "detail": "Chiffrage publié par l'équipe de campagne le …",
        "url": "https://…",
        "source": { "titre": "…", "url": "…", "date": "…" }
      }
    }
  },
  "a_verifier": ["…"]
}
```

Règles des champs :
- `declaration.date` : date de l'annonce publique de candidature à la présidentielle 2027. Pour une primaire, c'est la date de candidature à la primaire, et `designation.detail` le précise.
- `designation.mode` :
  - `auto` : le candidat se déclare lui-même, sans processus interne ;
  - `vote_militants` : vote des adhérents ;
  - `instance_parti` : désignation par un bureau ou un conseil ;
  - `primaire_fermee` ou `primaire_ouverte` : primaire, si elle est en cours ou a eu lieu.
- `precedentes` : candidatures à l'élection présidentielle uniquement, y compris celles qui n'ont pas obtenu les 500 parrainages. Le résultat se donne alors sous la forme « non qualifié (X parrainages) ». Sources admises : Conseil constitutionnel, ministère de l'Intérieur, Wikipédia.
- `chiffrage.publie` :
  - `true` si le candidat ou son équipe a publié un **chiffrage de son programme** (coût et financement). Une mesure chiffrée isolée ne compte pas ;
  - `false` si le candidat a explicitement dit ne pas en avoir, ou si le programme publié n'en contient pas (préciser dans `detail`) ;
  - `null` si on ne sait pas.

## `data/evaluations.json`

On ne publie que des **évaluations d'institutions ayant analysé plusieurs candidats avec une méthode commune et publiée**. L'évaluation d'un seul candidat est exclue, pour éviter un traitement asymétrique. Pas d'avis d'économistes individuels.

```json
{
  "mise_a_jour": "2026-09-22",
  "institutions": [
    {
      "id": "montaigne",
      "nom": "Institut Montaigne",
      "presentation": "Think tank fondé en 2000…",
      "orientation": { "texte": "Généralement classé libéral / centre droit.", "source": { "titre": "…", "url": "…", "date": "…" } },
      "url": "https://…"
    }
  ],
  "evaluations": [
    {
      "institution": "montaigne",
      "titre": "Présidentielle 2027 : le chiffrage des programmes",
      "url": "https://…",
      "date": "2026-…",
      "methode": "Une phrase factuelle sur la méthode.",
      "candidats": ["melenchon", "philippe"],
      "liens_par_candidat": { "melenchon": "https://…" }
    }
  ],
  "a_verifier": []
}
```

- `orientation` : description courte de l'orientation de l'institution, sourcée (presse ou Wikipédia). Pour les institutions publiques ou académiques (OFCE, IPP, Cour des comptes…), on indique leur statut, par exemple « Centre de recherche de Sciences Po ».
- **On ne reprend jamais le verdict ou la note de l'évaluation** : on donne seulement le lien.
