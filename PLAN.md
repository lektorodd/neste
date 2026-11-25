# Plan for Neste

Status 25.11.2026: v3 er testa med påfunne Entur-svar (`tests/mock_test.py`) **og mot ekte Entur-data, Leaflet og OSM-fliser** i Chromium, både frå `http://` og `file://`.

## 1. Verifiser mot ekte data ✓ (25.11.2026)

- [x] **CORS**: Preflight er OK. Journey Planner og Geocoder svarar `Access-Control-Allow-Origin: *` og godtek `ET-Client-Name` og `Content-Type`. Fungerer både frå `http://`-opphav og `file://` (`Origin: null`).
- [x] **Schema**: `occupancyStatus` (EstimatedCall) og `parent` (StopPlace) finst. Fallback-fragmenta er fjerna; appen brukar no éin spørjing (`CALL` i `index.html`).
- [x] **ID-matching**: Geocoderen og `nearest` gir foreldre-ID (t.d. `NSR:StopPlace:62356`). I `estimatedCalls` står barne-stoppet (`30810`, `30865`, `62129` for Bergen busstasjon) med `parent.id` = 62356. `ids()` dekkjer begge.
- [x] **Ferjer**: Halhjem–Sandvikvåg (linje 1018) kjem med, og kvar tur har begge kaiane under same `serviceJourney`. Ekspressbussane som køyrer med ferja (NW400, VY190, FX652) kjem òg med.
- [x] **Belegg**: Behald stolpane. Vy-tog sender `manySeatsAvailable` på dei fleste avgangane; Skyss sender stort sett `noData`, men nokre gonger data.
- [x] **Kart**: Leaflet 1.9.4 lastar frå cdnjs, og flisene frå OSM. `nearest` gir foreldre-stopp; `transportMode` er ei **liste** (t.d. `["tram","bus"]`).
- [x] **Datamengd**: Bergen busstasjon, 60 avgangar: 306 kB rått / 26 kB gzip med den gamle spørjinga. Med `serviceJourneyEstimatedCalls.next` (berre stoppa etter avgangen) er det 219 kB / 14 kB. Ferjekaien Halhjem gjekk frå 18 kB til 9 kB gzip.

Funne og retta under verifiseringa:
- Ekspressbussar tek berre på passasjerar ut av byen (`forAlighting: false` heilt til Halhjem kai). Appen viste dei som alternativ til stopp der dei ikkje set av. No krev appen `forBoarding` på avgangsstoppet og `forAlighting` på målet.
- Turar etter midnatt kunne få feil dato, sidan `serviceJourney.estimatedCalls` utan `date` gjeld i dag. `next` brukar datoen til avgangen.
- Bergen busstasjon fekk trikkefarge (kategorien `onstreetTram`). Ny prioritering: tog, båt, bane, buss, trikk (`pickMode`).
- Klokkeslett blir no viste i norsk tid (`Europe/Oslo`), uavhengig av tidssona til eininga.

Observert, ikkje retta:
- På Bergen busstasjon dekkjer 60 avgangar berre om lag 30 minutt. Med linjefilter (sjå steg 3) kan ei reise då vise få eller ingen avgangar. Dette er hovudgrunnen til å flytte filteret til serveren.
- Ved likt framkomsttidspunkt (buss på ferja og sjølve ferja) avgjer rekkjefølgja i svaret kva som blir vist som raskast.

## 2. Publiser

- [ ] Slå på GitHub Pages (main, rot): Settings → Pages → «Deploy from a branch», `main`, `/ (root)`. Adresse: https://lektorodd.github.io/neste/. `.nojekyll` er lagt til.
- [x] Manifest og ikon (25.11.2026): `manifest.webmanifest` (`standalone`, mørk tema), logo «nedteljing» i `ikon/neste.svg`, PNG i 180 (iOS), 192/512 og maskable 512, og `favicon.ico` (16/32/48). Chrome melder ingen hinder for installering. PNG-ane er rendra frå SVG-en; teikn dei på nytt om logoen blir endra.
- [ ] Vurder service worker berre for app-skalet (ikkje for avgangsdata).
- [x] Lisens: MIT, `LICENSE` lagt til (25.11.2026).

## 3. Forbetringar

- [x] **Ferjesamband** (25.11.2026): éi reise av typen `{ferry:{a,b},dir}` i staden for to stader og to reiser. Kaiane på andre sida blir funne frå avgangane (`filters` med `transportMode: water`, `next`). Avgangane blir henta med same filter, så 60 avgangar dekkjer om lag eit døgn i staden for 2,5 timar på Halhjem. «Snu» byter side; «Vel kai etter kvar eg er» (lokal innstilling, ikkje i delingslenka) vel næraste kai ved opning og etter 2 min i bakgrunnen.
- [x] **Følg bussen på kartet** (25.11.2026): Trykk på ei avgangsrad. Appen spør `realtime/v2/vehicles/graphql` med `vehicles(serviceJourneyId: …)` kvart 10. sekund medan kartet er ope, og stoppar når det blir lukka eller appen ligg i bakgrunnen. Testa mot ekte data: Skyss sender buss og ferje, men ikkje Bybanen, og ein tur får først posisjon når han har starta. Frå endestasjonar (Bergen busstasjon, ferjekaiar) er det difor sjeldan posisjon før avgang. Ein mogleg vidareføring er å følgje køyretøyet på turen før (krev `vehicleId`/blokk, som avgangane ikkje har).
- [ ] **Linjefilter på serveren** (viktigast, sjå funn i steg 1): Når brukaren har sett linjer, slå opp line-ID-ar (`lines(publicCodes: […])` gir t.d. `SKY:Line:50E`) og bruk `estimatedCalls(filters: [{select: [{lines: […]}]}])`. `whiteListed` finst ikkje på `StopPlace.estimatedCalls` i v3. Utan filter kan `numberOfDeparturesPerLineAndDestinationDisplay` spreie avgangane over lengre tid.
- [ ] **Overgangar**: I dag er berre direkte turar med. Vurder `trip(from, to)` for reiser med bytte.
- [ ] **Avvik**: Vis `situations` (SIRI SX) på linja eller stoppet.
- [ ] **Sortering av reiser**: Dra og slepp, eller ein «Gjer til standard»-knapp.
- [ ] **QR-kode** for delingslenka, så familien kan skanne frå ein annan telefon.
- [x] **Gangtid / kvar er staden** (25.11.2026): kvar stad kan ha eit punkt (søk i geocoderen med `layers=address`, som òg finn skular og andre POI-ar, eller vel på kartet). «Stopp i nærleiken» brukar `nearest` (1,5 km, 20 stopp) og gangtid frå `trip(... modes:{directMode:foot, transportModes:[]})`, 20 stopp på om lag 0,5 s. Punkta ligg i `localStorage` under `neste.pts`, ikkje i `cfg`, så dei er aldri i delingslenka. Det gamle heimepunktet blir flytta til staden «Heim».

## Prinsipp som skal halde

- Inga adresse, inga heimeposisjon og ingen personlege stopp i repoet. Alt brukaroppsett ligg i `localStorage`.
- Punkta for stadene (kvar heim og jobb er) blir aldri med i delingslenka. Lenka brukar `#`-delen, så ingenting går via server.
- Éi fil (`index.html`) så lenge det går. Ingen byggesteg.
- Ikkje Skyss-oransje. Eigen palett: lime signal (`--sig`), blå buss, grøn bane, sjøblå ferje.
