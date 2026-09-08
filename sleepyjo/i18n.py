"""Lightweight JSON-based localization.

Language = primary subtag of the OS locale; default fallback is Portuguese (pt).
"""

from __future__ import annotations

import json
import locale
import logging
from pathlib import Path
from typing import Any, Dict

from sleepyjo import locales_data as _locales_data

log = logging.getLogger(__name__)

_DEFAULT_LANG = "pt"
SUPPORTED = ("pt", "en", "fr", "it", "de", "es")
_LOCALES_DIR = Path(__file__).parent / "locales"
_cache: Dict[str, Dict[str, str]] = {}


def _detect_os_language() -> str:
    try:
        raw = locale.getdefaultlocale()[0] or ""
    except Exception:  # noqa: BLE001
        raw = ""
    lang = raw.split("_")[0].lower()
    return lang if lang in SUPPORTED else _DEFAULT_LANG


class I18n:
    """Lazy-loading translation accessor: t('key') -> str."""

    def __init__(self, lang: str = "") -> None:
        self.lang = lang if lang in SUPPORTED else _detect_os_language()

    def set_language(self, lang: str) -> None:
        if lang in SUPPORTED:
            self.lang = lang

    def _load(self, lang: str) -> Dict[str, str]:
        if lang not in _cache:
            # Embedded data first (survives PyInstaller packaging);
            # JSON files as dev-time fallback/override.
            text = getattr(_locales_data, "LOCALES", {}).get(lang)
            if text is None:
                path = _LOCALES_DIR / f"{lang}.json"
                try:
                    text = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    log.error("Failed loading locale %s: %s", lang, exc)
                    text = {}
            _cache[lang] = text
        return _cache[lang]

    def t(self, key: str, **fmt: Any) -> str:
        text = self._load(self.lang).get(key)
        if text is None:  # fallback chain: chosen -> English -> raw key
            text = self._load("en").get(key, key)
        try:
            return text.format(**fmt) if fmt else text
        except (KeyError, IndexError) as exc:
            log.error("Bad format for %s: %s", key, exc)
            return text
