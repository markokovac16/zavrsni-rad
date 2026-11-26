"""Korak 9: ocjena modela na ispitnim fotografijama s iNaturalista (slabe oznake i, kad postoje, ručno provjerene)."""
import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

import config as c
import model as M
from k07_evaluacija import metrike, softmax, uz_prag

MODELI = ["osnovna", "osnovna_s1", "osnovna_s2", "jaka", "jaka_s1", "jaka_s2"]
PROVJERENE = c.KORIJEN / "oznake" / "provjerene.csv"
NEUPOTREBLJIVA = "neupotrebljiva"


def ocjena(y, p, skupine, prag):
    r = metrike(y, p, skupine)
    r["uz_prag"] = uz_prag(y, p, prag, skupine)
    return r


def provjera_oznaka(test, putanja):
    covjek = pd.read_csv(putanja).drop_duplicates("id", keep="last").set_index("id").oznaka
    test["covjek"] = test.id.map(covjek)
    pregledano = test.covjek.notna()
    upotrebljivo = test.covjek.isin([c.Z, c.N])
    tablica = pd.crosstab(test.covjek[pregledano], test.oznaka[pregledano])
    return upotrebljivo.to_numpy(), dict(
        datoteka=putanja.name, pregledano=int(pregledano.sum()),
        neupotrebljivih=int((test.covjek == NEUPOTREBLJIVA).sum()), upotrebljivih=int(upotrebljivo.sum()),
        nezdravih=int((test.covjek == c.N).sum()),
        slaganje=float((test.covjek[upotrebljivo] == test.oznaka[upotrebljivo]).mean()),
        kappa=float(cohen_kappa_score(test.covjek[upotrebljivo], test.oznaka[upotrebljivo])),
        tablica={covjek_: {model_: int(n) for model_, n in redak.items()}
                 for covjek_, redak in tablica.iterrows()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provjerene", default=str(PROVJERENE))
    a = ap.parse_args()

    inat = pd.read_csv(c.PODACI / "manifest_inat.csv")
    test = inat[inat.dio == "inat_test"].reset_index(drop=True)
    y = (test.oznaka == c.N).astype(int).to_numpy()
    skupine = test.skupina.to_numpy()
    rez = dict(slabe_oznake="prijedlozi jezičnog modela; mjere slaganje s njima, ne točnost",
               n=int(len(test)), nezdravih=int(y.sum()), autora=int(test.skupina.nunique()),
               interval="bootstrap po autoru", modeli={})

    putanja = Path(a.provjerene)
    upotrebljivo = None
    if putanja.exists():
        upotrebljivo, rez["provjera"] = provjera_oznaka(test, putanja)
        y_covjek = (test.covjek[upotrebljivo] == c.N).astype(int).to_numpy()

    for naziv in MODELI:
        ev = json.loads((c.REZULTATI / f"evaluacija_{naziv}.json").read_text())
        model, _ = M.ucitaj_model(c.MODELI / f"{naziv}.pt")
        p = softmax(M.logiti(model, test), ev["temperatura"])
        r = dict(temperatura=ev["temperatura"], prag=ev["prag"], slabe_oznake=ocjena(y, p, skupine, ev["prag"]))
        r["slabe_oznake"]["po_vrsti"] = {
            v: dict(n=int(len(g)), nezdravih=int(y[g.index].sum()),
                    slaganje=float((p[g.index].argmax(1) == y[g.index]).mean()))
            for v, g in test.groupby("vrsta")}
        if upotrebljivo is not None:
            r["provjerene_oznake"] = ocjena(y_covjek, p[upotrebljivo], skupine[upotrebljivo], ev["prag"])
        rez["modeli"][naziv] = r
        s = r["slabe_oznake"]
        print(f"{naziv:11s} n={s['n']} autora={s['skupina']} slaganje={s['tocnost']:.3f} "
              f"({s['tocnost_interval'][0]:.3f}-{s['tocnost_interval'][1]:.3f}) makroF1={s['makro_f1']:.3f} "
              f"P={s['preciznost']:.3f} R={s['odziv']:.3f} AUC={s['roc_auc']:.3f} "
              f"osnovica={s['osnovica_najcesci_razred']:.3f} pokrivenost={s['uz_prag']['pokrivenost']:.2f} "
              f"iznad praga={s['uz_prag']['tocnost_iznad_praga']:.3f}"
              + (f" | provjerene: točnost={r['provjerene_oznake']['tocnost']:.3f}" if upotrebljivo is not None else ""))
    (c.REZULTATI / "stvarne_evaluacija.json").write_text(json.dumps(rez, indent=1, ensure_ascii=False))
    if upotrebljivo is not None:
        print("provjera oznaka:", {k: v for k, v in rez["provjera"].items() if k != "tablica"})


if __name__ == "__main__":
    main()
