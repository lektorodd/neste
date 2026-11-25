# Neste

Superenkel avgangsapp for kollektivtrafikk i heile Noreg, bygd på opne data frå [Entur](https://developer.entur.no) (NLOD).

- **Stader**: ein stad (t.d. «Heim», «Jobb») er eit sett med stopp du brukar der, med gangtid til kvart stopp. Seier du kvar staden er (adresse, skule, arbeidsplass), viser appen stopp innan 1,5 km med gangtid rekna langs vegane, og nye stopp får ekte gangtid.
- **Reiser**: frå ein stad til ein annan. Appen samanliknar alle avgangar frå stoppa dine og sorterer etter når du er framme dør til dør.
- **Ferjesamband**: éi oppføring for begge retningar (t.d. «A ⇄ B»). Søk opp kaien og vel kaien på andre sida, så viser appen berre ferjer frå kaien du er ved. «Snu» byter side. Vil du, kan appen velje kai etter posisjonen din. Posisjonen blir då berre samanlikna med kaiane på eininga di og verken lagra eller sendt.
- **Følg bussen**: trykk på ein avgang, så viser kartet kvar bussen eller båten er no, med forseinking. Posisjonane kjem frå Entur sitt sanntids-API for køyretøy. Ikkje alle sender (til dømes Bybanen), og mange sender først når turen har starta.
- **Søk og kart**: finn stopp med søk (Entur Geocoder) eller på kartet (OpenStreetMap / Leaflet).
- **Del med familien**: delingslenka inneheld stader, stopp og reiser i `#`-delen av adressa, som aldri blir sendt til nokon server.

## Personvern

Ingen konto, ingen server, ingen sporing. Oppsettet blir lagra i `localStorage` i nettlesaren din.
Kvar ein stad er (valfritt, t.d. adressa eller arbeidsplassen) blir berre lagra i nettlesaren og er aldri med i delingslenka. Punktet blir sendt til Entur når appen finn stopp i nærleiken og reknar gangtid.
Appen sender stopp-ID-ar til Entur for å hente avgangar (og ID-en til turen du følgjer på kartet), og kartutsnittet til OpenStreetMap for å hente kartfliser.

## Køyre

Appen ligg på **https://lektorodd.github.io/neste/**. Opne adressa på telefonen og vel «Legg til på Heim-skjerm» (iPhone) eller «Installer app» (Android). Appen opnar då i eige vindauge utan adresselinje.

Éi fil: `index.html`. Ho kan òg liggje på Cloudflare Pages eller ein annan statisk vert. `.nojekyll` gjer at GitHub Pages serverer filene som dei er.

API-kall identifiserer seg med `ET-Client-Name: lektorodd-neste`. Lagar du din eigen variant, bytt til `<organisasjon>-<app>`.

## Lisens

Koden er under [MIT-lisensen](LICENSE). Avgangsdata frå Entur er under [NLOD](https://data.norge.no/nlod/no/2.0), kartdata © OpenStreetMap-bidragsytarar ([ODbL](https://www.openstreetmap.org/copyright)).
