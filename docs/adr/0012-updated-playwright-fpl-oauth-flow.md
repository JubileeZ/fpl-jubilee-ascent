# Playwright FPL OAuth Flow & OneTrust Overlay Handling

## Context
Premier League updated authentication infrastructure to `account.premierleague.com` OAuth endpoint (`https://account.premierleague.com/as/authorize`). Legacy URL `users.premierleague.com/accounts/login/` deprecated (`net::ERR_NAME_NOT_RESOLVED`). Dynamic OneTrust cookie consent overlay (`#onetrust-consent-sdk`) intercepts button click pointer events on headless Chromium.

## Decision
Refactored `async_login` in `clients/fpl_auth.py` to:
1. Navigate to `https://fantasy.premierleague.com/en/`.
2. Purge OneTrust DOM node overlay dynamically before interaction.
3. Click `button:has-text("Log in")` to trigger OAuth redirect to `account.premierleague.com`.
4. Fill `#username` and `#password` input fields on OAuth form.
5. Click submit button `button[data-skbuttonvalue="SIGNON"]` / `#btnSignIn`.
6. Intercept credential error message `"Invalid username and/or password"` on DOM body to fail fast with detailed `ValueError` when `.env` configuration invalid.
7. Intercept `x-api-authorization` Bearer token from `/api/` network requests upon redirect to `/transfers`.

## Consequences
- Prevents Playwright `TimeoutError` from element pointer interception.
- Restores automated JWT session token retrieval for 2026/27 FPL season.
- Validates credential accuracy before waiting for request interception.
