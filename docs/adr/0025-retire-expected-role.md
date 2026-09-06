# Expected Role is retired; product reports xMins from Club Fixtures

Expected Role, Dual-Source adapters, Expected Role Table, and Expected Role Rebuild are not product. `refresh_data` does not scrape FFS or Meerkat. Ownership Explorer has no Role column. Minutes are actual Club Fixture Start / Sub-in / DNP; surfaces report xMins from the Participation State posterior. Preseason 15 is MILP on Feature Contract xMins (Cold-Start seed), not a Role-gated Draft Shortlist.

**Status:** Accepted. Supersedes ADR 0016 remaining Dual-Source / Role-registry clauses. Supersedes ADR 0021 “Dual-Source adapters unchanged” and ADR 0022 optional Explorer Role label. ADR 0022 Club Fixture xMins as the minutes brain still stand.

**Considered:** Freeze `expected_roles.csv` as Explorer labels; rebuild Role from this-season FPL starts; keep scrapes for GW1 only. Rejected: Role is not data; starts already are Participation State; scrapes are other-source maintenance (ADR 0023).

**Consequences:** `--rebuild-roles` / `--keep-roles` are not required ingest. `features/lineup-signals.json` is not an operational pin. Project never waits on a Role table.
