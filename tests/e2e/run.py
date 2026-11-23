import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from cases import CASES

PACKAGE = "fresh-intellij-keymap"
BASE_CONFIG = {
    "check_for_updates": False,
    "clipboard": {"use_osc52": True, "use_system_clipboard": False},
}


def build_template(workdir):
    home = os.path.join(workdir, "template-home")
    pkg = os.path.join(home, ".config", "fresh", "plugins", "packages", PACKAGE)
    os.makedirs(pkg)
    for f in ("package.json", "fresh-intellij-keymap.ts", "keymap.json"):
        shutil.copy(os.path.join(ROOT, f), pkg)
    json.dump(BASE_CONFIG, open(os.path.join(home, ".config", "fresh", "config.json"), "w"))
    ws = os.path.join(workdir, "warmup")
    os.makedirs(ws)
    open(os.path.join(ws, "a.txt"), "w").write("warm up\n")
    res = drive(workdir, "warmup", {"home": home, "cwd": ws, "files": [f"{ws}/a.txt"], "steps": []})
    if not res.get("boot_ready") or res["timeouts"]:
        sys.exit(f"Fresh did not start with the plugin loaded: {res}")
    return home


def drive(workdir, name, spec):
    spec_path = os.path.join(workdir, f"{name}.spec.json")
    res_path = os.path.join(workdir, f"{name}.result.json")
    json.dump(spec, open(spec_path, "w"))
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "driver.py"), spec_path, res_path],
                   timeout=240, check=True)
    return json.load(open(res_path))


class Result:

    def __init__(self, res, files, config_before, config_after, log):
        self.steps, self.osc52, self.files = res["steps"], res["osc52"], files
        self.config_before, self.config_after = config_before, config_after
        self.log = log

    def screen(self, i=-1):
        return self.steps[i]["screen"]

    def new_lines(self, i=-1):
        before = set(self.steps[i]["before"].split("\n"))
        return [l.strip() for l in self.screen(i).split("\n") if l not in before and l.strip()]

    def cursor(self, i=-1):
        m = re.findall(r"Ln (\d+), Col (\d+)", self.screen(i))
        return (int(m[-1][0]), int(m[-1][1])) if m else None


def run_case(index, case, template, workdir):
    base = os.path.join(workdir, f"{index:02d}-" + re.sub(r"[^\w.+-]+", "_", case.name))
    home, ws = os.path.join(base, "home"), os.path.join(base, "ws")
    shutil.copytree(template, home, symlinks=True,
                    ignore=shutil.ignore_patterns("Application Support", "state"))
    os.makedirs(ws)
    for fn, content in case.files.items():
        open(os.path.join(ws, fn), "w").write(content)
    if case.git_modify:
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
        for cmd in (["init", "-q"], ["add", "."], ["commit", "-qm", "init"]):
            subprocess.run(git + cmd, cwd=ws, check=True)
        for fn, content in case.git_modify.items():
            open(os.path.join(ws, fn), "w").write(content)
    config_path = os.path.join(home, ".config", "fresh", "config.json")
    json.dump({**BASE_CONFIG, **case.cfg}, open(config_path, "w"))
    config_before = open(config_path).read()
    spec = {"home": home, "cwd": ws, "files": [os.path.join(ws, f) for f in case.open or list(case.files)[:1]],
            "steps": case.steps, "pre": case.pre, "ready": case.ready, "save": case.save}
    t0 = time.time()
    res = drive(base, "session", spec)
    files = {fn: open(os.path.join(ws, fn)).read() for fn in case.files}
    log = re.sub(r"\x1b\[[0-9;]*m", "", "".join(open(f, errors="replace").read() for f in _logs(home, "fresh-")))
    r = Result(res, files, config_before, open(config_path).read(), log)
    problems = []
    if not res["boot_ready"]:
        problems.append("Fresh did not start")
    problems += [f"timed out waiting for {t}" for t in res["timeouts"]]
    for log in _logs(home, "warnings-"):
        problems += [f"Fresh warning: {l.strip()}" for l in open(log, errors="replace") if "is not defined" in l]
    try:
        ok, detail = case.check(r)
    except Exception as e:
        ok, detail = False, f"check error: {e!r}"
    if problems:
        ok, detail = False, "; ".join(problems) + " | " + detail
    if os.environ.get("DUMP"):
        for i, s in enumerate(res["steps"]):
            print(f"===== {case.name} step {i} {s['label']}\n" + "\n".join(l for l in s["screen"].split("\n") if l.strip()))
    return case.name, ok, detail, time.time() - t0


def _logs(home, prefix):
    d = os.path.join(home, ".local", "state", "fresh", "logs")
    return [os.path.join(d, f) for f in os.listdir(d) if f.startswith(prefix)] if os.path.isdir(d) else []


def main(argv, cases=CASES):
    for tool in ("fresh", "gopls", "git"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH")
    try:
        import pyte
    except ImportError:
        sys.exit("pyte is missing: python3 -m venv .venv && .venv/bin/pip install pyte")
    filters = [a for a in argv if not a.startswith("--")]
    selected = [c for c in cases if not filters or any(f in c.name for f in filters)]
    workdir = tempfile.mkdtemp(prefix="fresh-keymap-tests-")
    template = build_template(workdir)
    failed = 0
    with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", os.cpu_count() or 4))) as pool:
        for name, ok, detail, secs in pool.map(lambda ic: run_case(*ic, template, workdir), enumerate(selected)):
            failed += not ok
            print(f"{'PASS' if ok else 'FAIL'}  {name:58} {secs:4.1f}s  {'' if ok else detail[:400]}", flush=True)
    print(f"\n{len(selected) - failed}/{len(selected)} passed")
    if failed or "--keep" in argv:
        print(f"sessions kept in {workdir}")
    else:
        shutil.rmtree(workdir, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
