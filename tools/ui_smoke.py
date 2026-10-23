#!/usr/bin/env python3
"""Browser smoke test of `aoc ui` with Playwright (headless Chromium). Saves screenshots to the given directory.
    python tools/ui_smoke.py audit/evidence
Exit 0 = every step worked and the page logged no JS errors."""
import json, os, re, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
shots = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()); shots.mkdir(parents=True, exist_ok=True)
ws = tempfile.mkdtemp(prefix="aoc_ui_")
srv = subprocess.Popen([sys.executable, "-u", "-m", "aoc", "ui", "--no-browser", "--port", "0", "--workspace", ws],
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
url = None
t0 = time.time()
while time.time() - t0 < 20:
    line = srv.stdout.readline()
    m = re.search(r"open: (http://\S+)", line)
    if m:
        url = m.group(1)
        break
if not url:
    srv.kill(); sys.exit("server did not start")
TOKEN = re.search(r"token=([\w-]+)", url).group(1)
BASE = url.split("/?")[0]


def api(req):
    """Query the engine directly (independent of the page) to confirm UI actions reached it."""
    r = urllib.request.Request(BASE + "/api", data=json.dumps(req).encode(), method="POST", headers={"X-AOC-Token": TOKEN})
    return json.loads(urllib.request.urlopen(r, timeout=30).read())


results, errors = [], []
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1180, "height": 900})
        pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        pg.goto(url)
        pg.wait_for_selector("h1")
        results.append(("page loads", "AOC" in pg.inner_text("h1")))
        pg.screenshot(path=str(shots / "ui_1_home.png"))
        # Speak
        pg.click("#sp_go")
        pg.wait_for_selector("#sp_msg:has-text('engine:'), #sp_msg.err", timeout=60000)
        msg = pg.inner_text("#sp_msg")
        results.append(("speak synthesizes", msg.startswith("engine:")))
        results.append(("audio element has a source", bool(pg.locator("#sp_audio").get_attribute("src")) and pg.locator("#sp_audio").is_visible()))
        pg.wait_for_timeout(800)
        pg.screenshot(path=str(shots / "ui_2_speak.png"))
        # Studio
        pg.click("nav button[data-t=studio]")
        pg.click("#st_build")
        pg.wait_for_selector("#st_body tr", timeout=30000)
        rows = pg.locator("#st_body tr").count()
        results.append(("studio builds tracks", rows >= 6))
        pg.locator("#st_body tr").nth(1).locator("input[data-k=mute]").check()
        pg.wait_for_timeout(500)
        st = api({"op": "studio.state"})
        muted = [t["name"] for t in st["result"]["tracks"] if t["settings"]["mute"]]
        results.append(("mute checkbox reaches the engine", len(muted) == 1))
        pg.locator("#st_body tr").nth(0).locator("input[data-k=level_db]").fill("-6")
        pg.wait_for_timeout(500)
        st = api({"op": "studio.state"})
        results.append(("level slider reaches the engine", abs(st["result"]["tracks"][0]["settings"]["level_db"] + 6) < 0.6))
        pg.click("#st_render")
        pg.wait_for_selector("#st_msg:has-text('rendered'), #st_msg.err", timeout=120000)
        results.append(("studio renders", pg.inner_text("#st_msg").startswith("rendered")))
        pg.click("#st_midi")
        pg.wait_for_selector("#st_links a:has-text('arrangement.mid')", timeout=30000)
        results.append(("midi export link", True))
        pg.screenshot(path=str(shots / "ui_3_studio.png"), full_page=True)
        # bad input surfaces as an error, not a crash
        pg.fill("#st_lead", "C4:1 ZZ:1")
        pg.click("#st_build")
        pg.wait_for_timeout(300)
        results.append(("bad lead shows an error", "bad token" in pg.inner_text("#st_msg")))
        # Doctor
        pg.click("nav button[data-t=status]")
        pg.click("#do_go")
        pg.wait_for_selector("#do_out:has-text('PASS')", timeout=60000)
        results.append(("doctor renders", "numpy" in pg.inner_text("#do_out")))
        pg.screenshot(path=str(shots / "ui_4_status.png"))
        b.close()
finally:
    srv.terminate()
results.append(("no JavaScript errors", not errors))
for name, ok in results:
    print(("PASS " if ok else "FAIL ") + name)
for e in errors:
    print("  " + e)
sys.exit(0 if all(ok for _, ok in results) else 1)
