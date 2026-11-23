"""Korak 7: metrike, kalibracija i prag pouzdanosti."""
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from PIL import Image
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

import config as c
import model as M

NASLOVI = {"val": "Validacijski skup", "test": "Testni skup",
           "vanjski_stvarni": "Vanjski skup: stvarne fotografije",
           "vanjski_usjevi": "Vanjski skup: usjevi (PlantDoc)"}
CILJANA_TOCNOST = 0.98
BEZ_PRIKAZA = {"plantvita_aloevera", "healthy_wilted"}
PO_RETKU = 4


def softmax(lg, T=1.0):
    z = lg / T
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def nauci_temperaturu(lg, y):
    lg_t, y_t = torch.tensor(lg), torch.tensor(y)
    log_T = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_T], lr=0.1, max_iter=200)

    def korak():
        opt.zero_grad()
        g = torch.nn.functional.cross_entropy(lg_t / log_T.exp(), y_t)
        g.backward()
        return g

    opt.step(korak)
    return log_T.detach().exp().item()


def ece(p, y, kosara=15):
    pouzd, pred = p.max(1), p.argmax(1)
    rubovi = np.linspace(0.5, 1.0, kosara + 1)
    ukupno = 0.0
    for a, b in zip(rubovi[:-1], rubovi[1:]):
        m = (pouzd > a) & (pouzd <= b)
        if m.any():
            ukupno += m.mean() * abs((pred[m] == y[m]).mean() - pouzd[m].mean())
    return float(ukupno)


def interval(y, pred, fn, skupine, n=1000):
    rng = np.random.default_rng(c.SJEME)
    clanovi = [np.flatnonzero(skupine == g) for g in np.unique(skupine)]
    v = []
    for _ in range(n):
        i = np.concatenate([clanovi[k] for k in rng.integers(0, len(clanovi), len(clanovi))])
        v.append(fn(y[i], pred[i]))
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def makro_f1(y, pred):
    return f1_score(y, pred, average="macro", zero_division=0)


def metrike(y, p, skupine):
    pred = p.argmax(1)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return dict(
        n=int(len(y)), udio_nezdravih=float(y.mean()),
        tocnost=float(accuracy_score(y, pred)),
        tocnost_interval=interval(y, pred, accuracy_score, skupine),
        preciznost=float(precision_score(y, pred, zero_division=0)),
        odziv=float(recall_score(y, pred, zero_division=0)),
        f1=float(f1_score(y, pred, zero_division=0)),
        makro_f1=float(makro_f1(y, pred)),
        makro_f1_interval=interval(y, pred, makro_f1, skupine),
        skupina=int(len(np.unique(skupine))),
        roc_auc=float(roc_auc_score(y, p[:, 1])) if 0 < y.mean() < 1 else None,
        osnovica_najcesci_razred=float(max(y.mean(), 1 - y.mean())),
        matrica=dict(tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp)),
    )


def uz_prag(y, p, prag):
    m = p.max(1) >= prag
    return dict(pokrivenost=float(m.mean()),
                tocnost_iznad_praga=float((p.argmax(1)[m] == y[m]).mean()) if m.any() else None,
                tocnost_ispod_praga=float((p.argmax(1)[~m] == y[~m]).mean()) if (~m).any() else None)


def krivulja(y, p):
    red = np.argsort(-p.max(1))
    tocno = (p.argmax(1) == y)[red]
    return np.arange(1, len(y) + 1) / len(y), np.cumsum(tocno) / np.arange(1, len(y) + 1)


def spremi(fig, putanja):
    fig.tight_layout()
    fig.savefig(putanja, dpi=200)
    plt.close(fig)


def kalibracijske_tocke(p, y, kosara=6, najmanje=5):
    pouzd, tocno = p.max(1), p.argmax(1) == y
    rubovi = np.linspace(0.5, 1, kosara + 1)
    maske = [(pouzd > a) & (pouzd <= b) for a, b in zip(rubovi[:-1], rubovi[1:])]
    maske = [m for m in maske if m.sum() >= najmanje]
    return [pouzd[m].mean() for m in maske], [tocno[m].mean() for m in maske]


def crtaj_matricu(y, p, naslov, putanja):
    mz = confusion_matrix(y, p.argmax(1), labels=[0, 1])
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    ax.imshow(mz, cmap="Greens")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{mz[i, j]}\n{mz[i, j] / mz[i].sum():.1%}", ha="center", va="center",
                    color="white" if mz[i, j] > mz.max() / 2 else "black")
    ax.set_xticks([0, 1], c.RAZREDI)
    ax.set_yticks([0, 1], c.RAZREDI, rotation=90, va="center")
    ax.set_xlabel("Predviđeni razred")
    ax.set_ylabel("Stvarni razred")
    ax.set_title(naslov, fontsize=9)
    spremi(fig, putanja)


def crtaj_primjere(d, y, p, prag, naslov, putanja):
    pouzd, pred = p.max(1), p.argmax(1)
    iznad = pouzd >= prag
    retci = [
        ("Točno: zdrava", iznad & (pred == 0) & (y == 0)),
        ("Točno: nezdrava", iznad & (pred == 1) & (y == 1)),
        ("Pogrešno: proglašena nezdravom", iznad & (pred == 1) & (y == 0)),
        ("Pogrešno: proglašena zdravom", iznad & (pred == 0) & (y == 1)),
        ("Ispod praga: nesigurno", ~iznad),
    ]
    dozvoljeno = ~d.izvor.isin(BEZ_PRIKAZA).to_numpy()
    rng = np.random.default_rng(c.SJEME)
    fig, osi = plt.subplots(len(retci), PO_RETKU, figsize=(2.1 * PO_RETKU, 2.45 * len(retci)))
    for r, (opis, maska) in enumerate(retci):
        kandidati = np.flatnonzero(maska & dozvoljeno)
        odabrani = rng.choice(kandidati, min(PO_RETKU, len(kandidati)), replace=False) if len(kandidati) else []
        for s in range(PO_RETKU):
            ax = osi[r, s]
            ax.axis("off")
            if s >= len(odabrani):
                continue
            i = odabrani[s]
            with Image.open(c.PREDMEMORIJA / d.kopija.iloc[i]) as im:
                ax.imshow(im.convert("RGB"))
            ax.set_title(f"{d.vrsta.iloc[i]}\nP(nezdrava) = {p[i, 1]:.2f}", fontsize=7)
        osi[r, 0].text(-0.08, 0.5, opis, transform=osi[r, 0].transAxes, rotation=90,
                       ha="right", va="center", fontsize=8)
    fig.suptitle(naslov, fontsize=10)
    spremi(fig, putanja)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--naziv", default=None, help="zadano: glavni model iz rezultati/odabrani_model.json")
    ap.add_argument("--manifest", default="manifest.csv")
    a = ap.parse_args()
    a.naziv = a.naziv or json.loads((c.REZULTATI / "odabrani_model.json").read_text())["naziv"]

    slike = c.REZULTATI / "slike"
    slike.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(c.PODACI / a.manifest)
    model, stanje = M.ucitaj_model(c.MODELI / f"{a.naziv}.pt")

    lg, y, dijelovi = {}, {}, {}
    for ime in NASLOVI:
        d = df[df.dio == ime]
        if len(d) == 0:
            continue
        dijelovi[ime], lg[ime], y[ime] = d, M.logiti(model, d), (d.oznaka == c.N).astype(int).to_numpy()
    np.savez(c.REZULTATI / f"logiti_{a.naziv}.npz", **{f"lg_{k}": v for k, v in lg.items()},
             **{f"y_{k}": v for k, v in y.items()}, **{f"id_{k}": dijelovi[k].id.to_numpy() for k in lg})

    T = nauci_temperaturu(lg["val"], y["val"])
    p_sirovo = {k: softmax(v) for k, v in lg.items()}
    p = {k: softmax(v, T) for k, v in lg.items()}

    pouzd = np.sort(np.unique(np.round(p["val"].max(1), 3)))
    prag = 1.0
    for t in pouzd:
        m = p["val"].max(1) >= t
        if (p["val"].argmax(1)[m] == y["val"][m]).mean() >= CILJANA_TOCNOST:
            prag = float(t)
            break

    rez = dict(model=a.naziv, arhitektura=stanje["arhitektura"], epoha=stanje["epoha"],
               temperatura=T, prag=prag, ciljana_tocnost=CILJANA_TOCNOST, skupovi={})
    for k in lg:
        r = metrike(y[k], p[k], dijelovi[k].skupina.to_numpy())
        r["ece_prije"], r["ece_poslije"] = ece(p_sirovo[k], y[k]), ece(p[k], y[k])
        r["uz_prag"] = uz_prag(y[k], p[k], prag)
        rez["skupovi"][k] = r
        crtaj_matricu(y[k], p[k], NASLOVI[k], slike / f"matrica_{a.naziv}_{k}.png")
        if k in ("test", "vanjski_stvarni"):
            crtaj_primjere(dijelovi[k], y[k], p[k], prag, NASLOVI[k], slike / f"primjeri_{a.naziv}_{k}.png")

    d = dijelovi["test"].assign(tocno=p["test"].argmax(1) == y["test"], nezdrava=y["test"])
    for stupac in ["izvor", "vrsta"]:
        rez[f"test_po_{stupac}"] = [
            dict(naziv=k, n=int(len(g)), nezdravih=int(g.nezdrava.sum()), tocnost=float(g.tocno.mean()))
            for k, g in d.groupby(stupac)]

    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    for k in ["test", "vanjski_stvarni", "vanjski_usjevi"]:
        if k in lg:
            pok, toc = krivulja(y[k], p[k])
            ax.plot(pok[10:], toc[10:], label=NASLOVI[k])
    ax.set_xlabel("Pokrivenost (udio slika iznad praga)")
    ax.set_ylabel("Točnost na pokrivenim slikama")
    ax.set_ylim(0.4, 1.01)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    spremi(fig, slike / f"pokrivenost_{a.naziv}.png")

    fig, osi = plt.subplots(1, 2, figsize=(7, 3.4), sharey=True)
    for ax, k in zip(osi, ["test", "vanjski_stvarni"]):
        if k not in lg:
            continue
        for pp, oznaka in [(p_sirovo[k], "prije skaliranja"), (p[k], f"nakon (T = {T:.2f})")]:
            ax.plot(*kalibracijske_tocke(pp, y[k]), marker="o", label=oznaka)
        ax.plot([0.5, 1], [0.5, 1], "k--", lw=0.8)
        ax.set_title(NASLOVI[k], fontsize=9)
        ax.set_xlabel("Pouzdanost modela")
        ax.grid(alpha=0.3)
    osi[0].set_ylabel("Točnost")
    osi[0].legend(fontsize=8)
    spremi(fig, slike / f"kalibracija_{a.naziv}.png")

    (c.REZULTATI / f"evaluacija_{a.naziv}.json").write_text(json.dumps(rez, indent=1, ensure_ascii=False))
    print(f"T = {T:.3f}, prag = {prag}")
    for k, r in rez["skupovi"].items():
        print(f"{k:16s} n={r['n']:5d} točnost={r['tocnost']:.3f} P={r['preciznost']:.3f} R={r['odziv']:.3f} "
              f"F1={r['f1']:.3f} makroF1={r['makro_f1']:.3f} AUC={r['roc_auc']} "
              f"osnovica={r['osnovica_najcesci_razred']:.3f} "
              f"ECE {r['ece_prije']:.3f}->{r['ece_poslije']:.3f} pokrivenost={r['uz_prag']['pokrivenost']:.2f} "
              f"točnost iznad praga={r['uz_prag']['tocnost_iznad_praga']}")


if __name__ == "__main__":
    main()
