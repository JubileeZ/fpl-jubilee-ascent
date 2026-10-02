# DESIGN.md: FPL Jubilee Ascent

Antigravity theme specification for antislop R-37.

## Product

Local FPL score projection + transfer MILP dashboard. Surfaces: Explorer (projections, Squad What-If pitch) and Transfer Plan (scenario arms). Single manager, weekly deadline use.

## Audience

One power user (repo owner) at a desktop, operating a high-precision FPL optimization workstation.

## Personality

Antigravity mission control: deep space obsidian canvas, precision hairline wireframes, high-legibility data grids, and focused cosmic accents. Calm, authoritative developer tool rather than flashy SaaS marketing.

## Palette

- Core Canvas: Deep space obsidian `#0a0b10`, elevated card `#121520`, hover state `#1a202e`
- Borders: Crisp hairline slate `#1e2538`
- Primary Accent: Electric cyan / cosmic sky `#38bdf8` (active tabs, primary CTA, solver actions)
- Secondary Accent: Cosmic indigo `#6366f1` (subtle secondary focus and badges)
- Text: Crisp white `#f8fafc`, muted slate `#94a3b8`
- Pitch Domain: Tactical dark pitch (`#081717` to `#050f14`) with subtle hairline markings (`rgba(56, 189, 248, 0.15)`)
- Position Markers (domain tokens):
  - GKP: Tactical gold `#eab308`
  - DEF: Cyan `#38bdf8`
  - MID: Emerald `#10b981`
  - FWD: Coral rose `#f43f5e`
- Forbidden: Gratuitous full-screen purple blur or glowing background blobs without purpose

## Typography

- UI & Controls: **Inter**, system sans-serif (`400`, `500`, `600`, `700`). Reason: crisp grotesque letterforms engineered for high legibility in dense toolbars and data-dense ops consoles.
- Tabular & Metrics: **JetBrains Mono** for numeric columns and metrics (xP, cost, SV, ownership). Reason: fixed-width tabular numeral alignment essential for comparing projection tables and decimal ratings.
- Brand Wordmark: Clean, solid light text (weight 700) with a subtle cyan dot accent marker.

## Theme

**Dark only.** Justification: Night ops, high-contrast numeric legibility, and native command-center aesthetic.

## Motif

Tactical data terminal: flat cards with razor-thin borders, clean pill status indicators where functional, and a tactical pitch matrix for squad views.

## Dial

`ENERGY 1 / RHYTHM 2 / MOTION 1`

- Energy 1: Linear workspace chrome, zero hero marketing fluff
- Rhythm 2: Clear logical sections: Explorer filters -> table -> charts; Plan chips -> scenarios -> pitch
- Motion 1: Micro-interactions on hover and focus rings; zero gratuitous scroll animations

## Layout Notes

- Mobile: Reflow toolbar and table stacks, minimum 44px tap targets on primary buttons
- Data cards: Functional containers with strict hierarchy and zero decorative padding bloat
