#!/usr/bin/env python3
"""Build the shared offline index.html for every GUStay Tauri project.

The original GUStay.html was saved from a browser and contains a second,
unrelated ChatGPT sidebar after </body>. Only the real application up to the
first </body> is kept. The script also:

  * removes the Google Fonts <link> tags and embeds Inter as base64 WOFF2;
  * wraps the application IIFE so settings can be loaded before it starts;
  * injects the native storage / .gustay bridge;
  * adds a visibility gate that is lifted once the app is ready.

Run from the repository root:  python3 shared/build_frontend.py
"""

from __future__ import annotations

import base64
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
SOURCE = ROOT / "GUStay.html"
OUTPUT = SHARED / "index.html"
PLATFORMS = ("android", "linux", "windows", "macos")

FONT_SUBSETS = (
    (
        "cyrillic-ext",
        "U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F",
    ),
    (
        "cyrillic",
        "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116",
    ),
    (
        "latin-ext",
        "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, "
        "U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, "
        "U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF",
    ),
    (
        "latin",
        "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, "
        "U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, "
        "U+2212, U+2215, U+FEFF, U+FFFD",
    ),
)


def font_css() -> str:
    rules = []
    for name, unicode_range in FONT_SUBSETS:
        data = base64.b64encode((SHARED / "fonts" / f"{name}.woff2").read_bytes()).decode("ascii")
        rules.append(
            "/* {name} */\n"
            "@font-face {{\n"
            "  font-family: 'Inter';\n"
            "  font-style: normal;\n"
            "  font-weight: 100 900;\n"
            "  font-display: swap;\n"
            "  src: url(data:font/woff2;base64,{data}) format('woff2');\n"
            "  unicode-range: {unicode_range};\n"
            "}}".format(name=name, data=data, unicode_range=unicode_range)
        )
    return "\n".join(rules)


def fail(message: str) -> None:
    raise SystemExit(f"build_frontend: {message}")


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    body_end = source.find("</body>")
    if body_end < 0:
        fail("</body> not found")
    # Drop the saved ChatGPT sidebar and every other byte after the app body.
    html = source[: body_end + len("</body>")] + "\n</html>\n"

    # Remove the Google Fonts requests. The build must work fully offline.
    for link in (
        '  <link rel="preconnect" href="https://fonts.googleapis.com/"> \n',
        '  <link rel="preconnect" href="https://fonts.gstatic.com/" crossorigin="">\n',
        '  <link href="./GUStay_files/css2" rel="stylesheet">\n',
    ):
        if link not in html:
            fail(f"expected font link not found: {link.strip()}")
        html = html.replace(link, "", 1)

    head_end = html.find("</head>")
    if head_end < 0:
        fail("</head> not found")
    head_injection = (
        '  <style id="inter-embedded">\n'
        + font_css()
        + "\n  </style>\n"
        + '  <style id="gustay-native-gate">html:not(.gustay-ready) body{visibility:hidden!important}</style>\n'
    )
    html = html[:head_end] + head_injection + html[head_end:]

    # The application is one large IIFE. Wrap its invocation in a named
    # function so the bridge can hydrate settings before any localStorage
    # access happens.
    app_start = '<script>\n    (function() {\n      \'use strict\';'
    if html.count(app_start) != 1:
        fail("application <script> opener was not found exactly once")
    html = html.replace(
        app_start,
        '<script>\n    window.__gustayBoot = function () {\n    (function() {\n      \'use strict\';',
        1,
    )

    app_end = "      init();\n    })();\n  </script>"
    if html.count(app_end) != 1:
        fail("application <script> terminator was not found exactly once")
    html = html.replace(
        app_end,
        "      window.GUStayNative = window.GUStayNative || {};\n"
        "      window.GUStayNative.importTheme = importTheme;\n"
        "      init();\n"
        "    })();\n"
        "    };\n"
        "  </script>",
        1,
    )

    bridge = (SHARED / "bootstrap.js").read_text(encoding="utf-8")
    if "</script" in bridge:
        fail("bootstrap.js contains a </script> sequence")
    bridge_block = "  <script>\n" + bridge + "  </script>\n"
    html = html.replace("</body>", bridge_block + "</body>", 1)

    OUTPUT.write_text(html, encoding="utf-8")

    for platform in PLATFORMS:
        target = ROOT / platform / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OUTPUT, target)

    print(f"wrote {OUTPUT} ({len(html):,} bytes)")
    print(f"localStorage references: {html.count('localStorage')}")
    for platform in PLATFORMS:
        print(f"  {ROOT / platform / 'index.html'}")


if __name__ == "__main__":
    main()
