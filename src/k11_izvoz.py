"""Korak 11: brojke, tablice i slike za tekst rada (rezultati/brojke.tex, rezultati/tablice/, rezultati/slike/)."""
import json
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import torch
from PIL import Image

import config as c
import k01_manifest as K1
import k02_ciscenje_i_podjela as K2
import k04_stvarne_fotografije as K4
import k07_evaluacija as E
import model as M
import slicnost as s

TABLICE = c.REZULTATI / "tablice"
SLIKE = c.REZULTATI / "slike"

IZVORI = {
    "aloe_vera_diseases": ("Aloe Vera Diseases", "Mendeley Data"),
    "aloe_vera_leaf_disease": ("Aloe Vera Leaf Disease", "Mendeley Data"),
    "combined_medicinal": ("Combined Medicinal Leaf", "Mendeley Data"),
    "epipremnum_aureum": ("Epipremnum aureum", "Mendeley Data"),
    "healthy_wilted": ("Healthy and Wilted Houseplant", "Kaggle"),
    "indoor_leaf_health": ("Indoor Plant Leaf Health", "Kaggle"),
    "indoor_plant_disease": ("Indoor Plant Disease", "Mendeley Data"),
    "medicinal_leaf_disease": ("Medicinal Leaf Disease", "Mendeley Data"),
    "medicinal_leaf_health": ("Medicinal Leaf Health", "Mendeley Data"),
    "money_plant_atlas": ("Money Plant Diseases", "Mendeley Data"),
    "multiclass_medicinal": ("Multi-Class Medicinal Leaf", "Mendeley Data"),
    "plantvita_aloevera": ("PlantVita Aloevera", "Kaggle"),
    "houseplant_health": ("Houseplant Health", "Kaggle"),
    "plantdoc": ("PlantDoc", "GitHub"),
}
ULOGE = {"skup": "podjela", "vanjski_stvarni": "vanjski", "vanjski_usjevi": "vanjski"}
DIJELOVI = {"train": "Skup za učenje", "val": "Skup za provjeru", "test": "Ispitni skup",
            "vanjski_stvarni": "Houseplant Health", "vanjski_usjevi": "PlantDoc"}
PRIMJERI = [("zlatni puzavac", "epipremnum_aureum"), ("sansevierija", "indoor_plant_disease"),
            ("zelenčica", "indoor_plant_disease"), ("aloja", "aloe_vera_diseases"),
            ("kalanhoja", "medicinal_leaf_disease"), ("hibiskus", "medicinal_leaf_health")]

SKUPOVI = {"val": "Skup za provjeru", "test": "Ispitni skup",
           "vanjski_stvarni": "Houseplant Health", "vanjski_usjevi": "PlantDoc"}
MODELI = {"osnovna": "osnovna", "jaka": "jaka"}
UCENJA = {"osnovna": ["osnovna", "osnovna_s1", "osnovna_s2"], "jaka": ["jaka", "jaka_s1", "jaka_s2"]}
IZVORI_CURENJA = ["plantvita_aloevera", "aloe_vera_leaf_disease", "money_plant_atlas"]

brojke = {}


def cijeli(x):
    return f"{int(x):,}".replace(",", ".")


def post(x, n=1):
    return f"{100 * x:.{n}f}".replace(".", ",") + r"~\%"


def dec(x, n=3):
    return f"{x:.{n}f}".replace(".", ",")


def broj_post(x):
    return f"{100 * x:.1f}".replace(".", ",")


def s_intervalom(x, iv):
    if iv[0] == iv[1]:
        return broj_post(x)
    return f"{broj_post(x)} ({broj_post(iv[0])} -- {broj_post(iv[1])})"


def bodovi(x):
    return f"{100 * x:.1f}".replace(".", ",")


def omjer(udjeli):
    return " : ".join(f"{round(100 * u)}" for u in udjeli.values())


def postavi(kljuc, vrijednost):
    brojke[kljuc] = str(vrijednost)


def ucitaj(ime):
    return json.loads((c.REZULTATI / ime).read_text())


def celija_zaglavlja(z, poravnanje):
    if "\n" not in z:
        return f"\\zaglavlje{{{z}}}"
    return f"\\zaglavlje{{\\begin{{tabular}}[b]{{@{{}}{poravnanje}@{{}}}}{z.replace(chr(10), ' \\\\ ')}\\end{{tabular}}}}"


def tablica(ime, stupci, zaglavlje, retci):
    poravnanja = [s[0].lower() for s in re.findall(r"[LCR]\{[^}]*\}|[lcr]", stupci)]
    t = [f"\\begin{{tabular}}{{{stupci}}}", "\\toprule", "\\rowcolor{fakplava}",
         " & ".join(celija_zaglavlja(z, "r" if a == "r" else "l") for z, a in zip(zaglavlje, poravnanja))
         + " \\\\", "\\midrule"]
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
        raspon = f"{u['od']} -- {u['do']}"
        for vrsta, r in [("uspravni", u), ("zakrenuti", z)]:
            postavi(f"parovi.{vrsta}.{r['od']}-{r['do']}.n", cijeli(r["parova"]))
            postavi(f"parovi.{vrsta}.{r['od']}-{r['do']}.razlicita", post(r["razlicita_oznaka"]))
        retci.append([raspon, cijeli(u["parova"]), broj_post(u["razlicita_oznaka"]),
                      cijeli(z["parova"]), broj_post(z["razlicita_oznaka"])])
    tablica("pragovi", "L{2.6cm} R{2.3cm} R{2.3cm} R{2.3cm} R{2.3cm}",
            ["Razlika (bitova)", "Parova, isti položaj", "Različita oznaka, \\%", "Parova, zakrenuti",
             "Različita oznaka, \\%"], retci)
    for k in ["identicnih_proturjecnih_skupina", "identicnih_proturjecnih_datoteka"]:
        postavi(f"podaci.{k}", cijeli(cz[k]))
    postavi("podaci.izvora.ukupno", len(cz["po_izvoru"]))


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
            (naziv, repozitorij), licenca = IZVORI[izvor], c.LICENCE[izvor]
            vrste = g.vrsta.unique()
            opis = ", ".join(sorted(vrste)) if len(vrste) <= 2 else f"{len(vrste)} vrste"
            retci.append([f"{naziv} \\citep{{skup_{izvor}}}", repozitorij, opis, licenca, ULOGE[uloga],
                          cijeli(sirovi[izvor]["ukupno"]), cijeli(len(g)),
                          cijeli((g.oznaka == c.Z).sum()), cijeli((g.oznaka == c.N).sum())])
    tablica("izvori", "L{2.4cm} L{1.8cm} L{1.4cm} L{1.5cm} l r r r r",
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
        retci.append([naziv, cijeli(len(g)), broj_post(len(g) / len(sk)) if dio in ("train", "val", "test") else "--",
                      cijeli(z), cijeli(n), broj_post(n / len(g))])
    tablica("podjela", "lrrrrr",
            ["Dio", "Slika", "Udio slika, \\%", "Zdrava", "Nezdrava", "Udio nezdravih, \\%"], retci)

    pd_ = df[df.dio == "vanjski_usjevi"]
    usjev = pd_.putanja.str.split("/").str[-2].str.split().str[0].str.lower()
    stanja = pd_.groupby(usjev).oznaka.nunique()
    jedno = usjev.isin(stanja[stanja == 1].index)
    postavi("plantdoc.usjeva", len(stanja))
    postavi("plantdoc.usjeva_jednog_stanja", int((stanja == 1).sum()))
    postavi("plantdoc.slika_jednog_stanja.udio", post(jedno.mean(), 0))

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
    fig, osi = plt.subplots(2, len(PRIMJERI), figsize=(E.SIRINA_TEKSTA, 0.4 * E.SIRINA_TEKSTA))
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
                osi[i, j].set_title(vrsta.replace("sansevierija", "sansevijerija").replace(" ", "\n"))
            if j == 0:
                osi[i, j].set_ylabel(oznaka)
    fig.tight_layout()
    fig.savefig(SLIKE / "primjeri_podataka.png", dpi=E.DPI)
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
    v = r["val"]
    postavi("podjela.val.n", cijeli(v["slika"]))
    postavi("podjela.val.slicne", cijeli(v["uspravne_iznad_praga"]["testnih_slika"]))
    postavi("podjela.val.slicne.udio", post(v["uspravne_iznad_praga"]["testnih_slika"] / v["slika"]))
    postavi("podjela.val.do_praga", v["uspravne_do_praga"]["testnih_slika"] + v["zakrenute_do_praga"]["testnih_slika"])
    postavi("podjela.val.uzastopne.n", cijeli(v["uzastopne"]["test_s_vremenom"]))
    postavi("podjela.val.uzastopne.do_300_s", cijeli(v["uzastopne"]["do_300_s"]))
    postavi("podjela.val.uzastopne.do_30_s", cijeli(v["uzastopne"]["do_30_s"]))
    postavi("podjela.val.uzastopne.do_300_s.udio", post(v["uzastopne"]["do_300_s"] / v["uzastopne"]["test_s_vremenom"], 0))


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


def metrike_skupa(k, r):
    postavi(k + ".n", cijeli(r["n"]))
    postavi(k + ".skupina", cijeli(r["skupina"]))
    postavi(k + ".osnovica", post(r["osnovica_najcesci_razred"]))
    for m in ["tocnost", "makro_f1"]:
        f = post if m == "tocnost" else dec
        postavi(f"{k}.{m}", f(r[m]))
        postavi(f"{k}.{m}.od", f(r[m + "_interval"][0]))
        postavi(f"{k}.{m}.do", f(r[m + "_interval"][1]))
    for m in ["preciznost", "odziv", "f1"]:
        postavi(f"{k}.{m}", dec(r[m]))
    if r.get("roc_auc") is not None:
        postavi(k + ".auc", dec(r["roc_auc"]))
    if r.get("roc_auc_interval") is not None:
        postavi(k + ".auc.od", dec(r["roc_auc_interval"][0]))
        postavi(k + ".auc.do", dec(r["roc_auc_interval"][1]))
    mz = r["matrica"]
    for m, v in mz.items():
        postavi(f"{k}.{m}", cijeli(v))
    postavi(k + ".pogresaka", cijeli(mz["fn"] + mz["fp"]))
    postavi(k + ".fn.udio", post(mz["fn"] / (mz["fn"] + mz["tp"])))
    postavi(k + ".fp.udio", post(mz["fp"] / (mz["fp"] + mz["tn"])))
    postavi(k + ".nezdravih", cijeli(mz["fn"] + mz["tp"]))
    postavi(k + ".zdravih", cijeli(mz["fp"] + mz["tn"]))
    if "ece_prije" in r:
        postavi(k + ".ece.prije", dec(r["ece_prije"]))
        postavi(k + ".ece.poslije", dec(r["ece_poslije"]))
        u = r["uz_prag"]
        postavi(k + ".pokrivenost", post(u["pokrivenost"]))
        postavi(k + ".ispod.n", cijeli(round(r["n"] * (1 - u["pokrivenost"]))))
        postavi(k + ".iznad.n", cijeli(round(r["n"] * u["pokrivenost"])))
        postavi(k + ".tocnost.iznad", post(u["tocnost_iznad_praga"]))
        postavi(k + ".tocnost.iznad.od", post(u["tocnost_iznad_praga_interval"][0]))
        postavi(k + ".tocnost.iznad.do", post(u["tocnost_iznad_praga_interval"][1]))
        postavi(k + ".tocnost.ispod", post(u["tocnost_ispod_praga"]))


def ucenje_i_odabir():
    od = ucitaj("odabrani_model.json")
    postavi("odabir.glavni", od["naziv"])
    for inacica, r in od["inacice"].items():
        for m in ["prosjek", "najmanji", "najveci"]:
            postavi(f"odabir.{inacica}.{m}", dec(r[m], 4))
    prva = ucitaj("odabrani_model_prva_podjela.json")
    postavi("odabir.prva.glavni", "osnovna" if prva["naziv"] == "osnovni" else prva["naziv"])
    for inacica, r in prva["inacice"].items():
        ime = "osnovna" if inacica == "osnovni" else inacica
        for m in ["prosjek", "najmanji", "najveci"]:
            postavi(f"odabir.prva.{ime}.{m}", dec(r[m], 4))

    retci, po_inacici = [], {}
    for inacica, ucenja in UCENJA.items():
        for u in ucenja:
            pov = ucitaj(f"povijest_{u}.json")
            naj = max(pov, key=lambda r: r["makro_f1_val"])
            sjeme = torch.load(c.MODELI / f"{u}.pt", map_location="cpu", weights_only=True)["postavke"]["sjeme"]
            ev = ucitaj(f"evaluacija_{u}.json")["skupovi"]
            k = f"ucenje.{u}"
            postavi(k + ".sjeme", sjeme)
            postavi(k + ".epoha", naj["epoha"])
            postavi(k + ".makro_f1_val", dec(naj["makro_f1_val"], 4))
            postavi(k + ".sekundi", round(sum(r["sekundi"] for r in pov) / len(pov)))
            po_inacici.setdefault(inacica, []).append(ev)
            retci.append([inacica, sjeme, naj["epoha"], dec(naj["makro_f1_val"], 4), dec(ev["test"]["makro_f1"]),
                          broj_post(ev["test"]["tocnost"]), broj_post(ev["vanjski_stvarni"]["tocnost"]),
                          broj_post(ev["vanjski_usjevi"]["tocnost"])])
    tablica("ucenja", "llrrrrrr",
            ["Augmentacija", "Sjeme", "Epoha", "Makro F1\n(provjera)", "Makro F1\n(ispitni)", "Točnost, \\%\n(ispitni)",
             "Točnost, \\%\n(Houseplant\nHealth)", "Točnost, \\%\n(PlantDoc)"], retci)
    for inacica, evs in po_inacici.items():
        for skup, m, f, ime in [("test", "makro_f1", dec, "test_makro_f1"), ("test", "tocnost", post, "test_tocnost"),
                                ("vanjski_stvarni", "tocnost", post, "hh_tocnost"),
                                ("vanjski_stvarni", "roc_auc", dec, "hh_auc"),
                                ("vanjski_usjevi", "tocnost", post, "plantdoc_tocnost")]:
            v = [e[skup][m] for e in evs]
            postavi(f"ucenje.{inacica}.{ime}.od", f(min(v)))
            postavi(f"ucenje.{inacica}.{ime}.do", f(max(v)))
    svi_ev = sum(po_inacici.values(), [])
    iznad = [e["test"]["uz_prag"] for e in svi_ev]
    postavi("ucenje.svi.test_tocnost_iznad.od", post(min(u["tocnost_iznad_praga"] for u in iznad)))
    postavi("ucenje.svi.test_tocnost_iznad.do", post(max(u["tocnost_iznad_praga"] for u in iznad)))
    postavi("ucenje.svi.test_iznad_bez_cilja", sum(not u["tocnost_iznad_praga_interval"][0] <= E.CILJANA_TOCNOST <= u["tocnost_iznad_praga_interval"][1] for u in iznad))
    hh = [e["vanjski_stvarni"]["uz_prag"] for e in svi_ev]
    postavi("ucenje.svi.hh_iznad_nize", sum(u["tocnost_iznad_praga"] < u["tocnost_ispod_praga"] for u in hh))
    for inacica, ucenja in UCENJA.items():
        mld, ostali = [], []
        for u in ucenja:
            po = {r["naziv"]: round(r["n"] * (1 - r["tocnost"])) for r in ucitaj(f"evaluacija_{u}.json")["test_po_izvor"]}
            mld.append(po["medicinal_leaf_disease"])
            ostali.append(sum(po.values()) - po["medicinal_leaf_disease"])
        for ime, v in [("mld_pogresaka", mld), ("ostali_pogresaka", ostali)]:
            postavi(f"ucenje.{inacica}.{ime}.od", min(v))
            postavi(f"ucenje.{inacica}.{ime}.do", max(v))
    postavi("ucenje.svi.hh_tocnost.do", post(max(e["vanjski_stvarni"]["tocnost"] for e in svi_ev)))
    postavi("ucenje.svi.hh_tocnost.od", post(min(e["vanjski_stvarni"]["tocnost"] for e in svi_ev)))
    postavi("ucenje.svi.test_makro_f1.od", dec(min(e["test"]["makro_f1"] for e in svi_ev)))
    postavi("ucenje.svi.test_makro_f1.do", dec(max(e["test"]["makro_f1"] for e in svi_ev)))
    sve = [r["sekundi"] for u in sum(UCENJA.values(), []) for r in ucitaj(f"povijest_{u}.json")]
    postavi("ucenje.sekundi.od", min(sve))
    postavi("ucenje.sekundi.do", max(sve))
    pov = ucitaj(f"povijest_{od['naziv']}.json")
    postavi("ucenje.epoha.ukupno", len(pov))
    najmanji = min(pov, key=lambda r: r["gubitak_val"])
    postavi("ucenje.glavni.epoha_najmanji_gubitak", najmanji["epoha"])
    postavi("ucenje.glavni.najmanji_gubitak_val", dec(najmanji["gubitak_val"]))
    postavi("ucenje.glavni.zadnji_gubitak_train", dec(pov[-1]["gubitak_train"]))
    postavi("ucenje.glavni.zadnji_gubitak_val", dec(pov[-1]["gubitak_val"]))


def evaluacija():
    df = pd.read_csv(c.PODACI / "manifest.csv")
    test = df[df.dio == "test"]
    ev = {m: ucitaj(f"evaluacija_{m}.json") for m in MODELI}
    retci_m, retci_p = [], []
    for skup, naziv in SKUPOVI.items():
        for m in MODELI:
            r = ev[m]["skupovi"][skup]
            metrike_skupa(f"m.{m}.{skup}", r)
            retci_m.append([naziv, m, cijeli(r["n"]), broj_post(r["osnovica_najcesci_razred"]),
                            s_intervalom(r["tocnost"], r["tocnost_interval"]), dec(r["preciznost"]),
                            dec(r["odziv"]), dec(r["f1"]), dec(r["makro_f1"]), dec(r["roc_auc"])])
            u = r["uz_prag"]
            retci_p.append([naziv, m, dec(r["ece_prije"]), dec(r["ece_poslije"]), broj_post(u["pokrivenost"]),
                            broj_post(u["tocnost_iznad_praga"]), broj_post(u["tocnost_ispod_praga"])])
    tablica("metrike", "L{1.9cm} l r r r r r r r r",
            ["Skup", "Model", "Slika", "Osnovica,\n\\%", "Točnost, \\%\n(interval)", "Preciznost", "Odziv", "F1",
             "Makro\nF1", "AUC"], retci_m)
    tablica("prag", "llrrrrr",
            ["Skup", "Model", "ECE\nprije", "ECE\nposlije", "Pokrivenost,\n\\%", "Točnost iznad\npraga, \\%",
             "Točnost ispod\npraga, \\%"], retci_p)
    for m in MODELI:
        e = ev[m]
        postavi(f"m.{m}.T", dec(e["temperatura"], 2))
        postavi(f"m.{m}.prag", dec(e["prag"]))
        postavi(f"m.{m}.epoha", e["epoha"])
        sl = e["test_slicne"]
        postavi(f"m.{m}.test.slicne.razlika", bodovi(sl["razlika"]))
        postavi(f"m.{m}.test.slicne.razlika.od", bodovi(sl["razlika_interval"][0]))
        postavi(f"m.{m}.test.slicne.razlika.do", bodovi(sl["razlika_interval"][1]))
        for ime in ["sa_slicnom_u_ucenju", "bez_slicne"]:
            r = sl[ime]
            k = f"m.{m}.test.{ime}"
            postavi(k + ".n", cijeli(r["n"]))
            postavi(k + ".tocnost", post(r["tocnost"]))
            postavi(k + ".tocnost.od", post(r["tocnost_interval"][0]))
            postavi(k + ".tocnost.do", post(r["tocnost_interval"][1]))
    postavi("m.osnovna.primjeri.izvori", "\\citep{" + ",".join(f"skup_{i}" for i in ev["osnovna"]["primjeri_izvori"]) + "}")
    postavi("m.ciljana_tocnost", post(ev["osnovna"]["ciljana_tocnost"], 0))

    for stupac, ime in [("izvor", "po_izvoru"), ("vrsta", "po_vrsti")]:
        skupine = test.groupby(stupac).skupina.nunique()
        jaka = {r["naziv"]: r for r in ev["jaka"][f"test_po_{stupac}"]}
        retci = []
        for r in ev["osnovna"][f"test_po_{stupac}"]:
            n = r["naziv"]
            kljuc = f"{ime}.{n.replace(' ', '_')}"
            for m, x in [("osnovna", r), ("jaka", jaka[n])]:
                postavi(f"{kljuc}.{m}.tocnost", post(x["tocnost"]))
            postavi(kljuc + ".n", cijeli(r["n"]))
            postavi(kljuc + ".pogresaka", cijeli(round(r["n"] * (1 - r["tocnost"]))))
            postavi(kljuc + ".jaka.pogresaka", cijeli(round(r["n"] * (1 - jaka[n]["tocnost"]))))
            postavi(kljuc + ".skupina", cijeli(skupine[n]))
            postavi(kljuc + ".nezdravih.udio", post(r["nezdravih"] / r["n"], 0))
            opis = f"\\textit{{{IZVORI[n][0]}}}" if stupac == "izvor" else n
            retci.append([opis, cijeli(r["n"]), cijeli(skupine[n]), f"{100 * r['nezdravih'] / r['n']:.0f}",
                          broj_post(r["tocnost"]), broj_post(jaka[n]["tocnost"])])
        if stupac == "izvor":
            postavi("po_izvoru.izvora", len(retci))
            postavi("po_izvoru.bez_pogreske", sum(r["tocnost"] == 1 for r in ev["osnovna"]["test_po_izvor"]))
        if stupac == "izvor":
            tablica(ime, "lrrrrr", ["Izvor", "Slika", "Skupina", "Udio\nnezdravih, \\%", "Točnost, \\%\n(osnovna)",
                                    "Točnost, \\%\n(jaka)"], retci)


def curenje():
    cu = ucitaj("curenje.json")
    for k, r in cu["naivni"].items():
        metrike_skupa(f"curenje.naivni.{k}", r)
    for k, r in cu["osnovna"].items():
        metrike_skupa(f"curenje.osnovna.{k}", r)
    naivni = pd.read_csv(c.PODACI / "manifest_naivni.csv")
    cisti = pd.read_csv(c.PODACI / "manifest.csv")
    postavi("curenje.naivni.train.n", cijeli((naivni.dio == "train").sum()))
    postavi("curenje.osnovna.train.n", cijeli((cisti.dio == "train").sum()))
    ev = ucitaj("evaluacija_naivni.json")["skupovi"]["val"]
    postavi("curenje.naivni.val.makro_f1", dec(ev["makro_f1"]))
    s_dupl = cu["naivni"]["test_s_duplikatom_u_ucenju"]["n"]
    iz_tri = sum(cu["po_izvoru"][i]["s_duplikatom"]["n"] for i in IZVORI_CURENJA)
    postavi("curenje.s_duplikatom.iz_tri_izvora", cijeli(iz_tri))
    postavi("curenje.s_duplikatom.iz_tri_izvora.udio", post(iz_tri / s_dupl, 0))

    def red(opis, r):
        return [opis, cijeli(r["n"]), f"{100 * r['udio_nezdravih']:.0f}", s_intervalom(r["tocnost"], r["tocnost_interval"])]
    n = cu["naivni"]
    retci = [red("Naivna podjela: svi", n["test_svi"]),
             red("\\quad s duplikatom u skupu za učenje", n["test_s_duplikatom_u_ucenju"]),
             red("\\quad bez duplikata", n["test_bez_duplikata_u_ucenju"]),
             red("\\quad bez duplikata, izvan triju izvora", n["test_bez_duplikata_izvan_izvora_s_duplikatima"])]
    for izvor in IZVORI_CURENJA:
        for ime, opis in [("s_duplikatom", "s duplikatom"), ("bez_duplikata", "bez duplikata")]:
            r = cu["po_izvoru"][izvor][ime]
            k = f"curenje.{izvor}.{ime}"
            postavi(k + ".n", cijeli(r["n"]))
            postavi(k + ".tocnost", post(r["tocnost"]))
            postavi(k + ".tocnost.od", post(r["tocnost_interval"][0]))
            postavi(k + ".tocnost.do", post(r["tocnost_interval"][1]))
            postavi(k + ".udio_nezdravih", post(r["udio_nezdravih"], 0))
            retci.append(red(f"\\textit{{{IZVORI[izvor][0]}}}: {opis}", r))
    retci.append(red("Očišćena podjela (osnovna): svi", cu["osnovna"]["test_cisti"]))
    tablica("curenje", "lrrr", ["Ispitne slike", "Slika", "Udio\nnezdravih, \\%", "Točnost, \\%\n(interval)"], retci)

    aloje = {"aloe_vera_leaf_disease", "plantvita_aloevera"}
    retci = []
    for ime, opis in [("velicina_2", "Skupine od dviju slika"), ("velicina_2_i_vise", "Sve skupine duplikata")]:
        r = cu["kontrola"][ime]
        k = f"curenje.kontrola.{ime}"
        for strana in ["s_kopijom", "bez_kopije"]:
            x = r[strana]
            postavi(f"{k}.{strana}.n", cijeli(x["n"]))
            postavi(f"{k}.{strana}.tocnost", post(x["tocnost"]))
            postavi(f"{k}.{strana}.tocnost.od", post(x["tocnost_interval"][0]))
            postavi(f"{k}.{strana}.tocnost.do", post(x["tocnost_interval"][1]))
        postavi(k + ".razlika", bodovi(r["razlika"]))
        postavi(k + ".razlika.od", bodovi(r["razlika_interval"][0]))
        postavi(k + ".razlika.do", bodovi(r["razlika_interval"][1]))
        iz_aloja = sum(n for i, n in r["bez_kopije_po_izvoru"].items() if i in aloje)
        postavi(k + ".bez_kopije.iz_aloja", cijeli(iz_aloja))
        postavi(k + ".bez_kopije.iz_aloja.udio", post(iz_aloja / r["bez_kopije"]["n"], 0))
        retci.append([opis, cijeli(r["s_kopijom"]["n"]), s_intervalom(r["s_kopijom"]["tocnost"], r["s_kopijom"]["tocnost_interval"]),
                      cijeli(r["bez_kopije"]["n"]), s_intervalom(r["bez_kopije"]["tocnost"], r["bez_kopije"]["tocnost_interval"]),
                      f"{bodovi(r['razlika'])} ({bodovi(r['razlika_interval'][0])} -- {bodovi(r['razlika_interval'][1])})"])
    tablica("curenje_kontrola", "lrrrrr", ["Ispitne slike\nu skupini duplikata", "Slika",
                                           "Kopija u učenju:\ntočnost, \\%", "Slika",
                                           "Kopija izvan učenja:\ntočnost, \\%", "Razlika,\nbodovi"], retci)


def znanstveni(x):
    m, e = f"{x:.0e}".split("e")
    return rf"\({m} \cdot 10^{{{int(e)}}}\)"


def postavke():
    st = torch.load(c.MODELI / "osnovna.pt", map_location="cpu", weights_only=True)["postavke"]
    postavi("postavke.velicina", c.VELICINA)
    velicina = M.transformacija_evaluacija().transforms[0].size
    postavi("postavke.smanjenje", velicina[0] if isinstance(velicina, (list, tuple)) else velicina)
    postavi("postavke.serija", c.SERIJA)
    postavi("postavke.udio_rasta", post(c.UDIO_RASTA, 0))
    postavi("postavke.lr", znanstveni(st["lr"]))
    postavi("postavke.tezinsko_slabljenje", znanstveni(c.TEZINSKO_SLABLJENJE))
    for vrsta in ["osnovna", "jaka"]:
        t = {type(x).__name__: x for x in M.transformacija_trening(vrsta).transforms}
        postavi(f"postavke.{vrsta}.izrez.od", post(t["RandomResizedCrop"].scale[0], 0))
        postavi(f"postavke.{vrsta}.izrez.do", post(t["RandomResizedCrop"].scale[1], 0))
        postavi(f"postavke.{vrsta}.omjer.od", dec(t["RandomResizedCrop"].ratio[0], 1))
        postavi(f"postavke.{vrsta}.omjer.do", dec(t["RandomResizedCrop"].ratio[1], 1))
    t = {type(x).__name__: x for x in M.transformacija_trening("jaka").transforms}
    postavi("postavke.jaka.randaugment.operacija", t["RandAugment"].num_ops)
    postavi("postavke.jaka.randaugment.jacina", t["RandAugment"].magnitude)
    postavi("postavke.jaka.zamucenje", post(t["RandomApply"].p, 0))
    postavi("postavke.jaka.sivo", post(t["RandomGrayscale"].p, 0))
    postavi("postavke.sjemena", len(UCENJA["osnovna"]))
    postavi("postavke.ucenja", sum(len(v) for v in UCENJA.values()))
    postavi("postavke.bootstrap", cijeli(E.BOOTSTRAP))
    postavi("postavke.razina_intervala", post((E.PERCENTILI[1] - E.PERCENTILI[0]) / 100, 0))
    postavi("postavke.ece_kosara", E.ECE_KOSARA)
    postavi("postavke.kalibracija_kosara", E.KALIBRACIJA_KOSARA)
    postavi("postavke.kalibracija_najmanje", E.KALIBRACIJA_NAJMANJE)
    postavi("postavke.pokrivenost_preskoci", E.POKRIVENOST_PRESKOCI)
    postavi("postavke.predmemorija", K1.MAX_STRANICA)
    postavi("postavke.kvaliteta_jpeg", K1.KVALITETA_JPEG)
    postavi("postavke.inacica", len(s.INACICE))
    postavi("postavke.omjer", omjer(K2.UDJELI))
    postavi("postavke.omjer_inat", omjer(K4.UDJELI))


def main():
    TABLICE.mkdir(exist_ok=True)
    SLIKE.mkdir(exist_ok=True)
    ciscenje()
    izvori_i_podjela()
    provjera_podjele()
    stvarne()
    ucenje_i_odabir()
    evaluacija()
    curenje()
    postavke()
    retci = [f"\\postavi{{{k}}}{{{v}}}" for k, v in sorted(brojke.items())]
    (c.REZULTATI / "brojke.tex").write_text(
        "% Stvara src/k11_izvoz.py; ne uređivati ručno.\n" + "\n".join(retci) + "\n", encoding="utf-8")
    print(f"{len(brojke)} brojki, tablice: {sorted(p.name for p in TABLICE.glob('*.tex'))}")


if __name__ == "__main__":
    main()
