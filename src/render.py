"""Pano üreteci: bulten.md -> statik HTML (markdown + Jinja2)."""
from __future__ import annotations

import re
from pathlib import Path

import markdown as md_lib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .storage import Storage

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )


def gun_dosya_adi(tarih: str) -> str:
    return f"gun-{tarih}.html"


def markdown_to_html(markdown_metin: str) -> str:
    return md_lib.markdown(markdown_metin, extensions=["extra", "sane_lists"])


def ozet_cikar(markdown_metin: str, limit: int = 200) -> str:
    """'## Günün Özeti' altındaki ilk paragrafı index önizlemesi için çıkarır."""
    satirlar = markdown_metin.splitlines()
    icinde = False
    for i, s in enumerate(satirlar):
        if s.strip().lower().startswith("## günün özeti"):
            icinde = True
            continue
        if icinde and s.strip() and not s.strip().startswith("#"):
            metin = re.sub(r"[*_`#]", "", s).strip()
            return metin[:limit] + ("…" if len(metin) > limit else "")
    # bulunamazsa ilk anlamlı paragraf
    for s in satirlar:
        t = s.strip()
        if t and not t.startswith("#") and not t.startswith("*"):
            metin = re.sub(r"[*_`#]", "", t).strip()
            return metin[:limit] + ("…" if len(metin) > limit else "")
    return ""


def render_gun(markdown_metin: str, env: Environment | None = None) -> str:
    env = env or _env()
    govde = markdown_to_html(markdown_metin)
    return env.get_template("bulten.html.j2").render(govde=govde)


def render_index(gunler: list[dict], env: Environment | None = None) -> str:
    """gunler: [{tarih, ozet, dosya, kaynak_sayisi, eksik_sayisi}] (en yeni üstte)."""
    env = env or _env()
    return env.get_template("index.html.j2").render(gunler=gunler)


def render_site(storage: Storage, pano_dizini: str | Path) -> Path:
    """Tüm arşivi statik siteye döker; index.html yolunu döndürür."""
    pano = Path(pano_dizini)
    pano.mkdir(parents=True, exist_ok=True)
    env = _env()

    index_satirlari = []
    for tarih in storage.list_days():
        md = storage.load_bulten(tarih)
        if not md:
            continue
        dosya = gun_dosya_adi(tarih)
        (pano / dosya).write_text(render_gun(md, env), encoding="utf-8")
        kd = storage.load_meta(tarih).get("kaynak_durumu", {})
        index_satirlari.append(
            {
                "tarih": tarih,
                "ozet": ozet_cikar(md),
                "dosya": dosya,
                "kaynak_sayisi": len(kd.get("alinan", [])),
                "eksik_sayisi": len(kd.get("alinamayan", [])),
            }
        )

    index_yolu = pano / "index.html"
    index_yolu.write_text(render_index(index_satirlari, env), encoding="utf-8")
    return index_yolu
