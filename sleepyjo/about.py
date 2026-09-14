"""About page: embedded modern HTML opened in the native browser.

Tk is gone (system Tcl/Tk 8.5 on macOS renders unreliably and looks
non-native on every platform). A styled HTML page with prefers-color-scheme
follows Apple HIG aesthetics on macOS and adapts to Windows/Linux themes.
The BMC logo is embedded as base64 — fully offline.
"""

from __future__ import annotations

import base64
import io
import logging
import tempfile
import webbrowser
from pathlib import Path

log = logging.getLogger(__name__)

BMC_URL = "https://buymeacoffee.com/filmfer"
EMAIL = "filmfer@gmail.com"
AUTHOR = "J. Filipe Fernandes"
# Injected by tools/embed_logo.py (PNG, 545x153).
BMC_LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAiEAAACZCAMAAADOzxqEAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAIRQTFRFw6kJSkAahnUS8NACHBkhpI8N4cME/+ZAhnUROjMcKyYfaFoW0rYHlYIPs5wLWU0Yd2cUHBkg//e/aFoVd2cTKyYe0rYG/98Q/+6AWU0X//vf//3v/+Eg//CP/+Mw//Sv/+pg//nP/+xw//Kf/+hQ/+5///a/DQwiDQwj/////90A////A0MgiAAAACx0Uk5T/////////////////////////////////////////////////////////wDH1gmMAAARpUlEQVR42uydaWPiOAyGfcQpuUMp04N2em8z8P//3xJiJ5btHJA2pY30ZbctE4z8RJZeK4bsTLt7ePq7RZuhXV+8PG4sHgj8cfNwj56atb29dhFy94QeQrt/bSXk/Rrdg1Yy8p+TkGfMPtCUvWxsQh4xgKA19vfOJOQVnYIGCptnSAgCgtaCSEXIIzoEzcpXNw0hz5iDoDlykYYQrGLQXPauCHlHX6A57bki5A7XGDS3XVSEoNSO1mb/lYRs0A9oHUGE7B7QD2itdrcnBLf70drtZUfu0Ato7fZ3R3CRQetcZghWMmhd9khQT0XrsneCPkDrsickBK3TLpAQNCQEDQlBQ0LQfjohnJB0oZsg5A/6FwnZbv10cUuXHy1Gbxepj26eLyHpav3Rb+uV4OjqGRLCF8uPobZcISOzI+TPcD4OjKTo7XkR4h8HyN6wbJoXISsw+wFdLRYJaUzsyxkKM9g1untWhNB6+ViQjhyDJKtAvRKr33kS8kEXoo0RkiZ/ypS2emGC/p4TIQszE6W0XGmkXe1/koXwVb0krdDfcyKEB0MzVH9f91TBBv09q2qX3x5Rw1T/h/6eFSH7LGO1HBhDZNaC+vvMCNlbekX7ACnzkO0VKiIzJaS0P+liRV2glKlrWpW46eEXC3T4LAmpzdcUM0P78LGYQUK67ZCxLHH7bjaE/FksFuSYxLNahW4xV50HIWTdNAiJ/lYyn4grVfWsMReZASHCykkDSq+qzkO4d7egdgob4FLz2wk5ft/fUf6i/WJCVh8jDZORX07IWEAwiPxyQki1lStIchUcw8U+U0mqpCRAv/9qQpLDLMuu030+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"

_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SleepyJo — {title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                 "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background: light-dark(#f5f5f7, #1d1d1f);
    color: light-dark(#1d1d1f, #f5f5f7);
    -webkit-font-smoothing: antialiased;
  }}
  .card {{
    background: light-dark(#ffffff, #2c2c2e);
    border-radius: 20px;
    padding: 40px 44px;
    max-width: 380px; width: 92vw; text-align: center;
    box-shadow: 0 10px 40px light-dark(rgba(0,0,0,.12), rgba(0,0,0,.55));
  }}
  .appicon {{ width: 84px; height: 84px; margin-bottom: 14px;
              border-radius: 20px; }}
  h1 {{ font-size: 22px; font-weight: 600; letter-spacing: -.02em; margin-bottom: 2px; }}
  .version {{ font-size: 12px; color: light-dark(#86868b, #98989d); }}
  .divider {{ border: none; height: 1px; margin: 18px 0;
              background: light-dark(#e5e5ea, #3a3a3c); }}
  .row {{ font-size: 14px; line-height: 2.1; margin-bottom: 4px; }}
  .row .label {{ color: light-dark(#86868b, #98989d); margin-right: 6px; }}
  a {{ color: light-dark(#0066cc, #64b5f6); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .coffee {{
    display: inline-block; margin-top: 22px; padding: 10px 22px;
    background: #ffdd00; color: #0d0d0d; font-weight: 600; font-size: 14px;
    border-radius: 999px; transition: transform .15s ease;
  }}
  .coffee:hover {{ transform: scale(1.04); text-decoration: none; }}
</style>
</head>
<body>
  <main class="card">
    <img class="appicon" src="data:image/png;base64,{appicon}" alt="SleepyJo">
    <h1>SleepyJo</h1>
    <div class="version">{version_label} {version}</div>
    <hr class="divider">
    <div class="row">
      <div><span class="label">{author_label}</span>{author}</div>
      <div><span class="label">{email_label}</span><a href="mailto:{email}">{email}</a></div>
    </div>
    <a class="coffee" href="{bmc}">{coffee_label} &#9749;</a>
  </main>
</body>
</html>
"""


def _app_icon_b64() -> str:
    """Return the pre-rendered app icon as base64 PNG."""
    from sleepyjo.tray_icons_data import app_icon_b64
    return app_icon_b64


def _localized(i18n) -> dict:  # type: ignore[no-untyped-def]
    t = i18n.t
    return {
        "lang": i18n.lang,
        "version": _version(),
        "author": AUTHOR,
        "email": EMAIL,
        "author_label": t("about_author").split(":")[0],
        "email_label": t("about_email").split(":")[0],
        "title": t("about_title"),
        "version_label": t("about_version"),
        "coffee_label": t("about_coffee_button"),
        "bmc": BMC_URL,
        "logo": BMC_LOGO_B64,
        "appicon": _app_icon_b64(),
    }


def _version() -> str:
    from sleepyjo import __version__
    return __version__


def open_about(i18n) -> None:  # noqa: ANN001
    """Render the About page to a temp file and open it in the browser."""
    html = _TEMPLATE.format(**_localized(i18n))
    page = Path(tempfile.gettempdir()) / "sleepyjo_about.html"
    page.write_text(html, encoding="utf-8")
    ok = webbrowser.open(page.as_uri())
    log.info("About page written to %s (browser_open=%s)", page, ok)
    if not ok:
        # Last resort: give the URL directly to the OS default handler.
        webbrowser.open(BMC_URL)
