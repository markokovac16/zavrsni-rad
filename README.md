# Sustav za detekciju bolesti i preporuku njege biljaka

Programski dio završnog rada (Fakultet informatike u Puli, mentor doc. dr. sc. Sandi Baressi Šegota).

Sustav iz fotografije sobne biljke procjenjuje je li biljka **zdrava** ili **nezdrava**, a zatim jezičnim
modelom sastavlja preporuku za njegu na hrvatskom. Ako klasifikator nije dovoljno siguran, sustav to kaže i
daje samo opće savjete.

## Sadržaj

| Mapa | Što sadrži |
| --- | --- |
| `src/` | priprema podataka, učenje i evaluacija klasifikatora, preporuke o njezi (Python) |
| `rezultati/` | rezultati pokretanja (JSON) i slike za rad (`rezultati/slike/`) |
| `web/` | sučelje (Vue + Vite) |
| `znanje/` | baza činjenica o njezi s izvorima (`cinjenice.json`) |
| `alati/` | alat za ručnu provjeru oznaka fotografija |
| `oznake/` | slabe oznake stvarnih fotografija (prijedlozi jezičnog modela) i ručno provjerene oznake |

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

Oznake su nastale jednokratno i skripta nije dio repozitorija; izvor oznaka je sama datoteka. Postupak: svaka
fotografija smanjena je na najviše 768 px i poslana modelu s uputom ispod, a odgovor je strukturiran (oznaka i
kratko obrazloženje, stupci `label` i `reason`). Fotografije za koje model nije vratio odgovor poslane su
ponovno.

<details>
<summary>Uputa jezičnom modelu</summary>

```text
This photo should show a cultivated {species}. Judge the plant's health from what is visible.
- healthy: no visible problems. Natural leaf spots or variegation, naturally light or lime-green varieties (e.g. 'Neon' pothos) and a single old dry leaf at the base are normal.
- unhealthy: clear signs such as yellow or brown leaves, dry brown tips, spots or lesions, rot, wilting or drooping, pests, sunburn, or stretched pale growth.
- unclear: the plant is too small, blurry or hidden to judge.
- unusable: the {species} is not clearly the main subject (e.g. many plants, a different species, a drawing).
In "reason", name the visible signs in a few words.
```

`{species}`: pothos (*Epipremnum aureum*), snake plant (*Dracaena trifasciata*), spider plant
(*Chlorophytum comosum*), aloe vera.
</details>

```bash
uv run src/k04_stvarne_fotografije.py
```

Fotografije se dijele po autoru opažanja (učenje 60 %, validacija 15 %, test 25 %), jer isti autor često
snima istu biljku više puta. Za testni dio stvara se `alati/provjera_oznaka.html` (otvara se u pregledniku;
oznake jezičnog modela se u alatu ne vide). Izvezena datoteka `provjerene.csv` sprema se u `oznake/`.

### Klasifikator

Učenje klasifikatora (oko 17 min po modelu na Apple M5); svaka inačica uči se s tri sjemena:

```bash
uv run src/k05_trening.py --naziv osnovna
uv run src/k05_trening.py --naziv osnovna_s1 --sjeme 1
uv run src/k05_trening.py --naziv osnovna_s2 --sjeme 2
uv run src/k05_trening.py --naziv jaka --augmentacija jaka         # i jaka_s1, jaka_s2
```

Odabir glavnog modela (inačica s većim prosječnim makro F1 na validaciji) i evaluacija:

```bash
uv run src/k06_odabir_modela.py
uv run src/k07_evaluacija.py                  # glavni model: metrike, kalibracija, prag pouzdanosti, slike
uv run src/k07_evaluacija.py --naziv jaka     # druga inačica s prvim sjemenom
uv run src/k07_evaluacija.py --naziv osnovna_s1 --bez-slika   # i osnovna_s2, jaka_s1, jaka_s2 (rasponi po sjemenu)
```

Učinak curenja podataka: isti model učen na podjeli bez uklanjanja duplikata (`manifest_naivni.csv`, stvara
ga korak 2). Točnost na testu računa se posebno za slike koje imaju duplikat u skupu za učenje i za one koje ga
nemaju. Glavna je usporedba unutar skupina duplikata: je li kopija ispitne slike pala u skup za učenje odlučila je
nasumična podjela, pa slike čija je kopija izvan skupa za učenje služe kao kontrola:

```bash
uv run src/k05_trening.py --naziv naivni --manifest manifest_naivni.csv
uv run src/k07_evaluacija.py --naziv naivni --manifest manifest_naivni.csv
uv run src/k08_curenje.py
```

Ocjena na ispitnim fotografijama s iNaturalista (635 fotografija, 202 autora). Ocjenjuju se modeli učeni samo na
skupovima podataka, svih šest učenja, s temperaturom i pragom pouzdanosti iz koraka 7. Dok ručne provjere nema,
rezultat je slaganje s prijedlozima jezičnog modela, a ne točnost. Kad postoji `oznake/provjerene.csv`, isti se
modeli ocjenjuju i na provjerenim oznakama, a računa se i slaganje čovjeka i jezičnog modela (Cohenova kappa).
Intervali se računaju bootstrapom po autoru, jer isti autor često snima istu biljku više puta:

```bash
uv run src/k09_stvarne_evaluacija.py
```

### Preporuke o njezi

`src/preporuke.py` sastavlja preporuku pozivom jezičnog modela (ključ i model iz `.env`, isto kao za sučelje).
Model dobiva stanje iz klasifikatora (zdrava, nezdrava ili nesigurno), vrstu, uvjete uzgoja koje je unio korisnik i
činjenice iz `znanje/cinjenice.json`: opće, one o njezi odabrane vrste i one o njezinoj otrovnosti, u tri bloka. Ne
dobiva fotografiju, pouzdanost klasifikatora ni opće činjenice koje činjenica o vrsti zamjenjuje (polje `zamjenjuje`).

Odgovor je JSON po shemi (strukturirani izlaz): četiri popisa rečenica (procjena, što napraviti sada, redovita njega,
kada potražiti pomoć) i, kad je vrsta odabrana, popis s jednom rečenicom o otrovnosti; svaka rečenica ima oznake
činjenica (npr. `C012`) i tekst. Shema dopušta samo oznake priloženih činjenica, a u popisu o otrovnosti samo oznake
činjenica o otrovnosti. Program zatim izbacuje rečenice bez oznake, odsijeca višak rečenica, preslovljava ćirilicu u
latinicu, rečenicu o otrovnosti stavlja na kraj redovite njege i dodaje rečenice koje uvijek moraju biti točne:
rezultat klasifikatora s pouzdanošću, napomenu kad procjena nije pouzdana ili vrsta nije odabrana i uputu stručnjaku.
Ako model za vrstu s podatkom o otrovnosti ne napiše rečenicu o otrovnosti, program dodaje tu činjenicu iz baze. Uputa
modelu je u `znanje/sustav.md`, stalne rečenice u `znanje/predlosci.json`. Sučelje (`web/src/demo/preporuka.js`)
koristi iste datoteke i isti postupak. U inačici bez baze (`znanje/sustav_bez_baze.md`, samo za usporedbu u koraku
10) rečenicu o otrovnosti model piše iz vlastitog znanja, u istom zasebnom popisu. Primjer s jednom alojom:

```bash
uv run src/preporuke.py
```

### Ocjena preporuka

Korak 10 piše preporuke za unaprijed zadane scenarije (vrsta, stanje, uvjeti uzgoja) u tri inačice: s bazom
činjenica, bez nje (`znanje/sustav_bez_baze.md`) i prvom inačicom sa slobodnim tekstom (`src/preporuke_tekst.py`,
oznake u uglatim zagradama, ista baza), koja služi kao osnovica. Scenariji su u dva skupa. Na **razvojnim** (24: šest
vrsta i nepoznata vrsta u sva tri stanja, te upute u uvjetima, prazni uvjeti i simptom u uvjetima) uputa se smije
mijenjati; svaki se pokreće tri puta, jer odgovori modela nisu ponovljivi. **Ispitni** (39: šest vrsta u tri stanja,
svaka s dva vlastita skupa uvjeta, nepovoljnim i povoljnim, i nepoznata vrsta u tri stanja, jednom bez uvjeta; s
tekstovima uvjeta kojih u razvojnim nema) pokreću se jednom, kad je uputa konačna, i njih ocjenjuju ocjenjivači. Automatske provjere mjere oblik: broj rečenica i riječi, rečenice dulje od 20 riječi i
rečenice bez oznake, znakove izvan latinice u odgovoru modela, istu oznaku u više dijelova (osim uzroka iz procjene
i radnje u „što napraviti“), rečenicu o otrovnosti (postoji li, odgovara li na pitanje, je li dulja od 20 riječi),
ime izvora u tekstu te, kao gruba pravila, spominjanje klasifikatora, ponavljanje
stanja biljke ili upute stručnjaku, naziv vrste ponovljen više puta i u svakoj rečenici, tvrdnju da su zelenčica ili hibiskus otrovni
(ASPCA ih navodi kao netoksične; za hibiskus stranica navodi *Hibiscus syriacus*) i opću činjenicu tamo gdje postoji činjenica o vrsti iste kategorije. U dvjema strukturiranim
inačicama rečenice koje dodaje program i rečenica o otrovnosti ne broje se među rečenicama modela. Podupire li činjenica rečenicu, provjerava se ručno (obrazac `*_potkrijepljenost.csv`). Rezultati su u
`rezultati/preporuke/`; ime razvojne datoteke sadrži sažetak upute, baze, koda preporuke, scenarija i modela, pa svaka izmjena upute dobiva
svoju datoteku:

```bash
uv run src/k10_evaluacija_preporuka.py                 # razvojni scenariji, svaki 3 puta
uv run src/k10_evaluacija_preporuka.py --ispitni       # ispitni scenariji, jednom
uv run src/k10_evaluacija_preporuka.py --samo-pokazatelji razvojni_<inačica>.json   # bez novih poziva
uv run src/k10_evaluacija_preporuka.py --dopuni razvojni_<inačica>.json            # ponovi samo neuspjele pozive
```

### Brojke za tekst rada

Korak 11 iz rezultata koraka 1–8 zapisuje `rezultati/brojke.tex` (sve brojke koje tekst rada koristi),
tablice u `rezultati/tablice/` i sliku primjera podataka. Treba mu i `rezultati/odabrani_model_prva_podjela.json`,
odabir modela na prvoj inačici podjele (prije pravila istog imena i prije nego što su 13-znamenkasti brojevi u
imenima prestali vrijediti kao vrijeme snimanja), koji je spremljen kakav je bio:

```bash
uv run src/k11_izvoz.py
```
