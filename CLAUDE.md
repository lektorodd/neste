# Neste – notat for Claude Code

- Språk: grensesnitt, kommentarar og commit-meldingar på nynorsk.
- Appen er éi fil: `index.html` (HTML + CSS + JS, ingen byggesteg). Leaflet blir lasta frå cdnjs berre når kartet blir opna.
- Data: Entur Journey Planner v3 (`https://api.entur.io/journey-planner/v3/graphql`) og Geocoder (`/geocoder/v1/autocomplete`). Alle kall skal ha `ET-Client-Name: lektorodd-neste`.
- Personvern er eit krav: ingen adresse, ingen koordinatar og ingen personlege stopp i koden eller i testane. Bruk påfunne stopp-ID-ar i testane.
- Røyktest: `python tests/mock_test.py` (Playwright, med påfunne Entur-svar). Køyr han etter endringar. Med ferdig installert Chromium: `CHROME=/opt/pw-browsers/chromium python tests/mock_test.py`.
- Sjå `PLAN.md` for kva som står att. Steg 1 (verifisering mot ekte data) er gjort 25.11.2026; neste er steg 2 (publisering).
