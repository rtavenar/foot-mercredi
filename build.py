#!/usr/bin/env python3
"""Construit le site du planning foot à partir de planning.json.

Produit dans site/ :
  index.html                  la page consultable
  calendriers/<slug>.ics      un abonnement par famille
  calendriers/tout.ics        un abonnement avec toutes les voitures
  planning.json               une copie de la source, pour référence

Aucune dépendance : Python 3.9+ suffit.
"""

import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RACINE = Path(__file__).parent
SORTIE = RACINE / "site"


# --------------------------------------------------------------- utilitaires

def jour(s):
    a, m, j = (int(x) for x in s.split("-"))
    return date(a, m, j)


def slugifie(texte):
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


# ------------------------------------------------------- calcul du calendrier

def mercredis(cfg):
    """Les mercredis d'école, et ceux qu'on saute avec leur motif."""
    vac = [(jour(v["du"]), jour(v["au"]), v["nom"]) for v in cfg["vacances"]]
    fer = {jour(f["date"]): f["nom"] for f in cfg["feries"]}
    d, fin = jour(cfg["premier_mercredi"]), jour(cfg["dernier_jour_ecole"])
    retenus, sautes = [], []
    while d <= fin:
        if d.weekday() == 2:
            motif = next((n for a, b, n in vac if a <= d <= b), None)
            if motif is None and d in fer:
                motif = "Jour férié — " + fer[d]
            (sautes if motif else retenus).append(
                {"d": d.isoformat(), "why": motif} if motif else d)
        d += timedelta(days=1)
    return retenus, sautes


def compose(cfg, familles_de_service, avec_les_freres):
    """Deux voitures de trois enfants, chaque conducteur avec son ou ses enfants."""
    fams = cfg["familles"]
    freres = max(fams, key=lambda f: len(fams[f]["enfants"]))       # Hélène & Damien
    ordre = [k for f in fams.values() for k in f["enfants"]]
    fam_de = {k: f for f, v in fams.items() for k in v["enfants"]}

    xf = fam_de[avec_les_freres]
    groupe1 = fams[freres]["enfants"] + [avec_les_freres]
    groupe2 = sorted((k for f, v in fams.items() if f not in (freres, xf)
                      for k in v["enfants"]), key=ordre.index)

    if freres in familles_de_service:
        conducteur1 = freres
    elif xf in familles_de_service:
        conducteur1 = xf
    else:
        raise ValueError(
            f"personne ne peut conduire la voiture des frères : "
            f"de service {familles_de_service}, avec les frères {avec_les_freres}")
    conducteur2 = next(f for f in familles_de_service if f != conducteur1)

    def range_devant(groupe, conducteur):
        siens = fams[conducteur]["enfants"]
        return siens + [k for k in groupe if k not in siens]

    return [{"fam": conducteur1, "kids": range_devant(groupe1, conducteur1)},
            {"fam": conducteur2, "kids": range_devant(groupe2, conducteur2)}]


def saison(cfg, dates):
    roul = cfg["roulement"]["semaines"]
    dec = cfg["roulement"]["decalage"]
    exc = {e["date"]: e for e in cfg["exceptions"]}
    ech = {e["date"]: e for e in cfg["echanges"]}
    notes = {n["date"]: n["texte"] for n in cfg["notes"]}
    fams = cfg["familles"]

    semaines = []
    for i, d in enumerate(dates):
        iso = d.isoformat()
        if iso in exc:
            e = exc[iso]
            cars = compose(cfg, e["familles"], e["avec_les_freres"])
            note = e.get("note")
        else:
            m = roul[(i + dec) % len(roul)]
            cars = compose(cfg, m["familles"], m["avec_les_freres"])
            note = None

        if iso in ech:
            de, vers = ech[iso]["de"], ech[iso]["vers"]
            cible = next((c for c in cars if c["fam"] == de), None)
            if cible is None:
                raise ValueError(f"{iso} : {de} n'est pas de service, échange impossible")
            siens = fams[vers]["enfants"]
            manquants = [k for k in siens if k not in cible["kids"]]
            if manquants:
                raise ValueError(
                    f"{iso} : {vers} ne peut pas prendre ce tour, "
                    f"{', '.join(manquants)} n'est pas dans cette voiture")
            cible["fam"] = vers
            cible["kids"] = siens + [k for k in cible["kids"] if k not in siens]
            note = f"Échange convenu : {fams[vers]['nom']} prend le tour de {fams[de]['nom']}."

        if iso in notes:
            note = notes[iso]

        s = {"d": iso, "cars": cars}
        if note:
            s["note"] = note
        semaines.append(s)
    return semaines


def verifie(cfg, semaines):
    fams = cfg["familles"]
    tous = sorted(k for f in fams.values() for k in f["enfants"])
    freres = max(fams, key=lambda f: len(fams[f]["enfants"]))
    for s in semaines:
        c1, c2 = s["cars"]
        assert c1["fam"] != c2["fam"], f"{s['d']} : même famille deux fois"
        assert sorted(c1["kids"] + c2["kids"]) == tous, f"{s['d']} : enfants manquants ou en double"
        for c in s["cars"]:
            assert len(c["kids"]) == 3, f"{s['d']} : voiture de {len(c['kids'])} enfants"
            assert all(k in c["kids"] for k in fams[c["fam"]]["enfants"]), \
                f"{s['d']} : {c['fam']} ne conduit pas ses propres enfants"
        assert all(k in c1["kids"] for k in fams[freres]["enfants"]), \
            f"{s['d']} : les frères sont séparés"


# ---------------------------------------------------------------------- .ics

def plie(ligne):
    """Repli à 75 octets, comme l'exige la RFC 5545."""
    brut = ligne.encode("utf-8")
    if len(brut) <= 75:
        return ligne
    morceaux, courant = [], b""
    for car in ligne:
        b = car.encode("utf-8")
        if len(courant) + len(b) > (75 if not morceaux else 74):
            morceaux.append(courant)
            courant = b""
        courant += b
    morceaux.append(courant)
    return "\r\n ".join(m.decode("utf-8") for m in morceaux)


def echappe(t):
    return (t.replace("\\", "\\\\").replace(";", "\\;")
             .replace(",", "\\,").replace("\n", "\\n"))


def ics(cfg, semaines, titre, evenements):
    """evenements : liste de (date iso, suffixe d'uid, résumé, description)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    horaire = cfg.get("horaire")
    out = ["BEGIN:VCALENDAR", "VERSION:2.0",
           "PRODID:-//planning-foot-mercredi//FR", "CALSCALE:GREGORIAN",
           "METHOD:PUBLISH",
           f"NAME:{echappe(titre)}", f"X-WR-CALNAME:{echappe(titre)}",
           "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    for iso, uid, resume, desc in evenements:
        d = jour(iso)
        out += ["BEGIN:VEVENT", f"UID:{iso}-{uid}@planning-foot", f"DTSTAMP:{stamp}"]
        if horaire:
            h, m = (int(x) for x in horaire["debut"].split(":"))
            debut = datetime(d.year, d.month, d.day, h, m)
            fin = debut + timedelta(minutes=horaire["duree_min"])
            f = "%Y%m%dT%H%M%S"
            out += [f"DTSTART;TZID=Europe/Paris:{debut.strftime(f)}",
                    f"DTEND;TZID=Europe/Paris:{fin.strftime(f)}"]
        else:
            out += [f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
                    f"DTEND;VALUE=DATE:{d + timedelta(days=1):%Y%m%d}"]
        out += [f"SUMMARY:{echappe(resume)}", f"DESCRIPTION:{echappe(desc)}",
                "TRANSP:TRANSPARENT", "END:VEVENT"]
    out.append("END:VCALENDAR")
    return "\r\n".join(plie(l) for l in out) + "\r\n"


def ecris_calendriers(cfg, semaines, dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    fams = cfg["familles"]

    for cle, f in fams.items():
        evs = []
        for s in semaines:
            voiture = next((c for c in s["cars"] if c["fam"] == cle), None)
            if not voiture:
                continue
            passagers = [k for k in voiture["kids"] if k not in f["enfants"]]
            evs.append((s["d"], cle,
                        "Foot — au volant (" + ", ".join(voiture["kids"]) + ")",
                        "Trajet du mercredi midi. "
                        + (("Passagers : " + ", ".join(passagers) + ". ") if passagers else "")
                        + ("L'autre voiture : "
                           + next(fams[c["fam"]]["nom"] for c in s["cars"] if c["fam"] != cle)
                           + ".")))
        (dossier / f"{f['slug']}.ics").write_text(
            ics(cfg, semaines, f"Foot du mercredi — {f['nom']}", evs), encoding="utf-8")

    evs = [(s["d"], "tout",
            "Foot — " + " / ".join(fams[c["fam"]]["nom"] for c in s["cars"]),
            "\n".join(fams[c["fam"]]["nom"] + " : " + ", ".join(c["kids"]) for c in s["cars"]))
           for s in semaines]
    (dossier / "tout.ics").write_text(
        ics(cfg, semaines, "Foot du mercredi — toutes les voitures", evs), encoding="utf-8")


# ---------------------------------------------------------------------- page

def ecris_page(cfg, semaines, sautes, dossier):
    fams = cfg["familles"]
    cycle = []
    for i, m in enumerate(cfg["roulement"]["semaines"]):
        cycle.append({"n": i + 1,
                      "cars": compose(cfg, m["familles"], m["avec_les_freres"])})
    donnees = {
        "saison": cfg["saison"],
        "fams": {k: {"name": v["nom"], "kids": v["enfants"], "slug": v["slug"]}
                 for k, v in fams.items()},
        "season": semaines,
        "skipped": sautes,
        "cycle": cycle,
    }
    gabarit = (RACINE / "template.html").read_text(encoding="utf-8")
    page = gabarit.replace("/*__DATA__*/",
                           json.dumps(donnees, ensure_ascii=False, separators=(",", ":")))
    if "__DATA__" in page:
        raise ValueError("le gabarit ne contient pas le repère /*__DATA__*/")
    (dossier / "index.html").write_text(page, encoding="utf-8")


def main():
    cfg = json.loads((RACINE / "planning.json").read_text(encoding="utf-8"))
    dates, sautes = mercredis(cfg)
    semaines = saison(cfg, dates)
    verifie(cfg, semaines)

    SORTIE.mkdir(exist_ok=True)
    ecris_page(cfg, semaines, sautes, SORTIE)
    ecris_calendriers(cfg, semaines, SORTIE / "calendriers")
    (SORTIE / "planning.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    conduites = {}
    for s in semaines:
        for c in s["cars"]:
            conduites[c["fam"]] = conduites.get(c["fam"], 0) + 1
    print(f"{len(semaines)} mercredis, {len(sautes)} sans foot")
    for k, v in sorted(conduites.items(), key=lambda kv: -kv[1]):
        print(f"  {fams_nom(cfg, k):<22} {v} conduites")


def fams_nom(cfg, cle):
    return cfg["familles"][cle]["nom"]


if __name__ == "__main__":
    main()
