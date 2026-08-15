"""Embedded SVG assets (icons, logo, flags) used by the GUI and stat cards."""

ACCENT = "#4F8CFF"
ACCENT2 = "#22D3EE"
FG = "#E8ECF4"
MUTED = "#8A94A8"

LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="logo_g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#4F8CFF"/>
      <stop offset="1" stop-color="#22D3EE"/>
    </linearGradient>
  </defs>
  <rect x="2" y="2" width="60" height="60" rx="16" fill="url(#logo_g)"/>
  <circle cx="32" cy="32" r="17" fill="none" stroke="#0B1220" stroke-opacity="0.25" stroke-width="6"/>
  <circle cx="32" cy="32" r="17" fill="none" stroke="#FFFFFF" stroke-width="5"
          stroke-linecap="round" stroke-dasharray="80 27" transform="rotate(-90 32 32)"/>
  <path d="M32 24v9l6.5 4" stroke="#FFFFFF" stroke-width="5" stroke-linecap="round"
        stroke-linejoin="round" fill="none"/>
</svg>"""

FLAG_UA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <defs><clipPath id="ua_clip"><rect x="1" y="4" width="22" height="16" rx="3"/></clipPath></defs>
  <g clip-path="url(#ua_clip)">
    <rect x="1" y="4" width="22" height="8" fill="#338AF3"/>
    <rect x="1" y="12" width="22" height="8" fill="#FFDA44"/>
  </g>
</svg>"""

FLAG_GB = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <defs><clipPath id="gb_clip"><rect x="1" y="4" width="22" height="16" rx="3"/></clipPath></defs>
  <g clip-path="url(#gb_clip)">
    <rect x="1" y="4" width="22" height="16" fill="#0A3B8C"/>
    <path d="M1 4 23 20 M23 4 1 20" stroke="#FFFFFF" stroke-width="4"/>
    <path d="M1 4 23 20 M23 4 1 20" stroke="#D80027" stroke-width="1.6"/>
    <path d="M12 4v16 M1 12h22" stroke="#FFFFFF" stroke-width="6"/>
    <path d="M12 4v16 M1 12h22" stroke="#D80027" stroke-width="3"/>
  </g>
</svg>"""

_ICONS = {
    "clock": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="%C%" stroke-width="2"/>
      <path d="M12 7v5l3.5 2" stroke="%C%" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>""",
    "calendar": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
      <rect x="3.5" y="5" width="17" height="15.5" rx="3" stroke="%C%" stroke-width="2"/>
      <path d="M3.5 10h17" stroke="%C%" stroke-width="2"/>
      <path d="M8 3v4 M16 3v4" stroke="%C%" stroke-width="2" stroke-linecap="round"/>
    </svg>""",
    "copy": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
      <rect x="8.5" y="8.5" width="12" height="12" rx="3" stroke="%C%" stroke-width="2"/>
      <path d="M15.5 8.5V6a3 3 0 0 0-3-3H6a3 3 0 0 0-3 3v6.5a3 3 0 0 0 3 3h2.5"
            stroke="%C%" stroke-width="2" stroke-linecap="round"/>
    </svg>""",
    "send": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
      <path fill="%C%" d="M21.9 2.1 2.6 9.5c-.63.24-.6 1.14.05 1.34l5.5 1.7a1 1 0 0 1 .66.65l1.7 5.5c.2.65 1.1.68 1.34.05l7.4-19.3c.22-.57-.34-1.13-.91-.91zM10 14l9.5-9.5"/>
      <path d="M10 14l9.5-9.5" stroke="#0F1420" stroke-width="1.2" stroke-linecap="round"/>
    </svg>""",
    "globe": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="%C%" stroke-width="2"/>
      <ellipse cx="12" cy="12" rx="4" ry="9" stroke="%C%" stroke-width="2"/>
      <path d="M3 12h18" stroke="%C%" stroke-width="2"/>
    </svg>""",
    "chart": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
      <path d="M5 20v-8 M12 20V6 M19 20v-5" stroke="%C%" stroke-width="2.5" stroke-linecap="round"/>
    </svg>""",
    "power": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
      <path d="M12 3v8" stroke="%C%" stroke-width="2" stroke-linecap="round"/>
      <path d="M7 6.3a7.5 7.5 0 1 0 10 0" stroke="%C%" stroke-width="2" stroke-linecap="round"/>
    </svg>""",
    "check": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
      <path d="M5 12.5 10 17.5 19 7" stroke="%C%" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>""",
}


def svg(name: str, color: str = FG) -> bytes:
    """Return the SVG for `name` with its stroke/fill color applied."""
    return _ICONS[name].replace("%C%", color).encode("utf-8")


def names():
    return list(_ICONS)
