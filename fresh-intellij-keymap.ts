const editor = getEditor();

type Row = { intellij: string; key: string; modifiers: string[]; action: string };

let rows: Row[] | null = null;
try {
  const text = editor.readFile(editor.pathJoin(editor.getPluginDir(), "keymap.json"));
  rows = text === null ? null : (JSON.parse(text) as Row[]);
} catch (_) {
  rows = null;
}

if (!Array.isArray(rows)) {
  editor.setStatus("IntelliJ keymap: couldn't load keymap.json");
} else {
  const bindings = rows.map(({ key, modifiers, action }) => ({ key, modifiers, action, when: "normal" }));
  editor.setSetting("keybinding_maps", { intellij: { inherits: "macos-gui", bindings } });
  editor.setSetting("active_keybinding_map", "intellij");
  editor.setStatus("IntelliJ keymap active");
}
