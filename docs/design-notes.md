# Campus Customs — Design Reference

Research source: yalebulldogblue.com ("Yale Bulldog Blue by Campus Customs"),
the real storefront this project mirrors. Officially licensed Yale merchandise.
Physical store: 57 Broadway, New Haven.

## Palette

| Token | Hex | Use |
|---|---|---|
| Yale Blue (primary) | `#00356B` | Header, buttons, headings, links |
| Yale Blue dark | `#002247` | Hover/pressed states |
| Yale Blue light | `#286DC0` | Accents, focus rings |
| White | `#FFFFFF` | Page + card background |
| Off-white | `#F7F7F5` | Section bands, page background |
| Gray 600 | `#5C6670` | Secondary text |
| Gray 200 | `#E3E6E8` | Borders, dividers |
| Sale red | `#C8102E` | Sale price, "Sold out" badge |

`#00356B` is Yale's official Yale Blue.

## Typography

Clean modern sans-serif. Strong size hierarchy: large banner headlines →
medium section headings → small product meta. Product names regular weight,
prices slightly bolder. Generous letter-spacing on nav/section headers.

## Header

Fixed. Logo/wordmark left → primary nav center → search, login, cart right.

Nav categories (real site):
Clothing · Accessories · Home · Collections · Residential Colleges ·
Sports · Relatives · Graduate & Professional Schools

These map onto our `catalogue.garment_type` and `search_tags` — residential
colleges (Saybrook, Pierson, Morse, Branford, Davenport, Grace Hopper,
Jonathan Edwards, Benjamin Franklin, Berkeley), schools (Management,
Medicine, Nursing, Architecture, Art, Music, Engineering, Public Health,
Divinity), and sports (football, soccer, lacrosse, sailing, fencing,
ice hockey, diving, baseball, crew).

## Homepage sections

1. Hero banner → links to all products
2. Featured collection row (~6 items)
3. Promotional band ("Shop Bulldog Blue")
4. Larger featured grid (12+ items)
5. Seasonal section ("Tailgate Season")
6. Footer

## Product card

Image (front view, white background, consistent aspect ratio) → product name
as link → price (original struck through + current, when on sale) →
material/fit line → "Quick shop" / "Choose options" button.
"Sold out" badge when inventory is zero — we can drive this from the
`inventory` table summed across sizes.

## Footer

Store address, partner logos, policy links, currency/country selector,
copyright.

## Tone

Celebratory, school-pride voice. Real examples:
"Casual comfort, classic Bulldog pride", "Sip in style, the Bulldog way."
Useful for the chat agent's persona and for section copy.
