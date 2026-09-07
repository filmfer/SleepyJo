#!/usr/bin/env python3
"""Embed the BMC logo PNG into sleepyjo/about.py as base64."""

import base64
import re
import sys
from pathlib import Path

png_path = Path(sys.argv[1])
about_path = Path(__file__).resolve().parent.parent / "sleepyjo" / "about.py"

b64 = base64.b64encode(png_path.read_bytes()).decode()
source = about_path.read_text(encoding="utf-8")
source = re.sub(
    r'BMC_LOGO_B64 = ".*?"', f'BMC_LOGO_B64 = "{b64}"', source, count=1)
about_path.write_text(source, encoding="utf-8")
print(f"Embedded {png_path} ({len(b64)} b64 chars) into {about_path}")
