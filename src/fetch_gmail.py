"""Gmail toplayıcı (IMAP): yapılandırmadaki gönderenlerden o güne ait bültenleri çeker.

Salt-okunur (INBOX readonly + BODY.PEEK). Mailleri okundu işaretlemez.
"""
from __future__ import annotations

import email
import imaplib
import re
from email.header import decode_header, make_header
from email.utils import parseaddr

from bs4 import BeautifulSoup

from .config import Config
from .types import HamIcerik

_AYLAR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def imap_tarih(tarih: str) -> str:
    """'2026-06-29' -> '29-Jun-2026' (IMAP SEARCH formatı, locale'den bağımsız)."""
    y, a, g = tarih.split("-")
    return f"{int(g):02d}-{_AYLAR[int(a)]}-{y}"


def _decode(s: str | None) -> str:
    if not s:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for etiket in soup(["script", "style", "head", "title"]):
        etiket.decompose()
    metin = soup.get_text(separator="\n")
    # boş satırları ve fazla boşlukları toparla
    satirlar = [s.strip() for s in metin.splitlines()]
    satirlar = [s for s in satirlar if s]
    return "\n".join(satirlar)


def _part_text(part) -> str:
    yuk = part.get_payload(decode=True)
    if yuk is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    return yuk.decode(charset, "replace")


def extract_text(msg: email.message.Message) -> str:
    """Maildan okunabilir düz metin çıkarır (text/plain tercih; yoksa HTML temizlenir)."""
    plain_parcalar: list[str] = []
    html_parcalar: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp.lower():
                continue
            ctype = part.get_content_type()
            if ctype == "text/plain":
                plain_parcalar.append(_part_text(part))
            elif ctype == "text/html":
                html_parcalar.append(_part_text(part))
    else:
        if msg.get_content_type() == "text/html":
            html_parcalar.append(_part_text(msg))
        else:
            plain_parcalar.append(_part_text(msg))

    if plain_parcalar:
        metin = "\n".join(plain_parcalar)
    elif html_parcalar:
        metin = "\n".join(html_to_text(h) for h in html_parcalar)
    else:
        metin = ""

    return re.sub(r"\n{3,}", "\n\n", metin).strip()


def _kaynak_adi(cfg: Config, adres: str, gorunen_ad: str) -> str:
    return cfg.adlar.get(adres.lower()) or gorunen_ad or adres


def fetch_gmail(cfg: Config, tarih: str) -> tuple[list[HamIcerik], list[dict]]:
    """Gönderenlerden o güne ait mailleri çeker.

    Dönüş: (icerikler, alinamayan). 'alinamayan' yalnızca GERÇEK hatalar içindir
    (bağlantı/ayrıştırma); o gün mail gelmemiş olması hata değildir.
    """
    icerikler: list[HamIcerik] = []
    alinamayan: list[dict] = []

    if not cfg.gmail_user or not cfg.gmail_app_password:
        return icerikler, [{"kaynak": "Gmail", "neden": "kimlik bilgisi yok (.env)"}]

    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com")
        M.login(cfg.gmail_user, cfg.gmail_app_password)
    except Exception as e:
        return icerikler, [{"kaynak": "Gmail", "neden": f"bağlantı/giriş hatası: {e}"}]

    try:
        klasor = cfg.gmail_label or "INBOX"
        M.select(klasor, readonly=True)
        idate = imap_tarih(tarih)

        for sender in cfg.senderlar:
            ad_etiketi = cfg.adlar.get(sender, sender)
            try:
                typ, data = M.search(None, f'(FROM "{sender}" ON "{idate}")')
                if typ != "OK":
                    alinamayan.append({"kaynak": ad_etiketi, "neden": "IMAP arama başarısız"})
                    continue
                ids = data[0].split()
                for num in ids:
                    typ, msg_data = M.fetch(num, "(BODY.PEEK[])")
                    if typ != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    gorunen_ad, adres = parseaddr(msg.get("From", ""))
                    gorunen_ad = _decode(gorunen_ad)
                    baslik = _decode(msg.get("Subject", "")) or "(konu yok)"
                    metin = extract_text(msg)
                    if not metin:
                        continue
                    icerikler.append(
                        HamIcerik(
                            kaynak=_kaynak_adi(cfg, adres or sender, gorunen_ad),
                            baslik=baslik,
                            tarih=tarih,
                            metin=metin,
                        )
                    )
            except Exception as e:
                alinamayan.append({"kaynak": ad_etiketi, "neden": f"hata: {e}"})
    finally:
        try:
            M.logout()
        except Exception:
            pass

    return icerikler, alinamayan
