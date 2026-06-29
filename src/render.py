"""Pano üreteci: synthesis.json -> statik HTML (Jinja2)."""
from __future__ import annotations

from pathlib import Path

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


# gündem önem sırası
_ONEM_SIRA = {"yuksek": 0, "orta": 1, "dusuk": 2}


def render_gun(sentez: dict, env: Environment | None = None) -> str:
    env = env or _env()
    sentez = dict(sentez)
    sentez["gundem"] = sorted(
        sentez.get("gundem", []),
        key=lambda g: _ONEM_SIRA.get(g.get("onem", "orta"), 1),
    )
    return env.get_template("gun.html.j2").render(s=sentez)


def render_index(gunler: list[dict], env: Environment | None = None) -> str:
    """gunler: [{tarih, gun_ozeti, dosya, kaynak_sayisi}] (en yeni üstte)."""
    env = env or _env()
    return env.get_template("index.html.j2").render(gunler=gunler)


def render_site(storage: Storage, pano_dizini: str | Path) -> Path:
    """Tüm arşivi statik siteye döker; index.html yolunu döndürür."""
    pano = Path(pano_dizini)
    pano.mkdir(parents=True, exist_ok=True)
    env = _env()

    index_satirlari = []
    for tarih in storage.list_days():
        sentez = storage.load_synthesis(tarih)
        if not sentez:
            continue
        dosya = gun_dosya_adi(tarih)
        (pano / dosya).write_text(render_gun(sentez, env), encoding="utf-8")
        kd = sentez.get("kaynak_durumu", {})
        index_satirlari.append(
            {
                "tarih": tarih,
                "gun_ozeti": sentez.get("gun_ozeti", ""),
                "dosya": dosya,
                "kaynak_sayisi": len(kd.get("alinan", [])),
                "eksik_sayisi": len(kd.get("alinamayan", [])),
            }
        )

    index_yolu = pano / "index.html"
    index_yolu.write_text(render_index(index_satirlari, env), encoding="utf-8")
    return index_yolu
