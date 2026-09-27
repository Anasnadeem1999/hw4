/**
 * The catalogue stores colours as words ("heather gray", "dusty coral").
 * This maps the 22 names that actually appear in the data onto swatches, so a
 * shopper can see the colourway at a glance instead of reading a list.
 */
const SWATCHES: Record<string, string> = {
  'navy blue': '#1b2a4a',
  navy: '#1b2a4a',
  'royal blue': '#2f5fc4',
  blue: '#2f5fc4',
  'light blue': '#a8c6e8',
  white: '#ffffff',
  ivory: '#f7f3e8',
  cream: '#f2e9d8',
  'heather gray': '#b9bcc0',
  'light gray': '#d6d9dc',
  gray: '#9aa0a6',
  'charcoal gray': '#4a4f55',
  'dark heather gray': '#6b7076',
  'dark heather charcoal': '#44484d',
  'heather charcoal gray': '#585d63',
  black: '#17181a',
  red: '#c8102e',
  gold: '#c8a23c',
  yellow: '#e8c351',
  green: '#2f6b46',
  'dusty coral': '#d58a7c',
}

export function swatchFor(name: string): string | null {
  return SWATCHES[name.trim().toLowerCase()] ?? null
}

/** Multicolor gets a conic gradient rather than a single fill. */
export function isMulticolor(name: string): boolean {
  return name.trim().toLowerCase() === 'multicolor'
}
