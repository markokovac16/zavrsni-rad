"""Traženje sličnih slika preko perceptualnih sažetaka."""
import os
import re
from datetime import datetime
from multiprocessing import Pool

import imagehash
import numpy as np
from PIL import Image

import config as c

INACICE = ["ROTATE_90", "ROTATE_180", "ROTATE_270", "FLIP_LEFT_RIGHT", "FLIP_TOP_BOTTOM", "TRANSPOSE", "TRANSVERSE"]


def u_uint64(heksa):
    return np.array([int(h, 16) for h in heksa], dtype=np.uint64)


def parovi_ispod_praga(ph, dh, prag, blok=2000, ph2=None, dh2=None):
    n = len(ph)
    nadeni = []
    lijevo_ph, lijevo_dh = (ph, dh) if ph2 is None else (ph2, dh2)
    for a in range(0, n, blok):
        dp = np.bitwise_count(lijevo_ph[a:a + blok, None] ^ ph[None, :])
        dd = np.bitwise_count(lijevo_dh[a:a + blok, None] ^ dh[None, :])
        ii, jj = np.nonzero((dp <= prag) & (dd <= prag))
        ii = ii + a
        m = (ii < jj) if ph2 is None else (ii != jj)
        nadeni.append(np.stack([ii[m], jj[m], dp[ii[m] - a, jj[m]], dd[ii[m] - a, jj[m]]], axis=1))
    return np.concatenate(nadeni) if nadeni else np.zeros((0, 4), dtype=int)


class Skupine:

    def __init__(self, n):
        self.rod = np.arange(n)

    def korijen(self, x):
        while self.rod[x] != x:
            self.rod[x] = self.rod[self.rod[x]]
            x = self.rod[x]
        return x

    def spoji(self, a, b):
        ra, rb = self.korijen(a), self.korijen(b)
        if ra != rb:
            self.rod[max(ra, rb)] = min(ra, rb)

    def oznake(self):
        return np.array([self.korijen(i) for i in range(len(self.rod))])


def _sazeci_jedne(kopija):
    with Image.open(c.PREDMEMORIJA / kopija) as im:
        im = im.convert("RGB")
        ph, dh = [], []
        for ime in INACICE:
            v = im.transpose(getattr(Image, ime))
            ph.append(int(str(imagehash.phash(v)), 16))
            dh.append(int(str(imagehash.dhash(v)), 16))
    return ph, dh


def sazeci_inacica(df):
    put = c.PODACI / "sazeci_inacica.npz"
    if put.exists():
        z = np.load(put)
        if np.array_equal(z["id"], df.id.to_numpy()):
            return z["ph"], z["dh"]
    with Pool(os.cpu_count()) as bazen:
        rez = bazen.map(_sazeci_jedne, df.kopija.tolist(), chunksize=64)
    ph = np.array([r[0] for r in rez], dtype=np.uint64)
    dh = np.array([r[1] for r in rez], dtype=np.uint64)
    np.savez(put, id=df.id.to_numpy(), ph=ph, dh=dh)
    return ph, dh


def vrijeme_snimanja(ime):
    m = re.search(r"IMG_?(\d{8})_?(\d{6})", ime)
    if m:
        try:
            return "lokalno", datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").timestamp()
        except ValueError:
            return None
    return None


def parovi_istog_imena(df):
    ime = df.putanja.str.split("/").str[-1].str.rsplit(".", n=1).str[0]
    t = df.assign(red=np.arange(len(df)), ime=ime)
    parovi = []
    for _, g in t.groupby(["ime", "sirina", "visina"]):
        if g.izvor.nunique() > 1:
            parovi += [(g.red.iloc[0], r) for r in g.red.iloc[1:]]
    return parovi


def parovi_iste_serije(df, najveci_razmak):
    v = df.putanja.str.split("/").str[-1].map(vrijeme_snimanja)
    red = np.flatnonzero(v.notna().to_numpy())
    t = df.iloc[red].assign(red=red, zapis=[x[0] for x in v.iloc[red]], t=[x[1] for x in v.iloc[red]])
    parovi = []
    for _, g in t.groupby(["izvor", "zapis"]):
        g = g.sort_values("t")
        blizu = np.diff(g.t.to_numpy()) <= najveci_razmak
        parovi += list(zip(g.red.to_numpy()[:-1][blizu], g.red.to_numpy()[1:][blizu]))
    return parovi
