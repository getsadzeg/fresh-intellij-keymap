import ctypes
import ctypes.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "e2e"))
from cases import CASES
from keys import fresh_combo, split, symbols

GHOSTTY_APP = "/Applications/Ghostty.app"
KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12,
    "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23,
    "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34,
    "p": 35, "enter": 36, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44,
    "n": 45, "m": 46, ".": 47, "tab": 48, "space": 49, "`": 50, "backspace": 51, "esc": 53,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98, "f8": 100, "f9": 101,
    "f10": 109, "f11": 103, "f12": 111, "home": 115, "end": 119,
    "left": 123, "right": 124, "down": 125, "up": 126,
}
FLAGS = {"shift": 1 << 17, "ctrl": 1 << 18, "alt": 1 << 19, "cmd": 1 << 20}
NUMPAD, FN = 1 << 21, 1 << 23
MOD_NAMES = {"shift": "SHIFT", "ctrl": "CONTROL", "alt": "ALT", "cmd": "SUPER"}
CODE_NAMES = {"backspace": "Backspace", "enter": "Enter", "tab": "Tab", "esc": "Esc", "space": "Char(' ')",
              "up": "Up", "down": "Down", "left": "Left", "right": "Right", "home": "Home", "end": "End"}
TRANSLATED = {
    "cmd+backspace": ("Char('u')", {"CONTROL"}),
    "cmd+left": ("Char('a')", {"CONTROL"}),
    "cmd+right": ("Char('e')", {"CONTROL"}),
    "alt+left": ("Char('b')", {"ALT"}),
    "alt+right": ("Char('f')", {"ALT"}),
    "alt+shift+g": ("Char('G')", {"ALT"}),
}
PRACTICE = """class Practice {
    int area(int width, int height) {
        return width * height;
    }

    void main() {
        int a = area(2, 3);
        int b = area(a, 4);
        System.out.println(a + b);
    }
}
"""

_cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
_cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
_cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
_cg.CGEventSetFlags.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
_cg.CGEventPostToPid.argtypes = [ctypes.c_int, ctypes.c_void_p]
_cg.AXIsProcessTrusted.restype = ctypes.c_bool
_cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
_cf.CFRelease.argtypes = [ctypes.c_void_p]


def post(pid, combo):
    mods, key = split(combo)
    flags = sum(FLAGS[m] for m in mods)
    if key in ("up", "down", "left", "right"):
        flags |= NUMPAD | FN
    elif key in ("home", "end") or re.fullmatch(r"f\d+", key):
        flags |= FN
    for down in (True, False):
        ev = _cg.CGEventCreateKeyboardEvent(None, KEYCODES[key], down)
        _cg.CGEventSetFlags(ev, flags)
        _cg.CGEventPostToPid(pid, ev)
        _cf.CFRelease(ev)
        time.sleep(0.02)


def expected(combo):
    mods, key = split(combo)
    if key == "tab" and mods == ["shift"]:
        return "BackTab", set()
    code = CODE_NAMES.get(key) or (f"F({key[1:]})" if re.fullmatch(r"f\d+", key) else f"Char('{key}')")
    return code, {MOD_NAMES[m] for m in mods}


def matches(event, want):
    code, mods = event
    want_code, want_mods = want
    if want_code == "BackTab":
        return code == "BackTab" or (code == "Tab" and mods == {"SHIFT"})
    return code.lower() == want_code.lower() and mods == want_mods


def key_events(log_text):
    out = []
    for code, mods in re.findall(r"key routed by the tree code=(.+?) modifiers=KeyModifiers\(([^)]*)\)", log_text):
        out.append((code, set() if mods == "0x0" else set(mods.split(" | "))))
    return out


def fmt(event):
    code, mods = event
    return "+".join(sorted(mods) + [code])


def checklist():
    rows = json.load(open(os.path.join(ROOT, "keymap.json")))
    items = [(fresh_combo(r["key"], r["modifiers"]), r["action"]) for r in rows]
    seen = {c for c, _ in items}
    for case in CASES:
        if case.kind == "inherited" and case.shortcut not in seen:
            items.append((case.shortcut, case.intellij))
            seen.add(case.shortcut)
    return items


def ghostty_pids():
    out = subprocess.run(["pgrep", "-x", "ghostty"], capture_output=True, text=True).stdout
    return {int(p) for p in out.split()}


def wait_for(cond, timeout, step=0.2):
    end = time.time() + timeout
    while time.time() < end:
        v = cond()
        if v:
            return v
        time.sleep(step)
    return None


def main():
    if sys.platform != "darwin":
        sys.exit("macOS only")
    if not _cg.AXIsProcessTrusted():
        sys.exit("Needs Accessibility permission for this terminal app "
                 "(System Settings > Privacy & Security > Accessibility).")
    fresh = shutil.which("fresh")
    if not fresh or not os.path.isdir(GHOSTTY_APP):
        sys.exit("needs `fresh` on PATH and /Applications/Ghostty.app")

    work = tempfile.mkdtemp(prefix="fresh-keymap-e2e-")
    home, practice = os.path.join(work, "home"), os.path.join(work, "practice")
    pkg = os.path.join(home, ".config", "fresh", "plugins", "packages", "fresh-intellij-keymap")
    os.makedirs(pkg)
    os.makedirs(practice)
    for f in ("package.json", "fresh-intellij-keymap.ts", "keymap.json"):
        shutil.copy(os.path.join(ROOT, f), pkg)
    json.dump({"check_for_updates": False, "clipboard": {"use_osc52": False, "use_system_clipboard": False}},
              open(os.path.join(home, ".config", "fresh", "config.json"), "w"))
    open(os.path.join(practice, "Practice.java"), "w").write(PRACTICE)
    launcher = os.path.join(work, "launch.sh")
    open(launcher, "w").write(f"#!/bin/sh\nexport HOME='{home}'\ncd '{practice}'\nexec '{fresh}' Practice.java\n")
    os.chmod(launcher, 0o755)

    ghostty_args = ["--config-default-files=false",
                    f"--config-file={os.path.join(ROOT, 'ghostty', 'config.ghostty')}",
                    "--macos-option-as-alt=true",
                    "--window-save-state=never", "--confirm-close-surface=false",
                    "--quit-after-last-window-closed=true", f"--working-directory={practice}",
                    f"--command={launcher}"]
    before = ghostty_pids()
    subprocess.run(["open", "-na", GHOSTTY_APP, "--args", *ghostty_args], check=True)
    pid = wait_for(lambda: next(iter(ghostty_pids() - before), None), 20)
    logs = os.path.join(home, ".local", "state", "fresh", "logs")
    fresh_pid = None
    try:
        if not pid:
            sys.exit("Ghostty did not start")

        def ready():
            if not os.path.isdir(logs):
                return None
            status = [f for f in os.listdir(logs) if f.startswith("status-")]
            if any("IntelliJ keymap active" in open(os.path.join(logs, f)).read() for f in status):
                return [f for f in os.listdir(logs) if re.fullmatch(r"fresh-\d+\.log", f)][0]
            return None
        log_name = wait_for(ready, 60)
        if not log_name:
            sys.exit("Fresh did not start with the plugin loaded")
        fresh_pid = int(re.search(r"\d+", log_name).group())
        log_path = os.path.join(logs, log_name)
        time.sleep(1.5)

        def log_text():
            return re.sub(r"\x1b\[[0-9;]*m", "", open(log_path, errors="replace").read())

        print(f"Ghostty pid {pid} (with ghostty/config.ghostty), Fresh pid {fresh_pid}\n")
        results = {"PASS": 0, "FAIL": 0, "MACOS": 0}
        for combo, action in checklist():
            offset = len(log_text())
            post(pid, combo)
            time.sleep(0.6)
            for _ in range(2):
                post(pid, "esc")
                time.sleep(0.25)
            got = [e for e in key_events(log_text()[offset:]) if e[0] != "Esc"]
            want = expected(combo)
            if any(matches(e, want) for e in got):
                verdict, note = "PASS", ""
            elif combo in TRANSLATED and any(matches(e, TRANSLATED[combo]) for e in got):
                verdict, note = "PASS", "(Ghostty translation, handled by Fresh)"
            elif combo == "cmd+v" and not got:
                verdict, note = "PASS", "(Ghostty pasted the clipboard itself)"
            elif combo == "ctrl+space" and not got:
                verdict, note = "MACOS", "(macOS 'Select previous input source' shortcut takes ⌃Space)"
            else:
                verdict, note = "FAIL", ""
            results[verdict] += 1
            received = ", ".join(fmt(e) for e in got) or "nothing"
            print(f"{verdict:8} {symbols(combo):7} {action[:26]:26} expected {fmt(want):22} received {received} {note}")
        print(f"\n{results['PASS']} passed, {results['FAIL']} failed"
              + (f", {results['MACOS']} taken by macOS" if results["MACOS"] else "")
              + f" ({sum(results.values())} shortcuts)")
        return 1 if results["FAIL"] else 0
    finally:
        if fresh_pid:
            try:
                os.kill(fresh_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        if pid and not wait_for(lambda: pid not in ghostty_pids(), 8):
            os.kill(pid, signal.SIGTERM)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
