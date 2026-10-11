# Active Task: Default Explorer Horizon Start to Upcoming Transfer Deadline

- **Status:** Complete
- **Objective:** Default Explorer horizon start to the upcoming open transfer deadline (GW7) while preserving in-play inspection of unfinished gameweeks.
- **Acceptance:** Explorer selectbox defaults to upcoming transfer deadline (GW7), dashboard export metadata defaults planning horizon to upcoming deadline, test suite passes.
- **Issue/Ticket:** User request

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** dashboard/streamlit_dashboard.py, commands/export_dashboard.py, commands/dashboard.py, tests/test_dashboard.py, tests/test_streamlit_dashboard.py
- **Decisions:** Default Horizon start selectbox to transfer_plan_start (upcoming open transfer deadline). Preserve earliest unfinished gameweek in projection feature generation so current in-play matches remain inspectable. Filter default user plan weeks to target_gw <= gw < target_gw + horizon.
- **Blocked:** None
- **Next:** Ready for commit or user review.

## Todo
- [x] Update dashboard/streamlit_dashboard.py Explorer horizon selectbox default
- [x] Update commands/export_dashboard.py default target_gw resolution
- [x] Fix commands/dashboard.py _generate_default_user_plans week filter
- [x] Update test_dashboard.py and add test in test_streamlit_dashboard.py
- [x] Refresh data/dashboard_data.json
- [x] Verify test suite and gate checks

## Blockers / Notes
- None
