# Foot du mercredi — planning des trajets

Qui emmène qui au foot le mercredi midi, saison 2026-2027. Deux groupes indépendants,
chacun avec son planning : celui de Romain (`romain.json`, deux voitures) et celui de
Julien (`julien.json`, une voiture). La page et les calendriers de chaque groupe sont
reconstruits automatiquement à chaque commit sur `main`.


## Le dépôt

| Fichier | Rôle |
| --- | --- |
| `romain.json`, `julien.json` | Un fichier par groupe : familles, roulement, exceptions, échanges. Tout nouveau fichier `*.json` à la racine devient un groupe supplémentaire. |
| `build.py` | Reconstruit une page et des `.ics` par groupe. Python 3.9+, aucune dépendance. |
| `template.html` | Le gabarit commun aux groupes. `/*__DATA__*/`, `__TITRE__` et `__DESCRIPTION__` sont remplacés par les données de chaque groupe. |
| `.github/workflows/publier.yml` | Reconstruit et publie sur GitHub Pages. |
| `site/` | Produit par le build : `site/index.html` redirige vers le groupe par défaut, `site/romain/` et `site/julien/` contiennent chacun leur page et leurs `.ics`. À ne pas committer (voir `.gitignore`). |

## Mise en route

Dans **Settings → Pages**, choisir **GitHub Actions** comme source (et non « Deploy from a
branch »). Le premier `git push` sur `main` fait le reste.

Pour construire en local avant de pousser :

```sh
python build.py && open site/romain/index.html site/julien/index.html
```

Le build échoue si un planning devient incohérent — voiture de plus ou moins de trois enfants,
frères séparés, conducteur sans son enfant, échange impossible. Un workflow rouge signale donc
une erreur dans un des fichiers `*.json`, pas un bug.

## S'abonner au calendrier

Chaque famille a une URL qui ne change jamais, sous le sous-dossier de son groupe :

```
https://<compte>.github.io/<dépôt>/romain/calendriers/aude-romain.ics
https://<compte>.github.io/<dépôt>/romain/calendriers/estelle-sebastien.ics
https://<compte>.github.io/<dépôt>/romain/calendriers/helene-damien.ics
https://<compte>.github.io/<dépôt>/romain/calendriers/julie-guirec.ics
https://<compte>.github.io/<dépôt>/romain/calendriers/alice.ics
https://<compte>.github.io/<dépôt>/romain/calendriers/tout.ics

https://<compte>.github.io/<dépôt>/julien/calendriers/marina-erwan.ics
https://<compte>.github.io/<dépôt>/julien/calendriers/emmanuelle-gilles.ics
https://<compte>.github.io/<dépôt>/julien/calendriers/joanna-julien.ics
https://<compte>.github.io/<dépôt>/julien/calendriers/tout.ics
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

Tout se passe dans le fichier `*.json` du groupe concerné (`romain.json` ou `julien.json`).

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

Le champ `voitures` du fichier (1 ou 2) détermine comment `build.py` répartit les enfants :

- **`"voitures": 2`** (romain.json) — deux voitures de trois enfants. Une famille a deux enfants
  (« les frères ») : ils voyagent toujours ensemble, avec l'une des deux familles de service.
  Les familles de service avancent de deux crans à chaque semaine dans l'ordre
  Aude-Romain → Estelle-Sébastien → Hélène-Damien → Julie-Guirec → Alice, et l'enfant qui monte
  avec Maxence et Clément change au fil des semaines, ce qui étire le motif sur dix semaines.
  `decalage` règle le point de départ du cycle sur le premier mercredi.
  Sur 35 mercredis, le compte ne tombe pas rond : de 13 à 15 conduites selon la famille.
- **`"voitures": 1`** (julien.json) — une seule voiture avec tous les enfants du groupe ; chaque
  entrée du roulement ne liste qu'une famille (`"familles": ["ME"]`, pas de `avec_les_freres`).

Dans les deux cas, `exceptions` et `echanges` fonctionnent pareil ; pour un groupe à une voiture,
un échange remplace simplement la famille au volant.

## Ajouter un groupe

Copier un fichier `*.json` existant, changer `familles`, `roulement`, `voitures` et les textes du
bloc `texte` (`sous_titre`, `regles_roulement`, `academie` — affichés tels quels sur la page).
`build.py` construit un dossier `site/<nom-du-fichier>/` pour chaque fichier `*.json` trouvé à la
racine, sans autre configuration. `GROUPE_PAR_DEFAUT` dans `build.py` choisit vers quel groupe
`site/index.html` redirige.

## Saison suivante

Pour chaque groupe : mettre à jour `premier_mercredi`, `dernier_jour_ecole`, `vacances` et `feries`
avec le calendrier de l'académie de Rennes, ajuster `familles` si la bande change, vider
`exceptions`, `echanges` et `notes`. Le roulement, lui, se reconduit tel quel.
