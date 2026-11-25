"""Røyktest med påfunne Entur-svar.

Køyr:  pip install playwright && playwright install chromium
       python tests/mock_test.py
Skjermbilete hamnar i tests/out/. Testen går gjennom oppsettet
(søk, legg til stopp, ny stad, reise + retur), reisevisinga og
følgjekartet (Leaflet frå cdnjs; blir hoppa over utan nett).
"""
import json, datetime as dt, pathlib
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "out"; OUT.mkdir(parents=True, exist_ok=True)
now = dt.datetime.now().astimezone()
iso = lambda m: (now + dt.timedelta(minutes=m)).isoformat()

A, B, HUB, HUB_KAI = "NSR:StopPlace:1001", "NSR:StopPlace:1002", "NSR:StopPlace:2001", "NSR:StopPlace:2002"
GEO = {"Testvik": [(A, "Testvik øvre", "onstreetBus"), (B, "Testvik nedre", "onstreetBus")],
       "Sentrum": [(HUB, "Sentrum terminal", "busStation")]}

def geo(route):
    q = parse_qs(urlparse(route.request.url).query)["text"][0]
    f = [{"geometry": {"coordinates": [5.3, 60.4]},
          "properties": {"id": i, "name": n, "label": n + ", Testby", "category": [c]}}
         for k, v in GEO.items() if q.lower() in k.lower() for i, n, c in v]
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"features": f}))

def call(o, line, dep, arr, delay=0, occ="noData", board=True, alight=True):
    # Som hos Entur: stoppa vidare er barne-stopp (kai) med stoppet frå geocoderen som parent.
    return {"realtime": True, "cancellation": False, "forBoarding": board, "quay": {"latitude": 60.0, "longitude": 5.0},
            "aimedDepartureTime": iso(dep - delay),
            "expectedDepartureTime": iso(dep), "occupancyStatus": occ,
            "destinationDisplay": {"frontText": "Sentrum"},
            "serviceJourney": {"id": f"T:SJ:{line}{dep}", "line": {"publicCode": line, "transportMode": "bus"}},
            "serviceJourneyEstimatedCalls": {"next": [
                {"forAlighting": alight, "quay": {"stopPlace": {"id": HUB_KAI, "parent": {"id": HUB}}},
                 "aimedArrivalTime": iso(arr), "expectedArrivalTime": iso(arr)}]}}

def jp(route):
    q = json.loads(route.request.post_data)["query"]
    d = {}
    for i in range(4):
        if f"g{i}:" not in q:
            continue
        sid = q.split(f'g{i}:stopPlace(id:"')[1].split('"')[0]
        mins = (3, 12, 25) if sid == A else (9, 24)
        line = "1" if sid == A else "1E"
        calls = [call(sid, line, m, m + 19, delay=2 if m == 12 else 0,
                      occ="fewSeatsAvailable" if m == 12 else "noData") for m in mins]
        if sid == A:  # skal ikkje visast: set ikkje av i Sentrum / tek ikkje på her
            calls += [call(sid, "X9", 5, 20, alight=False), call(sid, "Y9", 6, 21, board=False)]
        d[f"g{i}"] = {"estimatedCalls": calls}
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"data": d}))

def veh(route):
    # Påfunnen posisjon: berre linje 1 sender, 1E sender ikkje (som Bybanen).
    q = json.loads(route.request.post_data)["query"]
    sj = q.split('serviceJourneyId:"')[1].split('"')[0]
    v = [{"location": {"latitude": 60.01, "longitude": 5.01}, "delay": 120.0,
          "lastUpdated": now.isoformat()}] if sj.startswith("T:SJ:1") and not sj.startswith("T:SJ:1E") else []
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"data": {"vehicles": v}}))

PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")

with sync_playwright() as p:
    import os
    b = p.chromium.launch(executable_path=os.environ.get("CHROME") or None)
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, color_scheme="dark")
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/geocoder/**", geo)
    pg.route("**/journey-planner/**", jp)
    pg.route("**/realtime/v2/vehicles/**", veh)
    pg.route("**/tile.openstreetmap.org/**", lambda r: r.fulfill(status=200, content_type="image/png", body=PNG))
    pg.goto((ROOT / "index.html").as_uri()); pg.wait_for_timeout(400)

    def pick(card, text, n):
        s = pg.locator("[data-act=search]").nth(card); s.fill(text); pg.wait_for_timeout(600)
        pg.locator("[data-act=pick]").nth(n).click(); pg.wait_for_timeout(200)

    pick(0, "Testvik", 0); pick(0, "Testvik", 1)
    pg.click("text=+ Ny stad"); pg.wait_for_timeout(200)
    n = pg.locator("[data-act=pname]").nth(1); n.fill("Sentrum"); n.dispatch_event("change")
    pick(1, "Sentrum", 0)
    pg.click("text=+ Ny reise"); pg.wait_for_timeout(200)
    pg.click("[data-act=trev]"); pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / "setup.png"), full_page=True)
    pg.click("[data-act=done]"); pg.wait_for_timeout(800)
    pg.screenshot(path=str(OUT / "trip.png"), full_page=True)
    assert pg.locator(".hero .big").count() == 1, "manglar hovudboks"
    assert pg.locator(".row").count() == 5, "feil tal på rader"
    pills = pg.locator(".pill").all_inner_texts()
    assert "X9" not in pills and "Y9" not in pills, "viste avgang utan på-/avstiging"

    # Følg ein tur på kartet (Leaflet frå cdnjs; fliser og posisjonar er påfunne)
    pg.locator(".row", has_text="1E").first.click(); pg.wait_for_timeout(2500)
    note = pg.locator("#mapNote").inner_text()
    if "lasta ikkje" in note:
        print("Hoppar over kartdelen: Leaflet lasta ikkje (utan nett?)")
    else:
        assert pg.locator("#map.on").count() == 1, "kartet opna ikkje"
        assert "Ingen posisjon" in note, "manglar melding utan posisjon: " + note
        assert pg.locator(".bus-ic").count() == 0
        pg.click("[data-act=mapClose]"); pg.wait_for_timeout(200)
        pg.locator(".row .pill", has_text="1").filter(has_not_text="E").first.click(); pg.wait_for_timeout(1500)
        note = pg.locator("#mapNote").inner_text()
        assert pg.locator(".bus-ic").count() == 1, "bussen vart ikkje vist"
        assert "2 min forseinka" in note, "feil statustekst: " + note
        assert pg.locator("[data-act=mapStops]").is_hidden(), "legg-til-knappane synest i følgjemodus"
        pg.screenshot(path=str(OUT / "follow.png"))
        pg.click("[data-act=mapClose]"); pg.wait_for_timeout(200)
        assert pg.locator("#map.on").count() == 0
    b.close()
    print("Feil i sida:", errs or "ingen")
    assert not errs
