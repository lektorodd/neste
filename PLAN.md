# Plan for Neste

Status 25.11.2026: v3 er skriven og testa med påfunne Entur-svar (`tests/mock_test.py`).
**Ingenting er testa mot ekte Entur-data eller ekte kart enno.** Utviklingsmiljøet der v3 vart laga, kom ikkje ut til `api.entur.io`, cdnjs eller OpenStreetMap.

## 1. Verifiser mot ekte data (gjer dette først)

- [ ] **CORS**: Godtek `api.entur.io` kall frå nettlesaren med headeren `ET-Client-Name` (preflight)? Test frå GitHub Pages-adressa og frå `file://`.
- [ ] **Schema**: Finst `occupancyStatus` på `EstimatedCall` og `parent` på `StopPlace` i Journey Planner v3? Appen fell tilbake til eit enklare fragment viss ikkje (sjå `FRAG` i `index.html`), men ta bort det som ikkje finst.
- [ ] **ID-matching**: Stopp frå geocoderen (`NSR:StopPlace:…`) må vere same ID som `quay.stopPlace.id` i `estimatedCalls`, eller som `parent.id`. Sjekk særleg terminalar med fleire transportmiddel (Bergen busstasjon `NSR:StopPlace:62356`).
- [ ] **Ferjer**: Kjem ferjesamband (t.d. Halhjem–Sandvikvåg) med i `estimatedCalls`, og har begge kaiane same `serviceJourney`?
- [ ] **Belegg**: Sender Skyss noko anna enn `noData`? Fjern stolpane om det aldri kjem data.
- [ ] **Kart**: Lastar Leaflet frå cdnjs og fliser frå OSM? Gir `nearest(...)` stopp, og kva for format har `transportMode` (liste eller enkeltverdi)?
- [ ] **Datamengd**: Kvart frå-stopp hentar 60 avgangar med alle vidare stopp. Mål responsstorleiken på ein travel terminal.

## 2. Publiser

- [ ] Slå på GitHub Pages (main, rot).
- [ ] Legg til `manifest.webmanifest` og ikon (192/512) så «Legg til på Heim-skjerm» blir fin på Android òg.
- [ ] Vurder service worker berre for app-skalet (ikkje for avgangsdata).
- [ ] Vel lisens (MIT?) og legg til `LICENSE`.

## 3. Forbetringar

- [ ] **Linjefilter på serveren**: Når brukaren har sett linjer, slå opp line-ID-ar (`lines(publicCodes: …)`) og bruk `whiteListed: {lines: […]}` i staden for å hente 60 avgangar og filtrere lokalt.
- [ ] **Overgangar**: I dag er berre direkte turar med. Vurder `trip(from, to)` for reiser med bytte.
- [ ] **Avvik**: Vis `situations` (SIRI SX) på linja eller stoppet.
- [ ] **Sortering av reiser**: Dra og slepp, eller ein «Gjer til standard»-knapp.
- [ ] **QR-kode** for delingslenka, så familien kan skanne frå ein annan telefon.
- [ ] **Gangtid**: La brukaren justere gangtid i kartet, og set eit fornuftig tak for forslaga frå heimepunktet.

## Prinsipp som skal halde

- Inga adresse, inga heimeposisjon og ingen personlege stopp i repoet. Alt brukaroppsett ligg i `localStorage`.
- Heimepunktet blir aldri med i delingslenka. Lenka brukar `#`-delen, så ingenting går via server.
- Éi fil (`index.html`) så lenge det går. Ingen byggesteg.
- Ikkje Skyss-oransje. Eigen palett: lime signal (`--sig`), blå buss, grøn bane, sjøblå ferje.
