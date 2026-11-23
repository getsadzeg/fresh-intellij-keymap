MOD_BITS = {"shift": 1, "alt": 2, "ctrl": 4, "cmd": 8}
MOD_SYMBOLS = [("cmd", "⌘"), ("ctrl", "⌃"), ("alt", "⌥"), ("shift", "⇧")]
CSI_LETTER = {"up": "A", "down": "B", "right": "C", "left": "D", "home": "H", "end": "F"}
TILDE = {"pageup": 5, "pagedown": 6}
F_KEYS = {5: 15, 6: 17, 7: 18, 8: 19, 9: 20, 10: 21, 11: 23, 12: 24}
NAMED = {"backspace": 127, "enter": 13, "space": 32, "esc": 27, "tab": 9}
KEY_SYMBOLS = {"up": "↑", "down": "↓", "left": "←", "right": "→", "home": "Home", "end": "End",
               "backspace": "⌫", "enter": "⏎", "space": "Space", "tab": "⇥", "esc": "Esc"}


def split(combo):
    *mods, key = combo.split("+")
    assert all(m in MOD_BITS for m in mods), combo
    return mods, key


def encode(combo):
    mods, key = split(combo)
    m = 1 + sum(MOD_BITS[x] for x in mods)
    if key in CSI_LETTER:
        return f"\x1b[1;{m}{CSI_LETTER[key]}" if mods else f"\x1b[{CSI_LETTER[key]}"
    if key in TILDE:
        return f"\x1b[{TILDE[key]};{m}~" if mods else f"\x1b[{TILDE[key]}~"
    if key[0] == "f" and key[1:].isdigit():
        n = int(key[1:])
        if n <= 4:
            letter = "PQRS"[n - 1]
            return f"\x1b[1;{m}{letter}" if mods else f"\x1bO{letter}"
        return f"\x1b[{F_KEYS[n]};{m}~" if mods else f"\x1b[{F_KEYS[n]}~"
    if key == "tab" and mods == ["shift"]:
        return "\x1b[Z"
    if not mods:
        return {"backspace": "\x7f", "enter": "\r", "tab": "\t", "space": " ", "esc": "\x1b[27u"}.get(key, key)
    return f"\x1b[{NAMED.get(key, ord(key) if len(key) == 1 else 0)};{m}u"


def fresh_combo(key, modifiers):
    key = {" ": "space"}.get(key, key.lower())
    mods = ["cmd" if m == "super" else m for m in modifiers]
    order = [name for name, _ in MOD_SYMBOLS]
    return "+".join(sorted(mods, key=order.index) + [key])


def symbols(combo):
    mods, key = split(combo)
    return "".join(s for name, s in MOD_SYMBOLS if name in mods) + KEY_SYMBOLS.get(key, key.upper())
