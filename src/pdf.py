"""Markdown bülteni -> PDF (pure-python, xhtml2pdf). Türkçe için Arial TTF gömülür."""
from __future__ import annotations

from pathlib import Path

import markdown as md_lib
from xhtml2pdf import pisa

_FONT_DIR = Path("/System/Library/Fonts/Supplemental")
_ARIAL = _FONT_DIR / "Arial.ttf"
_ARIAL_B = _FONT_DIR / "Arial Bold.ttf"
_ARIAL_I = _FONT_DIR / "Arial Italic.ttf"


def _font_css() -> str:
    if not _ARIAL.exists():
        return ""
    blok = f'@font-face {{ font-family: "TR"; src: url("{_ARIAL}"); }}\n'
    if _ARIAL_B.exists():
        blok += f'@font-face {{ font-family: "TR"; font-weight: bold; src: url("{_ARIAL_B}"); }}\n'
    if _ARIAL_I.exists():
        blok += f'@font-face {{ font-family: "TR"; font-style: italic; src: url("{_ARIAL_I}"); }}\n'
    blok += 'body, h1, h2, h3, p, li, td, th { font-family: "TR"; }\n'
    return blok


def _print_html(markdown_metin: str) -> str:
    govde = md_lib.markdown(markdown_metin, extensions=["extra", "sane_lists"])
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 1.6cm; }}
{_font_css()}
body {{ color: #111; font-size: 10pt; line-height: 1.5; }}
h1 {{ font-size: 17pt; border-bottom: 2px solid #333; padding-bottom: 5px; margin-bottom: 4px; }}
h2 {{ font-size: 12pt; color: #1a4480; border-top: 1px solid #ccc; padding-top: 8px;
     margin-top: 16px; text-transform: uppercase; }}
h3 {{ font-size: 11pt; margin-bottom: 2px; }}
p, li {{ margin: 4px 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
th, td {{ border: 1px solid #bbb; padding: 3px 6px; font-size: 9pt; }}
th {{ background: #f0f0f0; }}
em {{ color: #666; }}
hr {{ border: none; border-top: 1px solid #ccc; }}
</style></head><body>{govde}</body></html>"""


def markdown_to_pdf(markdown_metin: str, cikti_yolu: str | Path) -> Path:
    cikti = Path(cikti_yolu)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    html = _print_html(markdown_metin)
    with open(cikti, "wb") as f:
        sonuc = pisa.CreatePDF(html, dest=f, encoding="utf-8")
    if sonuc.err:
        raise RuntimeError(f"PDF üretilemedi (xhtml2pdf hata: {sonuc.err})")
    return cikti
