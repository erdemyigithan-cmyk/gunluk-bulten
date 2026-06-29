"""Hedeffiyat toplayıcı: seçili kurumların o güne ait GÜNLÜK bültenini çeker.

Akış: /raporlar listesi -> kart filtrele (kurum + tarih + 'günlük bülten')
      -> rapor sayfası -> PDF linki -> PDF metni (pypdf).
"""
from __future__ import annotations

import io
import re

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from .config import Config
from .types import HamIcerik

BASE = "https://www.hedeffiyat.com.tr"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# Günlük bülteni seçmek için başlık anahtarı (teknik/haftalık raporları eler).
GUNLUK_ANAHTAR = "günlük bülten"

# Token/maliyet için rapor başına metin üst sınırı (PDF'ler tablo ağırlıklı, uzun).
MAX_RAPOR_KARAKTER = 30000

_TR_AYLAR = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "mayis": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "agustos": 8, "eylül": 9, "eylul": 9, "ekim": 10, "kasım": 11,
    "kasim": 11, "aralık": 12, "aralik": 12,
}


def tr_tarih_to_iso(metin: str) -> str | None:
    """'Pazartesi, 29 Haziran 2026' -> '2026-06-29'."""
    m = re.search(r"(\d{1,2})\s+([A-Za-zçğıöşüÇĞİÖŞÜ]+)\s+(\d{4})", metin)
    if not m:
        return None
    gun = int(m.group(1))
    ay = _TR_AYLAR.get(m.group(2).lower())
    yil = m.group(3)
    return f"{yil}-{ay:02d}-{gun:02d}" if ay else None


def parse_liste(html: str) -> list[dict]:
    """Liste sayfasındaki kartları döndürür: {firma, baslik, tarih, href}."""
    soup = BeautifulSoup(html, "html.parser")
    kartlar = []
    for k in soup.select("div.raporbox"):
        img = k.find("img")
        firma = (img.get("alt") if img else "") or ""
        baslik_el = k.select_one("a.raporbox-title")
        baslik = " ".join(baslik_el.get_text(" ", strip=True).split()) if baslik_el else ""
        tarih_el = k.select_one("div.raporbox-tarih")
        tarih = tr_tarih_to_iso(tarih_el.get_text(" ", strip=True)) if tarih_el else None
        href = k.get("data-href")
        if not href and baslik_el:
            href = baslik_el.get("href")
        if firma and baslik and href:
            kartlar.append({"firma": firma, "baslik": baslik, "tarih": tarih, "href": href})
    return kartlar


def _eslesen_kurum(firma: str, kurumlar: list[str]) -> str | None:
    """Karttaki firma adını yapılandırmadaki kanonik kurum adıyla eşler."""
    fl = firma.lower()
    for k in kurumlar:
        if k.lower() in fl or fl in k.lower():
            return k
    return None


def _gunluk_mu(baslik: str) -> bool:
    return GUNLUK_ANAHTAR in baslik.lower()


def _pdf_metni(client: httpx.Client, rapor_url: str) -> str:
    """Rapor sayfasındaki PDF'i bulup metnini çıkarır (yoksa boş döner)."""
    r = client.get(rapor_url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    pdf_url = None
    for a in soup.find_all("a", href=True):
        if ".pdf" in a["href"].lower() and "/dosyalar/" in a["href"].lower():
            pdf_url = a["href"]
            break
    if not pdf_url:
        return ""
    pr = client.get(pdf_url)
    pr.raise_for_status()
    reader = PdfReader(io.BytesIO(pr.content))
    metin = "\n".join((p.extract_text() or "") for p in reader.pages)
    metin = re.sub(r"\n{3,}", "\n\n", metin).strip()
    if len(metin) > MAX_RAPOR_KARAKTER:
        metin = metin[:MAX_RAPOR_KARAKTER] + "\n\n[... rapor kısaltıldı ...]"
    return metin


def fetch_reports(cfg: Config, tarih: str) -> tuple[list[HamIcerik], list[dict]]:
    """Seçili kurumların o güne ait günlük bültenini çeker.

    Dönüş: (icerikler, alinamayan). Firma başına ilk günlük bülten alınır.
    """
    icerikler: list[HamIcerik] = []
    alinamayan: list[dict] = []
    if not cfg.kurumlar:
        return icerikler, alinamayan

    try:
        with httpx.Client(timeout=60, follow_redirects=True, headers=HEADERS) as client:
            r = client.get(f"{BASE}/raporlar")
            r.raise_for_status()
            kartlar = parse_liste(r.text)

            secilen: dict[str, dict] = {}  # kurum -> kart (firma başına ilk günlük bülten)
            for kart in kartlar:
                kurum = _eslesen_kurum(kart["firma"], cfg.kurumlar)
                if not kurum or kurum in secilen:
                    continue
                if kart["tarih"] != tarih:
                    continue
                if not _gunluk_mu(kart["baslik"]):
                    continue
                secilen[kurum] = kart

            for kurum in cfg.kurumlar:
                kart = secilen.get(kurum)
                if not kart:
                    alinamayan.append({"kaynak": kurum, "neden": "o güne ait günlük bülten bulunamadı"})
                    continue
                try:
                    url = kart["href"]
                    if url.startswith("/"):
                        url = BASE + url
                    metin = _pdf_metni(client, url)
                    if not metin:
                        alinamayan.append({"kaynak": kurum, "neden": "PDF bulunamadı/boş"})
                        continue
                    icerikler.append(
                        HamIcerik(kaynak=kurum, baslik=kart["baslik"], tarih=tarih, metin=metin)
                    )
                except Exception as e:
                    alinamayan.append({"kaynak": kurum, "neden": f"rapor indirilemedi: {e}"})
    except Exception as e:
        return icerikler, [{"kaynak": "Hedeffiyat", "neden": f"liste alınamadı: {e}"}]

    return icerikler, alinamayan
