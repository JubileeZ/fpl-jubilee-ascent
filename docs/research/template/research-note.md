# [Research topic]

**Updated**: YYYY-MM-DDTHH:MM:SS±HH:MM  
**Data stamp**: [Dataset, source, or evidence cutoff]  
**Season**: [FPL season or `Multi-season`]  
**Status**: [Draft / Active / Superseded]  
**Purpose**: [Decision or question this note addresses]  
**Scope**: [Included and excluded analysis]  
**Related**: [Links to sibling notes, issues, or decisions]
**Artifact**: [companion.csv](companion.csv) — same topic folder as this note

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence. Do not add duplicate `Last update` fields.

## Sources

- **Primary**: [Title — author/publisher](URL) — published [YYYY-MM-DD]; accessed [YYYY-MM-DD]; role: [source role]
- **Secondary**: [Title — author/publisher](URL) — published [YYYY-MM-DD]; accessed [YYYY-MM-DD]; role: [source role]
- **Repository data**: [Command, file, or dataset] — cutoff [YYYY-MM-DD]

**Source boundary**: [What sources support. State `Source claims not independently validated` when applicable.]

## Agent Prompt

```text
Full redo docs/research/[topic-slug]/[topic-slug].md

1. Re-read all primary sources and inspect current repository conventions.
2. Refresh or re-check every input listed under Sources and Method.
3. Preserve source-derived claims separately from Project interpretation.
4. Recompute evidence and decision rules; do not silently change Method.
5. Update Updated, Data stamp, Season, Sources, Findings, Decision, and Risks.
6. Keep filename stable; update cross-links when sibling notes change.
7. Write companions into this topic folder (CSV/HTML beside the note).
8. Store scratch under .tmp/agent/ only; delete scratch before finishing.
```

## Method

**Method type**: [Source synthesis / empirical analysis / backtest / comparison / other]

**Inputs**:
- [Source, dataset, command, or file]

**Procedure**:
1. [Step]
2. [Step]
3. [Step]

**Definitions and assumptions**:
- [Term, threshold, or interpretation rule]

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| [Metric Name] | `[Symbol]` | [Formula / Calculation] | Higher is better $\uparrow$ / Lower is better $\downarrow$ | [Target value] | [Concise rationale] |

**Validation boundary**: [Validated evidence, unvalidated claims, and known leakage or freshness limits]

## Source synthesis

<!-- Required when external sources inform note. Summarize source claims without upgrading them to facts. -->

### Main claims

- [Claim]

### Source rationale

- [Why source recommends or rejects option]

## Project interpretation

<!-- Separate translation into project decision rules from Source synthesis. -->

### Decision rules

- [If condition, then action]

### Practical implications

- [Implication]

## Findings

### Evidence

- [Finding with source, dataset, or calculation reference]

### Alternatives

- [Alternative and trade-off]

## Decision

**Verdict**: [One-sentence decision]

**Recommended action**:
- [Action]

**Trigger / kill switch**:
- [Condition that changes decision]

## Risks and unknowns

- [Risk, unresolved question, or stale input]

## Refresh checklist

- [ ] `Updated` uses ISO 8601 timestamp with timezone.
- [ ] `Data stamp` identifies current evidence cutoff.
- [ ] `Season` and scope remain accurate.
- [ ] Source URLs, publication dates, and access dates checked.
- [ ] Source synthesis and Project interpretation remain separate.
- [ ] Unvalidated claims labeled.
- [ ] Agent Prompt remains runnable and points to stable slug.
- [ ] Scratch files removed from `.tmp/agent/`.
