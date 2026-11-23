from dataclasses import dataclass, field
from typing import Callable

from keys import encode


@dataclass
class Case:
    name: str
    kind: str
    shortcut: str | None
    action: str | None
    files: dict
    steps: list
    check: Callable
    intellij: str = ""
    open: list | None = None
    cfg: dict = field(default_factory=dict)
    git_modify: dict | None = None
    save: bool = False
    pre: list = field(default_factory=list)
    ready: list = field(default_factory=list)


def raw(seq, label, until=None):
    return {"k": seq, "until": until, "timeout": 15.0 if until else 2.0, "label": label}


def press(combo, until=None):
    return raw(encode(combo), combo, until)


def type_(text, until=None):
    return raw(text, f"type {text!r}", until)


def times(n, combo):
    return [press(combo) for _ in range(n)]


def content(fname, expected):
    return lambda r: (r.files[fname] == expected, f"{fname}={r.files[fname]!r}")


def cursor_at(line, col=None, step=-1):
    def chk(r):
        got = r.cursor(step)
        return (got is not None and got[0] == line and (col is None or got[1] == col), f"cursor={got}")
    return chk


def new_text(*needles, step=-1):
    def chk(r):
        lines = r.new_lines(step)
        missing = [n for n in needles if not any(n in l for l in lines)]
        return (not missing, f"missing {missing} in new lines {lines[:8]}" if missing else f"found {list(needles)}")
    return chk


def both(*checks):
    def chk(r):
        results = [c(r) for c in checks]
        return all(ok for ok, _ in results), "; ".join(d for _, d in results)
    return chk


TXT = "line1\nline2\nline3\n"
NUMBERED = "".join(f"l{i}\n" for i in range(1, 30))

GO_MOD = "module t\n\ngo 1.21\n"
GO_SRC = (
    "package main\n\n"
    "type Shape interface{ Area() int }\n\n"
    "type Sq struct{}\n\n"
    "func (Sq) Area() int { return 1 }\n\n"
    "func foo(a int, b string) int { return a }\n\n"
    "func main() {\n"
    "\tvar s Shape = Sq{}\n"
    "\t_ = s\n"
    "\tfoo(1, \"x\")\n"
    "\tvar bad int = \"oops\"\n"
    "\t_ = bad\n"
    "}\n"
)
GOPLS = {"lsp": {"go": [{"command": "gopls", "args": [], "enabled": True, "auto_start": True}]}}


def go(src=GO_SRC, errors=False):
    ready = [r"LSP \(go\) ready"] + ([r"E:1"] if errors else [])
    return dict(files={"go.mod": GO_MOD, "main.go": src}, open=["main.go"], cfg=GOPLS,
                pre=[raw("", "trust dialog", until=r"SECURITY WARNING"), press("up"), press("enter")],
                ready=ready)


def at(line, col=1):
    return times(line - 1, "down") + times(col - 1, "right")


CASES = [
    Case("cmd+s saves all open files", "plugin", "cmd+s", "save_all",
         files={"a.txt": TXT, "b.txt": TXT}, open=["a.txt", "b.txt"],
         steps=[type_("X"), press("ctrl+pageup"), type_("Y"), press("cmd+s")],
         check=lambda r: ({r.files["a.txt"][0], r.files["b.txt"][0]} == {"X", "Y"},
                          f"a={r.files['a.txt'][:6]!r} b={r.files['b.txt'][:6]!r}")),
    Case("cmd+backspace deletes the line", "plugin", "cmd+backspace", "delete_line",
         files={"a.txt": TXT}, steps=[press("cmd+backspace")], save=True, check=content("a.txt", "line2\nline3\n")),
    Case("cmd+d duplicates the line", "plugin", "cmd+d", "duplicate_line",
         files={"a.txt": TXT}, steps=[press("cmd+d")], save=True,
         check=content("a.txt", "line1\nline1\nline2\nline3\n")),
    Case("cmd+d with a selection duplicates the whole line (partial)", "partial", "cmd+d", "duplicate_line",
         files={"a.txt": TXT}, steps=times(4, "shift+right") + [press("cmd+d")], save=True,
         check=content("a.txt", "line1\nline1\nline2\nline3\n")),
    Case("alt+shift+up moves the line up", "plugin", "alt+shift+up", "move_line_up",
         files={"a.txt": TXT}, steps=[press("down"), press("alt+shift+up")], save=True,
         check=content("a.txt", "line2\nline1\nline3\n")),
    Case("alt+shift+down moves the line down", "plugin", "alt+shift+down", "move_line_down",
         files={"a.txt": TXT}, steps=[press("alt+shift+down")], save=True,
         check=content("a.txt", "line2\nline1\nline3\n")),
    Case("ctrl+m jumps to the matching brace", "plugin", "ctrl+m", "goto_matching_bracket",
         files={"a.txt": "f(abc)\n"}, steps=[press("right"), press("ctrl+m")], check=cursor_at(1, 6)),
    Case("cmd+home moves to the start of the file", "plugin", "cmd+home", "move_document_start",
         files={"a.txt": TXT}, steps=[press("down"), press("down"), press("end"), press("cmd+home"), type_("Z")],
         save=True, check=content("a.txt", "Zline1\nline2\nline3\n")),
    Case("cmd+end moves to the end of the file", "plugin", "cmd+end", "move_document_end",
         files={"a.txt": TXT}, steps=[press("cmd+end"), type_("Z")], save=True,
         check=content("a.txt", TXT + "Z")),
    Case("cmd+shift+home selects to the start of the file", "plugin", "cmd+shift+home", "select_document_start",
         files={"a.txt": TXT}, steps=[press("down"), press("right"), press("cmd+shift+home"), type_("Z")], save=True,
         check=content("a.txt", "Zine2\nline3\n")),
    Case("cmd+shift+end selects to the end of the file", "plugin", "cmd+shift+end", "select_document_end",
         files={"a.txt": TXT}, steps=[press("down"), press("cmd+shift+end"), type_("Z")], save=True,
         check=content("a.txt", "line1\nZ")),
    Case("ctrl+g adds the next occurrence", "plugin", "ctrl+g", "add_cursor_next_match",
         files={"a.txt": "foo bar foo\n"}, steps=[press("ctrl+g"), press("ctrl+g"), type_("X")], save=True,
         check=content("a.txt", "X bar X\n")),
    Case("alt+shift+g adds a caret to each selected line", "plugin", "alt+shift+g", "add_cursors_to_line_ends",
         files={"a.txt": TXT}, steps=[press("shift+down"), press("shift+down"), press("shift+end"),
                                      press("alt+shift+g"), type_("X")], save=True,
         check=content("a.txt", "line1X\nline2X\nline3X\n")),
    Case("cmd+shift+c copies the file path", "plugin", "cmd+shift+c", "copy_file_path",
         files={"a.txt": TXT}, steps=[press("cmd+shift+c")],
         check=lambda r: (any(x.startswith("/") and x.endswith("/a.txt") for x in r.osc52), f"clipboard={r.osc52}")),

    Case("cmd+r replaces", "plugin", "cmd+r", "replace",
         files={"a.txt": TXT}, steps=[press("cmd+r", until=r"Replace"), type_("line"), press("enter"),
                                      type_("row"), press("enter")], save=True,
         check=content("a.txt", "row1\nrow2\nrow3\n")),
    Case("cmd+shift+f finds in files", "plugin", "cmd+shift+f", "open_live_grep",
         files={"a.txt": TXT, "other.txt": "zz needle zz\n"},
         steps=[press("cmd+shift+f", until=r"(?i)grep|search"), type_("needle", until=r"other\.txt")],
         check=new_text("other.txt")),
    Case("cmd+shift+r replaces in files", "plugin", "cmd+shift+r", "start_search_replace",
         files={"a.txt": "needle\n", "other.txt": "x needle\n"},
         steps=[press("cmd+shift+r", until=r"\*Search/Replace\*"), type_("needle", until=r"2 matches"), press("tab"),
                type_("pin"), press("alt+enter"), press("enter", until=r"Replaced 2 occurrences")],
         check=lambda r: (r.files == {"a.txt": "pin\n", "other.txt": "x pin\n"}, f"files={r.files}")),
    Case("cmd+shift+o goes to file", "plugin", "cmd+shift+o", "quick_open_files",
         files={"a.txt": TXT, "zzfile.txt": "z\n"}, steps=[press("cmd+shift+o", until=r"zzfile\.txt")],
         check=new_text("zzfile.txt")),
    Case("cmd+shift+a finds an action", "plugin", "cmd+shift+a", "command_palette",
         files={"a.txt": TXT}, steps=[press("cmd+shift+a", until=r">command"),
                                      type_("duplicate line above", until=r"Duplicate Line Above"), press("enter")],
         save=True, check=content("a.txt", "line1\nline1\nline2\nline3\n")),
    Case("cmd+1 toggles the project window", "plugin", "cmd+1", "toggle_file_explorer",
         files={"a.txt": TXT, "zzfile.txt": "z\n"}, steps=[press("cmd+1", until=r"zzfile\.txt")],
         check=new_text("File Explorer", "zzfile.txt")),
    Case("cmd+6 toggles the problems window", "plugin", "cmd+6", "toggle_diagnostics_panel",
         **go(errors=True), steps=[press("cmd+6", until=r"cannot use")], check=new_text("*Diagnostics*", "[E] 15:16 cannot use")),
    Case("cmd+shift+[ and cmd+shift+] switch tabs", "plugin", "cmd+shift+[", "prev_buffer",
         files={"a.txt": TXT, "b.txt": TXT}, open=["a.txt", "b.txt"],
         steps=[press("cmd+shift+["), type_("P"), press("cmd+shift+]"), type_("N"), press("cmd+s")],
         check=lambda r: (r.files["a.txt"][0] == "P" and r.files["b.txt"][0] == "N",
                          f"a={r.files['a.txt'][:6]!r} b={r.files['b.txt'][:6]!r}")),
    Case("cmd+shift+] selects the next tab", "plugin", "cmd+shift+]", "next_buffer",
         files={"a.txt": TXT, "b.txt": TXT, "c.txt": TXT}, open=["a.txt", "b.txt", "c.txt"],
         steps=[press("cmd+shift+]"), type_("N"), press("cmd+s")],
         check=lambda r: (r.files["a.txt"][0] == "N", f"a={r.files['a.txt'][:6]!r}")),
    Case("ctrl+alt+shift+down/up go to the next/previous change", "plugin", "ctrl+alt+shift+down", "diff_nav_next",
         files={"a.txt": NUMBERED}, git_modify={"a.txt": NUMBERED.replace("l10\n", "X\n").replace("l20\n", "Y\n")},
         ready=[r"│20 │"], steps=[press("ctrl+alt+shift+down", until=r"Ln 10,"), press("ctrl+alt+shift+down", until=r"Ln 20,"),
                              press("ctrl+alt+shift+up", until=r"Ln 10,")],
         check=lambda r: ((r.cursor(0), r.cursor(1), r.cursor(2)) == ((10, 1), (20, 1), (10, 1)),
                          f"cursor: {r.cursor(0)} {r.cursor(1)} {r.cursor(2)}")),
    Case("ctrl+alt+shift+up goes to the previous change", "plugin", "ctrl+alt+shift+up", "diff_nav_prev",
         files={"a.txt": NUMBERED}, git_modify={"a.txt": NUMBERED.replace("l10\n", "X\n")},
         ready=[r"│10 │"], steps=[press("cmd+end"), press("ctrl+alt+shift+up", until=r"Ln 10,")], check=cursor_at(10)),

    Case("cmd+b goes to declaration", "plugin", "cmd+b", "lsp_goto_definition",
         **go(), steps=at(14, 2) + [press("cmd+b", until=r"Ln 9,")], check=cursor_at(9)),
    Case("cmd+alt+b goes to implementation (shows a list)", "partial", "cmd+alt+b", "lsp_implementation",
         **go(), steps=at(3, 23) + [press("cmd+alt+b", until=r"main\.go:7")], check=new_text("main.go:7")),
    Case("alt+f7 finds usages", "plugin", "alt+f7", "lsp_references",
         **go(), steps=at(9, 6) + [press("alt+f7", until=r"main\.go:14")], check=new_text("main.go:14")),
    Case("shift+f6 renames", "plugin", "shift+f6", "lsp_rename",
         **go(), steps=at(14, 2) + [press("shift+f6"), *times(3, "backspace"), type_("bar"),
                                   press("enter", until=r"bar\(1")], save=True,
         check=lambda r: (r.files["main.go"].count("bar(") == 2 and "foo" not in r.files["main.go"],
                          f"main.go has {r.files['main.go'].count('bar(')} x 'bar('")),
    Case("f1 shows quick documentation", "plugin", "f1", "lsp_hover",
         **go(), steps=at(14, 2) + [press("f1", until=r"func foo\(a int, b string\) int")],
         check=new_text("func foo(a int, b string) int")),
    Case("ctrl+space completes", "plugin", "ctrl+space", "lsp_completion",
         **go(), steps=at(16) + [press("end"), press("enter"), type_("fo"), press("esc"),
                                 press("ctrl+space", until=r"foo \(a int, b string\)")],
         check=new_text("foo (a int, b string) int")),
    Case("cmd+p shows parameter info", "plugin", "cmd+p", "lsp_signature_help",
         **go(), steps=at(16) + [press("end"), press("enter"), type_("foo("), press("esc"),
                                 press("cmd+p", until=r"a int")],
         check=new_text("a int")),
    Case("alt+enter shows intention actions", "plugin", "alt+enter", "lsp_code_actions",
         **go(), steps=at(14, 2) + [press("alt+enter", until=r"Code Actions")], check=new_text("Code Actions")),
    Case("cmd+alt+l reformats the whole file, even with a selection (partial)", "partial", "cmd+alt+l", "format_buffer",
         **go("package main\n\nfunc a(x int,y int) {}\nfunc b(x int,y int) {}\n"),
         steps=[press("down"), press("down"), press("shift+end"), press("cmd+alt+l", until=r"b\(x int, y int\)")],
         save=True, check=content("main.go", "package main\n\nfunc a(x int, y int) {}\nfunc b(x int, y int) {}\n")),
    Case("f2 goes to the next error", "plugin", "f2", "jump_to_next_error",
         **go(errors=True), steps=[press("f2", until=r"Ln 15,")], check=cursor_at(15)),
    Case("shift+f2 goes to the previous error", "plugin", "shift+f2", "jump_to_previous_error",
         **go(errors=True), steps=[press("cmd+end"), press("shift+f2", until=r"Ln 15,")], check=cursor_at(15)),
    Case("cmd+f12 shows the file structure", "plugin", "cmd+f12", "goto_lsp_symbol",
         **go(), steps=[press("cmd+f12", until=r"\] Shape")], check=new_text("[iface] Shape", "[struct] Sq")),

    Case("cmd+z undoes", "inherited", "cmd+z", None, intellij="Undo / Redo",
         files={"a.txt": TXT}, steps=[type_("X"), press("cmd+z")], save=True, check=content("a.txt", TXT)),
    Case("cmd+shift+z redoes", "inherited", "cmd+shift+z", None, intellij="Undo / Redo",
         files={"a.txt": TXT}, steps=[type_("X"), press("cmd+z"), press("cmd+shift+z")], save=True,
         check=content("a.txt", "X" + TXT)),
    Case("cmd+x cuts", "inherited", "cmd+x", None, intellij="Cut",
         files={"a.txt": TXT}, steps=times(4, "shift+right") + [press("cmd+x")], save=True,
         check=both(content("a.txt", "1\nline2\nline3\n"), lambda r: ("line" in r.osc52, f"clipboard={r.osc52}"))),
    Case("cmd+c copies", "inherited", "cmd+c", None, intellij="Copy",
         files={"a.txt": TXT}, steps=times(4, "shift+right") + [press("cmd+c")],
         check=lambda r: ("line" in r.osc52, f"clipboard={r.osc52}")),
    Case("cmd+v pastes", "inherited", "cmd+v", None, intellij="Paste",
         files={"a.txt": TXT}, steps=times(4, "shift+right") + [press("cmd+c"), press("end"), press("cmd+v")],
         save=True, check=content("a.txt", "line1line\nline2\nline3\n")),
    Case("cmd+a selects all", "inherited", "cmd+a", None, intellij="Select All",
         files={"a.txt": TXT}, steps=[press("cmd+a"), type_("Z")], save=True, check=content("a.txt", "Z")),
    Case("cmd+f finds", "inherited", "cmd+f", None, intellij="Find / Find Next / Find Previous",
         files={"a.txt": "x\nhit\nx\nhit\nx\nhit\n"}, steps=[press("cmd+f"), type_("hit"), press("enter", until=r"Ln 2,")],
         check=cursor_at(2)),
    Case("cmd+g finds next", "inherited", "cmd+g", None, intellij="Find / Find Next / Find Previous",
         files={"a.txt": "x\nhit\nx\nhit\nx\nhit\n"},
         steps=[press("cmd+f"), type_("hit"), press("enter", until=r"Ln 2,"), press("cmd+g", until=r"Ln 4,"),
                press("cmd+g", until=r"Ln 6,")],
         check=lambda r: ([r.cursor(i)[0] for i in (-3, -2, -1)] == [2, 4, 6], f"lines {[r.cursor(i) for i in (-3, -2, -1)]}")),
    Case("cmd+shift+g finds previous", "inherited", "cmd+shift+g", None, intellij="Find / Find Next / Find Previous",
         files={"a.txt": "x\nhit\nx\nhit\nx\nhit\n"},
         steps=[press("cmd+f"), type_("hit"), press("enter", until=r"Ln 2,"), press("cmd+g", until=r"Ln 4,"),
                press("cmd+shift+g", until=r"Ln 2,")],
         check=cursor_at(2)),
    Case("cmd+l goes to line", "inherited", "cmd+l", None, intellij="Go to Line",
         files={"a.txt": TXT}, steps=[press("cmd+l"), type_("3"), press("enter", until=r"Ln 3,")], check=cursor_at(3)),
    Case("cmd+/ comments the line", "inherited", "cmd+/", None, intellij="Comment with Line Comment",
         files={"a.py": "x = 1\n"}, steps=[press("cmd+/")], save=True, check=content("a.py", "# x = 1\n")),
    Case("alt+left moves to the previous word", "inherited", "alt+left", None,
         intellij="Move Caret to Previous / Next Word",
         files={"a.txt": "foo bar baz\n"}, steps=[press("end"), press("alt+left"), type_("X")], save=True,
         check=content("a.txt", "foo bar Xbaz\n")),
    Case("alt+right moves to the end of the word", "inherited", "alt+right", None,
         intellij="Move Caret to Previous / Next Word",
         files={"a.txt": "foo bar baz\n"}, steps=[press("alt+right"), press("alt+right"), type_("X")], save=True,
         check=content("a.txt", "foo barX baz\n")),
    Case("alt+shift+left selects to the previous word", "inherited", "alt+shift+left", None,
         intellij="Move Caret to Previous / Next Word with Selection",
         files={"a.txt": "foo bar baz\n"}, steps=[press("end"), press("alt+shift+left"), type_("X")], save=True,
         check=content("a.txt", "foo bar X\n")),
    Case("alt+shift+right selects to the end of the word", "inherited", "alt+shift+right", None,
         intellij="Move Caret to Previous / Next Word with Selection",
         files={"a.txt": "foo bar baz\n"}, steps=[press("alt+shift+right"), type_("X")], save=True,
         check=content("a.txt", "X bar baz\n")),
    Case("cmd+left moves to the line start", "inherited", "cmd+left", None, intellij="Move Caret to Line Start / End",
         files={"a.txt": TXT}, steps=[press("end"), press("cmd+left"), type_("X")], save=True,
         check=content("a.txt", "Xline1\nline2\nline3\n")),
    Case("cmd+right moves to the line end", "inherited", "cmd+right", None, intellij="Move Caret to Line Start / End",
         files={"a.txt": TXT}, steps=[press("cmd+right"), type_("X")], save=True,
         check=content("a.txt", "line1X\nline2\nline3\n")),
    Case("cmd+shift+left selects to the line start", "inherited", "cmd+shift+left", None,
         intellij="Move Caret to Line Start / End with Selection",
         files={"a.txt": TXT}, steps=[press("end"), press("cmd+shift+left"), type_("X")], save=True,
         check=content("a.txt", "X\nline2\nline3\n")),
    Case("cmd+shift+right selects to the line end", "inherited", "cmd+shift+right", None,
         intellij="Move Caret to Line Start / End with Selection",
         files={"a.txt": TXT}, steps=[press("cmd+shift+right"), type_("X")], save=True,
         check=content("a.txt", "X\nline2\nline3\n")),
    Case("tab indents the selected lines", "inherited", "tab", None, intellij="Indent / Unindent Selection",
         files={"a.txt": TXT}, steps=[press("shift+down"), press("shift+end"), press("tab")], save=True,
         check=lambda r: (r.files["a.txt"].split("\n")[0].strip() == "line1" and r.files["a.txt"][0] in " \t"
                          and r.files["a.txt"].split("\n")[1][0] in " \t", f"a={r.files['a.txt']!r}")),
    Case("shift+tab unindents", "inherited", "shift+tab", None, intellij="Indent / Unindent Selection",
         files={"a.txt": "    line1\nline2\n"}, steps=[press("shift+tab")], save=True,
         check=content("a.txt", "line1\nline2\n")),
    Case("cmd+, opens settings", "inherited", "cmd+,", None, intellij="Settings",
         files={"a.txt": TXT}, steps=[press("cmd+,", until=r"Settings \[User\]")], check=new_text("Settings [User]")),

    Case("config.json is never written", "other", None, None,
         files={"a.txt": TXT}, steps=[press("cmd+backspace"), press("cmd+s")],
         check=both(lambda r: (r.config_after == r.config_before, f"config.json now {r.config_after!r}"),
                    content("a.txt", "line2\nline3\n"))),
    Case("your config.json keybindings win over the plugin", "other", "cmd+d", None,
         cfg={"keybindings": [{"key": "d", "modifiers": ["super"], "action": "add_cursor_next_match", "when": "normal"}]},
         files={"a.txt": "foo foo\n"}, steps=[press("cmd+d"), press("cmd+d"), type_("X")], save=True,
         check=content("a.txt", "X X\n")),
]
