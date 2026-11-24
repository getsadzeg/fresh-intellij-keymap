# How it's tested

## Unit tests

Check `keymap.json` without starting Fresh: every row is complete, uses known key and modifier
names, no two rows share a shortcut, and every row has a matching end-to-end test.

```sh
python3 -m unittest discover -s tests/unit
```

## End-to-end tests

Run the real Fresh in a simulated terminal that behaves like Ghostty, kitty or WezTerm, type each
shortcut as real keystrokes, and check the result: the saved file, the cursor position, the text
on screen, or what was copied. Language features run against gopls. The shortcuts that already
work in Fresh are covered too. Each test uses a throwaway home directory, so your own Fresh config
and clipboard are never touched. They run on every push.

```sh
python3 -m venv .venv && .venv/bin/pip install pyte
.venv/bin/python tests/e2e/run.py
```

Needs `fresh`, `gopls` and `git` on your PATH.

## Real terminal check

A script opens a separate Ghostty window running Fresh, presses every shortcut there, and confirms
from Fresh's own log which key arrived. It uses the [recommended Ghostty setup](ghostty.md) and
ignores your own Ghostty config. Java language features were also checked this way with jdtls.

```sh
python3 tests/ghostty_e2e/check.py
```

Needs Accessibility permission for your terminal app (System Settings → Privacy & Security →
Accessibility). Ghostty's ⌘V pastes your clipboard into a throwaway practice file.

## Tested with

Fresh 0.5.9, Ghostty 1.4, macOS 26.

## Not tested yet

kitty, WezTerm, iTerm2, Linux.
