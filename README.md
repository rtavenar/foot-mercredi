# Foot du mercredi — planning des trajets

Qui emmène qui au foot le mercredi midi, saison 2026-2027.
La page et les calendriers sont reconstruits automatiquement à chaque commit sur `main`.


## Le dépôt

| Fichier | Rôle |
| --- | --- |
| `planning.json` | La seule chose à modifier : familles, roulement, exceptions, échanges. |
| `build.py` | Reconstruit la page et les `.ics`. Python 3.9+, aucune dépendance. |
| `template.html` | Le gabarit de la page. `/*__DATA__*/` est remplacé par les données. |
| `.github/workflows/publier.yml` | Reconstruit et publie sur GitHub Pages. |
| `site/` | Produit par le build. À ne pas committer (voir `.gitignore`). |

## Mise en route

Dans **Settings → Pages**, choisir **GitHub Actions** comme source (et non « Deploy from a
branch »). Le premier `git push` sur `main` fait le reste.

Pour construire en local avant de pousser :

```sh
python build.py && open site/index.html
```

Le build échoue si le planning devient incohérent — voiture de plus ou moins de trois enfants,
frères séparés, conducteur sans son enfant, échange impossible. Un workflow rouge signale donc
une erreur dans `planning.json`, pas un bug.

## S'abonner au calendrier

Chaque famille a une URL qui ne change jamais :

```
https://<compte>.github.io/<dépôt>/calendriers/aude-romain.ics
https://<compte>.github.io/<dépôt>/calendriers/estelle-sebastien.ics
https://<compte>.github.io/<dépôt>/calendriers/helene-damien.ics
https://<compte>.github.io/<dépôt>/calendriers/julie-guirec.ics
https://<compte>.github.io/<dépôt>/calendriers/alice.ics
https://<compte>.github.io/<dépôt>/calendriers/tout.ics
```

La page les affiche déjà remplies : il suffit de choisir sa famille en haut.

- **Google Agenda** — Autres agendas → À partir de l'URL. Colle le lien en `https://`.
- **Apple Calendar, iOS, Outlook** — le bouton « Ouvrir dans mon agenda » suffit (lien `webcal://`).

Il s'agit d'un abonnement, pas d'un import : les modifications du planning arrivent toutes seules.
Le fichier demande un rafraîchissement toutes les six heures, mais chaque client fait un peu
à sa tête — Google vérifie plutôt une fois par jour. Une correction faite le mardi soir peut donc
n'apparaître dans l'agenda de tout le monde que le mercredi. Pour un changement de dernière minute,
mieux vaut prévenir directement.

## Modifier le planning

Tout se passe dans `planning.json`.

**Un échange entre deux familles** — la nouvelle famille doit déjà avoir son enfant dans la voiture
concernée, sinon le build refuse :

```json
"echanges": [
  { "date": "2026-11-04", "de": "ES", "vers": "JG" }
]
```

**Une semaine entièrement à part** — on impose les deux familles de service et l'enfant qui monte
avec les frères :

```json
"exceptions": [
  { "date": "2026-09-02", "familles": ["JG", "ES"], "avec_les_freres": "Marin",
    "note": "Seules ces deux familles étaient disponibles." }
]
```

**Un simple commentaire sur une date**, sans toucher au planning :

```json
"notes": [
  { "date": "2027-05-05", "texte": "Veille du pont de l'Ascension : à confirmer avec le club." }
]
```

**Donner une heure aux évènements** plutôt que la journée entière :

```json
"horaire": { "debut": "12:15", "duree_min": 105 }
```

## Le roulement

Les familles sont de service par deux et avancent de deux crans à chaque semaine dans l'ordre
Aude-Romain → Estelle-Sébastien → Hélène-Damien → Julie-Guirec → Alice. L'enfant qui monte avec
Maxence et Clément change au fil des semaines, ce qui étire le motif sur dix semaines. `decalage`
règle le point de départ du cycle sur le premier mercredi : c'est lui qui place Julie-Guirec en
dehors des 16 septembre et 14 octobre.

Sur 35 mercredis, le compte ne tombe pas rond : de 13 à 15 conduites selon la famille.

## Saison suivante

Mettre à jour `premier_mercredi`, `dernier_jour_ecole`, `vacances` et `feries` avec le calendrier
de l'académie de Rennes, ajuster `familles` si la bande change, vider `exceptions`, `echanges` et
`notes`. Le roulement, lui, se reconduit tel quel.
