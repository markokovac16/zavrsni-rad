<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import * as demo from './demo/api.js'
import { NAJVISE_ZNAKOVA } from './demo/preporuka.js'

const vrste = ref([])
const prag = ref(null)
const datoteka = ref(null)
const pregled = ref('')
const obrazac = ref({ vrsta: '', svjetlo: '', zalijevanje: '', prostorija: '' })
const rezultat = ref(null)
const ucitavanje = ref(false)
const greska = ref('')
const povlacenje = ref(false)
const odjeljakRezultat = ref(null)

onMounted(() => {
  try {
    ;({ vrste: vrste.value, prag: prag.value } = demo.postavke())
  } catch (e) {
    greska.value = e.message
  }
})

function postaviSliku(f) {
  if (!f || !f.type.startsWith('image/')) return
  datoteka.value = f
  if (pregled.value) URL.revokeObjectURL(pregled.value)
  pregled.value = URL.createObjectURL(f)
  rezultat.value = null
}

const odabranaSlika = (dogadaj) => postaviSliku(dogadaj.target.files[0])

function ispustenaSlika(dogadaj) {
  povlacenje.value = false
  postaviSliku(dogadaj.dataTransfer.files[0])
}

async function analiziraj() {
  if (!datoteka.value || prag.value === null) return
  ucitavanje.value = true
  greska.value = ''
  rezultat.value = null
  try {
    rezultat.value = await demo.analiziraj(obrazac.value, prag.value)
    await nextTick()
    const bezAnimacije = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    odjeljakRezultat.value?.scrollIntoView({ behavior: bezAnimacije ? 'auto' : 'smooth', block: 'start' })
  } catch (e) {
    greska.value = e.message
  } finally {
    ucitavanje.value = false
  }
}

const opisStanja = computed(() => ({
  zdrava: 'Biljka izgleda zdravo',
  nezdrava: 'Biljka pokazuje znakove bolesti ili oštećenja',
  nesigurno: 'Sustav nije siguran u procjenu',
}[rezultat.value?.stanje]))

const naTraci = (x) => `${Math.max(0, Math.min(1, (x - 0.5) / 0.5)) * 100}%`

const odjeljci = computed(() => {
  if (!rezultat.value?.preporuka) return []
  const redniBroj = Object.fromEntries(rezultat.value.izvori.map((izvor, i) => [izvor.id, i + 1]))
  return rezultat.value.odjeljci.map((o) => ({
    naslov: o.naslov,
    recenice: o.recenice.map((r) => ({ tekst: r.tekst, brojevi: r.oznake.map((i) => redniBroj[i]).filter(Boolean) })),
  }))
})

const postotak = (x) => `${Math.round(x * 100)} %`
</script>

<template>
  <header class="traka">
    <div class="sadrzaj traka-sadrzaj">
      <span class="znak">
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path d="M5 19c0-8 5-14 15-14 0 10-6 15-14 15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M5 19 13 11" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        Njega biljaka
      </span>
    </div>
  </header>

  <div class="sadrzaj">
    <div class="uvod">
      <h1>Procjena stanja i preporuka za njegu</h1>
      <p>Učitajte fotografiju sobne biljke. Sustav procjenjuje je li zdrava i daje preporuku za njegu s navedenim izvorima.</p>
    </div>

    <main>
      <section class="kartica" aria-label="Podaci za analizu">
        <div class="obrazac">
          <div class="stupac">
            <h2 class="korak" id="oznaka-fotografija"><span class="broj">1</span>Fotografija</h2>
            <label
              class="ucitaj"
              :class="{ ima: pregled, povlacenje }"
              @dragover.prevent="povlacenje = true"
              @dragleave="povlacenje = false"
              @drop.prevent="ispustenaSlika"
            >
              <input type="file" accept="image/*" aria-labelledby="oznaka-fotografija" aria-describedby="uputa-fotografija" @change="odabranaSlika" />
              <img v-if="pregled" :src="pregled" alt="Odabrana fotografija" />
              <span v-else class="ucitaj-prazno">
                <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
                  <rect x="3" y="4" width="18" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.5" />
                  <circle cx="9" cy="10" r="1.8" fill="none" stroke="currentColor" stroke-width="1.5" />
                  <path d="m4 18 5-5 4 4 3-3 4 4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
                </svg>
                <span class="ucitaj-poziv">Odaberite ili snimite fotografiju</span>
                <span class="ucitaj-sporedno">ili je povucite ovamo</span>
              </span>
            </label>
            <p id="uputa-fotografija" class="uputa">
              <template v-if="pregled">Kliknite fotografiju ili povucite drugu da biste je zamijenili.</template>
              <template v-else>JPG ili PNG, najviše 10 MB. Najbolje je da list ili biljka ispunjava kadar.</template>
            </p>
          </div>

          <fieldset class="stupac polja">
            <legend class="korak"><span class="broj">2</span>O biljci i uzgoju <span class="neobavezno">neobavezno</span></legend>
            <label>Vrsta biljke
              <select v-model="obrazac.vrsta">
                <option value="">ne znam</option>
                <option v-for="v in vrste" :key="v" :value="v">{{ v }}</option>
              </select>
            </label>
            <label>Svjetlo
              <input v-model="obrazac.svjetlo" :maxlength="NAJVISE_ZNAKOVA" placeholder="npr. istočni prozor, bez izravnog sunca" />
            </label>
            <label>Zalijevanje
              <input v-model="obrazac.zalijevanje" :maxlength="NAJVISE_ZNAKOVA" placeholder="npr. jednom tjedno" />
            </label>
            <label>Prostorija
              <input v-model="obrazac.prostorija" :maxlength="NAJVISE_ZNAKOVA" placeholder="npr. dnevni boravak, pokraj radijatora" />
            </label>
          </fieldset>
        </div>

        <div class="kartica-dno">
          <p class="uputa">
            <template v-if="!datoteka">Za analizu je potrebna fotografija.</template>
          </p>
          <button :disabled="!datoteka || ucitavanje" :aria-busy="ucitavanje" @click="analiziraj">
            <span v-if="ucitavanje" class="vrtuljak" aria-hidden="true"></span>
            {{ ucitavanje ? 'Analiziram…' : 'Analiziraj' }}
          </button>
        </div>
      </section>

      <div aria-live="polite">
        <p v-if="greska" class="greska" role="alert">{{ greska }}</p>

        <section v-if="rezultat" ref="odjeljakRezultat" class="kartica rezultat" aria-labelledby="naslov-rezultat">
          <div class="stanje" :class="rezultat.stanje">
            <div>
              <p class="korak-oznaka"><span class="broj">3</span>Rezultat</p>
              <h2 id="naslov-rezultat">{{ opisStanja }}</h2>
            </div>
            <div class="mjerilo">
              <div class="mjerilo-traka" aria-hidden="true">
                <div class="mjerilo-vrijednost" :style="{ width: naTraci(rezultat.pouzdanost) }"></div>
                <div class="mjerilo-prag" :style="{ left: naTraci(rezultat.prag) }"></div>
              </div>
              <p class="mjerilo-brojke">
                <span>pouzdanost <strong>{{ postotak(rezultat.pouzdanost) }}</strong></span>
                <span class="prag-oznaka" :style="{ left: naTraci(rezultat.prag) }">prag {{ postotak(rezultat.prag) }}</span>
              </p>
            </div>
          </div>

          <div class="rezultat-tijelo">
            <p v-if="rezultat.greska" class="greska">{{ rezultat.greska }}</p>

            <div class="preporuka">
              <article v-for="o in odjeljci" :key="o.naslov" class="odjeljak">
                <h3>{{ o.naslov }}</h3>
                <div>
                  <p>
                    <template v-for="(r, j) in o.recenice" :key="j">{{ j ? ' ' : '' }}{{ r.tekst }}<sup v-if="r.brojevi.length" class="poziv"><template v-for="(b, k) in r.brojevi" :key="b"><a :href="`#izvor-${b}`" :aria-label="`izvor ${b}`">{{ b }}</a><template v-if="k < r.brojevi.length - 1">,</template></template></sup></template>
                  </p>
                </div>
              </article>
            </div>

            <details v-if="rezultat.preporuka" class="izvori" open>
              <summary>Izvori<template v-if="rezultat.izvori.length"> ({{ rezultat.izvori.length }})</template></summary>
              <p v-if="!rezultat.izvori.length" class="izvori-uskoro">Plan je da imam bazu izvora, opcija B je da LLM pretraži web i navede stranice koje je pronašao.</p>
              <ol v-else>
                <li v-for="(izvor, i) in rezultat.izvori" :id="`izvor-${i + 1}`" :key="izvor.id">
                  {{ izvor.cinjenica }}
                  <a :href="izvor.url" target="_blank" rel="noopener">{{ izvor.izvor }}</a>
                </li>
              </ol>
            </details>
          </div>

        </section>
      </div>
    </main>

  </div>
</template>
