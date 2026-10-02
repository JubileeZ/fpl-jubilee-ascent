# DESIGN.md — FPL Jubilee Ascent

Agent-drafted from existing product chrome for antislop R-37. Owner may rewrite any field.

## Product

Local FPL score projection + transfer MILP dashboard. Surfaces: Explorer (projections, Squad What-If pitch) and Transfer Plan (scenario arms). Single manager, weekly deadline use.

## Audience

One power user (repo owner) at a desktop, often at night before GW deadline.

## Personality

Calm ops console. Pitch-first, not marketing landing. Specific over generic SaaS.

## Palette

- Core: pitch emerald `#059669` / `#10b981`
- Surface: night `#090d16`, card `#111827`
- Text: `#f8fafc`, muted `#94a3b8`
- Accent (one deliberate): emerald on primary actions + selected plan/tab
- Position colors (domain only): GKP / DEF / MID / FWD markers on pitch cards
- Forbidden default: blue→purple brand gradients, neon orbs, full-page glow

## Typography

- UI: **IBM Plex Sans** (readable ops tables; not Inter default)
- Brand wordmark: same family, weight 700, solid light text (no gradient fill)
- Reason: tabular clarity for xP grids; Jubilee name stays quiet, not display-serif theatre

## Theme

**Dark only.** Reason: late-night deadline ops, local tool, pitch grass already dark-green. No light/dark toggle.

## Motif

Football pitch (grass gradient + line geometry) only on Squad / Plan XI boards. Elsewhere: flat card surfaces, hairline borders.

## Dial

`ENERGY 1 / RHYTHM 2 / MOTION 1`

- Energy 1: linear tool chrome, no hero marketing
- Rhythm 2: Explorer filters → table → charts → components; Plan chips → scenario cards → weeks → pitch
- Motion 1: hover + focus only; no scroll choreography

## Layout notes

- Mobile: reflow stacks (toolbar, pitch, tables); tap targets ≥ 44px on primary controls
- Cards: data containers only, not decorative bento
