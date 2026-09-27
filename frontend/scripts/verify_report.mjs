/**
 * Opens output/app_check.html the way a double-click would (file:// protocol)
 * and confirms every screenshot resolves through its relative path.
 */

import { chromium } from 'playwright'
import { pathToFileURL } from 'node:url'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const report = resolve(HERE, '../../output/app_check.html')
const url = pathToFileURL(report).href

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1200, height: 1500 } })

const failed = []
page.on('requestfailed', (r) => failed.push(r.url()))

await page.goto(url, { waitUntil: 'networkidle' })

const images = await page.evaluate(() =>
  Array.from(document.images).map((i) => ({
    src: i.getAttribute('src'),
    loaded: i.naturalWidth > 0,
    w: i.naturalWidth,
  })),
)

console.log('opened:', url)
console.log('\nimages:')
for (const i of images) {
  console.log(`  ${i.loaded ? 'LOADED' : 'BROKEN'}  ${i.src}  (${i.w}px)`)
}
console.log('\nheadings:')
for (const h of await page.locator('h2').allInnerTexts()) console.log('  -', h)
console.log('\nfailed requests:', failed.length ? failed : 'none')

// Rendered only to confirm the page is not blank; not a deliverable.
await page.screenshot({ path: resolve(HERE, 'report_preview.png') })
await browser.close()
