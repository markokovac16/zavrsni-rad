"""Korak 8: koliko curenje podataka napuhuje rezultat (model učen na podjeli bez čišćenja prema osnovnom)."""
import json

import pandas as pd
from sklearn.metrics import accuracy_score

import config as c
import model as M
from k07_evaluacija import interval, interval_razlike, metrike, softmax

NAJMANJE = 20


def ocjena(model, d):
    y = (d.oznaka == c.N).astype(int).to_numpy()
    p = softmax(M.logiti(model, d))
    return y, p, metrike(y, p, d.skupina.to_numpy())


def dio_ocjena(y, p, skupine):
    if len(y) == 0:
        return dict(n=0)
    tocno = p.argmax(1) == y
    return dict(n=int(len(y)), udio_nezdravih=float(y.mean()), tocnost=float(tocno.mean()),
                tocnost_interval=interval(y, p.argmax(1), accuracy_score, skupine))


def ispis(naziv, r):
    print(f"{naziv:34s} n={r['n']:5d} točnost={r['tocnost']:.4f} ({r['tocnost_interval'][0]:.4f}-"
          f"{r['tocnost_interval'][1]:.4f}) makroF1={r['makro_f1']:.4f} osnovica={r['osnovica_najcesci_razred']:.4f}")


def main():
    naivni = pd.read_csv(c.PODACI / "manifest_naivni.csv")
    cisti = pd.read_csv(c.PODACI / "manifest.csv")
    m_naivni, _ = M.ucitaj_model(c.MODELI / "naivni.pt")
    m_osnovna, _ = M.ucitaj_model(c.MODELI / "osnovna.pt")

    test = naivni[naivni.dio == "test"].reset_index(drop=True)
    u_ucenju = set(naivni[naivni.dio == "train"].skupina_duplikata)
    ima_duplikat = test.skupina_duplikata.isin(u_ucenju).to_numpy()
    proturjecna = set(naivni.groupby("skupina_duplikata").oznaka.nunique().loc[lambda s: s > 1].index)
    iste_oznake = ima_duplikat & ~test.skupina_duplikata.isin(proturjecna).to_numpy()

    y, p, svi = ocjena(m_naivni, test)
    skupine = test.skupina.to_numpy()
    naivni_rez = dict(
        test_svi=svi,
        test_s_duplikatom_u_ucenju=metrike(y[ima_duplikat], p[ima_duplikat], skupine[ima_duplikat]),
        test_s_duplikatom_iste_oznake=metrike(y[iste_oznake], p[iste_oznake], skupine[iste_oznake]),
        test_bez_duplikata_u_ucenju=metrike(y[~ima_duplikat], p[~ima_duplikat], skupine[~ima_duplikat]),
    )
    osnovna_rez = dict(test_cisti=ocjena(m_osnovna, cisti[cisti.dio == "test"])[2])
    for dio in ["vanjski_stvarni", "vanjski_usjevi"]:
        d = cisti[cisti.dio == dio]
        naivni_rez[dio] = ocjena(m_naivni, d)[2]
        osnovna_rez[dio] = ocjena(m_osnovna, d)[2]

    po_izvoru = {}
    for izvor, g in test.groupby("izvor"):
        po_izvoru[izvor] = {}
        for ime, maska in [("s_duplikatom", ima_duplikat), ("bez_duplikata", ~ima_duplikat)]:
            i = g.index[maska[g.index]]
            po_izvoru[izvor][ime] = dio_ocjena(y[i], p[i], skupine[i])

    for k, r in naivni_rez.items():
        ispis(f"naivni  {k}", r)
    for k, r in osnovna_rez.items():
        ispis(f"osnovna  {k}", r)
    s_duplikatima = [s for s, r in po_izvoru.items() if r["s_duplikatom"]["n"] >= NAJMANJE]
    print("izvori s barem", NAJMANJE, "testnih slika s duplikatom:", s_duplikatima)
    izvan = ~test.izvor.isin(s_duplikatima).to_numpy() & ~ima_duplikat
    naivni_rez["test_bez_duplikata_izvan_izvora_s_duplikatima"] = metrike(y[izvan], p[izvan], skupine[izvan])
    ispis("naivni  test_bez_dupl_izvan_tih_izvora", naivni_rez["test_bez_duplikata_izvan_izvora_s_duplikatima"])
    for izvor, r in po_izvoru.items():
        if r["s_duplikatom"]["n"] >= NAJMANJE and r["bez_duplikata"]["n"] >= NAJMANJE:
            print(f"  {izvor:24s}" + "".join(
                f" | {k}: n={v['n']} točnost={v['tocnost']:.3f} ({v['tocnost_interval'][0]:.3f}-"
                f"{v['tocnost_interval'][1]:.3f}) nezdravih={v['udio_nezdravih']:.2f}" for k, v in r.items()))

    velicina = test.skupina_duplikata.map(naivni.skupina_duplikata.value_counts()).to_numpy()
    dosljedne = ~test.skupina_duplikata.isin(proturjecna).to_numpy()
    tocno = p.argmax(1) == y
    kontrola = {}
    for ime, m in [("velicina_2", (velicina == 2) & dosljedne), ("velicina_2_i_vise", (velicina >= 2) & dosljedne)]:
        s_kopijom, bez_kopije = m & ima_duplikat, m & ~ima_duplikat
        kontrola[ime] = dict(
            s_kopijom=dio_ocjena(y[s_kopijom], p[s_kopijom], skupine[s_kopijom]),
            bez_kopije=dio_ocjena(y[bez_kopije], p[bez_kopije], skupine[bez_kopije]),
            razlika=float(tocno[s_kopijom].mean() - tocno[bez_kopije].mean()),
            razlika_interval=interval_razlike(tocno[m], ima_duplikat[m], skupine[m]),
            bez_kopije_po_izvoru=test[bez_kopije].izvor.value_counts().to_dict())
        k = kontrola[ime]
        print(f"kontrola {ime}: s kopijom {k['s_kopijom']['n']} {k['s_kopijom']['tocnost']:.3f}, bez kopije "
              f"{k['bez_kopije']['n']} {k['bez_kopije']['tocnost']:.3f}, razlika {k['razlika']:.3f} "
              f"({k['razlika_interval'][0]:.3f}-{k['razlika_interval'][1]:.3f}); {k['bez_kopije_po_izvoru']}")

    rez = dict(naivni=naivni_rez, osnovna=osnovna_rez, po_izvoru=po_izvoru, kontrola=kontrola)
    (c.REZULTATI / "curenje.json").write_text(json.dumps(rez, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
