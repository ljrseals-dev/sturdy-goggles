import io, json, subprocess, sys, threading, urllib.request, urllib.error, socket
from pathlib import Path
from _util import *
from aoc.protocol import Engine, serve
from aoc.ui import make_server

ROOT = Path(__file__).resolve().parent.parent


def test_protocol_end_to_end_ops():
    e = Engine(tmp())
    c = e.handle
    assert c({"op": "version", "id": 7})["id"] == 7
    assert c({"op": "nope"})["error"]["code"] == "unknown_op" and c({"op": "../x"})["error"]["code"] == "unknown_op"
    b = c({"op": "studio.build", "lead": [[60, 0, .5], [64, .6, .5], [67, 1.2, .8, .9, "lo"]], "parts": 4, "doubles": 1, "bg": "soulful"})
    assert b["ok"] and [t["name"] for t in b["result"]["tracks"]][:2] == ["Lead", "Harm High"]
    assert c({"op": "studio.set_track", "name": "Lead", "set": {"level_db": -3, "pan": 0.2, "mute": False}})["ok"]
    for bad, code in (({"pan": 5}, "out_of_range"), ({"mute": "yes"}, "bad_request"), ({"bogus": 1}, "bad_request"),
                      ({"level_db": float("nan")}, "bad_request")):
        assert c({"op": "studio.set_track", "name": "Lead", "set": bad})["error"]["code"] == code, bad
    r = c({"op": "studio.render", "out_dir": "out1", "bits": 24})
    assert r["ok"] and r["result"]["duration_s"] > 1 and "mix" in r["result"]["files"]
    assert c({"op": "midi.export", "out": "a.mid"})["ok"]
    lead = c({"op": "midi.import_lead", "path": "a.mid", "track": "Lead"})["result"]["notes"]
    assert [n[0] for n in lead] == [60, 64, 67]
    s = c({"op": "speech.synth", "text": "hello world", "engine": "builtin", "out": "s.wav"})
    assert s["ok"] and s["result"]["engine"] == "builtin"
    assert c({"op": "pitch.track", "path": "out1/stem_Lead.wav"})["ok"]
    assert c({"op": "studio.set_notes", "name": "Lead", "notes": [[200, 0, 1]]})["error"]["code"] == "bad_note"
    assert c({"op": "studio.set_notes", "name": "Nope", "notes": [[60, 0, 1]]})["error"]["code"] == "invalid"
    assert c({"op": "studio.set_renderer", "name": "sample", "path": "s.wav"})["error"]["code"] == "consent_required"
    assert c({"op": "project.create", "dir": "proj"})["ok"] and c({"op": "project.save"})["ok"]
    assert c({"op": "project.verify"})["result"] == {"ok": True, "problems": []}
    assert c({"op": "doctor"})["ok"] and c({"op": "engines.list"})["ok"]


def test_protocol_confines_paths_and_validates_everything():
    e = Engine(tmp()); c = e.handle
    c({"op": "studio.build", "lead": [[60, 0, .5]]})
    for req in ({"op": "midi.export", "out": "../evil.mid"}, {"op": "studio.render", "out_dir": "/etc/x"},
                {"op": "speech.synth", "text": "x", "engine": "builtin", "out": "../x.wav"},
                {"op": "midi.import_lead", "path": "/etc/passwd"}, {"op": "project.create", "dir": "../p"}):
        assert c(req)["error"]["code"] in ("bad_path", "not_found"), req
    assert c({"op": "studio.build", "lead": [[60, 0, .5]], "parts": 5})["error"]["code"] == "out_of_range"
    assert c({"op": "studio.build", "lead": [[60, 0, .5]], "key": "H"})["error"]["code"] == "bad_request"
    assert c({"op": "studio.build"})["error"]["code"] == "bad_request"
    assert c({"op": "studio.build", "lead": [[60, 0, .5]] * 6000})["error"]["code"] == "out_of_range"
    assert c({"op": "speech.synth", "text": "x", "rate": 99})["error"]["code"] == "out_of_range"
    assert c([1, 2])["error"]["code"] == "bad_request" and c({"op": 5})["error"]["code"] == "unknown_op"
    assert c({"op": "consent.add", "file": "x.wav", "owner": "a", "scope": "b"})["error"]["code"] in ("not_found", "consent_required")


def test_serve_json_lines_handles_bad_input():
    out = io.StringIO()
    serve(tmp(), io.StringIO('{"op":"ping","id":1}\nnot json\n\n{"op":"version"}\n'), out)
    oks = [json.loads(l)["ok"] for l in out.getvalue().splitlines()]
    assert oks == [True, False, True]


def _server():
    srv = make_server(tmp())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}", srv.aoc_token


def _req(base, path, method="GET", data=None, headers=None):
    r = urllib.request.Request(base + path, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r, timeout=10) as x:
            return x.status, x.read(), x.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers


def test_ui_security_and_api():
    srv, base, tok = _server()
    try:
        s, b, h = _req(base, f"/?token={tok}")
        assert s == 200 and b"AOC" in b and h.get("Content-Security-Policy") and tok.encode() in b
        assert _req(base, "/")[0] == 403 and _req(base, "/?token=nope")[0] == 403
        assert _req(base, f"/?token={tok}", headers={"Host": "evil.com"})[0] == 403
        ok = {"X-AOC-Token": tok}
        assert json.loads(_req(base, "/api", "POST", b'{"op":"ping"}', ok)[1])["ok"]
        assert _req(base, "/api", "POST", b'{"op":"ping"}')[0] == 403
        assert _req(base, "/api", "POST", b'{"op":"ping"}', {**ok, "Origin": "http://evil.com"})[0] == 403
        assert _req(base, "/api", "POST", b"{", ok)[0] == 400
        r = json.loads(_req(base, "/api", "POST", json.dumps({"op": "speech.synth", "text": "hello", "engine": "builtin", "out": "ui/s.wav"}).encode(), ok)[1])
        assert r["ok"]
        s, b, h = _req(base, f"/files/ui/s.wav?token={tok}")
        assert s == 200 and "wav" in h.get("Content-Type") and len(b) > 1000
        assert _req(base, f"/files/..%2f..%2fetc%2fpasswd?token={tok}")[0] == 404
        assert _req(base, f"/files/%2e%2e/%2e%2e/etc/passwd?token={tok}")[0] == 404
        so = socket.create_connection(("127.0.0.1", srv.server_address[1]), timeout=5)
        so.sendall(f"POST /api HTTP/1.1\r\nHost: 127.0.0.1:{srv.server_address[1]}\r\nX-AOC-Token: {tok}\r\nContent-Length: 2000000\r\n\r\n".encode())
        assert b"413" in so.recv(200).split(b"\r\n")[0]; so.close()
    finally:
        srv.shutdown()


def run(*args, inp=None):
    return subprocess.run([sys.executable, "-m", "aoc", *args], cwd=ROOT, input=inp, capture_output=True, text=True, timeout=300)


def test_cli_commands_and_exit_codes():
    d = tmp()
    assert "standalone" in run("version").stdout
    assert run("speak", "hello there", "--out", d + "/s.wav", "--engine", "builtin").returncode == 0 and Path(d, "s.wav").stat().st_size > 1000
    r = run("studio", "demo", "--out", d + "/demo")
    assert r.returncode == 0 and "preview formant synth" in r.stdout and Path(d, "demo", "arrangement.mid").exists()
    Path(d, "lead.json").write_text(json.dumps([[60, 0, 0.5], [62, 0.6, 0.5], [64, 1.2, 1.0]]))
    assert run("studio", "build", "--lead", d + "/lead.json", "--parts", "3", "--key", "A", "--mode", "minor", "--bg", "none",
               "--out", d + "/b", "--midi-out", "--bits", "24").returncode == 0
    assert json.loads(run("midi", "lead", d + "/b/arrangement.mid", "--track", "Lead").stdout)["notes"][0][0] == 60
    assert run("studio", "render", "--session", d + "/b/session.json", "--out", d + "/r").returncode == 0
    assert run("studio", "build", "--lead", d + "/missing.json", "--out", d + "/x").returncode == 2
    assert run("speak", "", "--out", d + "/x.wav").returncode == 2
    assert run("consent", "add", "--file", d + "/s.wav", "--owner", "me", "--scope", "x").returncode == 2        # no --attest
    assert run("project", "new", d + "/pj").returncode == 0 and json.loads(run("project", "verify", d + "/pj").stdout)["ok"]
    assert run("doctor").returncode == 0
    resp = json.loads(run("serve", "--workspace", d, inp='{"op":"ping","id":3}\n').stdout)
    assert resp == {"ok": True, "result": {"pong": True}, "id": 3}


def test_cli_survives_closed_pipe():
    p = subprocess.Popen([sys.executable, "-m", "aoc", "studio", "demo", "--out", tmp() + "/d"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.stdout.readline(); p.stdout.close()
    err = p.stderr.read().decode(); p.wait(timeout=120)
    assert p.returncode == 0 and "Traceback" not in err
