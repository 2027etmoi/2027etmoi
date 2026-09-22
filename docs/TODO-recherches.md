# Recherches à reprendre

Point du 22 septembre 2026. Plusieurs recherches ont été interrompues : le quota de recherches web de la session (200) a été épuisé, et certains sites étaient inaccessibles (paywall Le Monde, Libération, Nouvel Obs ; erreur 403 sur JDD et CNews ; Cloudflare sur lesecologistes.fr). Rien de ce qui suit n'est publié sur le site.

La liste complète et détaillée, fiche par fiche, est générée dans [a-verifier.md](a-verifier.md) :

```bash
python3 scripts/a_verifier.py
```

Pour relancer les recherches avec un quota plus large, il faut augmenter la variable `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`, ou répartir le travail sur plusieurs sessions.

## Priorité 1 : affaires judiciaires dont l'issue n'a pas été trouvée

Ces procédures ne sont pas publiées tant que leur état actuel n'est pas vérifié dans la presse.

- [ ] **Mélenchon**
  - Diffamation envers Paranaguá : issue de l'appel.
  - Condamnation dans le litige avec Radio France (janvier 2022) : appel ?
  - Enquête pour « injure publique » après ses propos sur la BRAV-M : suites.
  - Plainte pour apologie du terrorisme (juin 2026) : une enquête est-elle ouverte ?
  - Assistants au Parlement européen : instruction close le 26/05/2026 sans mise en examen. Revoir l'état publié (actuellement « enquête ») : non-lieu ou autre suite ?
- [ ] **Roussel** : enquête préliminaire du PNF (mars 2022) sur un emploi présumé fictif d'assistant parlementaire. État actuel ?
- [ ] **Ruffin** : condamnation pour diffamation (livre « Quartier Nord », 2008). Date, peine, caractère définitif.
- [ ] **Tondelier** : relaxée le 6/11/2020 (diffamation, plainte de Briois et Bilde). Issue de l'appel.
- [ ] **Kazib** : procès pour apologie du terrorisme renvoyé fin juin 2026. Nouvelle date, jour exact de l'audience, juridiction.
- [ ] **Maurel** : enquête préliminaire pour abus de confiance ouverte en mars 2017 (eurodéputés, signalement de Sophie Montel). Issue.
- [ ] **Royal** : condamnation pour diffamation envers Sylvain Tronchet (20/04/2023, 500 € avec sursis). Issue de l'appel. Seule source trouvée : Puremédias.
- [ ] **Philippe** : dossier du Havre, juge d'instruction désigné le 19/05/2026. Suites depuis mai. Absence de pourvoi contre le non-lieu Covid (CJR, 7/07/2025).
- [ ] **Villepin**
  - Enquête sur les statuettes : audition libre mi-juillet 2026 selon le JDD ?
  - Clearstream : absence de pourvoi, qui rendrait la relaxe définitive ?
- [ ] **Le Maire** : enquête préliminaire pour faux en écriture publique (dossier des autoroutes, 2024). État actuel.
- [ ] **Retailleau**
  - Plainte devant la CJR pour ses propos sur Mayotte : chronologie à établir.
  - Fonds du groupe UMP au Sénat : une procédure le vise-t-elle personnellement ?
- [ ] **Bertrand** : plainte en diffamation de Mediapart (mis en examen en 2011, renvoyé en correctionnelle). Issue introuvable.
- [ ] **Attal** : plainte de six militants kanak devant la CJR ; plainte classée le 17/04/2023, dont l'objet est à préciser.
- [ ] **Cazeneuve** : deux plaintes devant la CJR (assignations à résidence ; attentat de Nice). Issue selon une presse reconnue.
- [ ] **Hollande** : enquête préliminaire du 21/11/2016 pour compromission de la défense nationale. Le visait-elle personnellement ? Issue.
- [ ] **Bouamrane** : enquête franceinfo du 22/05/2026 et signalement à la chambre régionale des comptes. Une procédure judiciaire a-t-elle été ouverte ?

## Priorité 2 : mesures de programme à confirmer par une source ouverte

- [ ] **Glucksmann**
  - 100 Md€ d'investissement vert sur 10 ans.
  - Hausse de 10 % du salaire des enseignants.
  - Leasing social.
  - Dissuasion étendue à l'Europe et fonds de défense de 500 Md€.
- [ ] **Guedj** : « gel » de la réforme des retraites.
- [ ] **Roussel** : SMIC à 1 700 € et +5 % pour tous les salaires ; retraite à 60 ans ; 32 heures.
- [ ] **Ruffin** : SMIC à 1 600 € et retraite à 60 ans (reprise du programme du NFP ?).
- [ ] **Tondelier**
  - Liste complète des « 21 priorités » : page programme bloquée par Cloudflare, et X bloqué.
  - Taxe Zucman, ISF climatique, contribution climat-énergie, sortie du nucléaire.
- [ ] **Bertrand** : mesures de 2021-2022 (prison ferme pour agression d'élus ou de forces de l'ordre, regroupement familial, 400 000 logements). Sont-elles reprises en 2026 ?
- [ ] **Attal** : « 13e mois pour tous » (CNews, erreur 403) ; réforme institutionnelle et sécurité (JDD, erreur 403) ; aucune mesure de sécurité sourcée.
- [ ] **Philippe** : chiffres de défense (700 000 munitions, navires aux Antilles). Aucune mesure santé ni institutions.
- [ ] **Villepin** : abrogation de la réforme des retraites et retraite par points.
- [ ] **Le Pen** : trajectoire économique annoncée pour début octobre 2026. Mettre la fiche à jour.
- [ ] **Asselineau** : programme 2027 annoncé « prochainement ».
- [ ] **Faure** : livre-programme *La Loi du plus juste* (paru le 17/09), non consulté.
- [ ] **Royal** : ses 5 priorités sont des orientations. Guetter des mesures précises.
- [ ] **Santé** : aucune mesure sourcée chez Attal, Philippe, Villepin et Retailleau (chapitre « à venir »).

## Priorité 3 : faits biographiques et statuts

- [ ] **Cazeneuve** : statut passé à « déclaré » d'après le titre du Monde (16/07/2026, article payant). Confirmer par une source ouverte. La note de sa fiche programme dit encore qu'il n'est pas déclaré.
- [ ] **Bertrand** : est-il encore membre de LR ? (franceinfo le présente comme « président LR de la région » le 27/08/2026.)
- [ ] **Egger** : date de naissance (Wikipédia porte un bandeau « Autobiographie ») ; affiliation universitaire (Groningue ou Rotterdam) ; date de déclaration (19/04, 20/04 ou mai).
- [ ] **Lalanne** : inéligibilité de 18 mois prononcée en avril 2025 (comptes de campagne des européennes). Vérifier qu'elle a pris fin avant 2027.
- [ ] **Durif** : nom de son parti (« Elvita », selon Wikipédia seulement).
- [ ] **Massard** : sa candidature est-elle maintenue hors primaire ?
- [ ] **Mikolajczak** : âge (27 ou 28 ans) et date de déclaration (27/06 selon Sud Radio).
- [ ] **Lisnard** : date de création de Nouvelle Énergie (2013, 2014 ou 2021 selon les sources).
- [ ] **Guedj** : mandat régional en cours ?
- [ ] Biographies et fiches programme manquantes pour les candidats ajoutés le 22/09 : Lalanne, Branco, Durif, Mikolajczak, Massard. Pas de programme pour Hollande ni Le Maire (pressentis).

## Priorité 4 : photos

- [ ] Pas de portrait officiel libre pour la plupart des candidats. Les portraits du Parlement européen sur Commons ont un modèle de licence proposé à la suppression le 19/09/2026 : les écarter tant que ce n'est pas tranché.
- [ ] Pas de photo libre pour Labib, Mlekuz et Mathieu.
- [ ] Photos anciennes à remplacer si une version libre récente apparaît : Villepin (2005), Guedj (2010), Lisnard (2013).
