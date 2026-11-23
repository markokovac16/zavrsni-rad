"""Korak 5: učenje klasifikatora zdrava / nezdrava."""
import argparse
import json
import time

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score
from torch import nn

import config as c
import model as M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--naziv", required=True)
    ap.add_argument("--manifest", default="manifest.csv")
    ap.add_argument("--augmentacija", default="osnovna", choices=["osnovna", "jaka"])
    ap.add_argument("--epohe", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--sjeme", type=int, default=c.SJEME)
    a = ap.parse_args()

    torch.manual_seed(a.sjeme)
    np.random.seed(a.sjeme)
    dev = M.uredaj()

    df = pd.read_csv(c.PODACI / a.manifest)
    tr, va = df[df.dio == "train"], df[df.dio == "val"]
    print(f"{a.naziv}: train {len(tr)}, val {len(va)}, uređaj {dev}")

    model = M.napravi_model().to(dev)
    ucit_tr = M.ucitavac(tr, M.transformacija_trening(a.augmentacija), mijesaj=True)

    udio = (tr.oznaka == c.N).mean()
    tezine = torch.tensor([0.5 / (1 - udio), 0.5 / udio], dtype=torch.float32, device=dev)
    gubitak_fn = nn.CrossEntropyLoss(weight=tezine)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    koraka = a.epohe * len(ucit_tr)
    raspored = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=koraka, pct_start=0.15)

    y_va = (va.oznaka == c.N).astype(int).to_numpy()
    povijest, najbolji = [], -1.0
    c.MODELI.mkdir(exist_ok=True)
    c.REZULTATI.mkdir(exist_ok=True)
    for epoha in range(1, a.epohe + 1):
        t0 = time.time()
        model.train()
        zbroj, n = 0.0, 0
        for x, y in ucit_tr:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad()
            g = gubitak_fn(model(x), y)
            g.backward()
            opt.step()
            raspored.step()
            zbroj += g.item() * len(y)
            n += len(y)

        lg = M.logiti(model, va, dev)
        g_va = nn.functional.cross_entropy(torch.tensor(lg), torch.tensor(y_va)).item()
        pred = lg.argmax(1)
        red = dict(epoha=epoha, gubitak_train=zbroj / n, gubitak_val=g_va,
                   tocnost_val=accuracy_score(y_va, pred),
                   makro_f1_val=f1_score(y_va, pred, average="macro"),
                   sekundi=round(time.time() - t0))
        povijest.append(red)
        print(json.dumps(red), flush=True)
        if red["makro_f1_val"] > najbolji:
            najbolji = red["makro_f1_val"]
            torch.save({"tezine": model.state_dict(), "arhitektura": "efficientnet_b0",
                        "epoha": epoha, "postavke": vars(a)}, c.MODELI / f"{a.naziv}.pt")

    (c.REZULTATI / f"povijest_{a.naziv}.json").write_text(json.dumps(povijest, indent=1))
    print(f"najbolji makro F1 na validaciji: {najbolji:.4f}")


if __name__ == "__main__":
    main()
