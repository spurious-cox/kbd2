# KBD2

A floating alphanumeric keyboard for macOS. It sits above every window, on
every Space, and types into whatever text field currently has focus — in any
application.

The full-keyboard sibling of [KBD](../KBD), which does the same job for a
numeric keypad.

![KBD2](icon/KBD2_1024.png)

## What it does

- **Never steals focus.** The panel is a non-activating `NSPanel` with no Dock
  icon and no menu bar, so clicking a key leaves the cursor exactly where it
  was, in the field you are typing into.
- **Floats over everything**, including full-screen apps, and follows you
  across Spaces.
- **SHIFT LOCKS.** It is a toggle, not a held key: tap it on and every letter
  arrives uppercase and every dual-legend key sends its upper symbol; tap it
  off and both revert. The engaged key fills with a lighter face, and each key
  draws its live legend bright with the other dimmed, so the state is readable
  key by key.
- **`^` `⌥` `⌘` latch the same way** — tap one on, it applies to every key
  until tapped off. All four modifiers behave alike by design.
- **Drag it anywhere** on the coloured field, header included.
- **Resize** by the corner grip, by option-dragging, or from the size menu.
  The whole keyboard scales as one.
- **Nine key colours**, from the `•••` at either end of the header or from a
  right-click anywhere. The colour lands on the key faces, the legends flip to
  whatever contrasts, and the field takes a darkened version of the same hue.
- **Position, size and colour are remembered** across launches.

## Layout

Five rows on a fourteen-column grid, modelled on a physical Mac keyboard.
Every key is one column wide except SHIFT and RETURN (two each) and the space
bar, which takes what is left of row five beside the globe.

The globe key opens **Emoji & Symbols** — macOS has no other keyboard to
switch to, and a key that did nothing would read as broken.

## Accessibility permission

macOS only lets an app post keystrokes to other applications once you allow
it, so KBD2 asks on first launch and offers to open the right settings pane.
It keeps watching, and the warning in its header clears the moment you grant
it. See [PRIVACY.md](PRIVACY.md) for what that permission does and does not
allow.

KBD2 has its own bundle id (`com.timmccoy.kbd2`), so it holds a **separate**
grant from KBD — allowing one does not allow the other.

## Building

Uses KBD's virtual environment rather than keeping a second copy of PyObjC and
py2app in step:

```
../KBD/venv/bin/python make_icon.py     # only when the artwork changes
./build.sh --install                    # build, sign, install to /Applications
./release.sh                            # notarize + staple, and build a DMG
```

`APP_VERSION` in `kbd2.py` is the single source of truth for the version;
`setup.py` reads it, and the app draws it in its own header.

### Checking the layout without launching it

```
KBD2_SKIP_AX_PROMPT=1 ../KBD/venv/bin/python render_test.py out.png [colour] [scale] [shift]
```

Renders the panel straight to a PNG and exits, leaving no app instance
running and needing no screen-recording permission. It also prints each row's
key count and total span, so a misaligned key shows up as a number rather
than only as a picture — every row should span exactly the same width.

## Licence

MIT — see [LICENSE](LICENSE).
