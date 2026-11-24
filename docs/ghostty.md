# Ghostty details

## Why some keys don't reach Fresh

Ghostty looks at every key before the app in its window does. If a key is one of Ghostty's own
shortcuts, Ghostty runs its feature and Fresh never sees the key. With Ghostty's default config
that happens for ⌘Z, ⌘⇧Z, ⌘A, ⌘F, ⌘,, ⌘D, ⌘Home, ⌘End, ⌘1, ⌘6, ⌘⇧[ and ⌘⇧]. ⌘C, ⌘G, ⌘⇧G and
⌘⇧F only go to Ghostty while text is selected in Ghostty or its search bar is open, so they need
nothing.

Ghostty also sends F1 and F2 in a format Fresh doesn't read yet. The setup below makes Ghostty send
them in the classic format instead.

## Recommended setup

Add [these lines](../ghostty/config.ghostty) to `~/.config/ghostty/config.ghostty`, then choose
**Ghostty → Reload Configuration** from the menu bar. The keys then go to Fresh. Ghostty's
features stay available from its menu bar and its command palette (⌘⇧P).

## Keep Ghostty's shortcuts

To keep every Ghostty feature on a key, use these lines instead. They move Ghostty's features to
⌘⌥ keys (split right moves to ⌘⌥⇧D, because ⌘⌥D shows and hides the Dock). ⌃⇥ and ⌃⇧⇥ keep
switching Ghostty tabs.

```
keybind = super+z=unbind
keybind = super+alt+z=undo
keybind = super+shift+z=unbind
keybind = super+alt+shift+z=redo
keybind = super+d=unbind
keybind = super+alt+shift+d=new_split:right
keybind = super+a=unbind
keybind = super+alt+a=select_all
keybind = super+f=unbind
keybind = super+alt+f=start_search
keybind = super+,=unbind
keybind = super+alt+,=open_config:os_open
keybind = super+home=unbind
keybind = super+alt+home=scroll_to_top
keybind = super+end=unbind
keybind = super+alt+end=scroll_to_bottom
keybind = super+1=unbind
keybind = super+digit_1=unbind
keybind = super+alt+1=goto_tab:1
keybind = super+6=unbind
keybind = super+digit_6=unbind
keybind = super+alt+6=goto_tab:6
keybind = super+shift+[=unbind
keybind = super+shift+]=unbind
keybind = f1=esc:OP
keybind = f2=esc:OQ
```

## Optional Fresh tweaks

Add these to the `keybindings` list in `~/.config/fresh/config.json`:

```json
"keybindings": [
  { "key": "u", "modifiers": ["ctrl"], "action": "delete_line", "when": "normal" },
  { "key": "f", "modifiers": ["alt"], "action": "move_word_end", "when": "normal" }
]
```

- **⌘⌫ deletes the line.** Ghostty sends ⌘⌫ as ⌃U so shells can clear the line, and Fresh reads ⌃U
  as "delete to line start". With this line, ⌃U deletes the whole line in Fresh.
- **⌥→ stops at the end of the word.** Ghostty sends ⌥→ as ⌥F, which Fresh reads as "start of the
  next word". With this line it stops at the end of the word, as in IntelliJ.

## Other keyboard layouts

Shortcuts with ⌥ and a letter (such as ⌥⇧G) need ⌥ to act as Alt. Ghostty does that by default
only for U.S. keyboard layouts. For any other layout, add this to your Ghostty config:

```
macos-option-as-alt = left
```
