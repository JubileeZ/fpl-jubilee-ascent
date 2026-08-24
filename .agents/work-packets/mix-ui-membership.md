# Active Task: Mix vs Mix membership UI

**Objective:** Exclusive Mix occupancy with Mix-list remove, A↔B drag-move, table letters, Mix panel after charts

**Acceptance:** `uv run pytest tests/test_mix.py tests/test_ownership_explorer_view.py` green; Mix panel after charts before table; × removes; drag moves; full Mix no-op shows reason

**Status:** Done on main; delete this packet after commit lands

**Files:** `projections/mix.py`, `dashboard/explorer.js`, `dashboard/index.html`, `dashboard/styles.css`, `tests/test_mix.py`, `tests/test_ownership_explorer_view.py`

**Decisions:** Exclusive Mix Member; × removes; name drags/highlights (toggle); dest full no-op + reason; session-only; layout charts then Mix then table

**Blocked:** None

**Next:** Delete this packet (file was untracked, so it ships with the first commit)

## Work Packet (SFDBN)

- **Status:** Implemented; waiting for commit so the packet can be deleted
- **Files:** `projections/mix.py`, `dashboard/explorer.js`, `dashboard/index.html`, `dashboard/styles.css`
- **Decisions:** Exclusive occupancy; Mix-list ×/drag; table letters add/move/remove; full Mix reason on panel
- **Blocked:** None
- **Next:** Delete `.agents/work-packets/mix-ui-membership.md` after this commit

## Todo
- [x] Occupancy algebra: apply letter, remove Mix Member, move Mix Member
- [x] Mix panel after charts; list ×, drag A↔B, highlight; table letter pressed; full reason
- [x] README + current-state Mix notes
- [ ] Delete this packet after commit (cannot delete an untracked packet in the same first commit)
