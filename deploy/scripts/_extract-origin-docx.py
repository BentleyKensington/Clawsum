#!/usr/bin/env python3
"""Extract Origin DOCX to plain text for analysis."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

DOC = Path(
    "/docker/clawsum/data/.openclaw/media/inbound/"
    "Origin_Platform_V1_Product_Technical_Specification---e63a8e13-99f8-4640-b142-efe95d17e706.docx"
)
OUT = Path("/tmp/origin-spec-extracted.txt")
QS = Path("/tmp/origin-spec-questions.txt")


def main() -> int:
    with zipfile.ZipFile(DOC) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    text = re.sub(r"</w:p>", "\n", xml)
    text = re.sub(r"<w:tab[^/]*/>", "\t", text)
    text = re.sub(r"<[^>]+>", "", text)
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')):
        text = text.replace(a, b)
    text = re.sub(r"\n{3,}", "\n\n", text)
    OUT.write_text(text, encoding="utf-8")
    qs = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        low = s.lower()
        if "?" in s or low.startswith(
            ("how ", "what ", "which ", "will ", "confirm ", "show ", "define ")
        ):
            qs.append(s)
    QS.write_text("\n".join(qs), encoding="utf-8")
    print(f"chars={len(text)} questions={len(qs)} out={OUT}")
    print("--- questions head ---")
    for q in qs[:100]:
        print(q[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
