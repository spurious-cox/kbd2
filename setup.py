"""py2app build for KBD2.app

    ../KBD/venv/bin/python make_icon.py      (icon/ must be built first)
    ../KBD/venv/bin/python setup.py py2app

LSUIElement is what makes this work: the app has no Dock icon and no menu
bar, so it never becomes the active application and never pulls focus out of
the text field the keys are being typed into.

KBD_glyph.png ships in Resources because the app draws the same mark as its
icon in its own header, recolouring it to suit the field colour.

The bundle id is com.timmccoy.kbd2 -- distinct from KBD's com.timmccoy.kbd,
so the two apps hold SEPARATE Accessibility grants and separate saved
position, size and colour. Sharing an id would have made granting one
silently grant the other, and macOS would have had no way to tell which app
it was being asked about.
"""

import re
from pathlib import Path

from setuptools import setup

APP = ["kbd2.py"]
DATA_FILES = [("", ["icon/KBD2_glyph.png"])]


def app_version():
    """The single source of truth: APP_VERSION in kbd2.py.

    KBD learned this the hard way at its 1.5.2, where a second copy of the
    number in this file shipped a bundle that disagreed with the app drawing
    its own version in its header. Bump APP_VERSION in kbd2.py, nowhere else.
    """
    source = Path(__file__).with_name("kbd2.py").read_text()
    match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', source, re.MULTILINE)
    if not match:
        raise SystemExit("setup.py: APP_VERSION not found in kbd2.py")
    return match.group(1)


VERSION = app_version()

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "icon/KBD2.icns",
    "plist": {
        "CFBundleName": "KBD2",
        "CFBundleDisplayName": "KBD2",
        "CFBundleIdentifier": "com.timmccoy.kbd2",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "13.0",
        "NSHighResolutionCapable": True,
        # Accessory app: no Dock icon, no menu bar, never activates.
        "LSUIElement": True,
        "NSHumanReadableCopyright":
            "Copyright © 2026 Tim McCoy. All rights reserved.",
        "CFBundleGetInfoString":
            "KBD2 — floating alphanumeric keyboard that types into any app's "
            "text field.",
    },
}

setup(
    name="KBD2",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
