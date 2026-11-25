"""Korak 3: srodne slike preostale s obje strane podjele."""
import json

import numpy as np
import pandas as pd

import config as c
import slicnost as s
from k02_ciscenje_i_podjela import PRAG_DUPLIKAT, PRAG_SLICNE, PRAG_ZAKRENUTE, RAZMAK_SERIJE

SEKUNDE = [RAZMAK_SERIJE, 60, 120, 300]


def prema_ucenju(parovi, dio, prvi="test"):
    i, j = parovi[:, 0], parovi[:, 1]
    a = (dio[i] == prvi) & (dio[j] == "train")
    b = (dio[i] == "train") & (dio[j] == prvi)
    p = np.concatenate([parovi[a], parovi[b][:, [1, 0, 2, 3]]])
    red = np.lexsort((np.maximum(p[:, 2], p[:, 3]), p[:, 1], p[:, 0]))
    _, jedan = np.unique(p[red][:, :2], axis=0, return_index=True)
    return p[red][jedan]


def razdvoji(parovi, prag):
    u = np.maximum(parovi[:, 2], parovi[:, 3])
    return parovi[u <= prag], parovi[u > prag]


def sazetak(parovi, df):
    oznaka = df.oznaka.to_numpy()
    return dict(testnih_slika=int(len(set(parovi[:, 0]))), parova=int(len(parovi)),
                parova_razlicite_oznake=int((oznaka[parovi[:, 0]] != oznaka[parovi[:, 1]]).sum()),
                po_izvoru=df.izvor.iloc[sorted(set(parovi[:, 0]))].value_counts().to_dict())


def main():
    svi = pd.read_csv(c.PODACI / "manifest_sirovi.csv")
    podjela = pd.read_csv(c.PODACI / "manifest.csv").set_index("id").dio
    dio = svi.id.map(podjela).fillna("").to_numpy()
    ph, dh = s.u_uint64(svi.phash), s.u_uint64(svi.dhash)
    rez = dict(test_slika=int((dio == "test").sum()), prag_zakrenute=PRAG_ZAKRENUTE, razmak_serije_s=RAZMAK_SERIJE)

    ph_i, dh_i = s.sazeci_inacica(svi)
    zakrenuti = np.concatenate([
        s.parovi_ispod_praga(ph, dh, PRAG_DUPLIKAT, ph2=ph_i[:, k], dh2=dh_i[:, k]) for k in range(ph_i.shape[1])])
    zakrenuti_svi = zakrenuti
    zakrenuti = prema_ucenju(zakrenuti, dio)
    udalj = np.maximum(zakrenuti[:, 2], zakrenuti[:, 3])
    rez["zakrenute_do_praga"] = sazetak(zakrenuti[udalj <= PRAG_ZAKRENUTE], svi)
    rez["zakrenute_iznad_praga"] = sazetak(zakrenuti[udalj > PRAG_ZAKRENUTE], svi)

    uspravni_svi = s.parovi_ispod_praga(ph, dh, PRAG_SLICNE)
    uspravni = prema_ucenju(uspravni_svi, dio)
    udalj = np.maximum(uspravni[:, 2], uspravni[:, 3])
    rez["uspravne_do_praga"] = sazetak(uspravni[udalj <= PRAG_DUPLIKAT], svi)
    rez["uspravne_iznad_praga"] = sazetak(uspravni[udalj > PRAG_DUPLIKAT], svi)
    rez["slicne_test_id"] = sorted(int(x) for x in set(svi.id.to_numpy()[uspravni[udalj > PRAG_DUPLIKAT][:, 0]]))

    isto_ime = np.array([(a, b, 0, 0) for a, b in s.parovi_istog_imena(svi)], dtype=int).reshape(-1, 4)
    rez["isto_ime"] = sazetak(prema_ucenju(isto_ime, dio), svi)

    v = svi.putanja.str.split("/").str[-1].map(s.vrijeme_snimanja)
    t = svi[v.notna()].assign(zapis=[x[0] for x in v.dropna()], t=[x[1] for x in v.dropna()], dio=dio[v.notna()])
    rez["uzastopne"] = uzastopne(t, "test")

    zv_do, _ = razdvoji(prema_ucenju(zakrenuti_svi, dio, "val"), PRAG_ZAKRENUTE)
    uv_do, uv_iznad = razdvoji(prema_ucenju(uspravni_svi, dio, "val"), PRAG_DUPLIKAT)
    rez["val"] = dict(slika=int((dio == "val").sum()), zakrenute_do_praga=sazetak(zv_do, svi),
                      uspravne_do_praga=sazetak(uv_do, svi), uspravne_iznad_praga=sazetak(uv_iznad, svi),
                      uzastopne=uzastopne(t, "val"))

    (c.REZULTATI / "provjera_podjele.json").write_text(json.dumps(rez, indent=1, ensure_ascii=False))
    for k in ["zakrenute_do_praga", "zakrenute_iznad_praga", "uspravne_do_praga", "uspravne_iznad_praga", "isto_ime"]:
        x = rez[k]
        print(f"{k:24s} testnih slika {x['testnih_slika']:4d}, parova {x['parova']:4d}, "
              f"različite oznake {x['parova_razlicite_oznake']:3d}; {x['po_izvoru']}")
    u = rez["uzastopne"]
    print(f"uzastopne snimke: od {u['test_s_vremenom']} testnih slika s vremenom u imenu, sliku za učenje istog izvora ima "
          + ", ".join(f"unutar {x} s: {u[f'do_{x}_s']}" for x in SEKUNDE)
          + f" (medijan razmaka {u['medijan_sekundi']:.0f} s)")
    for izvor, red in u["po_izvoru"].items():
        print(f"  {izvor:24s} {red}")
    v = rez["val"]
    print(f"skup za provjeru ({v['slika']}): sa sličnom u učenju {v['uspravne_iznad_praga']['testnih_slika']}, "
          f"do praga {v['uspravne_do_praga']['testnih_slika'] + v['zakrenute_do_praga']['testnih_slika']}, "
          f"unutar 300 s {v['uzastopne']['do_300_s']} od {v['uzastopne']['test_s_vremenom']}")


def uzastopne(t, prvi):
    razmaci, po_izvoru = [], {}
    for (izvor, zapis), g in t.groupby(["izvor", "zapis"]):
        t_te, t_tr = g[g.dio == prvi].t.to_numpy(), np.sort(g[g.dio == "train"].t.to_numpy())
        if len(t_te) == 0 or len(t_tr) == 0:
            continue
        k = np.searchsorted(t_tr, t_te)
        r = np.minimum(np.abs(t_te - t_tr[np.clip(k - 1, 0, len(t_tr) - 1)]),
                       np.abs(t_te - t_tr[np.clip(k, 0, len(t_tr) - 1)]))
        razmaci.append(r)
        red = po_izvoru.setdefault(izvor, dict(test_s_vremenom=0, **{f"do_{x}_s": 0 for x in SEKUNDE}))
        red["test_s_vremenom"] += int(len(r))
        for x in SEKUNDE:
            red[f"do_{x}_s"] += int((r <= x).sum())
    r = np.concatenate(razmaci)
    return dict(test_s_vremenom=int(len(r)), medijan_sekundi=float(np.median(r)),
                **{f"do_{x}_s": int((r <= x).sum()) for x in SEKUNDE}, po_izvoru=po_izvoru)


if __name__ == "__main__":
    main()
