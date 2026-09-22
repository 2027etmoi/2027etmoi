# Méthode : biographies, photos et affaires judiciaires

Un fichier par candidat : `data/biographies/<id>.json`. L'`id` est celui de `data/candidats.json`. Règle absolue : **rien n'est inventé, tout est sourcé.**

```json
{
  "id": "melenchon",
  "mise_a_jour": "2026-09-22",
  "photo": {
    "url": "https://upload.wikimedia.org/wikipedia/commons/…/Fichier.jpg",
    "page": "https://commons.wikimedia.org/wiki/File:Fichier.jpg",
    "auteur": "Nom de l'auteur ou institution",
    "licence": "CC BY-SA 4.0",
    "annee": "2022",
    "officielle": true,
    "legende": "Portrait officiel de député (Assemblée nationale)"
  },
  "presentation": {
    "texte": "2 à 3 phrases neutres : qui est la personne, ses fonctions principales, sa famille politique.",
    "sources": [{ "titre": "…", "url": "…", "date": "…" }]
  },
  "naissance": {
    "date": "1951-08-19",
    "lieu": "Tanger (Maroc)",
    "source": { "titre": "…", "url": "…", "date": "…" }
  },
  "parcours_politique": [
    { "periode": "2017-2022", "texte": "Député de la 4e circonscription des Bouches-du-Rhône.", "source": { "titre": "…", "url": "…", "date": "…" } }
  ],
  "parcours_professionnel": [
    { "periode": "1976-1978", "texte": "Professeur de lettres.", "source": { "titre": "…", "url": "…", "date": "…" } }
  ],
  "affaires": [
    {
      "titre": "Affaire des comptes de campagne 2017",
      "texte": "Description factuelle et courte : faits reprochés, qualification juridique, étapes.",
      "etat": "enquete | mise_en_examen | renvoi_proces | condamnation_non_definitive | condamnation_definitive | instruction_close | relaxe | non_lieu | classement",
      "etat_detail": "Ex. « Condamnée en appel le 7 juillet 2026 ; pourvoi en cassation en cours. »",
      "date_etat": "2026-07-07",
      "sources": [{ "titre": "…", "url": "…", "date": "…" }]
    }
  ],
  "a_verifier": ["Notes internes, non affichées."]
}
```

## Photo

- **Uniquement Wikimedia Commons**, sous licence libre (CC BY, CC BY-SA, CC0, domaine public ou Licence Ouverte). Pas de photo de site de campagne ni de média : elles sont protégées par le droit d'auteur.
- On privilégie un **portrait officiel** quand il est sur Commons : Assemblée nationale, Sénat, Parlement européen, gouvernement, Élysée ou collectivité. On met alors `officielle: true`. Sinon, on prend un portrait récent et net, et `officielle: false`.
- `url` est l'adresse directe `upload.wikimedia.org` du fichier. On prend de préférence une vignette de 500 px de large, au format `…/thumb/…/500px-Fichier.jpg` (Wikimedia refuse les largeurs non standard comme 400 px ; 250, 330 et 500 fonctionnent). L'URL doit avoir été vérifiée en l'ouvrant.
- `auteur` et `licence` sont recopiés depuis la page Commons.
- S'il n'y a aucune photo libre, on omet le champ `photo`.

## Parcours

- Parcours politique : mandats électifs, fonctions ministérielles, responsabilités de parti et candidatures présidentielles passées avec leur score. Ordre antichronologique, 3 à 10 entrées.
- Parcours professionnel : formation (grandes écoles, diplômes) et métiers exercés, 1 à 5 entrées.
- Sources admises : Wikipédia (admis ici), sites institutionnels (assemblee-nationale.fr, senat.fr, europarl.europa.eu, gouvernement.fr, HATVP) et médias reconnus.

## Affaires judiciaires

- On ne retient que les **procédures judiciaires visant personnellement la personne** : enquête, mise en examen, procès, condamnation, relaxe. Les polémiques sans procédure sont exclues.
- **Sources** : au moins une source de presse reconnue (AFP, franceinfo, Le Monde, Libération, Le Figaro, Mediapart, etc.) datée et ouverte. Wikipédia seul ne suffit pas.
- **État exact de la procédure à la date la plus récente trouvée.** Tant qu'il n'y a pas de condamnation définitive, `etat_detail` rappelle la présomption d'innocence.
- **Rédaction** : ton neutre, termes juridiques exacts (« mis en examen pour », « condamné en première instance à »), aucun adjectif et aucune spéculation.
- Les condamnations civiles pour diffamation ou injure peuvent être mentionnées si elles sont notables et bien sourcées.
- En cas de doute sur l'état actuel d'une procédure, elle va dans `a_verifier` et n'est pas publiée.
- S'il n'y a aucune affaire, on écrit `"affaires": []`.
- Périmètre : procédures pénales, et condamnations civiles pour diffamation ou injure. Les contentieux civils ordinaires (prud'hommes, litiges commerciaux) sont exclus.
