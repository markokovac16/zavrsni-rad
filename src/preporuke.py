"""Preporuka o njezi: jezični model bira provjerene činjenice i piše rečenice s oznakama, a sustav ih provjerava i slaže."""
import json
import math
import os
import re
import unicodedata

import anthropic

import config as c

ZNANJE = c.KORIJEN / "znanje"
VRSTE = ["zlatni puzavac", "sansevierija", "zelenčica", "aloja", "kalanhoja", "hibiskus"]
STANJA = ["zdrava", "nezdrava", "nesigurno"]
OPCENITO = "opcenito"
OTROVNOST = "otrovnost"
ZADANI_MODEL = "claude-haiku-5-5"
NAJVISE_TOKENA = 1500
NAJVISE_TOKENA_RAZMISLJANJE = 8000
NAJVISE_ZNAKOVA = 200
OZNAKA_U_TEKSTU = re.compile(
    r"\s*(?:[\[(]\s*C[0-9]{3}(?:\s*(?:[,;]|\bi\b)\s*C[0-9]{3})*\s*[\])]|(?<!\w)C[0-9]{3}(?!\w))"
    r"(?:\s*(?:[,;]|\bi\b)\s*(?:[\[(]\s*C[0-9]{3}(?:\s*(?:[,;]|\bi\b)\s*C[0-9]{3})*\s*[\])]|(?<!\w)C[0-9]{3}(?!\w)))*|\*+")
RAZMAK_PRIJE_ZNAKA = re.compile(r"\s+([.,;:!?])")
KRAJ_RECENICE = re.compile(r"(?<!\bnpr)(?<!\btj)(?<!\bitd)(?<!\bsl)(?<!\bspp)[.!?](?=\s+[A-ZČĆĐŠŽ]|\s*$)")
RIJEC = re.compile(r"[^\W_]")
CIRILICA = {**dict(zip("абвгдђежзијклљмнњопрстћуфхцчџшАБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШ",
                       ["a", "b", "v", "g", "d", "đ", "e", "ž", "z", "i", "j", "k", "l", "lj", "m", "n", "nj", "o", "p",
                        "r", "s", "t", "ć", "u", "f", "h", "c", "č", "dž", "š", "A", "B", "V", "G", "D", "Đ", "E", "Ž",
                        "Z", "I", "J", "K", "L", "Lj", "M", "N", "Nj", "O", "P", "R", "S", "T", "Ć", "U", "F", "H", "C",
                        "Č", "Dž", "Š"])),
            **dict(zip("ёйщъыьэюяєіїґЁЙЩЪЫЬЭЮЯЄІЇҐ",
                       ["jo", "j", "šč", "", "y", "", "e", "ju", "ja", "je", "i", "ji", "g", "Jo", "J", "Šč", "", "Y", "",
                        "E", "Ju", "Ja", "Je", "I", "Ji", "G"]))}

SUSTAV = (ZNANJE / "sustav.md").read_text(encoding="utf-8").strip()
SUSTAV_BEZ_BAZE = (ZNANJE / "sustav_bez_baze.md").read_text(encoding="utf-8").strip()
PREDLOSCI = json.loads((ZNANJE / "predlosci.json").read_text(encoding="utf-8"))


def ucitaj_env():
    env = c.KORIJEN / ".env"
    if env.exists():
        for red in env.read_text().splitlines():
            if "=" in red and not red.startswith("#"):
                k, v = red.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    return os.environ["CLAUDE_API_KEY"], os.environ.get("CLAUDE_MODEL", ZADANI_MODEL)


def ucitaj_cinjenice():
    return json.loads((ZNANJE / "cinjenice.json").read_text(encoding="utf-8"))


def odaberi_cinjenice(cinjenice, vrsta):
    o_vrsti = [f for f in cinjenice if f["tema"] == vrsta]
    zamijenjene = {i for f in o_vrsti for i in f.get("zamjenjuje", [])}
    opce = [f for f in cinjenice if f["tema"] == OPCENITO and f["id"] not in zamijenjene]
    return opce, o_vrsti


def je_otrovnost(f):
    return f["kategorija"] == OTROVNOST


def broj_rijeci(tekst):
    return sum(bool(RIJEC.search(r)) for r in tekst.split())


def blok(cinjenice):
    return [f"[{f['id']}] ({f['kategorija']}) {f['cinjenica']}" for f in cinjenice]


def slozi_upit(vrsta, stanje, uvjeti, opce=None, o_vrsti=None, otrovnost=None):
    dijelovi = []
    if opce is not None:
        dijelovi += ["OPĆE ČINJENICE", *blok(opce), ""]
        dijelovi += [f"ČINJENICE O VRSTI: {vrsta}" if vrsta else "ČINJENICE O VRSTI: nema, vrsta nije odabrana",
                     *blok(o_vrsti), ""]
    if otrovnost:
        dijelovi += [f"ČINJENICE O OTROVNOSTI: {vrsta}", *blok(otrovnost), ""]
    dijelovi += ["SLUČAJ", f"stanje prema klasifikatoru: {stanje}", f"vrsta biljke: {vrsta or 'nije odabrana'}"]
    navedeni = [(k, (v or "").strip()[:NAJVISE_ZNAKOVA]) for k, v in uvjeti.items()]
    navedeni = [(k, v) for k, v in navedeni if v]
    if navedeni:
        dijelovi += ["uvjeti koje je upisao korisnik:", *[f"- {k}: {v}" for k, v in navedeni]]
    else:
        dijelovi.append("uvjeti koje je upisao korisnik: nisu navedeni")
    return "\n".join(dijelovi)


def shema(oznake=None, oznake_otrovnosti=None, obavezna_otrovnost=False):
    def recenica(dopustene):
        svojstva = {"tekst": {"type": "string"}}
        if dopustene is not None:
            svojstva = {"oznake": {"type": "array", "items": {"type": "string", "enum": sorted(dopustene)}}, **svojstva}
        return {"type": "object", "properties": svojstva, "required": list(svojstva), "additionalProperties": False}
    popisi = {d["kljuc"]: "recenica" for d in PREDLOSCI["dijelovi"]}
    definicije = {"recenica": recenica(oznake)}
    if oznake is None:
        if obavezna_otrovnost:
            popisi[OTROVNOST] = "recenica"
    elif oznake_otrovnosti:
        popisi[OTROVNOST] = "recenica_otrovnost"
        definicije["recenica_otrovnost"] = recenica(oznake_otrovnosti)
        obavezna_otrovnost = True
    svojstva = {k: {"type": "array", "items": {"$ref": f"#/$defs/{v}"}} for k, v in popisi.items()}
    if obavezna_otrovnost:
        svojstva[OTROVNOST]["minItems"] = 1
    return {"type": "object", "properties": svojstva, "required": list(popisi), "additionalProperties": False,
            "$defs": definicije}


def pozovi_model(sustav, upit, shema_odgovora, razmisljanje=False):
    kljuc, model = ucitaj_env()
    odgovor = anthropic.Anthropic(api_key=kljuc).messages.create(
        model=model, max_tokens=NAJVISE_TOKENA_RAZMISLJANJE if razmisljanje else NAJVISE_TOKENA,
        thinking={"type": "adaptive" if razmisljanje else "disabled"},
        output_config={"format": {"type": "json_schema", "schema": shema_odgovora}},
        system=sustav, messages=[{"role": "user", "content": upit}])
    if odgovor.stop_reason != "end_turn":
        raise RuntimeError(f"model nije dao potpunu preporuku: {odgovor.stop_reason}")
    tekst = "".join(b.text for b in odgovor.content if b.type == "text")
    return json.loads(tekst), dict(model=odgovor.model, ulaz=odgovor.usage.input_tokens,
                                   izlaz=odgovor.usage.output_tokens)


def nelatinicni(tekst):
    return sorted({z for z in tekst if z.isalpha() and z not in "ªº" and "LATIN" not in unicodedata.name(z, "")})


def obradi(sirovo, s_bazom):
    dijelovi, izbaceno = {}, []
    provjere = dict(bez_oznaka=0, skraceno=0, vise_oznaka=0, vise_recenica=0, ociscen_tekst=0, preslovljeno=0)
    popisi = PREDLOSCI["dijelovi"] + ([dict(kljuc=OTROVNOST, najvise=1)] if OTROVNOST in sirovo else [])
    for d in popisi:
        recenice = []
        for r in sirovo[d["kljuc"]]:
            tekst = r["tekst"].strip()
            cisto = RAZMAK_PRIJE_ZNAKA.sub(r"\1", re.sub(r"\s{2,}", " ", OZNAKA_U_TEKSTU.sub("", tekst))).strip()
            if cisto != tekst:
                provjere["ociscen_tekst"] += 1
            latinica = "".join(CIRILICA.get(z, z) for z in cisto)
            if latinica != cisto:
                provjere["preslovljeno"] += 1
                cisto = latinica
            oznake = list(dict.fromkeys(r.get("oznake", [])))
            if not cisto:
                continue
            if s_bazom and not oznake:
                provjere["bez_oznaka"] += 1
                izbaceno.append(dict(dio=d["kljuc"], tekst=cisto, razlog="bez oznake"))
                continue
            if len(oznake) > PREDLOSCI["najvise_oznaka"]:
                provjere["vise_oznaka"] += 1
            if len(KRAJ_RECENICE.findall(cisto)) > 1:
                provjere["vise_recenica"] += 1
            recenice.append(dict(tekst=cisto, oznake=oznake))
        for r in recenice[d["najvise"]:]:
            provjere["skraceno"] += 1
            izbaceno.append(dict(dio=d["kljuc"], tekst=r["tekst"], razlog="previše rečenica"))
        dijelovi[d["kljuc"]] = recenice[:d["najvise"]]
    provjere["rijeci_modela"] = sum(broj_rijeci(r["tekst"]) for d in PREDLOSCI["dijelovi"] for r in dijelovi[d["kljuc"]])
    dijelovi["redovita_njega"] += [dict(r, otrovnost=True) for r in dijelovi.pop(OTROVNOST, [])]
    provjere["nelatinicni_znakovi"] = nelatinicni(" ".join(r["tekst"] for rs in dijelovi.values() for r in rs))
    return dijelovi, izbaceno, provjere


def recenica_sustava(tekst, oznake=(), **oznaka):
    return dict(tekst=tekst, oznake=list(oznake), sustav=True, **oznaka)


def dodaj_recenice_sustava(dijelovi, vrsta, stanje, pouzdanost, o_vrsti, s_bazom):
    p = str(math.floor(pouzdanost * 100 + 0.5))
    prva, *ostale = PREDLOSCI["stanje"][stanje]
    prve = [recenica_sustava(prva.replace("{p}", p), stanje=True), *[recenica_sustava(t) for t in ostale]]
    if not vrsta:
        prve.append(recenica_sustava(PREDLOSCI["nepoznata_vrsta"]))
    dijelovi["procjena"] = prve + dijelovi["procjena"]
    oznaka = PREDLOSCI["otrovnost"].get(vrsta)
    if s_bazom and oznaka and not any(r.get("otrovnost") for r in dijelovi["redovita_njega"]):
        f = next(f for f in o_vrsti if f["id"] == oznaka)
        dijelovi["redovita_njega"].append(recenica_sustava(f["cinjenica"], [oznaka], otrovnost=True))
    dijelovi["kada_potraziti_pomoc"].append(recenica_sustava(PREDLOSCI["strucnjak"]))
    return dijelovi


def slozi_tekst(dijelovi):
    odlomci = []
    for d in PREDLOSCI["dijelovi"]:
        recenice = [r["tekst"] + (f" [{', '.join(r['oznake'])}]" if r["oznake"] else "") for r in dijelovi[d["kljuc"]]]
        if recenice:
            odlomci.append(f"**{d['naslov']}**\n" + " ".join(recenice))
    return "\n\n".join(odlomci)


def pripremi(vrsta, stanje, uvjeti, s_bazom=True):
    if vrsta is not None and vrsta not in VRSTE:
        raise ValueError(f"nepoznata vrsta: {vrsta}")
    if stanje not in STANJA:
        raise ValueError(f"nepoznato stanje: {stanje}")
    opce, o_vrsti = odaberi_cinjenice(ucitaj_cinjenice(), vrsta)
    if not s_bazom:
        return opce, o_vrsti, SUSTAV_BEZ_BAZE, slozi_upit(vrsta, stanje, uvjeti), shema(obavezna_otrovnost=vrsta is not None)
    njega = [f for f in o_vrsti if not je_otrovnost(f)]
    otrovnost = [f for f in o_vrsti if je_otrovnost(f)]
    return (opce, o_vrsti, SUSTAV, slozi_upit(vrsta, stanje, uvjeti, opce, njega, otrovnost),
            shema([f["id"] for f in opce + njega], [f["id"] for f in otrovnost]))


def zavrsi(sirovo, vrsta, stanje, pouzdanost, opce, o_vrsti, s_bazom=True):
    dijelovi, izbaceno, provjere = obradi(sirovo, s_bazom)
    dijelovi = dodaj_recenice_sustava(dijelovi, vrsta, stanje, pouzdanost, o_vrsti, s_bazom)
    provjere["dodana_otrovnost"] = sum(bool(r.get("sustav") and r.get("otrovnost")) for r in dijelovi["redovita_njega"])
    po_id = {f["id"]: f for f in opce + o_vrsti}
    navedene = sorted({i for rs in dijelovi.values() for r in rs for i in r["oznake"]})
    izvori = [dict(id=i, izvor=po_id[i]["izvor"], url=po_id[i]["url"], cinjenica=po_id[i]["cinjenica"])
              for i in navedene]
    return dict(tekst=slozi_tekst(dijelovi), dijelovi=dijelovi, izvori=izvori, izbaceno=izbaceno, provjere=provjere)


def preporuka(vrsta, stanje, pouzdanost, uvjeti, s_bazom=True, razmisljanje=False):
    opce, o_vrsti, sustav, upit, shema_odgovora = pripremi(vrsta, stanje, uvjeti, s_bazom)
    sirovo, potrosnja = pozovi_model(sustav, upit, shema_odgovora, razmisljanje)
    return dict(**zavrsi(sirovo, vrsta, stanje, pouzdanost, opce, o_vrsti, s_bazom), sirovo=sirovo,
                potrosnja=potrosnja)


if __name__ == "__main__":
    r = preporuka("aloja", "nezdrava", 0.97, {"svjetlo": "južni prozor, izravno sunce",
                                              "zalijevanje": "dvaput tjedno", "prostorija": "dnevni boravak"})
    print(r["tekst"], "\n", [i["id"] for i in r["izvori"]], r["provjere"], r["potrosnja"])
