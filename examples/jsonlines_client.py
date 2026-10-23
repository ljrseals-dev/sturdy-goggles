"""Drive the engine from ANY language: spawn `python -m aoc serve` and exchange one JSON object per line.
This Python client shows the shape; port it to C++/Rust/C#/JS by writing requests to the child's stdin and reading
responses from its stdout."""
import json, subprocess, sys, tempfile

ws = tempfile.mkdtemp(prefix="aoc_ws_")
p = subprocess.Popen([sys.executable, "-m", "aoc", "serve", "--workspace", ws],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)


def call(**req):
    p.stdin.write(json.dumps(req) + "\n"); p.stdin.flush()
    return json.loads(p.stdout.readline())


print(call(op="version"))
built = call(op="studio.build", lead=[[60, 0, .5], [64, .6, .5], [67, 1.2, 1.0]], parts=4, doubles=1)
print("tracks:", [t["name"] for t in built["result"]["tracks"]])
call(op="studio.set_track", name="Lead", set={"level_db": -2, "pan": 0.1})
r = call(op="studio.render", out_dir="render", bits=24)
print("rendered:", r["result"]["files"]["mix"], r["result"]["duration_s"], "s in", ws)
print(call(op="midi.export", out="arrangement.mid"))
p.stdin.close(); p.wait()
