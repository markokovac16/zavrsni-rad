import Anthropic from '@anthropic-ai/sdk'
import postavkeDemo from './postavke.json'
import cinjenice from '../../../znanje/cinjenice.json'
import predlosci from '../../../znanje/predlosci.json'
import sustav from '../../../znanje/sustav.md?raw'
import { pripremi, zavrsi } from './preporuka.js'

export function postavke() {
  if (!__KLJUC__) throw new Error('Nema API ključa: u projekt/.env treba postaviti CLAUDE_API_KEY i pokrenuti pnpm dev.')
  return postavkeDemo
}

const izmedu = (a, b) => a + Math.random() * (b - a)

export function nasumicanRezultat(prag) {
  const stanje = ['zdrava', 'nezdrava', 'nesigurno'][Math.floor(Math.random() * 3)]
  const pouzdanost = stanje === 'nesigurno' ? izmedu(0.5, prag) : izmedu(prag, 0.995)
  const nezdravaJeVeca = stanje === 'nezdrava' || (stanje === 'nesigurno' && Math.random() < 0.5)
  return { stanje, pouzdanost, vjerojatnost_nezdrave: nezdravaJeVeca ? pouzdanost : 1 - pouzdanost, prag }
}

const klijent = new Anthropic({ apiKey: __KLJUC__, dangerouslyAllowBrowser: true })

export async function analiziraj(obrazac, prag) {
  const rezultat = nasumicanRezultat(prag)
  const { vrsta, ...uvjeti } = obrazac
  const p = pripremi(cinjenice, predlosci, sustav.trim(), vrsta || null, rezultat.stanje, uvjeti)

  let sirovo
  try {
    const odgovor = await klijent.messages.create({
      model: __MODEL__,
      max_tokens: 1500,
      thinking: { type: 'disabled' },
      output_config: { format: { type: 'json_schema', schema: p.shema } },
      system: p.sustav,
      messages: [{ role: 'user', content: p.upit }],
    })
    if (odgovor.stop_reason !== 'end_turn') throw new Error(odgovor.stop_reason)
    sirovo = JSON.parse(odgovor.content.filter((b) => b.type === 'text').map((b) => b.text).join(''))
  } catch (e) {
    return { ...rezultat, preporuka: null, izvori: [], greska: `Preporuka nije dostupna: ${e.status ?? e.message ?? e.name}` }
  }

  const r = zavrsi(predlosci, sirovo, vrsta || null, rezultat.stanje, rezultat.pouzdanost, p.opce, p.oVrsti)
  return { ...rezultat, preporuka: r.tekst, izvori: r.izvori }
}
