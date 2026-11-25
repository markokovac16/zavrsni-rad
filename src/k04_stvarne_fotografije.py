"""Korak 4: stvarne fotografije uzgojenih biljaka s iNaturalista, podjela po autoru i popis za ručnu provjeru."""
import json
from multiprocessing import Pool

import imagehash
import numpy as np
import pandas as pd
from PIL import Image, ImageOps

import config as c
import slicnost as s
from k01_manifest import KVALITETA_JPEG, MAX_STRANICA
from k02_ciscenje_i_podjela import PRAG_DUPLIKAT, podijeli

MAPA = "inaturalist_uzgojene"
VRSTE = {"pothos": "zlatni puzavac", "snake_plant": "sansevierija", "spider_plant": "zelenčica", "aloe_vera": "aloja"}
OZNAKE = {"healthy": c.Z, "unhealthy": c.N}
UDJELI = {"inat_train": 0.60, "inat_val": 0.15, "inat_test": 0.25}
PRVI_ID = 200000
OZNAKE_MAPA = c.KORIJEN / "oznake"


def obradi(arg):
    id_, putanja = arg
    with Image.open(c.SIROVO / MAPA / putanja) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        sirina, visina = im.size
        im.thumbnail((MAX_STRANICA, MAX_STRANICA), Image.LANCZOS)
        kopija = f"inat_{id_}.jpg"
        im.save(c.PREDMEMORIJA / kopija, quality=KVALITETA_JPEG)
        return dict(id=id_, sirina=sirina, visina=visina, phash=str(imagehash.phash(im)),
                    dhash=str(imagehash.dhash(im)), kopija=kopija)


def main():
    prijedlozi = pd.read_csv(OZNAKE_MAPA / "prijedlozi_modela.csv")
    opis = pd.read_csv(c.SIROVO / MAPA / "manifest.csv")
    df = prijedlozi.merge(opis, left_on="file", right_on="putanja", validate="one_to_one")
    assert (df.observer_id_x == df.observer_id_y).all()
    print("prijedlozi modela:", prijedlozi.label.value_counts().to_dict())
    df = df[df.label.isin(OZNAKE)].reset_index(drop=True)
    df["id"] = PRVI_ID + df.index
    with Pool(6) as bazen:
        slike = pd.DataFrame(bazen.map(obradi, list(zip(df.id, df.file)), chunksize=32))
    df = df.merge(slike, on="id")
    m = pd.DataFrame(dict(
        id=df.id, izvor="inaturalist", uloga="stvarne", vrsta=df.species.map(VRSTE), razred=df.label,
        oznaka=df.label.map(OZNAKE), sirina=df.sirina, visina=df.visina, phash=df.phash, dhash=df.dhash,
        putanja=MAPA + "/" + df.file, kopija=df.kopija, skupina=df.observer_id_x,
        licenca=df.licenca, atribucija=df.atribucija, opazanje=df.observation_url))
    m["dio"] = podijeli(m, "skupina", np.random.default_rng(c.SJEME), udjeli=UDJELI, sloj=m.vrsta + "|" + m.oznaka)

    ostale = pd.read_csv(c.PODACI / "manifest_sirovi.csv")
    ph_o, dh_o = s.u_uint64(ostale.phash), s.u_uint64(ostale.dhash)
    kopija = 0
    for ph, dh in zip(s.u_uint64(m.phash), s.u_uint64(m.dhash)):
        kopija += bool((np.maximum(np.bitwise_count(ph_o ^ ph), np.bitwise_count(dh_o ^ dh)) <= PRAG_DUPLIKAT).any())
    m.to_csv(c.PODACI / "manifest_inat.csv", index=False)

    print(m.groupby(["dio", "oznaka"]).size().unstack(fill_value=0))
    print(m.groupby(["dio", "vrsta"]).size().unstack(fill_value=0))
    rez = dict(
        prijedloga=int(len(prijedlozi)), po_prijedlogu=prijedlozi.label.value_counts().to_dict(),
        upotrebljivih=int(len(m)), autora=int(m.skupina.nunique()), kopija_iz_ostalih_skupova=int(kopija),
        po_vrsti=m.vrsta.value_counts().to_dict(), po_licenci=m.licenca.value_counts().to_dict(),
        podjela={dio: dict(slika=int(len(g)), autora=int(g.skupina.nunique()), nezdravih=int((g.oznaka == c.N).sum()))
                 for dio, g in m.groupby("dio")})
    (c.REZULTATI / "stvarne_fotografije.json").write_text(json.dumps(rez, indent=1, ensure_ascii=False))
    print(json.dumps(rez, ensure_ascii=False))

    test = m[m.dio == "inat_test"].sample(frac=1, random_state=c.SJEME)
    popis = [dict(id=int(r.id), vrsta=r.vrsta, slika=f"../data/raw/{r.putanja}", opazanje=r.opazanje)
             for r in test.itertuples()]
    predlozak = (c.KORIJEN / "alati" / "provjera_oznaka.predlozak.html").read_text(encoding="utf-8")
    (c.KORIJEN / "alati" / "provjera_oznaka.html").write_text(
        predlozak.replace("/*POPIS*/[]", json.dumps(popis, ensure_ascii=False)), encoding="utf-8")
    print(f"za ručnu provjeru: {len(popis)} fotografija -> alati/provjera_oznaka.html")


if __name__ == "__main__":
    main()
