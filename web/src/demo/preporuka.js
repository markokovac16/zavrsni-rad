export const OPCENITO = 'opcenito'
export const OTROVNOST = 'otrovnost'
export const NAJVISE_ZNAKOVA = 200
const OZNAKA_U_TEKSTU = /\[?\bC\d{3}\b\]?|\*+/g
const KRAJ_RECENICE = /(?<!\bnpr)(?<!\btj)(?<!\bitd)(?<!\bsl)[.!?](?:\s|$)/g
const CIRILICA = Object.fromEntries(
  [...'абвгдђежзијклљмнњопрстћуфхцчџшАБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШ'].map((z, i) => [
    z,
    ['a', 'b', 'v', 'g', 'd', 'đ', 'e', 'ž', 'z', 'i', 'j', 'k', 'l', 'lj', 'm', 'n', 'nj', 'o', 'p', 'r', 's', 't', 'ć', 'u', 'f', 'h', 'c', 'č', 'dž', 'š',
      'A', 'B', 'V', 'G', 'D', 'Đ', 'E', 'Ž', 'Z', 'I', 'J', 'K', 'L', 'Lj', 'M', 'N', 'Nj', 'O', 'P', 'R', 'S', 'T', 'Ć', 'U', 'F', 'H', 'C', 'Č', 'Dž', 'Š'][i],
  ]),
)

export function odaberiCinjenice(cinjenice, vrsta) {
  const oVrsti = cinjenice.filter((f) => f.tema === vrsta)
  const zamijenjene = new Set(oVrsti.flatMap((f) => f.zamjenjuje ?? []))
  const opce = cinjenice.filter((f) => f.tema === OPCENITO && !zamijenjene.has(f.id))
  return { opce, oVrsti }
}

const blok = (cinjenice) => cinjenice.map((f) => `[${f.id}] (${f.kategorija}) ${f.cinjenica}`)

export function sloziUpit(vrsta, stanje, uvjeti, opce = null, oVrsti = null) {
  const dijelovi = []
  if (opce !== null) {
    dijelovi.push('OPĆE ČINJENICE', ...blok(opce), '')
    dijelovi.push(vrsta ? `ČINJENICE O VRSTI: ${vrsta}` : 'ČINJENICE O VRSTI: nema, vrsta nije odabrana', ...blok(oVrsti), '')
  }
  dijelovi.push('SLUČAJ', `stanje prema klasifikatoru: ${stanje}`, `vrsta biljke: ${vrsta || 'nije odabrana'}`)
  const navedeni = Object.entries(uvjeti)
    .map(([k, v]) => [k, (v ?? '').trim().slice(0, NAJVISE_ZNAKOVA)])
    .filter(([, v]) => v)
  if (navedeni.length) dijelovi.push('uvjeti koje je upisao korisnik:', ...navedeni.map(([k, v]) => `- ${k}: ${v}`))
  else dijelovi.push('uvjeti koje je upisao korisnik: nisu navedeni')
  return dijelovi.join('\n')
}

export function shema(predlosci, oznake = null) {
  let svojstva = { tekst: { type: 'string' } }
  if (oznake !== null) svojstva = { oznake: { type: 'array', items: { type: 'string', enum: [...oznake].sort() } }, ...svojstva }
  return {
    type: 'object',
    properties: Object.fromEntries(predlosci.dijelovi.map((d) => [d.kljuc, { type: 'array', items: { $ref: '#/$defs/recenica' } }])),
    required: predlosci.dijelovi.map((d) => d.kljuc),
    additionalProperties: false,
    $defs: { recenica: { type: 'object', properties: svojstva, required: Object.keys(svojstva), additionalProperties: false } },
  }
}

const nelatinicni = (tekst) =>
  [...new Set([...tekst].filter((z) => /\p{L}/u.test(z) && !/\p{Script=Latin}/u.test(z)))].sort()

export function obradi(predlosci, sirovo, sBazom) {
  const dijelovi = {}
  const izbaceno = []
  const provjere = { bez_oznaka: 0, skraceno: 0, vise_oznaka: 0, vise_recenica: 0, ociscen_tekst: 0, preslovljeno: 0 }
  for (const d of predlosci.dijelovi) {
    const recenice = []
    for (const r of sirovo[d.kljuc]) {
      const tekst = r.tekst.trim()
      let cisto = tekst.replace(OZNAKA_U_TEKSTU, '').replace(/\s{2,}/g, ' ').trim()
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
  const tekstovi = Object.values(dijelovi).flat().map((r) => r.tekst)
  provjere.rijeci_modela = tekstovi.reduce((n, t) => n + t.split(/\s+/).filter(Boolean).length, 0)
  provjere.nelatinicni_znakovi = nelatinicni(tekstovi.join(' '))
  return { dijelovi, izbaceno, provjere }
}

const recenicaSustava = (tekst, oznake = []) => ({ tekst, oznake: [...oznake], sustav: true })

export function dodajReceniceSustava(predlosci, dijelovi, vrsta, stanje, pouzdanost, oVrsti, sBazom) {
  const prve = [recenicaSustava(predlosci.stanje[stanje].replace('{p}', String(Math.round(pouzdanost * 100))))]
  if (!vrsta) prve.push(recenicaSustava(predlosci.nepoznata_vrsta))
  dijelovi.procjena = [...prve, ...dijelovi.procjena]
  const oznaka = predlosci.otrovnost[vrsta]
  if (sBazom && oznaka) {
    const f = oVrsti.find((f) => f.id === oznaka)
    dijelovi.redovita_njega.push(recenicaSustava(f.cinjenica, [oznaka]))
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
  const zaModel = oVrsti.filter((f) => f.kategorija !== OTROVNOST)
  return {
    opce,
    oVrsti,
    sustav,
    upit: sloziUpit(vrsta, stanje, uvjeti, opce, zaModel),
    shema: shema(predlosci, [...opce, ...zaModel].map((f) => f.id)),
  }
}

export function zavrsi(predlosci, sirovo, vrsta, stanje, pouzdanost, opce, oVrsti, sBazom = true) {
  const { dijelovi: obradeni, izbaceno, provjere } = obradi(predlosci, sirovo, sBazom)
  const dijelovi = dodajReceniceSustava(predlosci, obradeni, vrsta, stanje, pouzdanost, oVrsti, sBazom)
  const poId = Object.fromEntries([...opce, ...oVrsti].map((f) => [f.id, f]))
  const navedene = [...new Set(Object.values(dijelovi).flat().flatMap((r) => r.oznake))].sort()
  const izvori = navedene.map((id) => {
    const { izvor, url, cinjenica } = poId[id]
    return { id, izvor, url, cinjenica }
  })
  return { tekst: sloziTekst(predlosci, dijelovi), dijelovi, izvori, izbaceno, provjere }
}
