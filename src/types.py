"""Ortak veri tipleri ve sentez JSON şema doğrulaması.

Tasarım: docs/superpowers/specs/2026-06-29-gunluk-bulten-sentezi-design.md
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


# --- Ortak ham içerik tipi (tüm toplayıcılar bunu üretir) ---

@dataclass
class HamIcerik:
    kaynak: str   # ör. "Burgan Yatırım"
    baslik: str
    tarih: str    # ISO "YYYY-MM-DD"
    metin: str    # temizlenmiş düz metin

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "HamIcerik":
        return HamIcerik(
            kaynak=d["kaynak"],
            baslik=d["baslik"],
            tarih=d["tarih"],
            metin=d["metin"],
        )


# --- Sentez şeması için izin verilen enum değerleri ---

ONEM_DEGERLERI = {"yuksek", "orta", "dusuk"}
VARLIK_TIPLERI = {"hisse", "sektor", "endeks", "doviz", "emtia"}
GORUS_DEGERLERI = {"olumlu", "notr", "olumsuz", "karisik"}


class SemaHatasi(ValueError):
    """Sentez JSON'u beklenen şemaya uymuyor."""


def _zorunlu(d: dict, anahtar: str, tip, yol: str):
    if anahtar not in d:
        raise SemaHatasi(f"{yol}: zorunlu alan eksik: '{anahtar}'")
    if not isinstance(d[anahtar], tip):
        raise SemaHatasi(
            f"{yol}.{anahtar}: beklenen tip {tip.__name__}, gelen {type(d[anahtar]).__name__}"
        )


def validate_synthesis(s: dict) -> None:
    """Sentez sözlüğünü yerinde doğrular; hata varsa SemaHatasi fırlatır.

    Zorunlu: tarih, gun_ozeti, kaynak_durumu.
    gundem / ayrisan_gorusler / one_cikan_varliklar / etiketler boş olabilir.
    """
    if not isinstance(s, dict):
        raise SemaHatasi("kök: sözlük bekleniyor")

    _zorunlu(s, "tarih", str, "kök")
    _zorunlu(s, "gun_ozeti", str, "kök")
    _zorunlu(s, "kaynak_durumu", dict, "kök")

    # gundem
    gundem = s.get("gundem", [])
    if not isinstance(gundem, list):
        raise SemaHatasi("gundem: liste bekleniyor")
    for i, g in enumerate(gundem):
        yol = f"gundem[{i}]"
        _zorunlu(g, "baslik", str, yol)
        _zorunlu(g, "ne_oldu", str, yol)
        _zorunlu(g, "nasil_yorumlaniyor", str, yol)
        _zorunlu(g, "kaynaklar", list, yol)
        _zorunlu(g, "onem", str, yol)
        if g["onem"] not in ONEM_DEGERLERI:
            raise SemaHatasi(f"{yol}.onem: geçersiz değer '{g['onem']}' (izinli: {ONEM_DEGERLERI})")

    # ayrisan_gorusler
    ayrisan = s.get("ayrisan_gorusler", [])
    if not isinstance(ayrisan, list):
        raise SemaHatasi("ayrisan_gorusler: liste bekleniyor")
    for i, a in enumerate(ayrisan):
        yol = f"ayrisan_gorusler[{i}]"
        _zorunlu(a, "konu", str, yol)
        _zorunlu(a, "gorusler", list, yol)
        for j, gr in enumerate(a["gorusler"]):
            gyol = f"{yol}.gorusler[{j}]"
            _zorunlu(gr, "kaynak", str, gyol)
            _zorunlu(gr, "gorus", str, gyol)

    # one_cikan_varliklar
    varliklar = s.get("one_cikan_varliklar", [])
    if not isinstance(varliklar, list):
        raise SemaHatasi("one_cikan_varliklar: liste bekleniyor")
    for i, v in enumerate(varliklar):
        yol = f"one_cikan_varliklar[{i}]"
        _zorunlu(v, "sembol", str, yol)
        _zorunlu(v, "tip", str, yol)
        _zorunlu(v, "neden_gundemde", str, yol)
        _zorunlu(v, "kaynak_gorusu", str, yol)
        _zorunlu(v, "kaynaklar", list, yol)
        if v["tip"] not in VARLIK_TIPLERI:
            raise SemaHatasi(f"{yol}.tip: geçersiz değer '{v['tip']}' (izinli: {VARLIK_TIPLERI})")
        if v["kaynak_gorusu"] not in GORUS_DEGERLERI:
            raise SemaHatasi(
                f"{yol}.kaynak_gorusu: geçersiz değer '{v['kaynak_gorusu']}' (izinli: {GORUS_DEGERLERI})"
            )

    # etiketler
    etiketler = s.get("etiketler", [])
    if not isinstance(etiketler, list) or not all(isinstance(e, str) for e in etiketler):
        raise SemaHatasi("etiketler: string listesi bekleniyor")

    # kaynak_durumu
    kd = s["kaynak_durumu"]
    _zorunlu(kd, "alinan", list, "kaynak_durumu")
    _zorunlu(kd, "alinamayan", list, "kaynak_durumu")
    for i, al in enumerate(kd["alinamayan"]):
        yol = f"kaynak_durumu.alinamayan[{i}]"
        _zorunlu(al, "kaynak", str, yol)
        _zorunlu(al, "neden", str, yol)
