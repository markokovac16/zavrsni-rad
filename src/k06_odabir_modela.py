"""Korak 6: odabir glavnog modela prema prosječnom makro F1 na validaciji."""
import json

import config as c

INACICE = {
    "osnovni": ["osnovni", "osnovni_s1", "osnovni_s2"],
    "jaka": ["jaka", "jaka_s1", "jaka_s2"],
}


def najbolji_val(naziv):
    povijest = json.loads((c.REZULTATI / f"povijest_{naziv}.json").read_text())
    return max(r["makro_f1_val"] for r in povijest)


def main():
    rez = {}
    for inacica, ucenja in INACICE.items():
        vrijednosti = {u: najbolji_val(u) for u in ucenja}
        rez[inacica] = dict(po_sjemenu=vrijednosti, prosjek=sum(vrijednosti.values()) / len(vrijednosti),
                            najmanji=min(vrijednosti.values()), najveci=max(vrijednosti.values()))
        print(f"{inacica:8s} prosjek {rez[inacica]['prosjek']:.4f}  "
              f"({rez[inacica]['najmanji']:.4f}–{rez[inacica]['najveci']:.4f})")
    glavni = max(rez, key=lambda k: rez[k]["prosjek"])
    (c.REZULTATI / "odabrani_model.json").write_text(
        json.dumps(dict(naziv=glavni, mjerilo="prosječni makro F1 na validaciji", inacice=rez), indent=1))
    print(f"glavni model: {glavni}")


if __name__ == "__main__":
    main()
