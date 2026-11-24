import base64
import fcntl
import json
import os
import pty
import re
import select
import signal
import struct
import sys
import termios
import time

import pyte

COLS, ROWS = 140, 40
TERMINAL_REPLIES = {
    b"\x1b[6n": b"\x1b[1;1R",
    b"\x1b[?u": b"\x1b[?1u",
    b"\x1b[c": b"\x1b[?62;22c",
    b"\x1b]10;?": b"\x1b]10;rgb:ffff/ffff/ffff\x1b\\",
    b"\x1b]11;?": b"\x1b]11;rgb:0000/0000/0000\x1b\\",
}


class Session:
    def __init__(self, spec):
        self.screen = pyte.Screen(COLS, ROWS)
        self.stream = pyte.ByteStream(self.screen)
        self.raw = b""
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("XDG_", "FRESH_"))}
        env.update(HOME=spec["home"], TERM="xterm-256color", COLORTERM="truecolor")
        os.chdir(spec["cwd"])
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.execvpe("fresh", ["fresh", *spec["files"]], env)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))

    def text(self):
        return "\n".join(line.rstrip() for line in self.screen.display)

    def _read(self, timeout):
        r, _, _ = select.select([self.fd], [], [], timeout)
        if not r:
            return b""
        try:
            chunk = os.read(self.fd, 65536)
        except OSError:
            return None
        self.raw += chunk
        self.stream.feed(chunk)
        for query, reply in TERMINAL_REPLIES.items():
            if query in chunk:
                os.write(self.fd, reply)
        return chunk

    def wait(self, until=None, timeout=2.0, quiet=0.3, before=None):
        if isinstance(until, str):
            pattern = re.compile(until)
            old = set(before.split("\n")) if before else set()
            until = lambda: any(pattern.search(l) for l in self.text().split("\n") if l not in old)
        end = time.time() + timeout
        last = time.time()
        while time.time() < end:
            chunk = self._read(0.05)
            if chunk is None:
                return False
            if chunk:
                last = time.time()
            if until:
                if until():
                    return True
            elif time.time() - last >= quiet:
                return True
        return False

    def send(self, keys):
        os.write(self.fd, keys.encode("utf-8"))

    def close(self):
        self.send("\x11")
        end = time.time() + 3
        while time.time() < end:
            if self._read(0.05) is None:
                break
            if os.waitpid(self.pid, os.WNOHANG)[0]:
                return False
        try:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
        return True


def main(spec_path, result_path):
    spec = json.load(open(spec_path))
    s = Session(spec)
    res = {"steps": [], "timeouts": []}
    res["boot_ready"] = s.wait(until=r"Palette", timeout=30)
    logs = os.path.join(spec["home"], ".local", "state", "fresh", "logs")

    def plugin_ready():
        return any("IntelliJ keymap active" in open(os.path.join(logs, f), errors="replace").read()
                   for f in os.listdir(logs) if f.startswith("status-"))
    if not s.wait(until=plugin_ready, timeout=10):
        res["timeouts"].append("plugin did not report ready")
    for step in spec.get("pre", []):
        s.send(step["k"])
        if not s.wait(until=step.get("until"), timeout=step.get("timeout", 2.0)) and step.get("until"):
            res["timeouts"].append(f"{step['label']}: {step['until']}")
    for cond in spec.get("ready", []):
        if not s.wait(until=cond, timeout=30):
            res["timeouts"].append(f"ready: {cond}")
    for step in spec["steps"]:
        before = s.text()
        s.send(step["k"])
        ok = s.wait(until=step.get("until"), timeout=step.get("timeout", 2.0),
                    before=None if step.get("anywhere") else before)
        if not ok and step.get("until"):
            res["timeouts"].append(f"{step.get('label') or repr(step['k'])}: {step['until']}")
        res["steps"].append({"label": step.get("label", ""), "before": before, "screen": s.text()})
    if spec.get("save"):
        before = s.text()
        s.send("\x13")
        s.wait(until=r"Saved", timeout=3.0, before=before)
    res["killed"] = s.close()
    res["osc52"] = [base64.b64decode(m).decode("utf-8", "replace")
                    for m in re.findall(rb"\x1b\]52;[a-z]*;([A-Za-z0-9+/=]+)", s.raw)]
    json.dump(res, open(result_path, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
