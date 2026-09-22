# Consignes : mise à jour hebdomadaire par Claude

Tu mets à jour les **données** du site « 2027 et moi », un site d'information non partisan sur la présidentielle française de 2027. Date du jour : celle de l'exécution.

## Règle absolue

**Rien n'est inventé, tout est sourcé.** Chaque donnée ajoutée ou modifiée repose sur une source que tu as **ouverte** (WebFetch) et qui la contient réellement. En cas de doute, tu ne publies pas : tu ajoutes une note dans le champ `a_verifier` du fichier concerné. Ton neutre, aucun adjectif évaluatif. Lis d'abord :

- `docs/methode-sources.md` : programmes et mesures ;
- `docs/methode-biographies.md` : biographies et affaires judiciaires, avec des règles strictes et la présomption d'innocence ;
- `docs/methode-candidatures.md` : données de candidature ;
- `docs/questions-cles.md` : positions sur les questions clés.

Sources refusées : les agrégateurs et comparateurs non officiels (elyseescope, monvote2027, candidatspresidentielles2027, etc.), et Wikipédia pour une mesure ou une affaire. Pour tes recherches, privilégie les sources ouvertes : franceinfo.fr, france24.com, publicsenat.fr, lcp.fr, europe1.fr, ici.fr et francebleu.fr, ainsi que les sites officiels des candidats, des partis et des institutions (conseil-constitutionnel.fr, commission-des-sondages.fr, arcom.fr).

## Ce que tu fais, par ordre de priorité

1. **Lis `rapport.md`**, le rapport de veille de la semaine, et traite chaque point d'attention.
2. **Calendrier** (`data/calendrier.json`) :
   - pour chaque étape passée, mets à jour ce qui en découle : résultats d'une primaire, statuts des candidats concernés ;
   - ajoute les nouvelles étapes annoncées, avec leur source ;
   - passe les dates « estimee » en « officielle » dès qu'une source officielle les fixe (décret de convocation).
3. **Statuts** (`data/candidats.json`) :
   - recherche les déclarations, retraits, résultats de primaire et désignations de la semaine ;
   - mets à jour `statut`, `statut_detail`, `source` et `verifie_le` ;
   - pour chaque candidat « declare », « primaire » ou « pressenti » dont tu confirmes le statut, mets `verifie_le` à la date du jour ;
   - n'ajoute un nouveau candidat qu'avec une source de presse reconnue.
4. **Sondages** (`data/sondages.json`) :
   - ajoute les nouveaux sondages d'intentions de vote au 1er tour, en recopiant les chiffres exacts de la notice de la Commission des sondages ou de l'institut ;
   - avance la fenêtre (`fenetre`) pour couvrir environ les 7 dernières semaines, et retire les sondages sortis de la fenêtre ;
   - respecte le format existant (hypothèses, scores par id).
5. **Programmes** (`data/programmes/<id>.json`) : ajoute les mesures des programmes publiés ou détaillés depuis la dernière mise à jour. Commence par les points signalés dans `docs/a-verifier.md` (par exemple la trajectoire économique de Marine Le Pen ou le programme de l'UPR).
6. **Positions sur les questions clés** (`data/questions.json`) : mets-les à jour si une nouvelle position sourcée est apparue.
7. **Affaires judiciaires** (`data/biographies/<id>.json`) : mets à jour l'état des procédures qui ont évolué, avec une source de presse reconnue ouverte.

Limite-toi à ce que tu peux vérifier sérieusement. Mieux vaut peu de changements sûrs que beaucoup de changements douteux.

## Contraintes techniques

- Modifie uniquement les fichiers de `data/` (et `docs/a-verifier.md` via le script). Ne touche jamais au code : `assets/`, `scripts/`, les pages `.html` et `.github/`.
- Mets à jour le champ `mise_a_jour` des fichiers que tu modifies.
- Avant de conclure, lance :
  - `python3 scripts/propositions_phares.py`
  - `python3 scripts/a_verifier.py`
  - `python3 scripts/verifier.py`, qui doit afficher OK. Sinon, corrige.
- Crée une branche `veille/AAAA-MM-JJ`, fais un commit par type de changement, pousse la branche, puis ouvre une pull request avec `gh pr create` vers `main` :
  - **titre** : « Veille du AAAA-MM-JJ : mises à jour sourcées » ;
  - **corps** : la liste de chaque changement (fichier, donnée, ancienne valeur puis nouvelle valeur, source avec lien et date), puis la liste des points laissés en suspens et pourquoi.
- **Si tu n'as rien trouvé** de fiable à changer, n'ouvre pas de pull request. Commente l'issue de veille la plus récente (étiquette `veille`) avec un court compte rendu de ce que tu as vérifié.
