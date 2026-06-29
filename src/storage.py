"""Dosya tabanlı arşiv: archive/YYYY-MM-DD/{raw.json, synthesis.json}."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .types import HamIcerik

_TARIH_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Storage:
    def __init__(self, arsiv_dizini: str | Path):
        self.kok = Path(arsiv_dizini)

    def _gun_dizini(self, tarih: str) -> Path:
        return self.kok / tarih

    # --- ham içerik ---

    def save_raw(self, tarih: str, icerikler: list[HamIcerik]) -> Path:
        d = self._gun_dizini(tarih)
        d.mkdir(parents=True, exist_ok=True)
        yol = d / "raw.json"
        yol.write_text(
            json.dumps([ic.to_dict() for ic in icerikler], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return yol

    def load_raw(self, tarih: str) -> list[HamIcerik]:
        yol = self._gun_dizini(tarih) / "raw.json"
        if not yol.exists():
            return []
        veri = json.loads(yol.read_text(encoding="utf-8"))
        return [HamIcerik.from_dict(d) for d in veri]

    def has_raw(self, tarih: str) -> bool:
        return (self._gun_dizini(tarih) / "raw.json").exists()

    # --- sentez ---

    def save_synthesis(self, tarih: str, sentez: dict) -> Path:
        d = self._gun_dizini(tarih)
        d.mkdir(parents=True, exist_ok=True)
        yol = d / "synthesis.json"
        yol.write_text(json.dumps(sentez, ensure_ascii=False, indent=2), encoding="utf-8")
        return yol

    def load_synthesis(self, tarih: str) -> dict | None:
        yol = self._gun_dizini(tarih) / "synthesis.json"
        if not yol.exists():
            return None
        return json.loads(yol.read_text(encoding="utf-8"))

    # --- gün listesi ---

    def list_days(self) -> list[str]:
        """Sentezi olan günleri, en yeni üstte olacak şekilde döndürür."""
        if not self.kok.exists():
            return []
        gunler = [
            p.name
            for p in self.kok.iterdir()
            if p.is_dir() and _TARIH_RE.match(p.name) and (p / "synthesis.json").exists()
        ]
        return sorted(gunler, reverse=True)
