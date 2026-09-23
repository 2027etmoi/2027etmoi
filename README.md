# 2027 et moi

Site d'information indépendant et non partisan sur l'élection présidentielle française de 2027 : qui se présente, avec quel parti, quel parcours et quelles propositions. Chaque élément renvoie à sa source.

## Pages

| Page | Contenu |
|---|---|
| `index.html` | Accueil : compte à rebours, prochaines étapes (data/calendrier.json), entrées, liste des candidats |
| `candidats.html` | Tableau des candidats : statut, moyenne des sondages, propositions phares, liens |
| `candidats/<id>.html` | Fiche candidat (générée par le build à partir du gabarit `candidat.html`) : photo, présentation, parcours, affaires, programme par thème, temps de parole |
| `mes-priorites.html` | Questionnaire : choix de thèmes, propositions anonymes, puis révélation de qui propose quoi (sans recommandation de vote, rien n'est enregistré) |
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
data/questions.json          questions clés et positions sourcées des candidats
data/votes.json              votes nominatifs au Parlement (AN, Sénat, PE), fusion de votes-an/senat/pe.json
```

Méthode des données de candidature et des évaluations : [docs/methode-candidatures.md](docs/methode-candidatures.md). Recherches à reprendre : [docs/TODO-recherches.md](docs/TODO-recherches.md) et [docs/a-verifier.md](docs/a-verifier.md) (généré par `python3 scripts/a_verifier.py`).

Mise à jour des votes : `python3 scripts/votes_an.py` (17e législature), `scripts/votes_an_historique.py` (12e-16e), `scripts/votes_senat.py`, `scripts/votes_pe.py`, puis `python3 scripts/fusion_votes.py` (qui fusionne tous les `data/votes-*.json`). Méthode : [docs/methode-votes.md](docs/methode-votes.md).

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

## Build (référencement)

```bash
python3 scripts/build.py
```

Lancé automatiquement par Netlify à chaque déploiement (`netlify.toml`). Il :
- écrit `data/meta.json` (date de dernière mise à jour affichée dans le pied de page) ;
- génère une page statique par candidat dans `candidats/` (titre, description, balises de partage, données structurées `ProfilePage`, résumé lisible sans JavaScript) ;
- met à jour les balises SEO des pages principales (entre `<!--SEO-->` et `<!--/SEO-->`), les données structurées de la FAQ et la liste des candidats de l'accueil ;
- versionne les fichiers CSS/JS (`?v=` + empreinte) ;
- écrit `sitemap.xml` et `robots.txt`.

`candidats/`, `sitemap.xml` et `robots.txt` ne sont pas versionnés dans git : ils sont régénérés. L'URL du site vient de la variable `SITE_URL` (ou `URL`, fournie par Netlify).

## Lancer en local

```bash
python3 -m http.server 8027
```

Lancer d'abord `python3 scripts/build.py` (pages candidats), puis ouvrir http://localhost:8027. Un serveur local est nécessaire : les pages chargent les données JSON avec `fetch`.

## Déploiement

Site statique sans build. Netlify publie la racine du dépôt (voir `netlify.toml`).

## Veille hebdomadaire

Chaque lundi, l'action GitHub `.github/workflows/veille-hebdo.yml` lance `scripts/check_hebdo.py` et publie un rapport en issue (étiquette `veille`) :
- cohérence des données et liens morts ;
- étapes du calendrier passées dans la semaine (statuts et résultats à mettre à jour) et à venir ;
- statuts de candidature non revérifiés depuis 30 jours (champ `verifie_le` de `data/candidats.json`) ;
- ancienneté du dernier sondage ;
- nouveaux fichiers de temps de parole publiés par l'Arcom ;
- nombre de points en attente dans `docs/a-verifier.md`.

Aucune donnée n'est modifiée automatiquement. Lancement manuel : onglet **Actions** du dépôt → « Veille hebdomadaire » → **Run workflow**, ou en local :

```bash
python3 scripts/check_hebdo.py > rapport.md
```

Après avoir revérifié un statut, mettre à jour son champ `verifie_le`.
