# Using the Dashboard

One Streamlit application: Transfer Planner, Explorer, Research, Model Methodology. Local planning only; dashboard edits never submit transfers to FPL. Hosting deferred. [Launch and deployment preparation](streamlit-planner-deployment.md).

## Start locally

From repository root:

```powershell
uv sync --locked
uv run python -m commands.dashboard
```

Open `http://127.0.0.1:8000`. Keep terminal running; Ctrl+C stops application. With existing project environment and no global `uv`/Python:

```powershell
.venv/Scripts/python.exe -m commands.dashboard
```

Existing environment requires no Administrator access. Alternate `uv run python -m commands.streamlit_planner` opens same application on port 8501. Run one launcher at a time against shared storage. `--no-browser` prevents automatic browser opening; `--port 8001` selects another dashboard port.

Fresh setup: copy `.env.example` to local `.env`; configure `FPL_EMAIL` and `FPL_PASSWORD` for authenticated User Squad ingestion. Browser authentication fallback requires installed Playwright Chromium (`uv run playwright install chromium`). Existing cached data works without reinstalling dependencies or browser runtime.

Open Transfer Planner and click **Refresh** to ingest current FPL data and rebuild projections. Wait for job completion. Without authenticated User Squad, Explorer can inspect available public projections; planner and Squad What-If require squad ingestion. Refresh needs network access; viewing cached data does not trigger live ingestion.

## Navigate and resize

Navigation starts collapsed. Open with upper-left chevron; choose workspace; close with sidebar chevron to recover content width. First visit opens Transfer Planner; later visits restore last workspace.

Narrow windows stack controls, Player groups, and charts. Scroll vertically; tables and long equations scroll within their own area. Advanced controls remain in expanders. Player dialogs use **Back to squad** or **Back to Explorer**, close button, or Escape. Tab moves focus; Enter activates focused buttons.

Layouts checked at 320–1440px with navigation open/closed. Actual 200% browser zoom remains unverified; available verification browser lacks working zoom control.

## Generate a transfer plan

1. Confirm refreshed User Squad and projections loaded.
2. Set **Horizon end**. Start fixed at upcoming open deadline; horizon 1–10 Gameweeks, ending no later than GW38.
3. Click **Generate plan**. Wait for job status to finish; other heavy jobs wait until active job completes.
4. Choose **Scenario policy**: Optimal, No Hit, Conservative; click **Use selected scenario** to apply selection. Confirm **Replace edits** when replacing manual choices, or cancel.
5. Choose **Gameweek** to inspect Starting XI, bench, transfers, bank, Free Transfers, Hits, and projected scores.

Solver runs three policies. Displayed policy selects recommendation to inspect. **Unsolved hold draft** means current squad baseline without solver recommendation. **Solver recommendation** means applicable solver result. **Draft** indicates manual choices. **Needs recalculation** identifies dependent recommendations invalidated by edits.

Projected lineup points after Hits and Expected GW Score differ: Expected GW Score includes appearance uncertainty and substitution effects. Missing projections display Unavailable.

## Inspect and edit Players

Click Player on Starting XI or bench to open inspection dialog. Selected-week projected points/minutes appear first, followed by prices, availability, upcoming fixtures/projections, recent history, and projection components when available.

- **Sell from GW…** removes ownership from selected week onward. Position-labelled replacement slot appears under **Bench and replacement slots**.
- **Bench this week** retains ownership and excludes Player from selected-week Starting XI. **Clear bench override** restores automatic selection.
- **Replace Player** opens eligible replacement search directly. Clicking empty replacement slot opens same search.
- **Find replacement** filters by Player or Club. Candidates respect Position, budget, uniqueness, and Club limit; displayed candidates ordered by selected-week projection. Choose **Add…** to purchase. Narrow search when desired Player outside first 20 displayed candidates.
- **Undo sale** restores pending outgoing Player and draft accounting.
- **Set captain**, **Set vice-captain**, and **Clear captain and vice overrides** control selected-week choices.
- **Booked chip** sets chip for selected Gameweek from available options.

After ownership changes, planner selects best feasible XI and bench from retained/added Players, respecting manual overrides. Vacancies remain in bench area; incomplete selection shown when remaining Players cannot form legal XI. Bank/Hits provisional until replacement complete. Restore valid 15-player squad throughout horizon and resolve conflicts before solving.

Ownership changes propagate forward; bench/captain/vice overrides apply only to selected week. Earlier changes can invalidate later recommendations; review later Gameweeks.

Click **Optimize remaining transfers** after manual choices to solve remaining horizon while preserving explicit choices. Manual clicks update lineup immediately without starting transfer MILP each time. **Reset to solver** restores applicable cached recommendation after confirmation and replaces manual edits.

## Saved drafts and job recovery

Planner autosaves edits, selected policy/Gameweek, overrides, and completed recommendations. Default storage `data/planner/`; browser reload restores draft. Explorer What-If stays browser-session only. Local projections, credentials, and operational caches do not arrive through git pull.

- **Saved draft uses older data:** review draft; click **Use refreshed User Squad**, then **Start new plan** to replace choices with refreshed baseline. Regenerate recommendation.
- **Reload latest draft:** another browser tab saved newer version; reload before editing further.
- **Retry saving draft:** storage write failed; restore writable storage, then retry. Error means latest changes not confirmed saved.
- **Solver results retained from an earlier draft:** result belongs to different inputs; download retained result if needed, regenerate for current choices.
- Failed solve retains last usable draft/recommendation. Process restart marks unfinished job interrupted; retry explicitly. Running solve does not resume automatically after process restart.

## Explorer

Choose **Projection model**, **Horizon start**, **Horizon end**. Explorer horizon independent from planner; start any unfinished Gameweek. **Model provenance** exposes Champion metadata.

Use **Filters**: Positions, Clubs, Find Player, Price range, Minimum xMins / GW. Filters apply to charts and table; no Clubs selected means all clubs. **Chart points** chooses xP / GW or xP / 90. **Assume 90 minutes per projected match (view only)** changes displayed comparison values.

Charts compare ownership/price with selected projection measure. Select chart point or table row to inspect Player; alternatively choose **Inspect Player** and click **View player details**. Table starts with Player, Position, Price, xP, xP / GW, Club; additional columns available through local scroll. **Download filtered Players** exports current filtered table.

**Squad What-If** starts from User Squad independently of saved planner:

1. Choose **Replace Player** and **With Player**; click **Replace in What-If**.
2. Choose **Starter to bench** and **Substitute to start**; click **Swap starting places**. Correct flagged legality/budget conflicts.
3. Set What-If captain/vice or use Automatic each Gameweek.
4. Choose **First substitute**; click **Move to first bench place**.
5. Inspect bank, transfers, Hits, and comparison scores. **Reset What-If to User Squad** restores baseline. New browser session or changed dataset resets What-If.

**Solve Dream Team** produces independent squad result using Explorer model/horizon. Does not replace saved transfer draft or What-If squad. **Advanced strategy solve**, available under Planner and Explorer, runs separate experiment; retained results/downloads do not overwrite planner.

## Research and Model Methodology

**Research:** search **Find research topic**, select **Topic**, read note, **Download note**. When companion CSVs exist, select companion for first-100-row preview and **Download full CSV**.

**Model Methodology:** inspect Champion, projection layers/formulas, Candidate policy, Comparison Slate. **Draft a model research prompt** accepts category, hypothesis, targets; download resulting prompt. Generating prompt does not run experiment or promote model.

## Common problems

- Empty planner: configure local credentials, Refresh, wait for authenticated squad/projections. Read job error if ingestion fails.
- Disabled solve: finish pending replacements, resolve conflicts, replace stale baseline, or wait for active job.
- No replacement: clear search, inspect budget/Position/Club constraints, or sell another Player before completing replacements.
- Empty Explorer list: widen filters, select Positions, lower minutes floor, clear search.
- Port occupied: stop existing dashboard or choose `uv run python -m commands.dashboard --port 8001`.
- Older visual design: use current checkout and normal dashboard command; reload browser after restarting application.

Behavior references: [planner spec](streamlit-transfer-planner.md), [single-dashboard integration](dashboard-planner-integration.md), [responsive layout](dashboard-responsive-layout.md).
