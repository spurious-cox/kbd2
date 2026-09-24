#!/usr/bin/env python3
"""
KBD2 - floating alphanumeric keyboard for macOS
Version: 1.0.0

A borderless, non-activating floating panel holding a full alphanumeric
keyboard: five rows built to Tim's mockup of his own physical Mac keyboard.
Key presses are posted as real keyboard events to the HID event tap, so they
land in whatever text field currently has keyboard focus -- in any app.

Sibling of KBD ([[project-kbd]]), the numeric keypad, and deliberately built
on the same bones: same non-activating panel, same scale-by-one-factor
geometry, same colour and size persistence, so a future iOS port has the
same shape to follow.

Behaviour:
  * Non-activating panel: clicking a key never steals focus from the text
    field being typed into.
  * Floats above all windows, on every Space, including full-screen apps.
  * SHIFT LOCKS. It is a toggle, not a held key -- tap it on, every dual
    legend key sends its upper symbol and every letter arrives uppercase;
    tap it off and they go back to the lower legend and lowercase. The
    engaged key is filled with the accent colour so the state is never in
    doubt, and each key's active legend is drawn bright while the inactive
    one dims.
  * ^ (control), (option) and (command) latch the same way: tap one on, it
    stays on and applies to every key until tapped off again. Tim's choice
    over one-shot, matching the shift lock so all four behave alike.
  * Draggable from anywhere on the coloured field, header included.
  * Resizable: corner grip, option-drag, or a size from the right-click menu.
  * The ellipsis at EITHER end of the header opens the colour menu; the
    colour lands on the KEY FACES, with the legend text flipped to whatever
    contrasts, and the field behind takes a darkened version of the same hue.

Requires Accessibility permission (System Settings > Privacy & Security >
Accessibility) so the app is allowed to post keyboard events, exactly as KBD
does, and asks for it the same way.

History:
  1.5.1  The icon is also an Icon Composer icon, so macOS 26 and later draw it
         full size with the system's own shape, not shrunk onto a plate.
  1.5.0  THE LAYOUT NOW MATCHES THE iOS KEYBOARD, at Tim's ask, so a key is
         in the same place on his Mac as on his iPad and iPhone. Row two
         starts at Q and closes with forward delete; row four gives up the
         three modifiers ^ ⌥ ⌘ -- iOS has none to offer -- and takes TAB
         (down from row two, into the slot iOS fills with its globe) plus
         cursor left and right. **Losing ⌘ means this keyboard can no longer
         send ⌘C and the like; that was Tim's call, made knowingly.** Row
         five is untouched by his instruction: globe, space bar, DISMISS,
         where they have always been. The space bar also gains the one thing
         it never had -- the open box legend, SF Symbol "space" -- so it
         reads as a key rather than a blank strip.
  1.4.0  The globe key now does what its glyph promises: it lists the other
         keyboard input sources macOS has enabled and switches to the one
         picked. With only one enabled -- the usual Mac -- there is nothing
         to switch to, so it says "no keyboards found" in the header and
         changes nothing.
  1.3.0  Tim's own KBD2 artwork becomes the icon and the header mark. It
         already contains the 2, so the separately drawn digit is gone.
         Keys narrowed by a third (KEY_W 44 -> 29.3): the panel is 508 wide
         instead of 714, which is close to KBD's own footprint.
  1.2.0  DISMISS added at the right end of the bottom row, the same two
         columns wide as RETURN directly above it, with the space bar
         shortened to make room. A row's flexible key now measures itself
         from what the keys AFTER it need, so nothing has to be hand-fitted.
  1.1.0  Transparent by default: the field behind the keys is no longer
         painted, so the gaps between keys show whatever is underneath --
         Tim's mockup had a transparent background and the dark field was
         reading as a black border around every key. The header keeps a
         small pill of its own, because text alone on a transparent panel
         is unreadable over a light window. "Show Backing" on the menu
         brings the old solid field back; the choice is remembered.
  1.0.0  Initial version. Layout from Tim's mockup, with three additions he
         chose when the mockup proved unusable as drawn: a fifth row holding
         the globe key on the far left and a full-width space bar, and
         dedicated comma and period keys in row four. Keys are uniform
         everywhere except SHIFT (two keys wide) and the space bar.
"""

import math
import os

import objc
from Foundation import (
    NSBundle,
    NSMakeRange,
    NSMutableAttributedString,
    NSObject,
    NSMakePoint,
    NSMakeRect,
    NSMakeSize,
    NSNotificationCenter,
    NSPointInRect,
    NSTimer,
    NSURL,
    NSUserDefaults,
    NSZeroRect,
)
from AppKit import (
    NSAlert,
    NSButton,
    NSAlertFirstButtonReturn,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSAttributedString,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSColorSpace,
    NSCompositingOperationSourceAtop,
    NSCompositingOperationSourceOver,
    NSEvent,
    NSEventModifierFlagOption,
    NSFont,
    NSFontAttributeName,
    NSFontWeightMedium,
    NSFontWeightRegular,
    NSFontWeightSemibold,
    NSForegroundColorAttributeName,
    NSImage,
    NSImageOnly,
    NSImageSymbolConfiguration,
    NSMenu,
    NSMenuItem,
    NSMutableParagraphStyle,
    NSOffState,
    NSOnState,
    NSPanel,
    NSParagraphStyleAttributeName,
    NSRectFillUsingOperation,
    NSScreen,
    NSStatusWindowLevel,
    NSTextAlignmentCenter,
    NSTextAlignmentLeft,
    NSTextAlignmentRight,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowDidMoveNotification,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
    NSWorkspace,
)
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    CGEventSourceCreate,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
    kCGEventSourceStateHIDSystemState,
    kCGHIDEventTap,
)
from ApplicationServices import (
    AXIsProcessTrusted,
    AXIsProcessTrustedWithOptions,
    kAXTrustedCheckOptionPrompt,
)

# ---------------------------------------------------------------- constants

APP_VERSION = "1.5.1"
CREDIT_TEXT = "(c) 2026 Tim McCoy"
DEFAULTS_ORIGIN_KEY = "KBD2PanelOrigin"
DEFAULTS_COLOR_KEY = "KBD2KeyColor"
DEFAULTS_SCALE_KEY = "KBD2Scale"
DEFAULTS_BACKING_KEY = "KBD2Backing"

# Virtual keycodes, ANSI layout. Every printable key is here by its UNSHIFTED
# character: the shifted symbol is the same keycode with the shift flag, which
# is exactly what the shift lock adds. No key needs a second code.
KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7,
    "c": 8, "v": 9, "b": 11, "q": 12, "w": 13, "e": 14, "r": 15,
    "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22,
    "5": 23, "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29,
    "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35, "l": 37,
    "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44,
    "n": 45, "m": 46, ".": 47, "`": 50,
}
KEYCODE_RETURN = 36
KEYCODE_TAB = 48
KEYCODE_SPACE = 49
KEYCODE_DELETE = 51
# 1.5.0, for the iOS arrangement: forward delete and the two cursor keys.
KEYCODE_FORWARD_DELETE = 117
KEYCODE_LEFT = 123
KEYCODE_RIGHT = 124

# Sentinels. No virtual keycode is negative, so these can never collide.
TAG_SHIFT = -1
TAG_CONTROL = -2
TAG_OPTION = -3
TAG_COMMAND = -4
TAG_GLOBE = -5
TAG_ELLIPSIS = -6
TAG_BACKING = -7
TAG_DISMISS = -8

MODIFIER_TAGS = (TAG_SHIFT, TAG_CONTROL, TAG_OPTION, TAG_COMMAND)
MODIFIER_FLAGS = {
    TAG_SHIFT: kCGEventFlagMaskShift,
    TAG_CONTROL: kCGEventFlagMaskControl,
    TAG_OPTION: kCGEventFlagMaskAlternate,
    TAG_COMMAND: kCGEventFlagMaskCommand,
}

TAG_SIZE_BASE = 100

# ------------------------------------------------------------------ layout
#
# Five rows on a fourteen-column grid. Every key is exactly one column wide
# except SHIFT and RETURN and DISMISS (two each) and the space bar (the rest
# of row five beside the globe) -- Tim asked for keys as uniform as possible.
#
# SINCE 1.5.0 ROWS ONE TO FOUR ARE THE iOS LAYOUT, key for key and column for
# column, so nothing moves between Tim's Mac, iPad and iPhone. Row five is the
# one deliberate difference: iOS has no globe to place and cannot dismiss
# itself, so it carries the space bar alone, while the Mac keeps globe, space
# and DISMISS. The only key kind iOS has no use for is "mod" -- it is left in
# the code, unused by any row, rather than torn out.
#
# A key is (lower, upper, keycode, kind):
#   "dual"   both legends drawn, upper sent when the shift lock is on
#   "alpha"  one legend, drawn lowercase until the shift lock is on
#   "glyph"  one symbol, no shift meaning (tab, delete, return, cursor keys)
#   "symbol" an SF Symbol, tinted like text (the globe and the space bar)
#   "mod"    latches instead of typing -- no row uses this since 1.5.0
#
ROWS = [
    [("`", "~", KEYCODES["`"], "dual"),
     ("1", "!", KEYCODES["1"], "dual"),
     ("2", "@", KEYCODES["2"], "dual"),
     ("3", "#", KEYCODES["3"], "dual"),
     ("4", "$", KEYCODES["4"], "dual"),
     ("5", "%", KEYCODES["5"], "dual"),
     ("6", "^", KEYCODES["6"], "dual"),
     ("7", "&", KEYCODES["7"], "dual"),
     ("8", "*", KEYCODES["8"], "dual"),
     ("9", "(", KEYCODES["9"], "dual"),
     ("0", ")", KEYCODES["0"], "dual"),
     ("-", "_", KEYCODES["-"], "dual"),
     ("=", "+", KEYCODES["="], "dual"),
     ("⌫", None, KEYCODE_DELETE, "glyph")],

    # Row two starts at Q, as it does on iOS -- the tab key moved down to
     # row four, into the slot iOS gives the globe. Forward delete closes the
     # row on both platforms.
    [("q", None, KEYCODES["q"], "alpha"),
     ("w", None, KEYCODES["w"], "alpha"),
     ("e", None, KEYCODES["e"], "alpha"),
     ("r", None, KEYCODES["r"], "alpha"),
     ("t", None, KEYCODES["t"], "alpha"),
     ("y", None, KEYCODES["y"], "alpha"),
     ("u", None, KEYCODES["u"], "alpha"),
     ("i", None, KEYCODES["i"], "alpha"),
     ("o", None, KEYCODES["o"], "alpha"),
     ("p", None, KEYCODES["p"], "alpha"),
     ("[", "{", KEYCODES["["], "dual"),
     ("]", "}", KEYCODES["]"], "dual"),
     ("\\", "|", KEYCODES["\\"], "dual"),
     ("⌦", None, KEYCODE_FORWARD_DELETE, "glyph")],

    [("⇪", None, TAG_SHIFT, "mod"),
     ("a", None, KEYCODES["a"], "alpha"),
     ("s", None, KEYCODES["s"], "alpha"),
     ("d", None, KEYCODES["d"], "alpha"),
     ("f", None, KEYCODES["f"], "alpha"),
     ("g", None, KEYCODES["g"], "alpha"),
     ("h", None, KEYCODES["h"], "alpha"),
     ("j", None, KEYCODES["j"], "alpha"),
     ("k", None, KEYCODES["k"], "alpha"),
     ("l", None, KEYCODES["l"], "alpha"),
     (",", "<", KEYCODES[","], "dual"),
     (";", ":", KEYCODES[";"], "dual"),
     ("'", "\"", KEYCODES["'"], "dual")],

    # 1.5.0: ^ ⌥ ⌘ are gone, at Tim's ask to match the iOS layout, which has
     # no modifiers to give. iOS puts the globe, cursor left and cursor right
     # in these three slots; the Mac keeps its globe down in row five, so the
     # vacated slot takes the TAB key that row two gave up -- which keeps
     # every letter in the same column as iOS, and keeps a key the Mac can
     # genuinely send and iOS cannot.
    [("⇥", None, KEYCODE_TAB, "glyph"),
     ("←", None, KEYCODE_LEFT, "glyph"),
     ("→", None, KEYCODE_RIGHT, "glyph"),
     ("z", None, KEYCODES["z"], "alpha"),
     ("x", None, KEYCODES["x"], "alpha"),
     ("c", None, KEYCODES["c"], "alpha"),
     ("v", None, KEYCODES["v"], "alpha"),
     ("b", None, KEYCODES["b"], "alpha"),
     ("n", None, KEYCODES["n"], "alpha"),
     ("m", None, KEYCODES["m"], "alpha"),
     (".", ">", KEYCODES["."], "dual"),
     ("/", "?", KEYCODES["/"], "dual"),
     ("↩", None, KEYCODE_RETURN, "glyph")],

    [("globe", None, TAG_GLOBE, "symbol"),
     # 1.5.0: the space bar carries the OPEN BOX now. It was the one key
     # with no legend at all, which left it reading as a blank strip rather
     # than as a key; SF Symbols has "space" for exactly this, so it goes
     # through the symbol path and is tinted and centred like any other.
     ("space", None, KEYCODE_SPACE, "symbol"),
     ("DISMISS", None, TAG_DISMISS, "action")],
]

COLUMNS = 14

# The only keys that are not one column wide. Tim asked for keys as uniform as
# possible; on a fourteen-column grid these are the two that cannot be, and
# both are wide on his own keyboard for the same reason -- they are the keys
# a hand finds without looking. The space bar is wider still and is measured
# from what is left of row five beside the globe.
WIDE_COLUMNS = {TAG_SHIFT: 2, KEYCODE_RETURN: 2, TAG_DISMISS: 2}

# Base geometry, in points, at 100%. One set of measurements times a single
# scale factor -- a keyboard keeps its proportions at every size, and one
# factor is also what an iOS port would need.
MARGIN = 10.0
GAP = 6.0
ROW_GAP = 5.0           # tighter than GAP: Tim asked to close up the rows
KEY_W = 29.3            # a third off 44.0, at Tim's ask
KEY_H = 38.0
ROW_W = KEY_W * COLUMNS + GAP * (COLUMNS - 1)           # 694
HEADER_H = 22.0
HEADER_GAP = 6.0
PANEL_W = ROW_W + MARGIN * 2                                            # 714
PANEL_H = (MARGIN * 2 + KEY_H * len(ROWS) + ROW_GAP * (len(ROWS) - 1)
           + HEADER_GAP + HEADER_H)                                     # 258
FIELD_RADIUS = 10.0
KEY_RADIUS = 7.0
GRIP_SIZE = 18.0
CREDIT_FONT_SIZE = 11.0
GLYPH_H = 17.0              # the KBD mark in the header
ELLIPSIS_W = 26.0           # the colour hotspot at each end of the header

# Legend sizes, at 100%.
FONT_ALPHA = 16.0
FONT_DUAL = 10.0
FONT_GLYPH = 13.0
FONT_ACTION = 10.5          # a word on a key, not a symbol
DUAL_GAP = 1.0              # between a key's two legends

ACCESSIBILITY_PANE = (
    "x-apple.systempreferences:com.apple.preference.security"
    "?Privacy_Accessibility"
)
TRUST_POLL_SECONDS = 2.0
NOTICE_SECONDS = 3.0        # how long a header message stays up

MIN_SCALE = 0.5
MAX_SCALE = 2.5
SIZE_PRESETS = [("Small", 0.75), ("Default", 1.0), ("Large", 1.25),
                ("Larger", 1.5), ("Largest", 2.0)]


def _color(r, g, b):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1.0)


# Key colour presets. Unlike KBD, where the preset colours the FIELD, here it
# colours the KEY FACES -- that is what Tim's mockup shows, green keys with
# white legends -- and the field takes a darkened version of the same hue.
DEFAULT_KEY_COLOR = (0.082, 0.396, 0.251)      # DupScore green, as KBD's Green
KEY_PRESETS = [
    ("Green", DEFAULT_KEY_COLOR),
    ("Blue", (0.12, 0.56, 1.00)),
    ("Indigo", (0.35, 0.34, 0.84)),
    ("Teal", (0.11, 0.60, 0.62)),
    ("Orange", (0.95, 0.55, 0.15)),
    ("Red", (0.83, 0.26, 0.26)),
    ("Graphite", (0.38, 0.39, 0.42)),
    ("Charcoal", (0.16, 0.17, 0.19)),
    ("Bone", (0.93, 0.92, 0.89)),
]


def rgb_components(color):
    """(r, g, b) in device RGB, safe for any colour value."""
    converted = color.colorUsingColorSpace_(NSColorSpace.deviceRGBColorSpace())
    if converted is None:
        return DEFAULT_KEY_COLOR
    return (converted.redComponent(),
            converted.greenComponent(),
            converted.blueComponent())


def is_light(color):
    """True when the colour is bright enough to need dark text on it."""
    r, g, b = rgb_components(color)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 0.62


def shaded(color, factor):
    """The same hue, darker (factor < 1) or lighter (factor > 1)."""
    r, g, b = rgb_components(color)
    if factor <= 1.0:
        return _color(r * factor, g * factor, b * factor)
    return _color(r + (1.0 - r) * (factor - 1.0),
                  g + (1.0 - g) * (factor - 1.0),
                  b + (1.0 - b) * (factor - 1.0))


def contrast_text(color):
    """Legend colour: near-black on a light key, white on a dark one."""
    if is_light(color):
        return NSColor.colorWithCalibratedWhite_alpha_(0.12, 1.0)
    return NSColor.colorWithCalibratedWhite_alpha_(1.0, 1.0)


def clamp_scale(scale):
    return max(MIN_SCALE, min(MAX_SCALE, scale))


# ------------------------------------------------------------- the KBD mark

def glyph_path():
    """KBD_glyph.png, whether running from the bundle or from source."""
    packaged = NSBundle.mainBundle().pathForResource_ofType_("KBD2_glyph", "png")
    if packaged:
        return packaged
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "icon", "KBD2_glyph.png")
    return local if os.path.exists(local) else None


def load_glyph():
    path = glyph_path()
    if path is None:
        return None
    return NSImage.alloc().initWithContentsOfFile_(path)


def tinted_glyph(glyph, color, height):
    """The mark recoloured, drawn into its own image so the tint lands on the
    artwork's alpha and not on the field behind it."""
    if glyph is None or height <= 0:
        return None
    source = glyph.size()
    if source.height <= 0:
        return None
    width = source.width * height / source.height
    tinted = NSImage.alloc().initWithSize_(NSMakeSize(width, height))
    rect = NSMakeRect(0, 0, width, height)
    tinted.lockFocus()
    glyph.drawInRect_fromRect_operation_fraction_(
        rect, NSZeroRect, NSCompositingOperationSourceOver, 1.0)
    color.set()
    NSRectFillUsingOperation(rect, NSCompositingOperationSourceAtop)
    tinted.unlockFocus()
    return tinted


# ------------------------------------------------------- keyboard sources
#
# The Text Input Source API lives in HIToolbox, which PyObjC does not wrap,
# so its handful of functions and constants are loaded by hand. Looking the
# bundle up by IDENTIFIER returns nothing (it is a sub-framework of Carbon
# and not loaded by default); the path is what works.

_TIS = {}


def _tis():
    """The TIS symbols, loaded once. An empty dict means unavailable, and
    every caller treats that as 'no other keyboards' rather than failing."""
    if _TIS:
        return _TIS
    bundle = NSBundle.bundleWithPath_(
        "/System/Library/Frameworks/Carbon.framework/Frameworks/HIToolbox.framework")
    if bundle is None:
        return _TIS
    try:
        objc.loadBundleFunctions(bundle, _TIS, [
            ("TISCreateInputSourceList", b"@@Z"),
            ("TISSelectInputSource", b"i@"),
            ("TISGetInputSourceProperty", b"@@@"),
            ("TISCopyCurrentKeyboardInputSource", b"@"),
        ])
        objc.loadBundleVariables(bundle, _TIS, [
            ("kTISPropertyInputSourceIsSelectCapable", b"@"),
            ("kTISPropertyInputSourceIsEnabled", b"@"),
            ("kTISPropertyLocalizedName", b"@"),
            ("kTISPropertyInputSourceCategory", b"@"),
            ("kTISCategoryKeyboardInputSource", b"@"),
        ])
    except Exception:
        _TIS.clear()
    return _TIS


def keyboard_sources():
    """[(name, source)] for every enabled, selectable keyboard layout OTHER
    than the one in use. The current one is excluded because switching to it
    is not a switch."""
    tis = _tis()
    if not tis:
        return []
    try:
        found = tis["TISCreateInputSourceList"]({
            tis["kTISPropertyInputSourceCategory"]:
                tis["kTISCategoryKeyboardInputSource"],
            tis["kTISPropertyInputSourceIsEnabled"]: True,
            tis["kTISPropertyInputSourceIsSelectCapable"]: True,
        }, False) or []
        current = tis["TISCopyCurrentKeyboardInputSource"]()
        current_name = (tis["TISGetInputSourceProperty"](
            current, tis["kTISPropertyLocalizedName"]) if current else None)
        sources = []
        for source in found:
            name = tis["TISGetInputSourceProperty"](
                source, tis["kTISPropertyLocalizedName"])
            if name and name != current_name:
                sources.append((str(name), source))
        return sources
    except Exception:
        return []


def select_keyboard_source(source):
    tis = _tis()
    if not tis:
        return False
    try:
        return tis["TISSelectInputSource"](source) == 0
    except Exception:
        return False


# ------------------------------------------------------------ event posting

def post_keycode(keycode, flags=0):
    """Post a key down/up pair to the HID tap, i.e. to the focused field."""
    source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)
    for is_down in (True, False):
        event = CGEventCreateKeyboardEvent(source, keycode, is_down)
        if event is None:
            continue
        # Set the flags explicitly every time, never inherit: a latched
        # modifier here is ours to apply, and a stray one from the real
        # keyboard would silently change what the key types.
        CGEventSetFlags(event, flags)
        CGEventPost(kCGHIDEventTap, event)


# --------------------------------------------------------------- ui classes

class KeypadPanel(NSPanel):
    """A panel that refuses to become key, so focus stays in the text field."""

    def canBecomeKeyWindow(self):
        return False

    def canBecomeMainWindow(self):
        return False


class FieldView(NSView):
    """The coloured field: drag handle, header, and resize grip."""

    def initWithFrame_(self, frame):
        self = objc.super(FieldView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.fieldColor = shaded(_color(*DEFAULT_KEY_COLOR), 0.35)
        self.keyColor = _color(*DEFAULT_KEY_COLOR)
        self.showBacking = False
        self.scale = 1.0
        self.controller = None
        self.resizing = False
        self.resizeStartX = 0.0
        self.resizeStartWidth = PANEL_W
        self.glyph = load_glyph()
        self.tintedGlyph = None      # cached, rebuilt when colour or size change
        self.tintedKey = None
        return self

    def setFieldColor_(self, color):
        self.fieldColor = color
        self.setNeedsDisplay_(True)

    def setKeyColor_(self, color):
        self.keyColor = color
        self.setNeedsDisplay_(True)

    def setShowBacking_(self, show):
        self.showBacking = bool(show)
        self.setNeedsDisplay_(True)

    def setScale_(self, scale):
        self.scale = scale
        self.setNeedsDisplay_(True)

    # -- drawing ----------------------------------------------------------

    def headerColors(self):
        """Header text: dark on a light ground, white on a dark one.

        With the backing off the ground is the header's own pill, which is
        the KEY colour -- so the test has to follow whichever is actually
        behind the text."""
        ground = self.fieldColor if self.showBacking else self.pillColor()
        if is_light(ground):
            return (NSColor.colorWithCalibratedWhite_alpha_(0.10, 0.90),
                    NSColor.colorWithCalibratedWhite_alpha_(0.10, 0.65))
        return (NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.95),
                NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.75))

    def pillColor(self):
        """The header's own background when the field is transparent: the KEY
        colour, so the bar reads as part of the keyboard rather than as a
        separate white strip laid over it."""
        return self.keyColor

    def headerRect(self):
        scale = self.scale
        y = self.bounds().size.height - (MARGIN + HEADER_H) * scale
        return NSMakeRect(MARGIN * scale, y, ROW_W * scale, HEADER_H * scale)

    def drawRect_(self, dirty_rect):
        # Nothing is painted behind the keys unless the backing is switched
        # on: an unpainted area of a borderless clear-background panel is
        # genuinely see-through, and still takes the clicks that drag the
        # window, since hit testing goes by frame and not by alpha.
        if self.showBacking:
            self.fieldColor.set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                self.bounds(), FIELD_RADIUS * self.scale,
                FIELD_RADIUS * self.scale).fill()
        self.drawHeader()
        self.drawGrip()

    def drawHeader(self):
        name_color, credit_color = self.headerColors()
        scale = self.scale
        rect = self.headerRect()

        # Without the field there is nothing behind the header, and white
        # text on a white window is invisible. The pill is the smallest
        # thing that guarantees the version and the mark stay readable.
        if not self.showBacking:
            self.pillColor().set()
            pad = 4.0 * scale
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(rect.origin.x - pad, rect.origin.y,
                           rect.size.width + pad * 2, rect.size.height),
                rect.size.height / 2.0, rect.size.height / 2.0).fill()
        size = CREDIT_FONT_SIZE * scale

        # The ellipsis buttons own the two ends, so the texts are inset past
        # them or the version would sit underneath a control.
        inset = (ELLIPSIS_W + 4.0) * scale
        text_rect = NSMakeRect(rect.origin.x + inset, rect.origin.y,
                               rect.size.width - inset * 2, rect.size.height)

        # While the permission is missing, the left slot says so instead of
        # naming the version -- the one place the user is already looking.
        if self.controller is not None and self.controller.notice:
            left_text = self.controller.notice
        elif self.controller is not None and not self.controller.trusted:
            left_text = "KBD2 — needs Accessibility"
        else:
            left_text = "KBD2 %s" % APP_VERSION

        self.drawText_inRect_color_size_weight_alignment_(
            left_text, text_rect, name_color,
            size, NSFontWeightSemibold, NSTextAlignmentLeft)
        self.drawText_inRect_color_size_weight_alignment_(
            CREDIT_TEXT, text_rect, credit_color,
            size, NSFontWeightRegular, NSTextAlignmentRight)
        self.drawMarkInRect_color_(rect, name_color)

    def drawMarkInRect_color_(self, rect, color):
        """The KBD2 mark, centred in the header.

        Tim's artwork already contains the 2, so nothing is drawn beside it;
        earlier versions composed a separate digit and had to cap-height
        match it to the monogram."""
        height = GLYPH_H * self.scale
        key = (color.description(), round(height, 2))
        if self.tintedGlyph is None or self.tintedKey != key:
            self.tintedGlyph = tinted_glyph(self.glyph, color, height)
            self.tintedKey = key
        if self.tintedGlyph is None:
            return
        size = self.tintedGlyph.size()
        origin = NSMakePoint(
            rect.origin.x + (rect.size.width - size.width) / 2.0,
            rect.origin.y + (rect.size.height - size.height) / 2.0)
        self.tintedGlyph.drawInRect_fromRect_operation_fraction_(
            NSMakeRect(origin.x, origin.y, size.width, size.height),
            NSZeroRect, NSCompositingOperationSourceOver, 1.0)

    def drawText_inRect_color_size_weight_alignment_(self, text, rect, color,
                                                     size, weight, alignment):
        paragraph = NSMutableParagraphStyle.alloc().init()
        paragraph.setAlignment_(alignment)
        font = NSFont.systemFontOfSize_weight_(size, weight)
        attributes = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: color,
            NSParagraphStyleAttributeName: paragraph,
        }
        # Vertically centre the single line inside the header bar.
        inset = (rect.size.height - font.ascender() + font.descender()) / 2.0
        text_rect = NSMakeRect(rect.origin.x, rect.origin.y,
                               rect.size.width, rect.size.height - inset)
        NSAttributedString.alloc().initWithString_attributes_(
            text, attributes
        ).drawInRect_(text_rect)

    def gripRect(self):
        size = GRIP_SIZE * self.scale
        return NSMakeRect(self.bounds().size.width - size, 0.0, size, size)

    def drawGrip(self):
        """Three diagonals in the bottom-right corner, the resize affordance."""
        _name_color, credit_color = self.headerColors()
        credit_color.set()
        rect = self.gripRect()
        step = 4.0 * self.scale
        path = NSBezierPath.bezierPath()
        path.setLineWidth_(1.0 * self.scale)
        for index in (1, 2, 3):
            offset = step * index
            path.moveToPoint_(NSMakePoint(
                rect.origin.x + rect.size.width - offset, rect.origin.y + 2.0))
            path.lineToPoint_(NSMakePoint(
                rect.origin.x + rect.size.width - 2.0, rect.origin.y + offset))
        path.stroke()

    # -- mouse ------------------------------------------------------------

    def mouseDown_(self, event):
        point = self.convertPoint_fromView_(event.locationInWindow(), None)
        option_held = bool(event.modifierFlags() & NSEventModifierFlagOption)
        if option_held or NSPointInRect(point, self.gripRect()):
            # Resize: track in screen coordinates, which stay meaningful even
            # as the view resizes underneath the pointer.
            self.resizing = True
            self.resizeStartX = NSEvent.mouseLocation().x
            self.resizeStartWidth = self.window().frame().size.width
            return
        # Any other mouse-down on the field (keys swallow their own) drags it.
        self.window().performWindowDragWithEvent_(event)

    def mouseDragged_(self, event):
        if not self.resizing or self.controller is None:
            return
        delta = NSEvent.mouseLocation().x - self.resizeStartX
        self.controller.applyScale_((self.resizeStartWidth + delta) / PANEL_W)

    def mouseUp_(self, event):
        if self.resizing and self.controller is not None:
            self.controller.saveGeometry()
        self.resizing = False


class KeyButton(NSButton):
    """A rounded key that knows both its legends and whether it is latched."""

    def initWithFrame_(self, frame):
        self = objc.super(KeyButton, self).initWithFrame_(frame)
        if self is None:
            return None
        self.baseFrame = frame
        self.lower = ""
        self.upper = None
        self.kind = "glyph"
        self.latched = False
        self.faceColor = _color(*DEFAULT_KEY_COLOR)
        self.downColor = self.faceColor
        self.setBordered_(False)
        self.setWantsLayer_(True)
        layer = self.layer()
        layer.setCornerRadius_(KEY_RADIUS)
        layer.setBorderWidth_(0.0)
        layer.setBackgroundColor_(self.faceColor.CGColor())
        return self

    def mouseDown_(self, event):
        self.layer().setBackgroundColor_(self.downColor.CGColor())
        objc.super(KeyButton, self).mouseDown_(event)  # tracks until mouse up
        self.layer().setBackgroundColor_(self.faceColor.CGColor())


class HeaderButton(NSButton):
    """The ellipsis at each end of the header.

    It exists as its own class only so it can carry `baseFrame`: PyObjC lets
    a Python subclass hold Python attributes, and a plain NSButton instance
    does not, so the scaler had nothing to measure from."""

    def initWithFrame_(self, frame):
        self = objc.super(HeaderButton, self).initWithFrame_(frame)
        if self is None:
            return None
        self.baseFrame = frame
        self.setBordered_(False)
        return self


class KeypadController(NSObject):
    """Owns the panel, holds the latch state, routes key taps."""

    def init(self):
        self = objc.super(KeypadController, self).init()
        if self is None:
            return None
        self.panel = None
        self.field = None
        self.menu = None
        self.keys = []
        self.ellipses = []
        self.keyColor = self.savedColor() or _color(*DEFAULT_KEY_COLOR)
        self.scale = self.savedScale()
        self.showBacking = self.savedBacking()
        # Every latch lives here, shift included, so all four behave alike
        # and one place decides what a keystroke carries.
        self.latched = set()
        self.trusted = True     # assume yes until the launch check says otherwise
        self.trustTimer = None
        self.notice = ""
        self.noticeTimer = None
        self.sourceMenuItems = []
        return self

    @property
    def shiftLocked(self):
        return TAG_SHIFT in self.latched

    # -- accessibility permission -----------------------------------------

    def checkAccessibility(self):
        """Ask once at launch, then keep watching until the switch is on."""
        self.trusted = bool(AXIsProcessTrusted())
        if self.trusted:
            return
        self.field.setNeedsDisplay_(True)
        AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})

        alert = NSAlert.alloc().init()
        alert.setMessageText_("KBD2 needs Accessibility permission")
        alert.setInformativeText_(
            "macOS only lets an app send keystrokes to other applications "
            "once you allow it.\n\n"
            "Open Privacy & Security > Accessibility and switch KBD2 on. The "
            "keys start working as soon as you do — the keyboard stays open "
            "and notices the change on its own.")
        alert.addButtonWithTitle_("Open Accessibility Settings")
        alert.addButtonWithTitle_("Later")
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        if alert.runModal() == NSAlertFirstButtonReturn:
            self.openAccessibilitySettings_(None)
        self.startTrustTimer()

    def openAccessibilitySettings_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(
            NSURL.URLWithString_(ACCESSIBILITY_PANE))
        if not self.trusted:
            self.startTrustTimer()

    def startTrustTimer(self):
        if self.trustTimer is not None:
            return
        self.trustTimer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                TRUST_POLL_SECONDS, self, "trustTick:", None, True))

    def trustTick_(self, timer):
        """Clear the warning the moment the permission is granted."""
        if not AXIsProcessTrusted():
            return
        self.trusted = True
        timer.invalidate()
        self.trustTimer = None
        self.field.setNeedsDisplay_(True)

    # -- key actions ------------------------------------------------------

    def currentFlags(self):
        """What every keystroke carries: the union of the latched modifiers."""
        flags = 0
        for tag in self.latched:
            flags |= MODIFIER_FLAGS.get(tag, 0)
        return flags

    def keyTapped_(self, sender):
        post_keycode(sender.tag(), self.currentFlags())

    def modTapped_(self, sender):
        """Latch on, or latch off. Tim chose this over one-shot so that all
        four modifiers behave the way the shift lock does."""
        tag = sender.tag()
        if tag in self.latched:
            self.latched.discard(tag)
        else:
            self.latched.add(tag)
        # A shift change rewrites every legend, so restyle the lot rather
        # than just the key that was hit.
        self.restyleKeys()

    def globeTapped_(self, sender):
        """Offer the other enabled keyboard layouts, and switch to the chosen
        one. With only one layout enabled there is nothing to offer, so it
        says so and changes nothing -- a silent no-op reads as a bug."""
        sources = keyboard_sources()
        if not sources:
            self.showNotice_("no keyboards found")
            return
        menu = NSMenu.alloc().initWithTitle_("Keyboards")
        self.sourceMenuItems = []
        for name, source in sources:
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                name, "keyboardChosen:", "")
            item.setTarget_(self)
            item.setTag_(len(self.sourceMenuItems))
            self.sourceMenuItems.append(source)
            menu.addItem_(item)
        menu.popUpMenuPositioningItem_atLocation_inView_(
            None, NSMakePoint(0, 0), sender)

    def keyboardChosen_(self, sender):
        source = self.sourceMenuItems[sender.tag()]
        if not select_keyboard_source(source):
            self.showNotice_("could not switch keyboard")

    # -- the header's transient message -----------------------------------

    def showNotice_(self, text):
        """A word in the header, cleared after a few seconds. An alert or a
        dialog would take focus off the field being typed into, which is the
        one thing this app must never do."""
        self.notice = text
        if self.field is not None:
            self.field.setNeedsDisplay_(True)
        if self.noticeTimer is not None:
            self.noticeTimer.invalidate()
        self.noticeTimer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                NOTICE_SECONDS, self, "clearNotice:", None, False))

    def clearNotice_(self, timer):
        self.notice = ""
        self.noticeTimer = None
        if self.field is not None:
            self.field.setNeedsDisplay_(True)

    def ellipsisTapped_(self, sender):
        """Either end of the header opens the colour menu."""
        if self.menu is None:
            return
        self.menu.popUpMenuPositioningItem_atLocation_inView_(
            None, NSMakePoint(0, 0), sender)

    def dismiss_(self, sender):
        self.saveGeometry()
        NSApplication.sharedApplication().terminate_(None)

    def windowMoved_(self, notification):
        self.saveGeometry()

    # -- colour -----------------------------------------------------------

    def latchedFaceColor(self):
        """A latched key has to read as engaged at a glance. Light key
        colours darken and dark ones lighten, so the contrast survives every
        preset instead of vanishing on the pale ones."""
        if is_light(self.keyColor):
            return shaded(self.keyColor, 0.55)
        return shaded(self.keyColor, 1.5)

    def applyColor_(self, color):
        self.keyColor = color
        if self.field is not None:
            # The field is the same hue, well darkened, so the panel reads as
            # one object and the keys still stand off it.
            self.field.setFieldColor_(shaded(color, 0.35))
            self.field.setKeyColor_(color)
        r, g, b = rgb_components(color)
        NSUserDefaults.standardUserDefaults().setObject_forKey_(
            "%.4f,%.4f,%.4f" % (r, g, b), DEFAULTS_COLOR_KEY
        )
        self.restyleKeys()
        self.refreshMenuState()

    def savedColor(self):
        stored = NSUserDefaults.standardUserDefaults().stringForKey_(
            DEFAULTS_COLOR_KEY
        )
        if not stored:
            return None
        try:
            r, g, b = [float(part) for part in str(stored).split(",")]
        except ValueError:
            return None
        return _color(r, g, b)

    def savedBacking(self):
        """Off by default: Tim's mockup is transparent, and the solid field
        read as a black border around every key."""
        stored = NSUserDefaults.standardUserDefaults().stringForKey_(
            DEFAULTS_BACKING_KEY)
        return str(stored) == "1" if stored else False

    def toggleBacking_(self, sender):
        self.showBacking = not self.showBacking
        if self.field is not None:
            self.field.setShowBacking_(self.showBacking)
        NSUserDefaults.standardUserDefaults().setObject_forKey_(
            "1" if self.showBacking else "0", DEFAULTS_BACKING_KEY)
        self.refreshMenuState()

    def presetChosen_(self, sender):
        self.applyColor_(_color(*KEY_PRESETS[sender.tag()][1]))

    # -- size -------------------------------------------------------------

    def applyScale_(self, scale):
        """Resize the whole keyboard, keeping its top-left corner anchored."""
        scale = clamp_scale(scale)
        self.scale = scale
        if self.panel is None:
            return

        frame = self.panel.frame()
        top = frame.origin.y + frame.size.height
        width, height = PANEL_W * scale, PANEL_H * scale
        self.panel.setFrame_display_(
            NSMakeRect(frame.origin.x, top - height, width, height), True
        )

        self.field.setFrameSize_(NSMakeSize(width, height))
        self.field.setScale_(scale)
        for button in self.keys + self.ellipses:
            base = button.baseFrame
            button.setFrame_(NSMakeRect(
                base.origin.x * scale, base.origin.y * scale,
                base.size.width * scale, base.size.height * scale))
        self.restyleKeys()
        self.refreshMenuState()

    def sizeChosen_(self, sender):
        self.applyScale_(SIZE_PRESETS[sender.tag() - TAG_SIZE_BASE][1])
        self.saveGeometry()

    def savedScale(self):
        stored = NSUserDefaults.standardUserDefaults().stringForKey_(
            DEFAULTS_SCALE_KEY
        )
        if not stored:
            return 1.0
        try:
            return clamp_scale(float(str(stored)))
        except ValueError:
            return 1.0

    # -- context menu -----------------------------------------------------

    def buildMenu(self):
        menu = NSMenu.alloc().initWithTitle_("KBD2")

        menu.addItem_(self.sectionHeader_("Key Colour"))
        for index, (name, rgb) in enumerate(KEY_PRESETS):
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                name, "presetChosen:", "")
            item.setTarget_(self)
            item.setTag_(index)
            item.setImage_(self.swatchForColor_(_color(*rgb)))
            menu.addItem_(item)

        menu.addItem_(NSMenuItem.separatorItem())
        menu.addItem_(self.sectionHeader_("Keyboard Size"))
        for index, (name, scale) in enumerate(SIZE_PRESETS):
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "%s (%d%%)" % (name, round(scale * 100)), "sizeChosen:", "")
            item.setTarget_(self)
            item.setTag_(TAG_SIZE_BASE + index)
            menu.addItem_(item)

        menu.addItem_(NSMenuItem.separatorItem())
        backing = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Show Backing", "toggleBacking:", "")
        backing.setTarget_(self)
        backing.setTag_(TAG_BACKING)
        menu.addItem_(backing)

        menu.addItem_(NSMenuItem.separatorItem())
        for title, action in (
            ("Accessibility Permission…", "openAccessibilitySettings:"),
            ("Dismiss KBD2", "dismiss:"),
        ):
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                title, action, "")
            item.setTarget_(self)
            menu.addItem_(item)

        self.menu = menu
        self.refreshMenuState()
        return menu

    def sectionHeader_(self, title):
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title, None, "")
        item.setEnabled_(False)
        return item

    def swatchForColor_(self, color):
        image = NSImage.alloc().initWithSize_(NSMakeSize(14, 14))
        image.lockFocus()
        color.set()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(0, 0, 14, 14), 3, 3).fill()
        image.unlockFocus()
        return image

    def refreshMenuState(self):
        """Tick the colour and size currently in effect."""
        if self.menu is None:
            return
        current = rgb_components(self.keyColor)
        for index, (_name, rgb) in enumerate(KEY_PRESETS):
            item = self.menu.itemWithTag_(index)
            if item is not None:
                matches = all(abs(a - b) < 0.01 for a, b in zip(current, rgb))
                item.setState_(NSOnState if matches else NSOffState)
        for index, (_name, scale) in enumerate(SIZE_PRESETS):
            item = self.menu.itemWithTag_(TAG_SIZE_BASE + index)
            if item is not None:
                matches = abs(self.scale - scale) < 0.005
                item.setState_(NSOnState if matches else NSOffState)
        item = self.menu.itemWithTag_(TAG_BACKING)
        if item is not None:
            item.setState_(NSOnState if self.showBacking else NSOffState)

    # -- position and size on disk ----------------------------------------

    def saveGeometry(self):
        if self.panel is None:
            return
        defaults = NSUserDefaults.standardUserDefaults()
        origin = self.panel.frame().origin
        defaults.setObject_forKey_(
            "%.1f,%.1f" % (origin.x, origin.y), DEFAULTS_ORIGIN_KEY)
        defaults.setObject_forKey_("%.4f" % self.scale, DEFAULTS_SCALE_KEY)

    def savedOrigin(self):
        """Last saved origin, if it still lands on an attached screen."""
        stored = NSUserDefaults.standardUserDefaults().stringForKey_(
            DEFAULTS_ORIGIN_KEY
        )
        if not stored:
            return None
        try:
            x_str, y_str = str(stored).split(",")
            x, y = float(x_str), float(y_str)
        except ValueError:
            return None
        width, height = PANEL_W * self.scale, PANEL_H * self.scale
        for screen in NSScreen.screens():
            frame = screen.frame()
            if (x + width > frame.origin.x
                    and x < frame.origin.x + frame.size.width
                    and y + height > frame.origin.y
                    and y < frame.origin.y + frame.size.height):
                return NSMakePoint(x, y)
        return None

    def defaultOrigin(self):
        visible = NSScreen.mainScreen().visibleFrame()
        x = visible.origin.x + (visible.size.width - PANEL_W * self.scale) / 2.0
        y = visible.origin.y + 120.0
        return NSMakePoint(x, y)

    # -- construction -----------------------------------------------------

    def buildPanel(self):
        panel = KeypadPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, PANEL_W, PANEL_H),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setLevel_(NSStatusWindowLevel)       # above ordinary windows
        panel.setFloatingPanel_(True)
        panel.setBecomesKeyOnlyIfNeeded_(True)
        panel.setHidesOnDeactivate_(False)         # persistent across apps
        panel.setMovableByWindowBackground_(True)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        field = FieldView.alloc().initWithFrame_(
            NSMakeRect(0, 0, PANEL_W, PANEL_H)
        )
        field.setWantsLayer_(True)
        field.controller = self
        field.setFieldColor_(shaded(self.keyColor, 0.35))
        field.setKeyColor_(self.keyColor)
        field.setShowBacking_(self.showBacking)
        panel.setContentView_(field)
        self.field = field

        menu = self.buildMenu()
        field.setMenu_(menu)

        # Rows are listed top to bottom but AppKit counts y upward, so the
        # first row in ROWS gets the highest origin.
        top_of_rows = PANEL_H - MARGIN - HEADER_H - HEADER_GAP
        for row_index, row in enumerate(ROWS):
            y = top_of_rows - KEY_H * (row_index + 1) - ROW_GAP * row_index
            x = MARGIN
            for spec_index, (lower, upper, tag, kind) in enumerate(row):
                # Match on the TAG, not the kind: 1.5.0 made the space bar a
                # "symbol" key so it could carry the open box, and keying this
                # off "glyph" would have silently shrunk it to one column.
                if tag == KEYCODE_SPACE and row_index == len(ROWS) - 1:
                    # The space bar is the one key whose width is a remainder
                    # rather than a column count: it takes what is left after
                    # everything that FOLLOWS it in the row has been allowed
                    # for, so adding DISMISS beside it needed no hand-fitting.
                    trailing = 0.0
                    for _l, _u, later_tag, _k in row[spec_index + 1:]:
                        columns = WIDE_COLUMNS.get(later_tag, 1)
                        trailing += (KEY_W * columns + GAP * (columns - 1)) + GAP
                    width = MARGIN + ROW_W - x - trailing
                else:
                    columns = WIDE_COLUMNS.get(tag, 1)
                    width = KEY_W * columns + GAP * (columns - 1)
                frame = NSMakeRect(x, y, width, KEY_H)
                field.addSubview_(
                    self.makeKey_lower_upper_kind_frame_(tag, lower, upper,
                                                         kind, frame))
                x += width + GAP

        # The colour hotspot at each end of the header, per Tim's design.
        header_y = PANEL_H - MARGIN - HEADER_H
        for x in (MARGIN, MARGIN + ROW_W - ELLIPSIS_W):
            self.ellipses.append(self.makeEllipsisAtX_y_(x, header_y))
        for button in self.ellipses:
            field.addSubview_(button)

        for subview in field.subviews():
            subview.setMenu_(menu)  # right-click works over the keys too

        panel.setFrameOrigin_(self.savedOrigin() or self.defaultOrigin())
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, "windowMoved:", NSWindowDidMoveNotification, panel
        )

        self.panel = panel
        if abs(self.scale - 1.0) > 0.005:
            self.applyScale_(self.scale)   # restore the size last used
        panel.orderFrontRegardless()

    def makeKey_lower_upper_kind_frame_(self, tag, lower, upper, kind, frame):
        button = KeyButton.alloc().initWithFrame_(frame)
        button.baseFrame = frame
        button.lower = lower
        button.upper = upper
        button.kind = kind
        button.setTag_(tag)
        button.setTarget_(self)
        if kind == "mod":
            button.setAction_("modTapped:")
        elif tag == TAG_DISMISS:
            button.setAction_("dismiss:")
        elif tag == TAG_GLOBE:
            button.setAction_("globeTapped:")
        else:
            button.setAction_("keyTapped:")
        self.styleKey_(button)
        self.keys.append(button)
        return button

    def makeEllipsisAtX_y_(self, x, y):
        button = HeaderButton.alloc().initWithFrame_(
            NSMakeRect(x, y, ELLIPSIS_W, HEADER_H))
        button.setTag_(TAG_ELLIPSIS)
        button.setTarget_(self)
        button.setAction_("ellipsisTapped:")
        self.styleEllipsis_(button)
        return button

    def styleEllipsis_(self, button):
        color = (NSColor.colorWithCalibratedWhite_alpha_(0.10, 0.90)
                 if is_light(shaded(self.keyColor, 0.35))
                 else NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.95))
        paragraph = NSMutableParagraphStyle.alloc().init()
        paragraph.setAlignment_(NSTextAlignmentCenter)
        font = NSFont.systemFontOfSize_weight_(
            CREDIT_FONT_SIZE * self.scale * 1.4, NSFontWeightSemibold)
        button.setAttributedTitle_(
            NSAttributedString.alloc().initWithString_attributes_("•••", {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: color,
                NSParagraphStyleAttributeName: paragraph,
            }))

    def restyleKeys(self):
        for button in self.keys:
            self.styleKey_(button)
        for button in self.ellipses:
            self.styleEllipsis_(button)
        if self.field is not None:
            self.field.setNeedsDisplay_(True)

    def styleKey_(self, button):
        """(Re)draw one key for the current colour, scale and latch state."""
        scale = self.scale
        latched = button.tag() in self.latched and button.kind == "mod"
        button.latched = latched
        face = self.latchedFaceColor() if latched else self.keyColor
        button.faceColor = face
        # Pressed state: a light key darkens, a dark one lightens, so the
        # press is visible whichever preset is in use.
        button.downColor = (shaded(face, 0.80) if not is_light(face)
                            else shaded(face, 0.88))
        layer = button.layer()
        layer.setBackgroundColor_(face.CGColor())
        layer.setCornerRadius_(KEY_RADIUS * scale)

        text = contrast_text(face)
        dim = text.colorWithAlphaComponent_(0.45)
        paragraph = NSMutableParagraphStyle.alloc().init()
        paragraph.setAlignment_(NSTextAlignmentCenter)

        if button.kind == "dual":
            # Both legends are always drawn -- that is what Tim's mockup
            # shows -- and the one the shift lock would send is the bright
            # one, so the lock's effect is readable key by key.
            font = NSFont.systemFontOfSize_weight_(
                FONT_DUAL * scale, NSFontWeightMedium)
            paragraph.setLineSpacing_(DUAL_GAP * scale)
            body = NSMutableAttributedString.alloc().initWithString_(
                u"%s\n%s" % (button.upper, button.lower))
            whole = NSMakeRange(0, body.length())
            body.addAttribute_value_range_(NSFontAttributeName, font, whole)
            body.addAttribute_value_range_(
                NSParagraphStyleAttributeName, paragraph, whole)
            split = len(button.upper)
            upper_color = text if self.shiftLocked else dim
            lower_color = dim if self.shiftLocked else text
            body.addAttribute_value_range_(
                NSForegroundColorAttributeName, upper_color,
                NSMakeRange(0, split))
            body.addAttribute_value_range_(
                NSForegroundColorAttributeName, lower_color,
                NSMakeRange(split, body.length() - split))
            button.setAttributedTitle_(body)
            return

        if button.kind == "symbol":
            symbol = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                button.lower, None)
            if symbol is not None:
                config = NSImageSymbolConfiguration.configurationWithPointSize_weight_(
                    FONT_GLYPH * scale, NSFontWeightMedium)
                symbol = symbol.imageWithSymbolConfiguration_(config)
                tinted = tinted_glyph(symbol, text, FONT_GLYPH * scale)
                if tinted is not None:
                    button.setImage_(tinted)
                    button.setImagePosition_(NSImageOnly)
                    return

        if button.kind == "alpha":
            # The letters carry the lock as well: lowercase until it is on.
            title = button.lower.upper() if self.shiftLocked else button.lower
            size = FONT_ALPHA
        elif button.kind == "action":
            title = button.lower
            size = FONT_ACTION
        else:
            title = button.lower
            size = FONT_GLYPH

        font = NSFont.systemFontOfSize_weight_(size * scale, NSFontWeightMedium)
        button.setAttributedTitle_(
            NSAttributedString.alloc().initWithString_attributes_(title, {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: text,
                NSParagraphStyleAttributeName: paragraph,
            }))


class AppDelegate(NSObject):

    def applicationWillTerminate_(self, notification):
        if self.controller is not None:
            self.controller.saveGeometry()


# --------------------------------------------------------------------- main

def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    controller = KeypadController.alloc().init()
    controller.buildPanel()

    delegate = AppDelegate.alloc().init()
    delegate.controller = controller
    app.setDelegate_(delegate)

    # Checked after the panel is up, so the keyboard is visible behind the
    # alert.  KBD2_SKIP_AX_PROMPT=1 skips it (used by the render test).
    if os.environ.get("KBD2_SKIP_AX_PROMPT") != "1":
        controller.checkAccessibility()

    app.run()


if __name__ == "__main__":
    main()
