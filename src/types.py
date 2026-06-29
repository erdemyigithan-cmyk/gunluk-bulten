"""Ortak veri tipleri.

Tasarım: docs/superpowers/specs/2026-06-29-gunluk-bulten-sentezi-design.md
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class HamIcerik:
    """Tüm toplayıcıların ürettiği ortak ham içerik birimi."""
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
