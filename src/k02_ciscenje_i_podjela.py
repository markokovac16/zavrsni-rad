"""Korak 2: uklanjanje duplikata i podjela na učenje, validaciju i test."""
import json

import numpy as np
import pandas as pd

import config as c
import slicnost as s

PRAG_DUPLIKAT = 6
PRAG_SLICNE = 10
PRAG_ZAKRENUTE = 4
RAZMAK_SERIJE = 30  # sekundi
UDJELI = {"train": 0.70, "val": 0.15, "test": 0.15}

# kad je ista slika u više izvora, ostaje ona iz izvora koji je ranije na popisu
PREDNOST = ["houseplant_health", "plantdoc", "indoor_plant_disease", "money_plant_atlas",
            "epipremnum_aureum", "aloe_vera_leaf_disease", "aloe_vera_diseases",
            "medicinal_leaf_health", "medicinal_leaf_disease", "multiclass_medicinal",
            "combined_medicinal", "indoor_leaf_health", "healthy_wilted", "plantvita_aloevera"]


def spoji_do_praga(sk, parovi, prag):
    for a, b in parovi[np.maximum(parovi[:, 2], parovi[:, 3]) <= prag][:, :2]:
        sk.spoji(a, b)
    return sk


def skupine(n, parovi, prag):
    return spoji_do_praga(s.Skupine(n), parovi, prag).oznake()


def podijeli(df, stupac_skupine, rng, udjeli=None, sloj=None):
    udjeli = udjeli or UDJELI
    sloj = df.izvor + "|" + df.oznaka if sloj is None else sloj
    sloj_skupine = sloj.groupby(df[stupac_skupine]).agg(lambda v: v.mode().iloc[0])
    velicina = df.groupby(stupac_skupine).size()
    dio_skupine = {}
    for _, sk in sloj_skupine.groupby(sloj_skupine):
        idovi = sk.index.to_numpy().copy()
        rng.shuffle(idovi)
        nedostaje = {ime: udio * velicina[idovi].sum() for ime, udio in udjeli.items()}
        for g in idovi:
            ime = max(nedostaje, key=nedostaje.get)
            dio_skupine[g] = ime
            nedostaje[ime] -= velicina[g]
    return df[stupac_skupine].map(dio_skupine)


def po_udaljenosti(parovi, df):
    udalj = np.maximum(parovi[:, 2], parovi[:, 3])
    izvor, oznaka = df.izvor.to_numpy(), df.oznaka.to_numpy()
    redovi = []
    for a, b in [(0, 2), (3, 4), (5, 6), (7, 8), (9, 10)]:
        m = (udalj >= a) & (udalj <= b)
        i, j = parovi[m, 0], parovi[m, 1]
        redovi.append(dict(od=a, do=b, parova=int(m.sum()),
                           razlicita_oznaka=float((oznaka[i] != oznaka[j]).mean()) if m.any() else None,
                           razlicit_izvor=float((izvor[i] != izvor[j]).mean()) if m.any() else None))
    return redovi


def main():
    df = pd.read_csv(c.PODACI / "manifest_sirovi.csv")
    ph, dh = s.u_uint64(df.phash), s.u_uint64(df.dhash)
    parovi = s.parovi_ispod_praga(ph, dh, PRAG_SLICNE)
    df["skupina_duplikata"] = skupine(len(df), parovi, PRAG_DUPLIKAT)
    samo_slicne = skupine(len(df), parovi, PRAG_SLICNE)

    sk = spoji_do_praga(s.Skupine(len(df)), parovi, PRAG_DUPLIKAT)
    ph_i, dh_i = s.sazeci_inacica(df)
    zakrenuti = np.concatenate([
        s.parovi_ispod_praga(ph, dh, PRAG_SLICNE, ph2=ph_i[:, k], dh2=dh_i[:, k]) for k in range(ph_i.shape[1])])
    s_zakrenutima = spoji_do_praga(sk, zakrenuti, PRAG_ZAKRENUTE).oznake()
    serije = s.parovi_iste_serije(df, RAZMAK_SERIJE)
    for a, b in serije:
        sk.spoji(a, b)
    df["skupina"] = sk.oznake()
    print(f"skupina: slične do {PRAG_SLICNE} bitova {len(set(samo_slicne))}; "
          f"za podjelu: duplikati i zakrenute {len(set(s_zakrenutima))}, "
          f"sa serijama snimanja {df.skupina.nunique()}; parova u serijama {len(serije)}")
    print("najveće skupine:", df.skupina.value_counts().head(8).tolist())

    df["rang"] = df.izvor.map({ime: i for i, ime in enumerate(PREDNOST)})
    broj_oznaka = df.groupby("skupina_duplikata").oznaka.transform("nunique")
    df["status"] = "ostaje"
    df.loc[broj_oznaka > 1, "status"] = "proturječna oznaka"
    prvi = df.sort_values(["rang", "id"]).groupby("skupina_duplikata").id.transform("first").sort_index()
    df.loc[(df.status == "ostaje") & (df.id != prvi), "status"] = "duplikat"

    po_izvoru = df.groupby(["izvor", "status"]).size().unstack(fill_value=0)
    po_izvoru.insert(0, "ukupno", po_izvoru.sum(axis=1))
    print(po_izvoru)

    izvori_skupine = df.groupby("skupina_duplikata").izvor.agg(lambda v: " + ".join(sorted(set(v))))
    medu_izvorima = izvori_skupine[izvori_skupine.str.contains(r"\+")].value_counts().to_dict()

    cist = df[df.status == "ostaje"].copy()
    rng = np.random.default_rng(c.SJEME)
    skup = cist[cist.uloga == "skup"]
    cist["dio"] = cist.uloga
    cist.loc[skup.index, "dio"] = podijeli(skup, "skupina", rng)
    cist.drop(columns=["rang", "status"]).to_csv(c.PODACI / "manifest.csv", index=False)
    print(cist.groupby(["dio", "oznaka"]).size().unstack(fill_value=0))

    naivni = df[df.uloga == "skup"].copy()
    naivni["svaka_za_sebe"] = naivni.id
    naivni["dio"] = podijeli(naivni, "svaka_za_sebe", np.random.default_rng(c.SJEME))
    u_treningu = set(naivni[naivni.dio == "train"].skupina_duplikata)
    test_n = naivni[naivni.dio == "test"]
    naivni.drop(columns=["rang", "status", "svaka_za_sebe"]).to_csv(c.PODACI / "manifest_naivni.csv", index=False)

    test_c = cist[cist.dio == "test"]
    dio_reda = pd.Series("", index=df.index)
    dio_reda[cist.index] = cist.dio
    dio_reda = dio_reda.to_numpy()
    oznaka = df.oznaka.to_numpy()
    i, j = parovi[:, 0], parovi[:, 1]
    tt = ((dio_reda[i] == "test") & (dio_reda[j] == "train")) | ((dio_reda[i] == "train") & (dio_reda[j] == "test"))
    testne = np.where(dio_reda[i[tt]] == "test", i[tt], j[tt])
    statistika = dict(
        prag_duplikat=PRAG_DUPLIKAT, prag_slicne=PRAG_SLICNE,
        slika_ukupno=int(len(df)), ostaje=int((df.status == "ostaje").sum()),
        duplikata=int((df.status == "duplikat").sum()),
        proturjecnih=int((df.status == "proturječna oznaka").sum()),
        identicnih_datoteka_visak=int(len(df) - df.md5.nunique()),
        skupine_medu_izvorima=medu_izvorima,
        po_izvoru=po_izvoru.reset_index().to_dict(orient="records"),
        podjela=cist.groupby(["dio", "oznaka"]).size().unstack(fill_value=0).reset_index().to_dict(orient="records"),
        podjela_po_izvoru=cist[cist.uloga == "skup"].groupby(["izvor", "dio"]).size().unstack(fill_value=0)
        .reset_index().to_dict(orient="records"),
        naivna_test_slika=int(len(test_n)),
        naivna_test_s_duplikatom_u_treningu=int(test_n.skupina_duplikata.isin(u_treningu).sum()),
        cista_test_slika=int(len(test_c)),
        cista_test_sa_slicnom_u_treningu=int(len(set(testne))),
        parova_test_ucenje_slicnih=int(tt.sum()),
        parova_test_ucenje_slicnih_razlicita_oznaka=int((oznaka[i[tt]] != oznaka[j[tt]]).sum()),
        prag_zakrenute=PRAG_ZAKRENUTE, razmak_serije_s=RAZMAK_SERIJE,
        uspravni_po_udaljenosti=po_udaljenosti(parovi, df),
        zakrenuti_po_udaljenosti=po_udaljenosti(zakrenuti, df),
        skupina_samo_slicne=int(pd.Series(samo_slicne)[cist.index][cist.uloga == "skup"].nunique()),
        skupina_sa_zakrenutima=int(pd.Series(s_zakrenutima)[cist.index][cist.uloga == "skup"].nunique()),
        skupina_bez_grupiranja=int(len(skup)),
        skupina_za_podjelu=int(skup.skupina.nunique()),
        najveca_skupina=int(skup.skupina.value_counts().max()),
        slika_u_skupinama_od_10_i_vise=int((skup.groupby("skupina").skupina.transform("size") >= 10).sum()),
    )
    c.REZULTATI.mkdir(exist_ok=True)
    (c.REZULTATI / "ciscenje.json").write_text(json.dumps(statistika, indent=1, ensure_ascii=False))
    print(f"naivna podjela: {statistika['naivna_test_s_duplikatom_u_treningu']} od {len(test_n)} "
          "testnih slika ima duplikat u treningu")


if __name__ == "__main__":
    main()
