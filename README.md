# Neste

Superenkel avgangsapp for kollektivtrafikk i heile Noreg, bygd på opne data frå [Entur](https://developer.entur.no) (NLOD).

- **Stader**: ein stad (t.d. «Heim», «Jobb») er eit sett med stopp du brukar der, med gangtid til kvart stopp.
- **Reiser**: frå ein stad til ein annan. Appen samanliknar alle avgangar frå stoppa dine og sorterer etter når du er framme dør til dør.
- **Følg bussen**: trykk på ein avgang, så viser kartet kvar bussen eller båten er no, med forseinking. Posisjonane kjem frå Entur sitt sanntids-API for køyretøy. Ikkje alle sender (til dømes Bybanen), og mange sender først når turen har starta.
- **Søk og kart**: finn stopp med søk (Entur Geocoder) eller på kartet (OpenStreetMap / Leaflet).
- **Del med familien**: delingslenka inneheld stader, stopp og reiser i `#`-delen av adressa, som aldri blir sendt til nokon server.

## Personvern

Ingen konto, ingen server, ingen sporing. Oppsettet blir lagra i `localStorage` i nettlesaren din.
Heimepunktet (valfritt) blir berre brukt til å føreslå gangtid og er aldri med i delingslenka.
Appen sender stopp-ID-ar til Entur for å hente avgangar (og ID-en til turen du følgjer på kartet), og kartutsnittet til OpenStreetMap for å hente kartfliser.

## Køyre

Éi fil: `index.html`. Legg ho på GitHub Pages, Cloudflare Pages eller ein annan statisk vert, og vel «Legg til på Heim-skjerm» på telefonen.

API-kall identifiserer seg med `ET-Client-Name: lektorodd-neste`. Lagar du din eigen variant, bytt til `<organisasjon>-<app>`.
