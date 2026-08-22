#!/usr/bin/env python3
"""
KBD2 render test
Version: 1.0.0

Builds the keyboard panel, renders its content view straight to a PNG and
exits.  Verifies layout and drawing without leaving an app instance running
and without needing screen-recording permission.

    render_test.py OUT.png [preset-name] [scale] [shift]

Pass "shift" as the fourth argument to render with the shift lock engaged,
which is the only way to see the upper legends and the latched key face
without touching the running app.
"""

import os
import sys

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBitmapImageFileTypePNG,
)

import kbd2


def main(out_path, preset=None, scale=None, shift=False):
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    controller = kbd2.KeypadController.alloc().init()
    controller.buildPanel()
    controller.panel.orderOut_(None)

    if preset:
        controller.applyColor_(kbd2._color(*dict(kbd2.KEY_PRESETS)[preset]))
    if scale:
        controller.applyScale_(float(scale))
    if os.environ.get("KBD2_BACKING") == "1":
        controller.toggleBacking_(None)
    if shift:
        controller.latched.add(kbd2.TAG_SHIFT)
        controller.restyleKeys()

    view = controller.panel.contentView()
    bounds = view.bounds()
    rep = view.bitmapImageRepForCachingDisplayInRect_(bounds)
    view.cacheDisplayInRect_toBitmapImageRep_(bounds, rep)
    data = rep.representationUsingType_properties_(NSBitmapImageFileTypePNG, {})
    data.writeToFile_atomically_(out_path, True)

    print("panel %.0fx%.0f  scale=%s  shift=%s -> %s"
          % (kbd2.PANEL_W, kbd2.PANEL_H, scale or 1.0, shift, out_path))
    print("subviews: %d" % len(view.subviews()))
    # Row-by-row geometry, so a misaligned key is visible as a number rather
    # than only as a picture.
    rows = {}
    for sub in view.subviews():
        frame = sub.frame()
        rows.setdefault(round(frame.origin.y, 1), []).append(
            (frame.origin.x, frame.size.width,
             sub.attributedTitle().string().replace("\n", "/")))
    for y in sorted(rows, reverse=True):
        keys = sorted(rows[y])
        span = keys[-1][0] + keys[-1][1] - keys[0][0]
        print("  y=%-6.1f n=%-3d span=%-6.1f %s"
              % (y, len(keys), span,
                 " ".join(k[2] if k[2].strip() else "[space]" for k in keys)))


if __name__ == "__main__":
    main(sys.argv[1],
         sys.argv[2] if len(sys.argv) > 2 else None,
         sys.argv[3] if len(sys.argv) > 3 else None,
         len(sys.argv) > 4 and sys.argv[4] == "shift")
