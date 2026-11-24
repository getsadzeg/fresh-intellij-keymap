# Details

## Not supported yet

- **Extend / Shrink Selection** (⌥↑ / ⌥↓): Fresh's expand selection grows from the cursor rather
  than by code structure.
- **Toggle Case** (⌘⇧U): Fresh's toggle case cycles through case styles in a different way.
- **Recent Files** (⌘E): Fresh's list holds recently closed files only.
- **Back / Forward** (⌘[ / ⌘]): didn't return to the right position in testing.
- **Start New Line** (⇧⏎) and **Join Lines** (⌃⇧J): not in Fresh yet.
- **Search Everywhere** (double ⇧): terminals don't pass a lone ⇧ press to apps.
- **Other refactorings, run / debug, VCS dialogs, folding**: no Fresh equivalent.

## Keys that mean something else in Fresh

The plugin only adds IntelliJ shortcuts and leaves Fresh's other keys alone. These keys do
something different in Fresh:

| Key | IntelliJ | Fresh |
|---|---|---|
| ⌥↑ / ⌥↓ | Extend / Shrink Selection | Move line up / down |
| ⌘⇧K | Push | Delete line |
| ⌃H | Type Hierarchy | Delete previous word |
| ⌘⇧↑ / ⌘⇧↓ | Move Statement Up / Down | Select to start / end of file |

## Customize

Key bindings in the `keybindings` list of your `~/.config/fresh/config.json` take priority over
this plugin. For example, to keep Fresh's own ⌘D (add the next occurrence to the selection):

```json
"keybindings": [
  { "key": "d", "modifiers": ["super"], "action": "add_cursor_next_match", "when": "normal" }
]
```

Use `"action": "noop"` to turn a key off, for example one from the table above.

## Uninstalling

⌃P → **Package: Remove**, then restart Fresh. The shortcuts stay active until Fresh restarts.
