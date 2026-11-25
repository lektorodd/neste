"""Røyktest med påfunne Entur-svar.

Køyr:  pip install playwright && playwright install chromium
       python tests/mock_test.py
Skjermbilete hamnar i tests/out/. Testen går gjennom oppsettet
(søk, legg til stopp, ny stad, reise + retur), reisevisinga, linjefilteret, avvik, rekkjefølgja, QR-koden, overgangar (blanda med direkte avgangar,
minste bytetid, linjefilter på første tur, mellomlagring),
følgjekartet (Leaflet frå cdnjs; blir hoppa over utan nett), kvar ein
stad er (stopp i nærleiken med gangtid), ferjesamband (snu kai, og kai vald etter påfunnen posisjon) og
reise vald etter påfunnen posisjon (sist brukte reise frå staden, eit eige val står til du er ved ein annan
stad, kort venting på posisjonen og melding når reisa blir bytt etterpå), kort delingslenke
(komprimert, gamle lenker, utan CompressionStream/DecompressionStream) og QR-skannaren (falskt kamera med påfunnen
QR-kode; BarcodeDetector påfunnen, html5-qrcode frå cdnjs blir hoppa over utan nett). Sjekkar òg
manifest og ikon.
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
       "Sentrum": [(HUB, "Sentrum terminal", "busStation")],
       "Testkai": [("NSR:StopPlace:3001", "Testkai ferjekai", "harbourPort")],
       "Nordvik": [("NSR:StopPlace:1004", "Nordvik", "onstreetBus")]}
# Påfunnen gangtid (sekund) og avstand (meter) frå det påfunne punktet "Testgata 1".
WALK = {A: 240, B: 360, "NSR:StopPlace:1003": 545, "NSR:StopPlace:1004": 660}
NEAR = [(A, "Testvik øvre", 200), (B, "Testvik nedre", 350), ("NSR:StopPlace:1003", "Testvik sør", 500)]
# Påfunne ferjekaiar: barne-stopp 31xx med forelder 30xx, og kvar sin påfunne posisjon.
KAI = {"NSR:StopPlace:3001": ("Testkai ferjekai", 60.0), "NSR:StopPlace:3002": ("Motkai ferjekai", 60.1)}
# Påfunne linjer ved stoppa. «1E» finst òg ved eit anna stopp med ein annan ID, som ikkje skal med i filteret.
LINES = {A: ["1", "X9", "Y9"], B: ["1E"], "NSR:StopPlace:1004": ["1E-anna"]}
queries = []

def geo(route):
    qs = parse_qs(urlparse(route.request.url).query); q = qs["text"][0]
    if qs.get("layers") == ["address"]:
        f = [{"geometry": {"coordinates": [5.0, 60.0]}, "properties": {"id": "T:Adr:1", "name": "Testgata 1",
              "label": "Testgata 1, Testby", "category": ["vegadresse"]}}] if "testgata" in q.lower() else []
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"features": f}))
    f = [{"geometry": {"coordinates": [5.3, 60.4]},
          "properties": {"id": i, "name": n, "label": n + ", Testby", "category": [c]}}
         for k, v in GEO.items() if q.lower() in k.lower() for i, n, c in v]
    route.fulfill(status=200, content_type="application/json", body=json.dumps({"features": f}))

# Påfunne avvik (SIRI SX). Samandraget kjem med avgangen; heile teksten blir henta ved trykk.
SIT = {"T:SituationNumber:1": [{"value": "Diversion", "language": "en"}, {"value": "Omkøyring forbi Testvik", "language": "no"}],
       "T:SituationNumber:2": [{"value": "Heisen er ute av drift", "language": None}],
       "T:SituationNumber:3": [{"value": "Omkøyring forbi Testvik", "language": "nn"}]}  # same samandrag, eige avvik
SIT_FULL = {"T:SituationNumber:1": "Bussen køyrer ein annan veg på grunn av påfunne vegarbeid.",
            "T:SituationNumber:2": "Bruk trappa.", "T:SituationNumber:3": "Same omkøyring."}

def call(o, line, dep, arr, delay=0, occ="noData", board=True, alight=True, sit=()):
    # Som hos Entur: stoppa vidare er barne-stopp (kai) med stoppet frå geocoderen som parent.
    return {"realtime": True, "cancellation": False, "forBoarding": board, "quay": {"latitude": 60.0, "longitude": 5.0},
            "aimedDepartureTime": iso(dep - delay),
            "expectedDepartureTime": iso(dep), "occupancyStatus": occ,
            "destinationDisplay": {"frontText": "Sentrum"},
            "serviceJourney": {"id": f"T:SJ:{line}{dep}", "line": {"publicCode": line, "transportMode": "bus"}},
            "situations": [{"situationNumber": n, "summary": SIT[n]} for n in sit],
            "serviceJourneyEstimatedCalls": {"next": [
                {"forAlighting": alight, "quay": {"stopPlace": {"id": HUB_KAI, "parent": {"id": HUB}}},
                 "aimedArrivalTime": iso(arr), "expectedArrivalTime": iso(arr)}]}}

def ferry_call(sid, line, dep, mode="water"):
    other = next(k for k in KAI if k != sid)
    return {"realtime": True, "cancellation": False, "forBoarding": True, "quay": {"latitude": KAI[sid][1], "longitude": 5.0},
            "aimedDepartureTime": iso(dep), "expectedDepartureTime": iso(dep), "occupancyStatus": "noData",
            "destinationDisplay": {"frontText": KAI[other][0]},
            "serviceJourney": {"id": f"T:SJ:{line}-{sid[-1]}-{dep}", "line": {"publicCode": line, "transportMode": mode}},
            "serviceJourneyEstimatedCalls": {"next": [
                {"forAlighting": True, "quay": {"stopPlace": {"id": other.replace(":30", ":31"), "name": KAI[other][0],
                  "latitude": KAI[other][1], "longitude": 5.0, "parent": {"id": other, "name": KAI[other][0],
                  "latitude": KAI[other][1], "longitude": 5.0}}},
                 "aimedArrivalTime": iso(dep + 20), "expectedArrivalTime": iso(dep + 20)}]}}

FJERN = "NSR:StopPlace:4001"  # påfunnen stad utan direkte avgang frå Testvik

def leg(line, dep, arr, frm, to, sj=None, aimed=None, sit=(), fsp=None, tsp=None, seated=False):
    """Ein etappe i trip-svaret. fsp/tsp: påfunne stoppestader (til minste bytetid), seated: bli sitjande (ikkje bytte)."""
    if line is None:
        return {"mode": "foot", "line": None, "aimedStartTime": iso(dep), "expectedStartTime": iso(dep), "expectedEndTime": iso(arr),
                "fromPlace": {"name": frm, "quay": None}, "toPlace": {"name": to}}
    return {"mode": "bus", "aimedStartTime": iso(aimed if aimed is not None else dep), "expectedStartTime": iso(dep), "expectedEndTime": iso(arr),
            "realtime": True, "fromPlace": {"name": frm, "quay": {"latitude": 60.0, "longitude": 5.0, "stopPlace": {"id": fsp} if fsp else None}},
            "toPlace": {"name": to, "quay": {"stopPlace": {"id": tsp} if tsp else None}},
            "line": {"publicCode": line, "transportMode": "bus"}, "serviceJourney": {"id": sj or f"T:SJ:{line}-{dep}"},
            "fromEstimatedCall": {"destinationDisplay": {"frontText": "Sentrum" if line != "7" else "Fjernby"}, "cancellation": False},
            "situations": [{"situationNumber": n, "summary": SIT[n]} for n in sit],
            "interchangeTo": {"staySeated": True} if seated else None}

def trips(frm):
    """Påfunne reiser med bytte i Sentrum. Berre den første typen (eitt bytte, utan gange først/sist) skal visast."""
    first = ("1", 10, 25, "Testvik øvre") if frm == A else ("1E", 14, 25, "Testvik nedre")
    ok = [leg(first[0], first[1], first[2], first[3], "Sentrum terminal", aimed=first[1] - 1),
          leg(None, first[2], first[2] + 3, "Sentrum terminal", "Sentrum torg"),
          leg("7", 31, 50, "Sentrum torg", "Fjernby", sj="T:SJ:7-31", sit=["T:SituationNumber:2"])]
    walk_first = [leg(None, 0, 4, first[3], "Anna stopp")] + ok
    two = [ok[0], leg("2", 27, 29, "Sentrum terminal", "Sentrum torg"), ok[2]]
    return [{"legs": ok}, {"legs": walk_first}, {"legs": two}]

MID, MID_AUST = "T:SP:Midtvegen", "T:SP:Midtvegen-aust"  # påfunne stoppestader for bytte
MIX = {"on": False}  # bytte til Sentrum, blanda med dei direkte avgangane

def trips_mix():
    """Påfunne reiser med bytte frå Testvik øvre til Sentrum, når det òg finst direkte avgangar."""
    s = lambda line, dep, arr, frm="Midtvegen", **k: leg(line, dep, arr, frm, "Sentrum terminal", fsp=MID if frm == "Midtvegen" else MID_AUST, **k)
    first = lambda sj="T:SJ:3-8", dep=8, arr=15, **k: leg("3", dep, arr, "Testvik øvre", "Midtvegen", sj=sj, tsp=MID, **k)
    return [{"legs": [first(), s("4", 18, 26)]},                                   # 3 min på same stoppestad: ok
            {"legs": [first(), s("5", 17, 24)]},                                   # 2 min: for kort
            {"legs": [first(), leg(None, 15, 16, "Midtvegen", "Midtvegen aust"), s("6", 19, 25, "Midtvegen aust")]},  # 4 min med 1 min gange: under 5
            {"legs": [first(), leg(None, 15, 17, "Midtvegen", "Midtvegen aust"), s("6", 21, 27, "Midtvegen aust")]},  # 6 min med 2 min gange: ok
            {"legs": [first(seated=True), s("3B", 15, 22)]},                       # blir sitjande: ikkje eit bytte
            {"legs": [first(sj="T:SJ:112", dep=12, arr=14), s("8", 18, 23)]},      # bussen går sjølv til Sentrum
            {"legs": [first(sj="T:SJ:9-6", dep=6, arr=12), s("10", 16, 34)]}]     # dominert av linje 1 kl. +12

def jp(route):
    q = json.loads(route.request.post_data)["query"]
    queries.append(q)
    d = {}
    if "nearest(" in q:
        d["nearest"] = {"edges": [{"node": {"distance": m, "place": {"id": i, "name": n, "transportMode": ["bus"]}}} for i, n, m in NEAR]}
    for i in range(30):
        if f"w{i}:trip(" in q:
            sid = q.split(f"w{i}:trip(")[1].split('place:"')[1].split('"')[0]
            d[f"w{i}"] = {"tripPatterns": [{"duration": WALK[sid]}]}
    if "situation(situationNumber:" in q:
        n = q.split('situationNumber:"')[1].split('"')[0]
        d["situation"] = {"description": [{"value": "Full text", "language": "en"}, {"value": SIT_FULL[n], "language": "nob"}],
                          "advice": [], "infoLinks": [{"uri": "https://example.org/avvik", "label": "Meir om avviket"},
                                                      {"uri": "javascript:alert(1)", "label": "farleg"}],
                          "validityPeriods": [{"startTime": iso(-60), "endTime": iso(600)}]}
    for k in range(9):  # reiser med bytte
        if f"x{k}:trip(" in q:
            seg = q.split(f"x{k}:trip(")[1]
            frm, to = seg.split('place:"')[1].split('"')[0], seg.split('place:"')[2].split('"')[0]
            d[f"x{k}"] = {"tripPatterns": trips(frm) if to == FJERN else trips_mix() if to == HUB and frm == A and MIX["on"] else []}
    for i in range(4):  # linjene ved eit stopp (til linjefilteret)
        if f"l{i}:stopPlace(" in q:
            sid = q.split(f'l{i}:stopPlace(id:"')[1].split('"')[0]
            d[f"l{i}"] = {"quays": [{"lines": [{"id": "T:Line:" + c, "publicCode": c} for c in LINES.get(sid, [])]}]}
    if q.startswith("{stopPlace(id:"):  # oppslag av ferjesamband frå ein kai
        sid = q.split('stopPlace(id:"')[1].split('"')[0]
        d["stopPlace"] = {"name": KAI[sid][0], "latitude": KAI[sid][1], "longitude": 5.0,
                          "estimatedCalls": [ferry_call(sid, "F1", m) for m in (10, 40)]}
    for i in range(4):
        if f"g{i}:" not in q:
            continue
        seg = q.split(f"g{i}:")[1].split("realtime")[0]
        sid = seg.split('stopPlace(id:"')[1].split('"')[0]
        only = json.loads(seg.split("lines:")[1].split("}")[0]) if "lines:" in seg else None
        if sid in KAI:  # ferje + ein buss som køyrer med ferja (skal filtrerast bort)
            d[f"g{i}"] = {"estimatedCalls": [ferry_call(sid, "F1", m) for m in (7, 37)] + [ferry_call(sid, "C9", 8, "coach")]}
            continue
        mins = (3, 12, 25) if sid == A else (9, 24)
        line = "1" if sid == A else "1E"
        calls = [call(sid, line, m, m + 19, delay=2 if m == 12 else 0,
                      occ="fewSeatsAvailable" if m == 12 else "noData",
                      sit={9: ["T:SituationNumber:1"], 12: ["T:SituationNumber:2"], 24: ["T:SituationNumber:3"]}.get(m, [])) for m in mins]
        if sid == A:  # skal ikkje visast: set ikkje av i Sentrum / tek ikkje på her
            calls += [call(sid, "X9", 5, 20, alight=False), call(sid, "Y9", 6, 21, board=False)]
        if only is not None:  # som Entur: berre avgangar med desse line-ID-ane
            calls = [c for c in calls if "T:Line:" + c["serviceJourney"]["line"]["publicCode"] in only]
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

def check_manifest():
    """Manifestet er gyldig JSON, og kvart ikon finst med rett storleik (PNG-storleik les vi frå IHDR)."""
    import struct
    m = json.loads((ROOT / "manifest.webmanifest").read_text())
    assert m["display"] == "standalone" and m["start_url"] == "./"
    assert any(i.get("purpose") == "maskable" for i in m["icons"]), "manglar maskable-ikon"
    for i in m["icons"]:
        f = ROOT / i["src"]; assert f.exists(), f"manglar {i['src']}"
        if i["type"] == "image/png":
            w, h = struct.unpack(">II", f.read_bytes()[16:24])
            assert i["sizes"] == f"{w}x{h}", f"{i['src']}: {w}x{h}, manifestet seier {i['sizes']}"
    html = (ROOT / "index.html").read_text()
    for ref in ("manifest.webmanifest", "favicon.ico", "ikon/neste.svg", "ikon/neste-180.png"):
        assert ref in html and (ROOT / ref).exists(), f"{ref} manglar i index.html eller på disk"

check_manifest()

# Falskt kamera til QR-skannaren: ein påfunnen QR-kode (versjon 9, feilretting M) med ei påfunnen delingslenke
# (2 stader, 1 reise). Modulane er rekna ut på førehand, så testdata treng ikkje nett.
SCAN_LINK = "https://example.org/neste/#oppsett=zJc0xDoAgEATAr5irrwB8CnYXCowUBCERThJ_Zu_HPLHdnc0SERwaEGzypTT2GyCRVkojLKFxj2l67l4D4OycQ9EG_mq9PmoGtaFwPfPEoeZY_A5o3ODiWfy4kKVkLw"
SCAN_QR = (
    "1fc7e96bd6ec7f 1044387598a641 174d0a4ed7ea5d 1743eb38cda55d 174e2ffff06c5d "
    "1050031117a441 1fd5555555557f a81d1299200 12d280ff01b7a0 1e179ac800029d "
    "702fdebeabda 110209a7fbd906 134b16c93f1c70 1e02f6f37da257 15ceb597f9dc37 "
    "4b614401af491 1cd6658efb6313 1e1a60c53b691b 17f0f1633f5273 1e35d748a3b243 "
    "11fe1856297d9c f823a08031028 bea27bc259446 e3c6a848c484d 5fad27fb5f3fa "
    "b187f3135011b 1d5b4435055353 91217b12fef13 1ffadc9f4b65f1 e9b629aa35b6f "
    "14dc2b162a93db 88f84299a89f2 1ee166f06df40d 1905c0908003c0 194d4c8ecb8f16 "
    "1d02f43cd750c4 19da80eeb3f9ac 1d219e7f839820 1d13ba3a722c7 e208df445f593 "
    "104625d7972aea 13a1bfbca36b84 1bf3c900a279df c0b638dfdeeda 257d0ff6975f4 "
    "14ab31020911 1fc2ae1556995e 105e62311ac114 174e2f7fd73ffa 175af47825b122 "
    "174c16c5cdda50 104a64427aa292 1fd05afb1365e2 ").split()

def fake_camera(path, scale=8, quiet=4):
    """Skriv QR-koden som Y4M-video (gråtone) til --use-file-for-fake-video-capture."""
    n = len(SCAN_QR); assert n == 53; size = (n + 2 * quiet) * scale
    bits = [format(int(h, 16), f"0{n}b") for h in SCAN_QR]
    y = bytearray()
    for r in range(size):
        mr = r // scale - quiet
        for c in range(size):
            mc = c // scale - quiet
            y.append(16 if 0 <= mr < n and 0 <= mc < n and bits[mr][mc] == "1" else 235)
    frame = b"FRAME\n" + bytes(y) + bytes([128]) * (size * size // 2)
    path.write_bytes(f"YUV4MPEG2 W{size} H{size} F10:1 Ip A1:1 C420jpeg\n".encode() + frame * 3)

CAM = OUT / "qr_kamera.y4m"; fake_camera(CAM)

with sync_playwright() as p:
    import os
    b = p.chromium.launch(executable_path=os.environ.get("CHROME") or None,
                          args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream", f"--use-file-for-fake-video-capture={CAM}"])
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, color_scheme="dark",
                        permissions=["geolocation"], geolocation={"latitude": 60.08, "longitude": 5.01})  # påfunne, nærast Motkai
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/geocoder/**", geo)
    pg.route("**/journey-planner/**", jp)
    pg.route("**/realtime/v2/vehicles/**", veh)
    pg.route("**/tile.openstreetmap.org/**", lambda r: r.fulfill(status=200, content_type="image/png", body=PNG))
    pg.goto((ROOT / "index.html").as_uri()); pg.wait_for_timeout(400)
    dq = lambda: next(x for x in reversed(queries) if "estimatedCalls(numberOfDepartures" in x and ":stopPlace(" in x)  # siste avgangsspørjing

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
    xq = [x for x in queries if "x0:trip(" in x]
    assert xq and "transferSlack:180" in xq[-1] and "numTripPatterns:5" in xq[-1], "bytte-søket skal køyrast også når det finst direkte avgangar"
    pills = pg.locator(".pill").all_inner_texts()
    assert "X9" not in pills and "Y9" not in pills, "viste avgang utan på-/avstiging"

    # Avvik: samandrag på norsk i helten og på radene, éi oppføring per avvik, heile teksten ved trykk
    assert "situations{situationNumber summary{value language}}" in dq()
    assert "description" not in dq().split("situations{")[1], "heile teksten skal ikkje hentast med avgangane"
    assert "Omkøyring forbi Testvik" in pg.locator(".hero .avb").inner_text(), pg.locator(".hero").inner_text()
    assert pg.locator(".row .av").count() == 3
    sit = pg.locator(".card .sit")
    assert sit.count() == 2, sit.all_inner_texts()
    assert "1E" in sit.nth(0).inner_text() and "Heisen er ute av drift" in sit.nth(1).inner_text()
    sit.nth(0).click(); pg.wait_for_timeout(400)
    dlg = pg.locator("#dlg").inner_text()
    assert "påfunne vegarbeid" in dlg and "Full text" not in dlg and "Meir om avviket" in dlg and "farleg" not in dlg, dlg
    assert "Gjeld til" in dlg
    pg.screenshot(path=str(OUT / "avvik.png"))
    n = len(queries); pg.click("#dlg [data-act=impNo]"); pg.locator(".hero .avb").click(); pg.wait_for_timeout(300)
    assert len(queries) == n and "påfunne vegarbeid" in pg.locator("#dlg").inner_text(), "heile teksten skal liggje i minnet"
    pg.click("#dlg [data-act=impNo]")

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

    # Linjefilter på serveren: berre line-ID-ar som går frå stoppa, og stopp utan linja blir ikkje spurde
    pg.click("#setup"); pg.wait_for_timeout(300)
    lf = pg.locator(".trip [data-act=tlines]").first
    lf.fill("1e"); lf.dispatch_event("change"); pg.click("[data-act=done]"); pg.wait_for_timeout(800)
    assert any("l0:stopPlace(" in x and "quays{lines{id publicCode}}" in x for x in queries), "slo ikkje opp linjene"
    q = dq()
    assert 'lines:["T:Line:1E"]' in q and "g1:" in q and "g0:" not in q, q
    assert pg.locator(".row .pill").all_inner_texts() == ["1E", "1E"], pg.locator(".row .pill").all_inner_texts()
    n = len(queries); pg.click("#status"); pg.wait_for_timeout(500)
    assert len(queries) == n + 1, "linjene skal liggje i minnet, ikkje slåast opp på nytt"
    pg.click("#setup"); pg.wait_for_timeout(300)
    lf = pg.locator(".trip [data-act=tlines]").first
    lf.fill("77"); lf.dispatch_event("change"); pg.click("[data-act=done]"); pg.wait_for_timeout(800)
    assert "Fann ikkje linje 77 ved stoppa i Heim" in pg.locator("#app").inner_text()
    pg.click("#setup"); pg.wait_for_timeout(300)
    lf = pg.locator(".trip [data-act=tlines]").first
    lf.fill(""); lf.dispatch_event("change"); pg.click("[data-act=done]"); pg.wait_for_timeout(800)
    assert pg.locator(".row").count() == 5 and "filters" not in dq()

    # Kvar er staden: søk adresse, få stopp i nærleiken med gangtid frå Entur
    pg.click("#setup"); pg.wait_for_timeout(300)
    heim = pg.locator("[data-place]").first
    heim.locator("[data-act=where]").click(); pg.wait_for_timeout(200)
    pg.locator("#dlg [data-act=search]").fill("Testgata"); pg.wait_for_timeout(600)
    pg.locator("[data-act=wpick]").first.click(); pg.wait_for_timeout(800)
    items = pg.locator("#dlg [data-act=ntog]")
    assert items.count() == 3, "feil tal på stopp i nærleiken"
    assert "4 min å gå" in items.nth(0).inner_text() and "10 min å gå" in items.nth(2).inner_text(), items.all_inner_texts()
    assert items.nth(0).get_attribute("aria-pressed") == "true", "stopp som alt er lagt til skal vere merkte"
    items.nth(2).click(); pg.wait_for_timeout(200)  # Testvik sør
    assert items.nth(2).get_attribute("aria-pressed") == "true"
    pg.click("[data-act=ndone]"); pg.wait_for_timeout(300)
    assert "Ved Testgata 1" in heim.inner_text(), heim.inner_text()
    walks = heim.locator("[data-act=walk]")
    assert walks.count() == 3 and walks.nth(2).input_value() == "10", [walks.nth(i).input_value() for i in range(walks.count())]
    # Stopp lagt til med vanleg søk får ekte gangtid når staden har eit punkt
    heim.locator("[data-act=search]").fill("Nordvik"); pg.wait_for_timeout(600)
    heim.locator("[data-act=pick]").first.click(); pg.wait_for_timeout(800)
    assert heim.locator("[data-act=walk]").nth(3).input_value() == "11"
    cfg = pg.evaluate("localStorage.getItem('neste.cfg')")
    assert "Testgata" not in cfg and "60.0" not in cfg, "punktet skal ikkje liggje i oppsettet (delingslenka)"
    assert "Testgata 1" in pg.evaluate("localStorage.getItem('neste.pts')")
    pg.click("[data-act=done]"); pg.wait_for_timeout(500)

    # Ferjesamband: éi oppføring, ferjer frå kaien du er ved, og Snu
    pg.click("#setup"); pg.wait_for_timeout(300)
    pg.click("text=+ Ferjesamband"); pg.wait_for_timeout(200)
    pg.locator("#dlg [data-act=search]").fill("Testkai"); pg.wait_for_timeout(600)
    pg.locator("[data-act=fpick]").first.click(); pg.wait_for_timeout(500)
    assert "Motkai ferjekai" in pg.locator("#dlg").inner_text(), "fann ikkje kaien på andre sida"
    pg.locator("[data-act=froute]").first.click(); pg.wait_for_timeout(800)
    assert pg.locator("#chips [aria-pressed=true]").inner_text() == "Testkai ⇄ Motkai"
    hero = pg.locator(".hero .k").inner_text()
    assert hero.startswith("Frå Testkai til Motkai"), hero
    assert "transportMode:water" in dq(), "ferjefilteret vart ikkje sendt"
    pills = pg.locator(".row .pill").all_inner_texts()
    assert pills == ["F1", "F1"], f"skulle berre vise ferjer: {pills}"
    pg.screenshot(path=str(OUT / "ferry.png"), full_page=True)
    pg.click("[data-act=flip]"); pg.wait_for_timeout(600)
    assert pg.locator(".hero .k").inner_text().startswith("Frå Motkai til Testkai")
    assert 'g0:stopPlace(id:"NSR:StopPlace:3002")' in dq()
    pg.click("[data-act=flip]"); pg.wait_for_timeout(600)
    assert pg.locator(".hero .k").inner_text().startswith("Frå Testkai")

    # Vel kai etter (påfunnen) posisjon ved Motkai
    pg.click("#setup"); pg.wait_for_timeout(300)
    assert pg.locator(".trip").count() == 2, "sambandet skal ikkje liggje mellom vanlege reiser"
    assert pg.locator("[data-act=auto]").count() == 1, "manglar innstillinga for posisjon"
    pg.check("[data-act=auto]"); pg.wait_for_timeout(300)
    pg.click("[data-act=done]"); pg.wait_for_timeout(1200)
    hero = pg.locator(".hero .k").inner_text()
    assert hero.startswith("Frå Motkai til Testkai") and "posisjonen din" in hero, hero
    stored = pg.evaluate("JSON.stringify(Object.assign({}, localStorage))")
    assert "60.08" not in stored and "5.01" not in stored, "posisjonen vart lagra"

    # Rekkjefølgje: opp/ned for alle reiser (vanlege og samband), og den første opnar utan lagra val
    pg.click("#setup"); pg.wait_for_timeout(300)
    order = lambda: [x.split("\n")[1] for x in pg.locator("#order .ord").all_inner_texts()]
    assert order() == ["Heim → Sentrum", "Sentrum → Heim", "Testkai ⇄ Motkai"], order()
    assert pg.locator("#order .ord").first.locator("[data-act=tup]").is_disabled()
    assert pg.locator("#order .ord").last.locator("[data-act=tdown]").is_disabled()
    pg.locator("#order .ord").last.locator("[data-act=tup]").click(); pg.wait_for_timeout(200)
    assert pg.evaluate("document.activeElement.dataset.act") == "tup", "fokus skal bli verande på knappen"
    pg.keyboard.press("Enter"); pg.wait_for_timeout(200)  # flytt han øvst med tastaturet
    assert order() == ["Testkai ⇄ Motkai", "Heim → Sentrum", "Sentrum → Heim"], order()
    assert pg.evaluate("document.activeElement.dataset.act") == "tdown", "øvst: fokus til ned-knappen"
    pg.locator("#order .ord").nth(1).locator("[data-act=tdown]").click(); pg.wait_for_timeout(200)
    assert order() == ["Testkai ⇄ Motkai", "Sentrum → Heim", "Heim → Sentrum"], order()
    pg.screenshot(path=str(OUT / "order.png"), full_page=True)
    pg.click("[data-act=done]"); pg.wait_for_timeout(300)
    assert pg.locator("#chips button").all_inner_texts() == ["Testkai ⇄ Motkai", "Sentrum → Heim", "Heim → Sentrum"]
    pg.locator("#chips button").nth(2).click(); pg.wait_for_timeout(300)
    pg.reload(); pg.wait_for_timeout(500)
    assert pg.locator("#chips [aria-pressed=true]").inner_text() == "Heim → Sentrum", "lagra val skal haldast"
    pg.evaluate("localStorage.removeItem('neste.cur')"); pg.reload(); pg.wait_for_timeout(500)
    assert pg.locator("#chips [aria-pressed=true]").inner_text() == "Testkai ⇄ Motkai", "den første skal opne utan lagra val"

    # Gamalt heimepunkt blir flytta til staden «Heim»
    pg.evaluate("() => { localStorage.setItem('neste.home', JSON.stringify({lat:60.2,lon:5.2})); localStorage.removeItem('neste.pts') }")
    pg.reload(); pg.wait_for_timeout(500)
    heim_id = pg.evaluate("JSON.parse(localStorage.getItem('neste.cfg')).places.find(p=>p.name==='Heim').id")
    moved = pg.evaluate("JSON.parse(localStorage.getItem('neste.pts'))")
    assert moved.get(heim_id, {}).get("lat") == 60.2, moved
    assert pg.evaluate("localStorage.getItem('neste.home')") is None

    # Overgangar: ingen direkte avgang til Fjernby, så appen søkjer etter reiser med eitt bytte frå kvart stopp
    pg.evaluate("""() => { const c = JSON.parse(localStorage.getItem('neste.cfg'));
        c.places.push({id: 'fj', name: 'Fjernby', stops: [{id: 'NSR:StopPlace:4001', name: 'Fjernby', label: '', mode: 'bus', walk: 2}]});
        c.trips.push({id: 'tf', from: c.places[0].id, to: 'fj', lines: ''}, {id: 'tl', from: c.places[0].id, to: 'fj', lines: '1'});
        localStorage.setItem('neste.cfg', JSON.stringify(c)); localStorage.setItem('neste.cur', JSON.stringify('tf')) }""")
    pg.reload(); pg.wait_for_timeout(1000)
    q = next(x for x in reversed(queries) if "x0:trip(" in x)
    assert "maximumTransfers:2" in q and 'place:"NSR:StopPlace:4001"' in q and "x1:trip(" in q, q[:300]
    walk_a = pg.evaluate("JSON.parse(localStorage.getItem('neste.cfg')).places[0].stops[0].walk")
    t0 = dt.datetime.fromisoformat(q.split('dateTime:"')[1].split('"')[0].replace("Z", "+00:00"))
    assert abs((t0 - dt.datetime.now(dt.timezone.utc)).total_seconds() / 60 - walk_a) < 1.5, "søket skal starte når du er ved stoppet"
    assert pg.locator(".card h2").first.inner_text().startswith("Med eitt bytte")
    rows = pg.locator(".row")
    assert rows.count() == 2, rows.all_inner_texts()
    assert [rows.nth(i).locator(".pill").all_inner_texts() for i in range(2)] == [["1", "7"], ["1E", "7"]]
    assert "bytt på Sentrum terminal → Sentrum torg (6 min)" in rows.first.inner_text(), rows.first.inner_text()
    hero = pg.locator(".hero .s").inner_text()
    assert "bytt til 7 på Sentrum torg" in hero, hero
    assert "Heisen er ute av drift" in rows.first.inner_text(), "avvik på den andre turen skal visast"
    assert pg.locator(".card .sit .ln").all_inner_texts() == ["7"], "avviket gjeld linje 7, ikkje den første bussen"
    pg.screenshot(path=str(OUT / "bytte.png"), full_page=True)
    rows.first.click(); pg.wait_for_timeout(1500)  # følg den første turen
    if "lasta ikkje" not in pg.locator("#mapNote").inner_text():
        assert "Testvik øvre" in pg.locator("#mapNote").inner_text()
        pg.click("[data-act=mapClose]"); pg.wait_for_timeout(200)
    # Linjefilteret gjeld berre første tur: 1 → 7 blir vist, 1E → 7 ikkje
    n = len(queries); pg.locator("#chips button", has_text="Heim → Fjernby").nth(1).click(); pg.wait_for_timeout(800)
    xq = [x for x in queries[n:] if "x0:trip(" in x]
    assert xq and "numTripPatterns:8" in xq[0], "med linjefilter skal appen søkje med fleire forslag"
    rows = pg.locator(".row")
    assert [rows.nth(i).locator(".pill").all_inner_texts() for i in range(rows.count())] == [["1", "7"]], rows.all_inner_texts()

    # Bytte blanda med direkte avgangar, minste bytetid, og mellomlagring av bytte-søket
    MIX["on"] = True
    pg.evaluate("""() => { const c = JSON.parse(localStorage.getItem('neste.cfg'));
        c.trips.push({id: 'tm', from: c.places[0].id, to: c.places[1].id, lines: ''});
        localStorage.setItem('neste.cfg', JSON.stringify(c)); localStorage.setItem('neste.cur', JSON.stringify('tm')) }""")
    n = len(queries); pg.reload(); pg.wait_for_timeout(1200)
    assert sum("x0:trip(" in x for x in queries[n:]) == 1
    assert pg.locator(".card h2").first.inner_text().startswith("Sortert etter når du er framme")
    pills = [r.locator(".pill").all_inner_texts() for r in pg.locator(".row").all()]
    assert ["3", "4"] in pills and ["3", "6"] in pills, pills
    for bad in ("5", "3B", "8", "10"):
        assert not any(bad in p for p in pills), f"bytte med {bad} skulle vore teke bort: {pills}"
    assert any(p == ["1"] for p in pills) and any(p == ["1E"] for p in pills), "dei direkte avgangane manglar"
    assert pg.locator(".row.best .pill").all_inner_texts() == ["3", "4"], "bytet er framme først og skal vere det beste"
    assert "bytt til 4 på Midtvegen" in pg.locator(".hero .s").inner_text()
    pg.screenshot(path=str(OUT / "bytte_blanda.png"), full_page=True)
    n = len(queries); pg.click("#status"); pg.wait_for_timeout(600)
    assert any("estimatedCalls(" in x for x in queries[n:]) and not any("trip(" in x for x in queries[n:]), "bytte-søket skal mellomlagrast"
    pg.evaluate("() => { const n = Date.now; Date.now = () => n() + 160000 }")  # 2 min 40 s seinare
    n = len(queries); pg.click("#status"); pg.wait_for_timeout(600)
    assert any("x0:trip(" in x for x in queries[n:]), "bytte-søket skal køyrast på nytt etter XFER_TTL"
    MIX["on"] = False

    # Vel reise etter kvar du er: påfunne punkt for stadene og påfunne posisjonar
    pg.evaluate("""() => { const c = JSON.parse(localStorage.getItem('neste.cfg')), [h, s] = c.places, pts = {};
        pts[h.id] = {lat: 61.0, lon: 5.0, label: 'Testpunkt heim'}; pts[s.id] = {lat: 61.5, lon: 5.0, label: 'Testpunkt sentrum'};
        localStorage.setItem('neste.pts', JSON.stringify(pts));
        localStorage.setItem('neste.brukt', JSON.stringify({tf: Date.now() - 3600e3, tm: Date.now() - 7200e3}));
        localStorage.setItem('neste.cur', JSON.stringify(c.trips.find(t => t.from === s.id).id)) }""")
    cur = lambda: pg.evaluate("JSON.parse(localStorage.getItem('neste.cur'))")
    ctx.set_geolocation({"latitude": 61.0013, "longitude": 5.0007})  # ved «Heim»
    pg.reload(); pg.wait_for_timeout(1200)
    assert cur() == "tf", "skulle opne den sist brukte reisa frå Heim"
    assert "vald etter posisjonen din" in pg.locator(".hero .k").inner_text(), pg.locator(".hero .k").inner_text()
    assert pg.locator(".switched").count() == 0, "posisjonen kom i tide: ingen melding om bytte"
    pg.screenshot(path=str(OUT / "auto_reise.png"))
    pg.locator("#chips button", has_text="Heim → Sentrum").first.click(); pg.wait_for_timeout(300)  # brukaren vel sjølv
    hs = cur()
    assert "posisjonen din" not in pg.locator(".hero .k").inner_text()
    ctx.set_geolocation({"latitude": 61.5004, "longitude": 5.0})  # ved «Sentrum»
    bg = """m => { Object.defineProperty(document, 'hidden', {configurable: true, get: () => window._h});
        window._h = true; document.dispatchEvent(new Event('visibilitychange'));
        const n = Date.now; Date.now = () => n() + m * 60000; window._h = false; document.dispatchEvent(new Event('visibilitychange')) }"""
    held = pg.evaluate("JSON.parse(localStorage.getItem('neste.held'))")
    assert held["where"].startswith("p:") and set(held) == {"at", "where"}, held
    ctx.set_geolocation({"latitude": 61.0013, "longitude": 5.0007})  # framleis heime
    pg.evaluate(bg, 30); pg.wait_for_timeout(800)
    assert cur() == hs, "eit eige val skal stå så lenge du er ved same stad"
    ctx.set_geolocation({"latitude": 61.5004, "longitude": 5.0})  # ved «Sentrum»
    pg.evaluate("() => new Promise(r => navigator.geolocation.getCurrentPosition(r, r, {maximumAge: 0}))")  # telefonen får ny posisjon
    pg.evaluate(bg, 3); pg.wait_for_timeout(800)
    sh = pg.evaluate("(c => c.trips.find(t => t.from === c.places[1].id).id)(JSON.parse(localStorage.getItem('neste.cfg')))")
    assert cur() == sh, "ved ein annan stad skal reisa veljast etter posisjonen"
    assert pg.evaluate("localStorage.getItem('neste.held')") == "null", "valet skal sleppast når du er ved ein annan stad"
    stored = pg.evaluate("JSON.stringify(Object.assign({}, localStorage))")
    assert "61.0013" not in stored and "61.5004" not in stored and "5.0007" not in stored, "posisjonen vart lagra"
    assert "brukt" not in pg.evaluate("localStorage.getItem('neste.cfg')"), "bruken skal ikkje i oppsettet (delingslenka)"
    ctx.set_geolocation({"latitude": 61.0013, "longitude": 5.0007}); pg.reload(); pg.wait_for_timeout(1000)
    assert cur() == hs, "heime igjen: den sist brukte reisa frå Heim er no den brukaren valde"
    ctx.set_geolocation({"latitude": 63.0, "longitude": 9.0}); pg.reload(); pg.wait_for_timeout(1000)  # langt frå alt
    assert cur() == hs and "posisjonen din" not in pg.locator("#app").inner_text(), "utan stad i nærleiken skal appen gjere som før"
    # Eit eige val går ut etter AUTO_HOLD sjølv om du er ved same stad
    ctx.set_geolocation({"latitude": 61.0013, "longitude": 5.0007}); pg.reload(); pg.wait_for_timeout(1000)
    pg.locator("#chips button", has_text="Heim → Sentrum").first.click(); pg.wait_for_timeout(300)
    assert pg.evaluate("JSON.parse(localStorage.getItem('neste.held'))")["where"].startswith("p:")
    pg.evaluate(bg, 361); pg.wait_for_timeout(800)
    assert pg.evaluate("localStorage.getItem('neste.held')") == "null", "valet skal gå ut etter 6 timar"
    # Treg posisjon: «Finn reisa di …» først, så lista etter AUTO_WAIT, så bytte med forklaring når posisjonen kjem
    pg.evaluate("id => localStorage.setItem('neste.cur', JSON.stringify(id))", hs)
    slow = ctx.new_page(); slow.on("pageerror", lambda e: errs.append(str(e)))
    slow.route("**/journey-planner/**", jp)
    slow.add_init_script("""Object.defineProperty(navigator.geolocation, 'getCurrentPosition', {value: ok =>
        setTimeout(() => ok({coords: {latitude: 61.5004, longitude: 5.0}}), 2600)})""")  # påfunnen, ved «Sentrum»
    slow.goto((ROOT / "index.html").as_uri()); slow.wait_for_timeout(600)
    assert "Finn reisa di" in slow.locator("#app").inner_text(), slow.locator("#app").inner_text()[:200]
    slow.wait_for_timeout(1300)
    assert slow.locator(".hero .big").count() == 1, "lista skal visast etter AUTO_WAIT"
    assert slow.evaluate("JSON.parse(localStorage.getItem('neste.cur'))") == hs
    slow.wait_for_timeout(1500)
    assert slow.evaluate("JSON.parse(localStorage.getItem('neste.cur'))") == sh, "seint svar skal framleis velje reise"
    msg = slow.locator(".switched").inner_text()
    assert "Bytte til" in msg and "du er ved" in msg, msg
    slow.screenshot(path=str(OUT / "auto_bytte.png")); slow.close()
    # Den gamle innstillinga berre for kai blir flytta til den nye
    pg.evaluate("() => { localStorage.setItem('neste.autoside', 'true'); localStorage.removeItem('neste.auto') }")
    pg.reload(); pg.wait_for_timeout(500)
    assert pg.evaluate("localStorage.getItem('neste.auto')") == "true" and pg.evaluate("localStorage.getItem('neste.autoside')") is None
    pg.click("#setup"); pg.wait_for_timeout(300)
    assert pg.locator("[data-act=auto]").is_checked()
    pg.locator("[data-act=auto]").scroll_into_view_if_needed(); pg.screenshot(path=str(OUT / "auto_oppsett.png"))
    pg.click("[data-act=done]"); pg.wait_for_timeout(300)
    ctx.set_geolocation({"latitude": 60.08, "longitude": 5.01})

    # Kort delingslenke: komprimert med deflate-raw («z…»), utan label, og ho gir same oppsett tilbake
    def norm(c):
        e = lambda x: (x["id"], x["name"], x["full"], round(x["lat"], 5), round(x["lon"], 5))
        return ([(p["id"], p["name"], [(s["id"], s["name"], s["walk"], s["mode"]) for s in p["stops"]]) for p in c["places"]],
                [(t["id"], e(t["ferry"]["a"]), e(t["ferry"]["b"]), t["dir"]) if "ferry" in t else (t["id"], t["from"], t["to"], t["lines"]) for t in c["trips"]])
    ctx.grant_permissions(["geolocation", "clipboard-read", "clipboard-write"])
    before = pg.evaluate("JSON.parse(localStorage.getItem('neste.cfg'))")
    assert any(s["label"] for p in before["places"] for s in p["stops"]) and any("ferry" in t for t in before["trips"]) and any(t.get("lines") for t in before["trips"])
    pg.click("#setup"); pg.wait_for_timeout(300); pg.click("[data-act=share]"); pg.wait_for_timeout(500)
    code = pg.evaluate("navigator.clipboard.readText()").split("#oppsett=")[1]
    assert code.startswith("z"), code[:20]
    import zlib, base64
    raw = zlib.decompress(base64.urlsafe_b64decode(code[1:] + "=" * (-len(code[1:]) % 4)), -15).decode()
    assert "Testby" not in raw and "NSR:StopPlace" not in raw, raw  # ingen label, stopp-ID som tal
    pg.click("[data-act=done]"); pg.wait_for_timeout(200)
    pg.evaluate("localStorage.setItem('neste.cfg', JSON.stringify({places: [{id: 'x', name: 'Anna', stops: []}], trips: []}))")
    pg.goto((ROOT / "index.html").as_uri() + "#oppsett=" + code); pg.wait_for_timeout(600)
    assert "3 stader og 6 reiser" in pg.locator("#dlg").inner_text(), pg.locator("#dlg").inner_text()
    pg.click("[data-act=impYes]"); pg.wait_for_timeout(500)
    after = pg.evaluate("JSON.parse(localStorage.getItem('neste.cfg'))")
    assert norm(after) == norm(before), (norm(after), norm(before))
    # Lima kort lenke, og ei øydelagd ei
    pg.click("#setup"); pg.wait_for_timeout(300)
    pg.click("[data-act=paste]"); pg.fill("#impTxt", "https://example.org/neste/#oppsett=" + code); pg.click("[data-act=impPaste]"); pg.wait_for_timeout(300)
    assert "Importere oppsett?" in pg.locator("#dlg").inner_text()
    pg.click("[data-act=impNo]"); pg.click("[data-act=paste]"); pg.fill("#impTxt", "#oppsett=" + code[:40]); pg.click("[data-act=impPaste]"); pg.wait_for_timeout(300)
    assert "Lenka var øydelagd" in pg.locator("#dlg").inner_text(), pg.locator("#dlg").inner_text()
    pg.click("[data-act=impNo]"); pg.click("[data-act=done]"); pg.wait_for_timeout(200)
    # Utan CompressionStream: ukomprimert lenke som før, men utan label. Utan DecompressionStream: tydeleg melding.
    old = ctx.new_page(); old.on("pageerror", lambda e: errs.append(str(e))); old.route("**/journey-planner/**", jp)
    old.add_init_script("delete window.CompressionStream")
    old.goto((ROOT / "index.html").as_uri()); old.wait_for_timeout(400)
    old.click("#setup"); old.wait_for_timeout(300); old.click("[data-act=share]"); old.wait_for_timeout(400)
    plain = old.evaluate("navigator.clipboard.readText()").split("#oppsett=")[1]
    js = json.loads(base64.urlsafe_b64decode(plain + "=" * (-len(plain) % 4)))
    assert plain.startswith("eyJ") and "label" not in json.dumps(js) and len(js["p"]) == 3, plain[:40]
    old.close()
    nd = ctx.new_page(); nd.on("pageerror", lambda e: errs.append(str(e))); nd.route("**/journey-planner/**", jp)
    nd.add_init_script("delete window.DecompressionStream")
    nd.goto((ROOT / "index.html").as_uri() + "#oppsett=" + code); nd.wait_for_timeout(500)
    assert "kan ikkje pakke ho ut" in nd.locator("#dlg").inner_text(), nd.locator("#dlg").inner_text()
    nd.screenshot(path=str(OUT / "lenke_utan_dekomp.png"))
    nd.goto((ROOT / "index.html").as_uri() + "#oppsett=" + plain); nd.wait_for_timeout(500)
    assert "3 stader og 6 reiser" in nd.locator("#dlg").inner_text(), "ukomprimert lenke skal fungere utan DecompressionStream"
    nd.close(); pg.bring_to_front()

    # Delingslenke med eit samband blir importert og vaska
    import base64
    share = {"p": [], "t": [{"id": "s1", "dir": "ba", "x": "<b>", "ferry": {
        "a": {"id": "NSR:StopPlace:3001", "name": "Testkai ferjekai", "lat": 60.0, "lon": 5.0},
        "b": {"id": "NSR:StopPlace:3002", "name": "Motkai", "lat": 60.1, "lon": 5.0}}}]}
    enc = base64.urlsafe_b64encode(json.dumps(share).encode()).decode().rstrip("=")
    pg.goto((ROOT / "index.html").as_uri() + "#oppsett=" + enc); pg.wait_for_timeout(500)
    pg.click("[data-act=impYes]"); pg.wait_for_timeout(1200)
    assert pg.locator("#chips button").all_inner_texts() == ["Testkai ⇄ Motkai"]
    t = pg.evaluate("JSON.parse(localStorage.getItem('neste.cfg')).trips[0]")
    assert "x" not in t and t["ferry"]["a"]["name"] == "Testkai", t

    # Lim inn delingslenke i appen (slik ein må gjere i appen på Heim-skjermen på iPhone)
    other = {"p": [{"id": "p1", "name": "Limstad", "stops": [{"id": A, "name": "Testvik øvre", "walk": 3}]}], "t": []}
    code = base64.urlsafe_b64encode(json.dumps(other).encode()).decode().rstrip("=")
    pg.click("#setup"); pg.wait_for_timeout(300)
    pg.click("[data-act=paste]"); pg.fill("#impTxt", "sjå her: https://example.org/neste/#oppsett=" + code)
    pg.click("[data-act=impPaste]"); pg.wait_for_timeout(200)
    assert "1 stader og 0 reiser" in pg.locator("#dlg").inner_text()
    assert pg.locator("[data-act=copyLink]").count() == 0, "iPhone-rettleiinga skal ikkje visast utanfor Safari"
    pg.click("[data-act=impYes]"); pg.wait_for_timeout(500)
    assert pg.evaluate("JSON.parse(localStorage.getItem('neste.cfg')).places[0].name") == "Limstad"
    pg.click("#setup"); pg.wait_for_timeout(300)
    pg.click("[data-act=paste]"); pg.fill("#impTxt", "ingen lenke her"); pg.click("[data-act=impPaste]")
    assert "Fann inga delingslenke" in pg.locator("#dlg").inner_text()
    pg.click("[data-act=impNo]"); pg.click("[data-act=done]"); pg.wait_for_timeout(300)

    # QR-kode for delingslenka: kodaren blir lasta frå cdnjs først når han trengst (blir hoppa over utan nett)
    assert pg.evaluate("!!document.querySelector('script[src*=qrcode]')") is False, "QR-kodaren skal ikkje lastast før han trengst"
    pg.click("#setup"); pg.wait_for_timeout(300)
    pg.click("[data-act=qr]"); pg.wait_for_timeout(2500)
    if "lasta ikkje" in pg.locator("#dlg").inner_text():
        print("Hoppar over QR-delen: QR-kodaren lasta ikkje (utan nett?)")
    else:
        assert pg.evaluate("document.querySelector('script[src*=qrcode]').integrity.startsWith('sha384-')")
        svg = pg.locator("#dlg .qr svg")
        assert svg.count() == 1 and pg.locator("#dlg .qr path").get_attribute("d").count("h1v1") > 200
        assert "Kopier lenka" in pg.locator("#dlg").inner_text(), "rettleiinga for iPhone manglar"
        pg.screenshot(path=str(OUT / "qr.png"))
        pg.click("#dlg [data-act=impNo]")
        # For stort oppsett til éin kode: melding i staden for feil
        # Tilfeldige namn, så heller ikkje den komprimerte lenka får plass
        import random; rnd = random.Random(1)
        big = [{"id": f"NSR:StopPlace:{rnd.randint(1000, 99999)}", "name": "".join(rnd.choice("abcdefghijklmnopqrstuvwxyzæøå ") for _ in range(24)),
                "label": "Testby", "mode": "bus", "walk": rnd.randint(1, 20)} for _ in range(120)]
        pg.evaluate("""big => { const c = JSON.parse(localStorage.getItem('neste.cfg'));
            c.places[0].stops = big; localStorage.setItem('neste.cfg', JSON.stringify(c)) }""", big)
        pg.reload(); pg.wait_for_timeout(500)  # utan reiser opnar appen i oppsettet
        pg.click("[data-act=qr]"); pg.wait_for_timeout(2500)
        assert "for stort til éin QR-kode" in pg.locator("#dlg").inner_text(), pg.locator("#dlg").inner_text()
        pg.click("#dlg [data-act=impNo]")
    pg.click("[data-act=done]"); pg.wait_for_timeout(300)

    # QR-skannar i appen. Straumane blir registrerte, så vi kan sjå at kameraet blir stoppa.
    ctx.grant_permissions(["geolocation", "clipboard-read", "clipboard-write", "camera"])
    REC = "{const g = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices); window._streams = [];" \
          " navigator.mediaDevices.getUserMedia = c => g(c).then(s => (window._streams.push(s), s))}"
    live = lambda q: q.evaluate("window._streams.flatMap(s => s.getTracks()).filter(t => t.readyState === 'live').length")
    def scanner(init):
        q = ctx.new_page(); q.on("pageerror", lambda e: errs.append(str(e))); q.route("**/journey-planner/**", jp)
        q.add_init_script(init); q.goto((ROOT / "index.html").as_uri()); q.wait_for_timeout(400)
        if q.locator("[data-act=paste]").count() == 0: q.click("#setup"); q.wait_for_timeout(200)
        q.click("[data-act=paste]"); q.click("#dlg [data-act=scan]")
        return q
    def wait_text(q, txt, ms=10000):
        for _ in range(ms // 250):
            if txt in q.locator("#dlg").inner_text(): return True
            q.wait_for_timeout(250)
        return False
    # Med BarcodeDetector (påfunnen, som i Chrome på Android): ingen nedlasting. Først ein QR-kode som ikkje er frå Neste.
    BD = "window.BarcodeDetector = class { static async getSupportedFormats() { return ['qr_code'] }" \
         " async detect(v) { window._n = (window._n || 0) + 1; if (!(v.videoWidth > 0)) return [];" \
         " return [{rawValue: window._n < 4 ? 'https://example.org/anna' : %s}] } };" % json.dumps(SCAN_LINK)
    q = scanner(REC + BD)
    assert wait_text(q, "ikkje ein QR-kode frå Neste", 4000), q.locator("#dlg").inner_text()
    assert wait_text(q, "Importere oppsett?"), q.locator("#dlg").inner_text()
    assert "2 stader og 1 reiser" in q.locator("#dlg").inner_text()
    assert live(q) == 0 and q.evaluate("window._streams.length") == 1, "kameraet skal stoppast når koden er funnen"
    assert q.evaluate("!document.querySelector('script[src*=html5-qrcode]')"), "med BarcodeDetector skal ingenting lastast ned"
    q.click("[data-act=impYes]"); q.wait_for_timeout(400)
    assert q.evaluate("JSON.parse(localStorage.getItem('neste.cfg')).places.map(p => p.name)") == ["Skannstad", "Testby"]
    # Lukk skannaren: kameraet stoppar
    q.evaluate("window._n = -1000")  # ingen kode no
    q.click("#setup"); q.wait_for_timeout(200); q.click(".card [data-act=scan]"); q.wait_for_timeout(600)
    assert live(q) == 1, "kameraet skulle gå"
    q.screenshot(path=str(OUT / "skann.png"))
    q.click("#dlg [data-act=impNo]"); q.wait_for_timeout(200)
    assert live(q) == 0, "kameraet skal stoppast når dialogen blir lukka"
    q.close()
    # Nei til kamera, og inkje kamera
    for name, txt in (("NotAllowedError", "fekk ikkje bruke kameraet"), ("NotFoundError", "Fann ikkje noko kamera")):
        q = scanner(BD + "navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('nei', '%s'))" % name)
        assert wait_text(q, txt, 3000), q.locator("#dlg").inner_text()
        assert q.locator("#scanBox").count() == 0
        if name == "NotAllowedError": q.screenshot(path=str(OUT / "skann_nei.png"))
        q.close()
    # Utan BarcodeDetector: html5-qrcode frå cdnjs les den påfunne QR-koden frå det falske kameraet (blir hoppa over utan nett)
    q = scanner(REC + "delete window.BarcodeDetector")
    wait_text(q, "Importere oppsett?", 15000)
    dl = q.locator("#dlg").inner_text()
    if "lasta ikkje" in dl:
        print("Hoppar over html5-qrcode: lasta ikkje (utan nett?)")
    else:
        assert "Importere oppsett?" in dl and "2 stader og 1 reiser" in dl, dl
        assert q.evaluate("document.querySelector('script[src*=html5-qrcode]').integrity.startsWith('sha384-')")
        q.wait_for_timeout(500)
        assert live(q) == 0, "kameraet skal stoppast når koden er funnen"
    q.close(); pg.bring_to_front()

    # Safari på iPhone: rettleiing om appen på Heim-skjermen, og ei anna open fane får med seg importen
    ios = ctx.new_page(); ios.on("pageerror", lambda e: errs.append(str(e)))
    ios.route("**/journey-planner/**", jp)
    ios.add_init_script("Object.defineProperty(navigator, 'standalone', {value: false})")
    ios.goto((ROOT / "index.html").as_uri() + "#oppsett=" + enc); ios.wait_for_timeout(500)
    assert "Brukar du Neste frå Heim-skjermen?" in ios.locator("#dlg").inner_text()
    assert ios.locator("[data-act=copyLink]").count() == 1
    ios.click("[data-act=impYes]"); ios.wait_for_timeout(800)
    pg.bring_to_front(); pg.wait_for_timeout(800)
    assert pg.locator("#chips button").all_inner_texts() == ["Testkai ⇄ Motkai"], "den andre fana fekk ikkje med seg importen"
    b.close()
    print("Feil i sida:", errs or "ingen")
    assert not errs
