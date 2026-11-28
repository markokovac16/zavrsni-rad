export const OPCENITO = 'opcenito'
export const OTROVNOST = 'otrovnost'
export const NAJVISE_ZNAKOVA = 200
const JEDNA = String.raw`(?:[[(]\s*C[0-9]{3}(?:\s*(?:[,;]|(?<![\p{L}\p{N}_])i(?![\p{L}\p{N}_]))\s*C[0-9]{3})*\s*[\])]|(?<![\p{L}\p{N}_])C[0-9]{3}(?![\p{L}\p{N}_]))`
const OZNAKA_U_TEKSTU = new RegExp(String.raw`\s*${JEDNA}(?:\s*(?:[,;]|(?<![\p{L}\p{N}_])i(?![\p{L}\p{N}_]))\s*${JEDNA})*|\*+`, 'gu')
const RAZMAK_PRIJE_ZNAKA = /\s+([.,;:!?])/g
const KRAJ_RECENICE = /(?<!\bnpr)(?<!\btj)(?<!\bitd)(?<!\bsl)(?<!\bspp)[.!?](?=\s+[A-ZČĆĐŠŽ]|\s*$)/g
const RIJEC = /[\p{L}\p{N}]/u
const preslovi = (slova, latinica) => [...slova].map((z, i) => [z, latinica[i]])
const CIRILICA = Object.fromEntries([
  ...preslovi('абвгдђежзијклљмнњопрстћуфхцчџшАБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШ', ['a', 'b', 'v', 'g', 'd', 'đ', 'e', 'ž', 'z', 'i', 'j', 'k', 'l', 'lj', 'm', 'n', 'nj', 'o', 'p', 'r', 's', 't', 'ć', 'u', 'f', 'h', 'c', 'č', 'dž', 'š',
    'A', 'B', 'V', 'G', 'D', 'Đ', 'E', 'Ž', 'Z', 'I', 'J', 'K', 'L', 'Lj', 'M', 'N', 'Nj', 'O', 'P', 'R', 'S', 'T', 'Ć', 'U', 'F', 'H', 'C', 'Č', 'Dž', 'Š']),
  ...preslovi('ёйщъыьэюяєіїґЁЙЩЪЫЬЭЮЯЄІЇҐ', ['jo', 'j', 'šč', '', 'y', '', 'e', 'ju', 'ja', 'je', 'i', 'ji', 'g', 'Jo', 'J', 'Šč', '', 'Y', '', 'E', 'Ju', 'Ja', 'Je', 'I', 'Ji', 'G']),
])
const jeOtrovnost = (f) => f.kategorija === OTROVNOST
export const brojRijeci = (tekst) => tekst.split(/\s+/).filter((r) => RIJEC.test(r)).length

export function odaberiCinjenice(cinjenice, vrsta) {
  const oVrsti = cinjenice.filter((f) => f.tema === vrsta)
  const zamijenjene = new Set(oVrsti.flatMap((f) => f.zamjenjuje ?? []))
  const opce = cinjenice.filter((f) => f.tema === OPCENITO && !zamijenjene.has(f.id))
  return { opce, oVrsti }
}

const blok = (cinjenice) => cinjenice.map((f) => `[${f.id}] (${f.kategorija}) ${f.cinjenica}`)

export function sloziUpit(vrsta, stanje, uvjeti, opce = null, oVrsti = null, otrovnost = null) {
  const dijelovi = []
  if (opce !== null) {
    dijelovi.push('OPĆE ČINJENICE', ...blok(opce), '')
    dijelovi.push(vrsta ? `ČINJENICE O VRSTI: ${vrsta}` : 'ČINJENICE O VRSTI: nema, vrsta nije odabrana', ...blok(oVrsti), '')
  }
  if (otrovnost?.length) dijelovi.push(`ČINJENICE O OTROVNOSTI: ${vrsta}`, ...blok(otrovnost), '')
  dijelovi.push('SLUČAJ', `stanje prema klasifikatoru: ${stanje}`, `vrsta biljke: ${vrsta || 'nije odabrana'}`)
  const navedeni = Object.entries(uvjeti)
    .map(([k, v]) => [k, [...(v ?? '').trim()].slice(0, NAJVISE_ZNAKOVA).join('')])
    .filter(([, v]) => v)
  if (navedeni.length) dijelovi.push('uvjeti koje je upisao korisnik:', ...navedeni.map(([k, v]) => `- ${k}: ${v}`))
  else dijelovi.push('uvjeti koje je upisao korisnik: nisu navedeni')
  return dijelovi.join('\n')
}

export function shema(predlosci, oznake = null, oznakeOtrovnosti = null, obaveznaOtrovnost = false) {
  const recenica = (dopustene) => {
    let svojstva = { tekst: { type: 'string' } }
    if (dopustene !== null) svojstva = { oznake: { type: 'array', items: { type: 'string', enum: [...dopustene].sort() } }, ...svojstva }
    return { type: 'object', properties: svojstva, required: Object.keys(svojstva), additionalProperties: false }
  }
  const popisi = Object.fromEntries(predlosci.dijelovi.map((d) => [d.kljuc, 'recenica']))
  const definicije = { recenica: recenica(oznake) }
  if (oznake === null) {
    if (obaveznaOtrovnost) popisi[OTROVNOST] = 'recenica'
  } else if (oznakeOtrovnosti?.length) {
    popisi[OTROVNOST] = 'recenica_otrovnost'
    definicije.recenica_otrovnost = recenica(oznakeOtrovnosti)
    obaveznaOtrovnost = true
  }
  const svojstva = Object.fromEntries(Object.entries(popisi).map(([k, v]) => [k, { type: 'array', items: { $ref: `#/$defs/${v}` } }]))
  if (obaveznaOtrovnost) svojstva[OTROVNOST].minItems = 1
  return {
    type: 'object',
    properties: svojstva,
    required: Object.keys(popisi),
    additionalProperties: false,
    $defs: definicije,
  }
}

const nelatinicni = (tekst) =>
  [...new Set([...tekst].filter((z) => /\p{L}/u.test(z) && !/\p{Script=Latin}/u.test(z)))].sort()

export function obradi(predlosci, sirovo, sBazom) {
  const dijelovi = {}
  const izbaceno = []
  const provjere = { bez_oznaka: 0, skraceno: 0, vise_oznaka: 0, vise_recenica: 0, ociscen_tekst: 0, preslovljeno: 0 }
  const popisi = [...predlosci.dijelovi, ...(OTROVNOST in sirovo ? [{ kljuc: OTROVNOST, najvise: 1 }] : [])]
  for (const d of popisi) {
    const recenice = []
    for (const r of sirovo[d.kljuc]) {
      const tekst = r.tekst.trim()
      let cisto = tekst.replace(OZNAKA_U_TEKSTU, '').replace(/\s{2,}/g, ' ').replace(RAZMAK_PRIJE_ZNAKA, '$1').trim()
      if (cisto !== tekst) provjere.ociscen_tekst += 1
      const latinica = [...cisto].map((z) => CIRILICA[z] ?? z).join('')
      if (latinica !== cisto) {
        provjere.preslovljeno += 1
        cisto = latinica
      }
      const oznake = [...new Set(r.oznake ?? [])]
      if (!cisto) continue
      if (sBazom && !oznake.length) {
        provjere.bez_oznaka += 1
        izbaceno.push({ dio: d.kljuc, tekst: cisto, razlog: 'bez oznake' })
        continue
      }
      if (oznake.length > predlosci.najvise_oznaka) provjere.vise_oznaka += 1
      if ((cisto.match(KRAJ_RECENICE) ?? []).length > 1) provjere.vise_recenica += 1
      recenice.push({ tekst: cisto, oznake })
    }
    for (const r of recenice.slice(d.najvise)) {
      provjere.skraceno += 1
      izbaceno.push({ dio: d.kljuc, tekst: r.tekst, razlog: 'previše rečenica' })
    }
    dijelovi[d.kljuc] = recenice.slice(0, d.najvise)
  }
  provjere.rijeci_modela = predlosci.dijelovi.flatMap((d) => dijelovi[d.kljuc]).reduce((n, r) => n + brojRijeci(r.tekst), 0)
  dijelovi.redovita_njega.push(...(dijelovi[OTROVNOST] ?? []).map((r) => ({ ...r, otrovnost: true })))
  delete dijelovi[OTROVNOST]
  provjere.nelatinicni_znakovi = nelatinicni(Object.values(dijelovi).flat().map((r) => r.tekst).join(' '))
  return { dijelovi, izbaceno, provjere }
}

const recenicaSustava = (tekst, oznake = [], oznaka = {}) => ({ tekst, oznake: [...oznake], sustav: true, ...oznaka })

export function dodajReceniceSustava(predlosci, dijelovi, vrsta, stanje, pouzdanost, oVrsti, sBazom) {
  const p = String(Math.floor(pouzdanost * 100 + 0.5))
  const [prva, ...ostale] = predlosci.stanje[stanje]
  const prve = [recenicaSustava(prva.replace('{p}', p), [], { stanje: true }), ...ostale.map((t) => recenicaSustava(t))]
  if (!vrsta) prve.push(recenicaSustava(predlosci.nepoznata_vrsta))
  dijelovi.procjena = [...prve, ...dijelovi.procjena]
  const oznaka = predlosci.otrovnost[vrsta]
  if (sBazom && oznaka && !dijelovi.redovita_njega.some((r) => r.otrovnost)) {
    const f = oVrsti.find((f) => f.id === oznaka)
    dijelovi.redovita_njega.push(recenicaSustava(f.cinjenica, [oznaka], { otrovnost: true }))
  }
  dijelovi.kada_potraziti_pomoc.push(recenicaSustava(predlosci.strucnjak))
  return dijelovi
}

export function sloziTekst(predlosci, dijelovi) {
  const odlomci = []
  for (const d of predlosci.dijelovi) {
    const recenice = dijelovi[d.kljuc].map((r) => r.tekst + (r.oznake.length ? ` [${r.oznake.join(', ')}]` : ''))
    if (recenice.length) odlomci.push(`**${d.naslov}**\n` + recenice.join(' '))
  }
  return odlomci.join('\n\n')
}

export function pripremi(cinjenice, predlosci, sustav, vrsta, stanje, uvjeti) {
  const { opce, oVrsti } = odaberiCinjenice(cinjenice, vrsta)
  const njega = oVrsti.filter((f) => !jeOtrovnost(f))
  const otrovnost = oVrsti.filter(jeOtrovnost)
  return {
    opce,
    oVrsti,
    sustav,
    upit: sloziUpit(vrsta, stanje, uvjeti, opce, njega, otrovnost),
    shema: shema(predlosci, [...opce, ...njega].map((f) => f.id), otrovnost.map((f) => f.id)),
  }
}

export function zavrsi(predlosci, sirovo, vrsta, stanje, pouzdanost, opce, oVrsti, sBazom = true) {
  const { dijelovi: obradeni, izbaceno, provjere } = obradi(predlosci, sirovo, sBazom)
  const dijelovi = dodajReceniceSustava(predlosci, obradeni, vrsta, stanje, pouzdanost, oVrsti, sBazom)
  provjere.dodana_otrovnost = dijelovi.redovita_njega.filter((r) => r.sustav && r.otrovnost).length
  const poId = Object.fromEntries([...opce, ...oVrsti].map((f) => [f.id, f]))
  const navedene = [...new Set(Object.values(dijelovi).flat().flatMap((r) => r.oznake))].sort()
  const izvori = navedene.map((id) => {
    const { izvor, url, cinjenica } = poId[id]
    return { id, izvor, url, cinjenica }
  })
  return { tekst: sloziTekst(predlosci, dijelovi), dijelovi, izvori, izbaceno, provjere }
}
