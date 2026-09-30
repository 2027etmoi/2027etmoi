# Méthode : prises de parole

Règle absolue : **on recense ce que la personne a dit, là où elle l'a dit — jamais ce qu'on dit d'elle.**

Une « revue de presse » classique choisit des articles *sur* un candidat : chaque choix est une décision éditoriale, impossible à défendre comme neutre. Ici, l'unité recensée est une **prise de parole publique** du candidat : un fait daté, comme un vote ou une mesure. On ne choisit pas ce qu'on pense de lui, on note où il s'est exprimé et ce qu'il a déclaré.

## Fichier

Un seul fichier, tous candidats confondus : `data/prises-de-parole.json`. Il alimente la rubrique « Prises de parole récentes » de chaque fiche et la page [Actualité de la campagne](/actualite.html).

```json
{
  "mise_a_jour": "2026-09-30",
  "fenetre": { "debut": "2026-08-19" },
  "types": { "interview": "Interview", "discours": "Discours ou meeting", "…": "…" },
  "prises_de_parole": [
    {
      "id": "le-pen",
      "date": "2026-09-28",
      "type": "interview",
      "media": "France Inter",
      "emission": "Le 7/10",
      "titre": "Titre tel que publié par le média",
      "url": "https://…",
      "declare": [
        "Une phrase factuelle par point : ce qui a été déclaré, reformulé sans qualificatif.",
        "Propose la suppression de … (« citation exacte et courte » si utile)."
      ],
      "themes": ["immigration", "economie"],
      "verifie_le": "2026-09-30"
    }
  ],
  "a_verifier": []
}
```

- `id` : identifiant de `data/candidats.json`.
- `date` : jour de la prise de parole (diffusion, publication ou tenue du discours), au format `AAAA-MM-JJ`.
- `type` : voir ci-dessous.
- `media` : le média ou le lieu où la parole a été tenue (chaîne, radio, journal, « Meeting de … », « Assemblée nationale »). `emission` est facultatif.
- `titre` : le titre tel que publié par la source, sans le modifier.
- `url` : la page de la source, **ouverte et lue** avant publication.
- `declare` : une à trois phrases, voir « Rédaction ».
- `themes` : un ou plusieurs thèmes parmi les 13 thèmes du site, plus `campagne` (candidature, alliances, primaires, stratégie).
- `verifie_le` : date à laquelle la source a été ouverte.

## Types (`type`)

| id | Libellé | Ce que c'est |
|---|---|---|
| `interview` | Interview | Entretien accordé à un média : télévision, radio, presse écrite, en ligne |
| `discours` | Discours ou meeting | Discours public, meeting, université d'été, vœux |
| `tribune` | Tribune signée | Texte signé par le candidat et publié par un média |
| `debat` | Débat | Débat contradictoire diffusé ou publié |
| `conference` | Conférence de presse | Conférence ou point de presse |
| `parlement` | Intervention au Parlement | Intervention en séance ou en commission, avec le compte rendu officiel |
| `communique` | Communiqué officiel | Communiqué publié par le candidat ou son parti |

## Ce qui est recensé, ce qui ne l'est pas

**Recensé** : toute occasion où le candidat s'exprime publiquement et de façon substantielle, dans l'un des types ci-dessus, rapportée par une source recevable.

**Non recensé**, quelle que soit sa notoriété :

- les articles *sur* le candidat : portraits, enquêtes, analyses, éditoriaux, chroniques, sondages commentés, « décryptages » ;
- les propos rapportés par des sources anonymes (« selon un proche », « dans son entourage ») ;
- les publications sur les réseaux sociaux, sauf communiqué officiel repris tel quel ;
- les échanges d'invectives et réactions à chaud d'une phrase, sans contenu de fond ;
- les comparateurs, agrégateurs et sites non officiels, et Wikipédia.

Lorsqu'une prise de parole contient une **proposition précise**, elle est aussi reportée dans le programme du candidat (`data/programmes/<id>.json`, mesure de nature `declaration`), avec la même source.

## Sources recevables

Le critère porte sur la nature de la source, pas sur sa ligne éditoriale :

- médias d'information disposant d'une rédaction professionnelle, nationaux ou régionaux : presse écrite reconnue par la CPPAP, chaînes et radios conventionnées par l'Arcom, agences de presse, quelle que soit leur orientation ;
- canaux officiels du candidat ou de son parti (site, chaîne vidéo officielle) pour les discours, conférences de presse et communiqués ;
- portails officiels des assemblées (vidéos et comptes rendus) pour les interventions parlementaires.

Un média n'est jamais écarté pour sa ligne : si le candidat y a parlé, la prise de parole est recensée. Quand un même entretien est repris par plusieurs médias, on cite le média d'origine.

## Rédaction de `declare`

Les mêmes règles que pour les mesures des programmes :

- **une à trois phrases**, à l'indicatif, qui disent *ce qui a été déclaré* : « Annonce… », « Propose… », « Déclare que… », « Estime que… », « Refuse… », « Répond que… » ;
- **aucun qualificatif** ni verbe de jugement : pas de « offensive », « recadrage », « polémique », « dérapage », « fustige », « tacle » ;
- pas d'interprétation du ton, de l'intention ou du contexte politique ;
- une citation exacte et courte, entre guillemets français « », est possible quand la formulation compte ; jamais de citation tronquée qui change le sens ;
- en cas de doute sur ce qui a été dit, la source fait foi ; si la source ne permet pas de trancher, on ne publie pas.

## Sélection : la même règle pour tous

- **Fenêtre** : les prises de parole depuis `fenetre.debut` ; la veille hebdomadaire avance cette date pour couvrir environ six semaines.
- **Fiche candidat** : les cinq prises de parole les plus récentes.
- **Page Actualité** : toutes, en ordre chronologique inverse, filtrables par candidat et par thème.
- **Couverture inégale** : tous les candidats ne sont pas invités aussi souvent ; cette inégalité est un fait du paysage médiatique, mesuré par ailleurs par l'Arcom (temps de parole). Le site l'affiche telle quelle (« Aucune prise de parole recensée depuis le … ») et ne la corrige pas.
- **Personnes ayant renoncé** : leurs prises de parole restent recensées quand elles portent sur l'élection (soutien, appel, refus), car elles éclairent la campagne.

## « En bref »

Le paragraphe affiché au-dessus de la liste n'est pas rédigé : il est **construit mécaniquement** à partir des prises de parole affichées — nombre, période, types, médias, thèmes. Il ne peut donc contenir ni appréciation ni synthèse d'opinion. Le code qui le produit est le même pour tous les candidats (`assets/common.js`, `scripts/build.py`).

## Ce que cette rubrique n'est pas

- Ce n'est pas une mesure de l'exposition médiatique : voir le temps de parole relevé par l'Arcom.
- Ce n'est pas un résumé de l'actualité du candidat : rien de ce qui lui arrive n'y figure, seulement ce qu'il dit.
- Ce n'est pas exhaustif : une prise de parole absente est une prise de parole non recensée, pas une prise de parole qui n'a pas eu lieu. Les manques se signalent via la [page Contact](/contact.html).
