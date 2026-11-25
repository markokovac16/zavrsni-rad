"""Model, priprema slika i učitavanje podataka."""
import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models
from torchvision.transforms import v2 as T

import config as c

SREDINA, DEVIJACIJA = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


def uredaj():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def napravi_model(predtreniran=True):
    m = models.efficientnet_b0(weights="IMAGENET1K_V1" if predtreniran else None)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, len(c.RAZREDI))
    return m


def _zavrsetak():
    return [T.ToImage(), T.ToDtype(torch.float32, scale=True), T.Normalize(SREDINA, DEVIJACIJA)]


def transformacija_evaluacija():
    return T.Compose([T.Resize(256), T.CenterCrop(c.VELICINA), *_zavrsetak()])


def transformacija_trening(vrsta="osnovna"):
    if vrsta == "osnovna":
        koraci = [
            T.RandomResizedCrop(c.VELICINA, scale=(0.6, 1.0)),
            T.RandomHorizontalFlip(),
            T.ColorJitter(0.2, 0.2, 0.2, 0.02),
        ]
    elif vrsta == "jaka":
        koraci = [
            T.RandomResizedCrop(c.VELICINA, scale=(0.25, 1.0), ratio=(0.6, 1.6)),
            T.RandomHorizontalFlip(),
            T.RandomVerticalFlip(),
            T.RandAugment(num_ops=2, magnitude=9),
            T.RandomApply([T.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.2),
            T.RandomGrayscale(p=0.05),
        ]
    else:
        raise ValueError(vrsta)
    return T.Compose([*koraci, *_zavrsetak()])


class Slike(Dataset):
    def __init__(self, df: pd.DataFrame, transformacija):
        self.kopije = df.kopija.tolist()
        self.oznake = (df.oznaka == c.N).astype(int).tolist()
        self.transformacija = transformacija

    def __len__(self):
        return len(self.kopije)

    def __getitem__(self, i):
        with Image.open(c.PREDMEMORIJA / self.kopije[i]) as im:
            x = self.transformacija(im.convert("RGB"))
        return x, self.oznake[i]


def ucitavac(df, transformacija, mijesaj=False, serija=c.SERIJA):
    return DataLoader(Slike(df, transformacija), batch_size=serija, shuffle=mijesaj,
                      num_workers=6, persistent_workers=False, drop_last=mijesaj)


@torch.no_grad()
def logiti(model, df, dev=None):
    dev = dev or uredaj()
    model.eval().to(dev)
    izlazi = [model(x.to(dev)).float().cpu().numpy()
              for x, _ in ucitavac(df, transformacija_evaluacija(), serija=128)]
    return np.concatenate(izlazi)


def ucitaj_model(putanja, dev=None):
    stanje = torch.load(putanja, map_location="cpu", weights_only=True)
    m = napravi_model(predtreniran=False)
    m.load_state_dict(stanje["tezine"])
    return m.eval().to(dev or uredaj()), stanje
