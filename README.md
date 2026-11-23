# Sustav za detekciju bolesti i preporuku njege biljaka

Programski dio završnog rada (Fakultet informatike u Puli, mentor doc. dr. sc. Sandi Baressi Šegota).

Sustav iz fotografije sobne biljke procjenjuje je li biljka **zdrava** ili **nezdrava**, a zatim jezičnim
modelom sastavlja preporuku za njegu na hrvatskom. Ako klasifikator nije dovoljno siguran, sustav to kaže i
daje samo opće savjete.

## Sadržaj

| Mapa | Što sadrži |
| --- | --- |
| `src/` | priprema podataka, učenje i evaluacija klasifikatora (Python) |
| `rezultati/` | rezultati pokretanja (JSON) i slike za rad (`rezultati/slike/`) |
| `web/` | sučelje (Vue + Vite) |
| `znanje/` | baza činjenica o njezi s izvorima (`cinjenice.json`) |
| `alati/` | alat za ručnu provjeru oznaka fotografija |

## Pokretanje sučelja

Potrebni su Node.js i pnpm. U `.env` (u korijenu repozitorija, nije u gitu) postavlja se ključ jezičnog modela:

```
CLAUDE_API_KEY=...
CLAUDE_MODEL=claude-haiku-5-5
```

```bash
pnpm --dir web install
pnpm --dir web dev
```

Ključ se čita samo u razvojnom načinu (`pnpm dev`) i ne ulazi u izgrađenu inačicu.

## Podaci i koraci

Slike se ne nalaze u repozitoriju (veličina i licence skupova). Preuzimaju se u `data/raw/`; koja mapa kojeg
skupa daje koju vrstu i oznaku zapisano je u `src/config.py`.

Potreban je [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run src/k01_manifest.py            # popis slika, sažeci, smanjene kopije
uv run src/k02_ciscenje_i_podjela.py  # uklanjanje duplikata; podjela po skupinama srodnih slika
uv run src/k03_provjera_podjele.py    # što je od srodnih slika ipak ostalo s obje strane podjele
```

### Stvarne fotografije (iNaturalist)

Fotografije uzgojenih biljaka s iNaturalista (`data/raw/inaturalist_uzgojene/`, licence CC0, CC BY i
CC BY-SA) nemaju oznaku zdravlja. Oznake u `oznake/prijedlozi_modela.csv` predložio je jezični model
(`claude-haiku-5-5`, 6. 11. 2026.) gledajući svaku fotografiju: zdrava, nezdrava, nejasna ili neupotrebljiva.
To su **slabe oznake**, a ne provjerene; nejasne i neupotrebljive fotografije se izostavljaju.

```bash
uv run src/k04_stvarne_fotografije.py
```

Fotografije se dijele po autoru opažanja (učenje 60 %, validacija 15 %, test 25 %), jer isti autor često
snima istu biljku više puta. Za testni dio stvara se `alati/provjera_oznaka.html` (otvara se u pregledniku;
oznake jezičnog modela se u alatu ne vide). Izvezena datoteka `provjerene.csv` sprema se u `oznake/`.

### Klasifikator

Učenje klasifikatora (oko 17 min po modelu na Apple M5); svaka inačica uči se s tri sjemena:

```bash
uv run src/k05_trening.py --naziv osnovni
uv run src/k05_trening.py --naziv osnovni_s1 --sjeme 1
uv run src/k05_trening.py --naziv osnovni_s2 --sjeme 2
uv run src/k05_trening.py --naziv jaka --augmentacija jaka         # i jaka_s1, jaka_s2
```

Odabir glavnog modela (inačica s većim prosječnim makro F1 na validaciji) i evaluacija:

```bash
uv run src/k06_odabir_modela.py
uv run src/k07_evaluacija.py    # metrike, kalibracija, prag pouzdanosti, slike primjera
```
