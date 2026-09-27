/**
 * Problem 11 — drives the live site in a real browser and captures the three
 * checks for output/app_check.html.
 *
 * Both servers must already be running:
 *   backend : uvicorn main:app --reload --port 8000   (from backend/)
 *   frontend: npm run dev                             (from frontend/)
 *
 * Run: node scripts/app_check.mjs
 */

import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const OUT = resolve(HERE, '../../output/app_check_images')
const BASE = 'http://localhost:5173'

mkdirSync(OUT, { recursive: true })

/** Wait for the assistant to finish answering, then return its last reply. */
async function askAssistant(page, question) {
  const botCount = await page.locator('.bubble--bot').count()
  await page.fill('.chat-form .input', question)
  await page.click('.chat-send')
  // The agent calls the model and its tools; this can take a while.
  await page.waitForFunction(
    (n) => document.querySelectorAll('.bubble--bot').length > n,
    botCount,
    { timeout: 180_000 },
  )
  await page.waitForSelector('.bubble--typing', { state: 'detached', timeout: 180_000 })
  await page.waitForTimeout(900) // let the entrance animation settle
  return page.locator('.bubble--bot').last().innerText()
}

async function openChat(page) {
  await page.click('.chat-launcher')
  await page.waitForSelector('.chat-panel', { state: 'visible' })
  await page.waitForTimeout(500)
}

const browser = await chromium.launch()
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  deviceScaleFactor: 2,
})

const notes = {}

// ---------------------------------------------------------------------------
// Check 1 — the chat reports honest stock and price from the database
// ---------------------------------------------------------------------------
{
  const page = await context.newPage()
  // This product has only M and XL in stock; XS, S, L and XXL are all zero.
  await page.goto(`${BASE}/products/champion-reverse-weave-crewneck`, {
    waitUntil: 'networkidle',
  })
  await page.waitForSelector('.detail__name')
  await openChat(page)

  notes.inventory = await askAssistant(
    page,
    'Do you have this in large? And what does it cost?',
  )
  console.log('\n[1] inventory reply:\n', notes.inventory, '\n')

  await page.screenshot({ path: `${OUT}/inventory.png` })
  await page.close()
}

// ---------------------------------------------------------------------------
// Check 2 — a category question fills the page with product cards
// ---------------------------------------------------------------------------
{
  const page = await context.newPage()
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await openChat(page)

  notes.search = await askAssistant(page, 'What shirts do you have?')
  console.log('[2] search reply:\n', notes.search, '\n')

  // The matches render on the page, above the routed content.
  await page.waitForSelector('.chat-matches .card', { timeout: 30_000 })
  notes.cardCount = await page.locator('.chat-matches .card').count()
  console.log('[2] product cards on page:', notes.cardCount, '\n')

  await page.evaluate(() => window.scrollTo({ top: 0 }))
  await page.waitForTimeout(700)
  await page.screenshot({ path: `${OUT}/search_cards.png` })
  await page.close()
}

// ---------------------------------------------------------------------------
// Check 3 — usability improvement from Problem 9: filter by size, and the
// size run shown on each card
// ---------------------------------------------------------------------------
{
  const page = await context.newPage()
  await page.goto(`${BASE}/products`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.card')

  const before = await page.locator('.card').count()

  // "My size" -> XXL
  await page.locator('.toolbar--secondary .chip', { hasText: /^XXL$/ }).click()
  await page.waitForTimeout(800)
  const after = await page.locator('.card').count()

  // Reveal the size run on the first card, which is the other half of the
  // improvement.
  await page.locator('.card').first().hover()
  await page.waitForTimeout(700)

  notes.sizeFilter = { before, after }
  console.log('[3] products before size filter:', before, '| after XXL filter:', after, '\n')

  await page.screenshot({ path: `${OUT}/usability_size_filter.png` })
  await page.close()
}

await browser.close()
console.log('Screenshots written to', OUT)
console.log(JSON.stringify(notes, null, 2))
