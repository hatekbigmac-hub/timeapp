"""Single source of truth for the app version.

Bump this before building a release, and tag the GitHub release with the same
number (e.g. v1.1.0) so the updater can compare them.
"""

APP_VERSION = "1.0.2"


def parse(text) -> tuple:
    """'v1.2.3' -> (1, 2, 3). Unparseable parts become 0."""
    text = (text or "").strip().lstrip("vV")
    # keep only the leading numeric-dot part ("1.2.3-beta" -> "1.2.3")
    cleaned = []
    for ch in text:
        if ch.isdigit() or ch == ".":
            cleaned.append(ch)
        else:
            break
    parts = "".join(cleaned).split(".")
    out = []
    for part in parts[:4]:
        try:
            out.append(int(part))
        except ValueError:
            out.append(0)
    while len(out) < 3:
        out.append(0)
    return tuple(out)


def is_newer(candidate, current=APP_VERSION) -> bool:
    return parse(candidate) > parse(current)
