---
name: domain-vocabulary
description: Resolve fuzzy terminology and name domain concepts using CONTEXT.md and docs/agents/domain.md. Use when a word is ambiguous or overloaded, when naming issues/modules/tests, or when checking glossary/ADR vocabulary before inventing new language. Read/when-to-open only — writing glossary or ADRs is grill-with-docs / domain-modeling.
---

# Domain vocabulary

Read/when-to-open policy. Complements `/grill-with-docs` (writer) — this skill does **not** update `CONTEXT.md` or ADRs.

## When to use

- Terminology fuzzy, overloaded, or conflicting across the conversation
- Naming a domain concept (issue, module, test, proposal)
- Before inventing a synonym — check glossary first

## Do

1. Read `docs/agents/domain.md` for how to consume domain docs.
2. Open root `CONTEXT.md`, or `CONTEXT-MAP.md` + relevant context glossaries if multi-context.
3. Read ADRs in `docs/adr/` that touch the area (and context-scoped ADRs if present).
4. Use glossary terms as defined; avoid synonyms the glossary rejects.
5. If files are missing — proceed silently; do not create them here.

## Don't

- Always-load full `CONTEXT.md` at session start (lean ritual in `AGENTS.md`)
- Write or expand the glossary / ADRs — hand off to `/grill-with-docs` or `/domain-modeling`
- Archive or relocate live `CONTEXT.md` / `CONTEXT-MAP.md` / ADRs
