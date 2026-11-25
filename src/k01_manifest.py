"""Korak 1: popis slika (manifest), sažeci i smanjene kopije."""
import hashlib
import os
from multiprocessing import Pool

import imagehash
import pandas as pd
from PIL import Image, ImageOps
from tqdm import tqdm

import config as c

MAX_STRANICA = 384
KVALITETA_JPEG = 92


def popis_datoteka():
    retci = []
    for izvor, opis in c.IZVORI.items():
        for mapa, (vrsta, oznaka) in opis["razredi"].items():
            dir_ = c.SIROVO / opis["mapa"] / mapa
            if not dir_.is_dir():
                raise FileNotFoundError(f"nema mape: {dir_}")
            for p in sorted(dir_.rglob("*")):
                if p.suffix.lower() in c.NASTAVCI:
                    retci.append((izvor, opis["uloga"], vrsta, mapa, oznaka, p))
    for p in sorted((c.SIROVO / c.PLANTDOC_MAPA).glob("*/*/*")):
        if p.suffix.lower() in c.NASTAVCI:
            razred = p.parent.name
            oznaka = c.Z if razred in c.PLANTDOC_ZDRAVI else c.N
            retci.append(("plantdoc", "vanjski_usjevi", "usjevi", razred, oznaka, p))
    return retci


def obradi(arg):
    i, (izvor, uloga, vrsta, razred, oznaka, p) = arg
    try:
        md5 = hashlib.md5(p.read_bytes()).hexdigest()
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            sirina, visina = im.size
            im.thumbnail((MAX_STRANICA, MAX_STRANICA), Image.LANCZOS)
            phash = str(imagehash.phash(im))
            dhash = str(imagehash.dhash(im))
            kopija = c.PREDMEMORIJA / f"{i:06d}.jpg"
            im.save(kopija, quality=KVALITETA_JPEG)
    except Exception as e:
        return dict(id=i, izvor=izvor, greska=f"{type(e).__name__}: {e}", putanja=str(p))
    return dict(
        id=i, izvor=izvor, uloga=uloga, vrsta=vrsta, razred=razred, oznaka=oznaka,
        sirina=sirina, visina=visina, md5=md5, phash=phash, dhash=dhash,
        putanja=str(p.relative_to(c.SIROVO)), kopija=kopija.name, greska="",
    )


def main():
    c.PREDMEMORIJA.mkdir(parents=True, exist_ok=True)
    datoteke = popis_datoteka()
    print(f"datoteka: {len(datoteke)}")
    with Pool(os.cpu_count()) as pool:
        retci = list(tqdm(pool.imap(obradi, enumerate(datoteke), chunksize=16),
                          total=len(datoteke), mininterval=10))
    df = pd.DataFrame(retci)
    lose = df[df.greska != ""]
    print(f"nečitljivih slika: {len(lose)}")
    lose.to_csv(c.PODACI / "necitljive.csv", index=False)
    df = df[df.greska == ""].drop(columns="greska")
    df.to_csv(c.PODACI / "manifest_sirovi.csv", index=False)
    print(df.groupby(["uloga", "izvor", "oznaka"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
