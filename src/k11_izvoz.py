"""Korak 11: brojke, tablice i slike za tekst rada (rezultati/brojke.tex, rezultati/tablice/, rezultati/slike/)."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image

import config as c
import slicnost as s

TABLICE = c.REZULTATI / "tablice"
SLIKE = c.REZULTATI / "slike"

IZVORI = {
    "aloe_vera_diseases": ("Aloe Vera Diseases", "Mendeley Data", "CC BY 4.0"),
    "aloe_vera_leaf_disease": ("Aloe Vera Leaf Disease", "Mendeley Data", "CC BY 4.0"),
    "combined_medicinal": ("Combined Medicinal Leaf", "Mendeley Data", "CC BY 4.0"),
    "epipremnum_aureum": ("Epipremnum aureum", "Mendeley Data", "CC BY 4.0"),
    "healthy_wilted": ("Healthy and Wilted Houseplant", "Kaggle", "© Original Authors"),
    "indoor_leaf_health": ("Indoor Plant Leaf Health", "Kaggle", "CC BY-SA 4.0"),
    "indoor_plant_disease": ("Indoor Plant Disease", "Mendeley Data", "CC BY 4.0"),
    "medicinal_leaf_disease": ("Medicinal Leaf Disease", "Mendeley Data", "CC BY 4.0"),
    "medicinal_leaf_health": ("Medicinal Leaf Health", "Mendeley Data", "CC BY 4.0"),
    "money_plant_atlas": ("Money Plant Diseases", "Mendeley Data", "CC BY 4.0"),
    "multiclass_medicinal": ("Multi-Class Medicinal Leaf", "Mendeley Data", "CC BY 4.0"),
    "plantvita_aloevera": ("PlantVita Aloevera", "Kaggle", "nije navedena"),
    "houseplant_health": ("Houseplant Health", "Kaggle", "CC BY-SA 4.0"),
    "plantdoc": ("PlantDoc", "GitHub", "CC BY 4.0"),
}
ULOGE = {"skup": "podjela", "vanjski_stvarni": "vanjski", "vanjski_usjevi": "vanjski"}
DIJELOVI = {"train": "Skup za učenje", "val": "Skup za provjeru", "test": "Ispitni skup",
            "vanjski_stvarni": "Houseplant Health", "vanjski_usjevi": "PlantDoc"}
PRIMJERI = [("zlatni puzavac", "epipremnum_aureum"), ("sansevierija", "indoor_plant_disease"),
            ("zelenčica", "indoor_plant_disease"), ("aloja", "aloe_vera_diseases"),
            ("kalanhoja", "medicinal_leaf_disease"), ("hibiskus", "medicinal_leaf_health")]

brojke = {}


def cijeli(x):
    return f"{int(x):,}".replace(",", ".")


def post(x, n=1):
    return f"{100 * x:.{n}f}".replace(".", ",") + r"~\%"


def postavi(kljuc, vrijednost):
    brojke[kljuc] = str(vrijednost)


def ucitaj(ime):
    return json.loads((c.REZULTATI / ime).read_text())


def tablica(ime, stupci, zaglavlje, retci):
    t = [f"\\begin{{tabular}}{{{stupci}}}", "\\toprule", "\\rowcolor{fakplava}",
         " & ".join(f"\\zaglavlje{{{z}}}" for z in zaglavlje) + " \\\\", "\\midrule"]
    t += [" & ".join(str(x) for x in r) + " \\\\" for r in retci]
    t += ["\\bottomrule", "\\end{tabular}"]
    (TABLICE / f"{ime}.tex").write_text("\n".join(t) + "\n", encoding="utf-8")


def ciscenje():
    cz = ucitaj("ciscenje.json")
    for k in ["prag_duplikat", "prag_slicne", "prag_zakrenute", "razmak_serije_s"]:
        postavi(f"podaci.{k}", cz[k])
    for k in ["slika_ukupno", "ostaje", "duplikata", "proturjecnih", "identicnih_datoteka_visak",
              "skupina_bez_grupiranja", "skupina_za_podjelu", "najveca_skupina", "slika_u_skupinama_od_10_i_vise",
              "naivna_test_slika", "naivna_test_s_duplikatom_u_treningu", "parova_istog_imena"]:
        postavi(f"podaci.{k}", cijeli(cz[k]))
    postavi("podaci.naivna_test_s_duplikatom_u_treningu.udio",
            post(cz["naivna_test_s_duplikatom_u_treningu"] / cz["naivna_test_slika"]))
    for k, v in cz["skupine_medu_izvorima"].items():
        postavi("podaci.zajednicke." + k.replace(" + ", "+"), cijeli(v))
    for r in cz["po_izvoru"]:
        postavi(f"izvor.{r['izvor']}.ukupno", cijeli(r["ukupno"]))
        postavi(f"izvor.{r['izvor']}.ostaje", cijeli(r["ostaje"]))

    retci = []
    for u, z in zip(cz["uspravni_po_udaljenosti"], cz["zakrenuti_po_udaljenosti"]):
        raspon = f"{u['od']}--{u['do']}"
        for vrsta, r in [("uspravni", u), ("zakrenuti", z)]:
            postavi(f"parovi.{vrsta}.{r['od']}-{r['do']}.n", cijeli(r["parova"]))
            postavi(f"parovi.{vrsta}.{r['od']}-{r['do']}.razlicita", post(r["razlicita_oznaka"]))
        retci.append([raspon, cijeli(u["parova"]), post(u["razlicita_oznaka"]),
                      cijeli(z["parova"]), post(z["razlicita_oznaka"])])
    tablica("pragovi", "L{2.6cm} R{2.3cm} R{2.3cm} R{2.3cm} R{2.3cm}",
            ["Razlika (bitova)", "Parova, isti položaj", "Različita oznaka", "Parova, zakrenuti",
             "Različita oznaka"], retci)


def izvori_i_podjela():
    cz = ucitaj("ciscenje.json")
    sirovi = {r["izvor"]: r for r in cz["po_izvoru"]}
    df = pd.read_csv(c.PODACI / "manifest.csv")
    sk = df[df.uloga == "skup"]
    postavi("podaci.skup.izvora", sk.izvor.nunique())
    postavi("podaci.skup.ostaje", cijeli(len(sk)))
    postavi("podaci.skup.sirovo", cijeli(sum(sirovi[i]["ukupno"] for i in sk.izvor.unique())))
    postavi("podaci.vrsta.n", sk[sk.vrsta != "razne"].vrsta.nunique())

    retci = []
    for uloga in ["skup", "vanjski_stvarni", "vanjski_usjevi"]:
        for izvor, g in df[df.uloga == uloga].groupby("izvor"):
            naziv, repozitorij, licenca = IZVORI[izvor]
            vrste = g.vrsta.unique()
            opis = ", ".join(sorted(vrste)) if len(vrste) <= 2 else f"{len(vrste)} vrste"
            retci.append([f"{naziv} \\citep{{skup_{izvor}}}", repozitorij, opis, licenca, ULOGE[uloga],
                          cijeli(sirovi[izvor]["ukupno"]), cijeli(len(g)),
                          cijeli((g.oznaka == c.Z).sum()), cijeli((g.oznaka == c.N).sum())])
    tablica("izvori", "lllllrrrr",
            ["Skup", "Repozitorij", "Vrste", "Licenca", "Namjena", "Preuzeto", "Zadržano", "Zdrava", "Nezdrava"],
            retci)

    po_sloju = sk.groupby(["izvor", "oznaka", "dio"]).size().unstack(fill_value=0)
    bez = po_sloju[po_sloju["test"] == 0]
    postavi("podjela.slojeva", len(po_sloju))
    postavi("podjela.slojeva_bez_testa", len(bez))
    u_bez = sk.set_index(["izvor", "oznaka"]).index.isin(bez.index)
    postavi("podjela.skupina_bez_testa", sk[u_bez].skupina.nunique())
    postavi("podjela.slojevi_bez_testa", " i ".join(
        f"\\textit{{{IZVORI[i][0]}}} (\\textit{{{o}}})"
        for i, o in bez.index))
    for (izvor, oznaka), red in bez.iterrows():
        k = f"podjela.bez_testa.{izvor}"
        postavi(k + ".train", cijeli(red["train"]))
        postavi(k + ".val", cijeli(red["val"]))
        postavi(k + ".skupina", sk[(sk.izvor == izvor) & (sk.oznaka == oznaka)].skupina.nunique())

    retci = []
    for dio, naziv in DIJELOVI.items():
        g = df[df.dio == dio]
        z, n = int((g.oznaka == c.Z).sum()), int((g.oznaka == c.N).sum())
        for k, v in [("n", cijeli(len(g))), ("zdrava", cijeli(z)), ("nezdrava", cijeli(n)),
                     ("udio_nezdravih", post(n / len(g)))]:
            postavi(f"dio.{dio}.{k}", v)
        retci.append([naziv, cijeli(len(g)), post(len(g) / len(sk)) if dio in ("train", "val", "test") else "--",
                      cijeli(z), cijeli(n), post(n / len(g))])
    tablica("podjela", "lrrrrr",
            ["Dio", "Slika", "Udio slika", "Zdrava", "Nezdrava", "Udio nezdravih"], retci)

    for vrsta, g in sk.groupby("vrsta"):
        postavi(f"vrsta.{vrsta.replace(' ', '_')}.n", cijeli(len(g)))

    svi = pd.read_csv(c.PODACI / "manifest_sirovi.csv")
    svi = svi[svi.uloga == "skup"]
    vrijeme = svi.putanja.str.split("/").str[-1].map(s.vrijeme_snimanja)
    postavi("podjela.izvora_s_vremenom", svi[vrijeme.notna()].izvor.nunique())
    yb = df[df.putanja.str.contains("/Kalanchoe_Yellow_Blight/")]
    for dio in ["train", "val", "test"]:
        postavi(f"podjela.bez_vremena.{dio}", cijeli((yb.dio == dio).sum()))
    svi_sirovi = pd.read_csv(c.PODACI / "manifest_sirovi.csv")
    isto_ime = s.parovi_istog_imena(svi_sirovi)
    oznaka = svi_sirovi.oznaka.to_numpy()
    postavi("podaci.parova_istog_imena.razlicita", sum(oznaka[a] != oznaka[b] for a, b in isto_ime))
    postavi("podaci.parova_istog_imena.izvora", len({svi_sirovi.izvor.iat[x] for p in isto_ime for x in p}))
    primjeri(df)


def primjeri(df):
    fig, osi = plt.subplots(2, len(PRIMJERI), figsize=(9, 3.4))
    for j, (vrsta, izvor) in enumerate(PRIMJERI):
        for i, oznaka in enumerate([c.Z, c.N]):
            g = df[(df.izvor == izvor) & (df.vrsta == vrsta) & (df.oznaka == oznaka)].sort_values("id")
            slika = Image.open(c.PREDMEMORIJA / g.iloc[len(g) // 2].kopija).convert("RGB")
            a = min(slika.size)
            slika = slika.crop(((slika.width - a) // 2, (slika.height - a) // 2,
                                (slika.width + a) // 2, (slika.height + a) // 2))
            osi[i, j].imshow(slika)
            osi[i, j].set_xticks([])
            osi[i, j].set_yticks([])
            if i == 0:
                osi[i, j].set_title(vrsta, fontsize=9)
            if j == 0:
                osi[i, j].set_ylabel(oznaka, fontsize=9)
    fig.tight_layout()
    fig.savefig(SLIKE / "primjeri_podataka.png", dpi=200)
    plt.close(fig)


def provjera_podjele():
    r = ucitaj("provjera_podjele.json")
    n = r["test_slika"]
    for kljuc, polje in [("podjela.slicne", "uspravne_iznad_praga"), ("podjela.zakrenute", "zakrenute_iznad_praga")]:
        x = r[polje]
        postavi(kljuc, cijeli(x["testnih_slika"]))
        postavi(kljuc + ".udio", post(x["testnih_slika"] / n))
        postavi(kljuc + ".parova", cijeli(x["parova"]))
        postavi(kljuc + ".razlicita", cijeli(x["parova_razlicite_oznake"]))
    postavi("podjela.do_praga", r["uspravne_do_praga"]["testnih_slika"] + r["zakrenute_do_praga"]["testnih_slika"])
    postavi("podjela.isto_ime", r["isto_ime"]["testnih_slika"])
    u = r["uzastopne"]
    postavi("podjela.uzastopne.n", cijeli(u["test_s_vremenom"]))
    postavi("podjela.uzastopne.izvora", len(u["po_izvoru"]))
    for k in ["do_30_s", "do_60_s", "do_300_s"]:
        postavi(f"podjela.uzastopne.{k}", cijeli(u[k]))
    postavi("podjela.uzastopne.do_300_s.udio", post(u["do_300_s"] / u["test_s_vremenom"], 0))


def stvarne():
    r = ucitaj("stvarne_fotografije.json")
    postavi("inat.prijedloga", cijeli(r["prijedloga"]))
    postavi("inat.upotrebljivih", cijeli(r["upotrebljivih"]))
    postavi("inat.neupotrebljivih", cijeli(r["po_prijedlogu"]["unusable"]))
    postavi("inat.nejasnih", cijeli(r["po_prijedlogu"]["unclear"]))
    postavi("inat.autora", cijeli(r["autora"]))
    postavi("inat.kopija", r["kopija_iz_ostalih_skupova"])
    for v, n in r["po_vrsti"].items():
        postavi(f"inat.vrsta.{v.replace(' ', '_')}", cijeli(n))
    for licenca, n in r["po_licenci"].items():
        postavi(f"inat.licenca.{licenca}", cijeli(n))
    for dio, x in r["podjela"].items():
        postavi(f"inat.{dio}.slika", cijeli(x["slika"]))
        postavi(f"inat.{dio}.autora", cijeli(x["autora"]))
        postavi(f"inat.{dio}.nezdravih", cijeli(x["nezdravih"]))
        postavi(f"inat.{dio}.udio_nezdravih", post(x["nezdravih"] / x["slika"]))
    test = pd.read_csv(c.PODACI / "manifest_inat.csv").query("dio == 'inat_test'")
    po_autoru = test.skupina.value_counts()
    postavi("inat.inat_test.najvise_od_autora", cijeli(po_autoru.iloc[0]))
    postavi("inat.inat_test.najvise_od_autora.udio", post(po_autoru.iloc[0] / len(test)))
    postavi("inat.inat_test.deset_autora.udio", post(po_autoru.iloc[:10].sum() / len(test), 0))


def main():
    TABLICE.mkdir(exist_ok=True)
    SLIKE.mkdir(exist_ok=True)
    ciscenje()
    izvori_i_podjela()
    provjera_podjele()
    stvarne()
    retci = [f"\\postavi{{{k}}}{{{v}}}" for k, v in sorted(brojke.items())]
    (c.REZULTATI / "brojke.tex").write_text(
        "% Stvara src/k11_izvoz.py; ne uređivati ručno.\n" + "\n".join(retci) + "\n", encoding="utf-8")
    print(f"{len(brojke)} brojki, tablice: {sorted(p.name for p in TABLICE.glob('*.tex'))}")


if __name__ == "__main__":
    main()
