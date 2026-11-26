"""Prva inačica preporuke (slobodan tekst s oznakama u zagradama), osnovica za usporedbu u koraku 10."""
import re

import anthropic

import preporuke as P

NAJVISE_TOKENA = 1500
NAJVISE_ZNAKOVA = 200
OZNAKA = re.compile(r"\bC\d{3}\b")

SUSTAV = """Ti si savjetnik za njegu sobnih biljaka. Pišeš kratku preporuku na standardnom hrvatskom jeziku za osobu bez stručnog predznanja.

Dobivaš: (1) rezultat automatskog klasifikatora koji fotografiju biljke svrstava samo u "zdrava" ili "nezdrava", uz pouzdanost; (2) podatke koje je unio korisnik; (3) popis provjerenih činjenica s oznakama.

Pravila:
1. Savjete temelji isključivo na priloženim činjenicama. Iza svake rečenice koja sadrži savjet ili tvrdnju o biljci navedi oznaku činjenice u uglatim zagradama, npr. [C012]. Ne dodaji tvrdnje kojih nema u činjenicama: rečenicu koju ne možeš potkrijepiti činjenicom izostavi.
2. Klasifikator ne prepoznaje uzrok ni naziv bolesti. Nemoj postavljati dijagnozu. Navedi najvjerojatnije uzroke koje korisnik sam može provjeriti, prema njegovim uvjetima uzgoja.
3. Ako je stanje "nesigurno", na početku jasno napiši da sustav nije mogao pouzdano procijeniti stanje biljke i da su savjeti opći, a ne prilagođeni ovoj biljci.
4. Ako vrsta nije poznata ili za nju nema činjenica, napiši da su savjeti opći za sobne biljke.
5. Ako je biljka otrovna za kućne ljubimce prema činjenicama, spomeni to u jednoj rečenici.
6. Mjerne jedinice piši u metričkom sustavu (°C, cm).
7. Koristi jednostavne riječi i kratke rečenice. Cijeli odgovor smije imati najviše 150 riječi: u svakom od četiri dijela najviše tri kratke rečenice. Odaberi samo ono što je za ovaj slučaj najvažnije.
8. Ako se činjenica o odabranoj vrsti razlikuje od opće činjenice (tema „opcenito“), vrijedi činjenica o vrsti.

Oblik odgovora (točno ova četiri naslova, bez uvoda i bez zaključka):
**Procjena**
**Što napraviti sada**
**Redovita njega**
**Kada potražiti pomoć**"""


def odaberi_cinjenice(cinjenice, vrsta):
    return [f for f in cinjenice if f["tema"] in (P.OPCENITO, vrsta)]


def slozi_upit(vrsta, stanje, pouzdanost, uvjeti, cinjenice):
    dijelovi = ["REZULTAT KLASIFIKATORA", f"stanje: {stanje}", f"pouzdanost: {round(pouzdanost * 100)}%", "",
                "PODACI KORISNIKA", f"vrsta biljke: {vrsta or 'nepoznata'}"]
    for naziv, vrijednost in uvjeti.items():
        vrijednost = (vrijednost or "").strip()[:NAJVISE_ZNAKOVA]
        if vrijednost:
            dijelovi.append(f"{naziv}: {vrijednost}")
    dijelovi += ["", "ČINJENICE"]
    dijelovi += [f"[{f['id']}] ({f['tema']}, {f['kategorija']}) {f['cinjenica']}" for f in cinjenice]
    return "\n".join(dijelovi)


def pozovi_model(sustav, upit, max_tokena=NAJVISE_TOKENA):
    kljuc, model = P.ucitaj_env()
    odgovor = anthropic.Anthropic(api_key=kljuc).messages.create(
        model=model, max_tokens=max_tokena, thinking={"type": "disabled"},
        system=sustav, messages=[{"role": "user", "content": upit}])
    if odgovor.stop_reason not in ("end_turn", "max_tokens"):
        raise RuntimeError(f"model nije dao preporuku: {odgovor.stop_reason}")
    tekst = "".join(b.text for b in odgovor.content if b.type == "text")
    return tekst, dict(model=odgovor.model, kraj=odgovor.stop_reason, ulaz=odgovor.usage.input_tokens,
                       izlaz=odgovor.usage.output_tokens)


def preporuka(vrsta, stanje, pouzdanost, uvjeti):
    if vrsta is not None and vrsta not in P.VRSTE:
        raise ValueError(f"nepoznata vrsta: {vrsta}")
    if stanje not in P.STANJA:
        raise ValueError(f"nepoznato stanje: {stanje}")
    odabrane = odaberi_cinjenice(P.ucitaj_cinjenice(), vrsta)
    tekst, potrosnja = pozovi_model(SUSTAV, slozi_upit(vrsta, stanje, pouzdanost, uvjeti, odabrane))
    dostupne = {f["id"]: f for f in odabrane}
    navedene = sorted(set(OZNAKA.findall(tekst)))
    izvori = [dict(id=i, izvor=dostupne[i]["izvor"], url=dostupne[i]["url"], cinjenica=dostupne[i]["cinjenica"])
              for i in navedene if i in dostupne]
    return dict(tekst=tekst, izvori=izvori, nepostojece_oznake=[i for i in navedene if i not in dostupne],
                potrosnja=potrosnja)
