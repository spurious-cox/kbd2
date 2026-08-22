# KBD2 Privacy Policy

Applies to **KBD2 for macOS** and **KBD2 for iOS** (iPhone and iPad).

**KBD2 collects no data whatsoever, on either platform.**

KBD2 is an on-screen keyboard. When you tap a key it hands that keystroke to
the operating system, which delivers it to whatever text field currently has
focus. That is the whole of what the app does with a keypress.

- **No keystroke is stored.** Nothing you type is written to disk, kept in
  memory beyond the instant it is posted, or logged anywhere.
- **No network access.** KBD2 makes no network connections of any kind. It
  has no servers, no analytics, no crash reporting, and no update check.
- **No personal information is read.** KBD2 never reads the contents of any
  text field, document, or other application's window.
- **Nothing is shared**, because nothing is collected.

## iOS: KBD2 does not request Full Access

On iPhone and iPad, KBD2 is a keyboard extension. iOS lets a keyboard ask for
"Full Access", which is what would allow it to reach the network or share data
with its containing app.

**KBD2 does not request Full Access.** Its Info.plist sets
`RequestsOpenAccess` to false, so iOS never offers you the switch, and the
keyboard runs in the tighter sandbox at all times. It is fully functional that
way — nothing in KBD2 is withheld or degraded for lack of Full Access.

What that means concretely on iOS:

- **No network connections of any kind**, so nothing you type could leave the
  device even in principle.
- **Nothing you type is stored.** Characters are passed to the focused field
  through the system's `UITextDocumentProxy` and are not written to disk,
  retained, or logged.
- **KBD2 cannot see what you type on any other keyboard.** A keyboard
  extension only ever receives input while it is the keyboard on screen.
- **The one thing KBD2 does remember** is the key colour you picked, stored as
  a single number in the extension's own preferences on your device. It is
  never transmitted, and it is removed when you delete the app.

The cursor keys and the forward-delete key work entirely through the system's
own text-editing interface, which is why they need no additional permission.

## macOS: about the Accessibility permission

macOS requires Accessibility permission before any app may post keystrokes to
another application. KBD2 asks for it for exactly that reason, and uses it for
nothing else. The permission lets KBD2 *send* keys; it does not cause KBD2 to
read, record, or monitor anything you type on your real keyboard.

This section applies to the Mac app only; the iOS keyboard uses no such
permission. You can revoke it at any time in System Settings > Privacy &
Security > Accessibility. KBD2 keeps running and notices the change; its keys simply
stop reaching other apps until you switch it back on.

## What KBD2 does save

On macOS, three preferences, stored locally in the standard user defaults for
the app, and never transmitted anywhere:

- the keyboard's position on screen
- its size
- the key colour you picked

On iOS, one preference: the key colour. Removing the app removes them.

## Contact

Tim McCoy — questions about this policy can be raised on the project's
GitHub repository.
