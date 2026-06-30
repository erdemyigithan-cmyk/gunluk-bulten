"""Orkestratör: topla -> sentezle (kapsamlı markdown bülten) -> kaydet -> render et.

Faz 1: toplama henüz bağlı değil; diskteki ham içerikten (raw.json) çalışır.
Faz 2-3: fetch_reports / fetch_gmail bağlandı.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from pathlib import Path

from .config import load_config, Config
from .fetch_gmail import fetch_gmail
from .fetch_reports import fetch_reports
from .pdf import markdown_to_pdf
from .render import render_site
from .storage import Storage
from .synthesize import synthesize_bulten
from .types import HamIcerik


def _bugun() -> str:
    return date.today().isoformat()


def _kaynak_durumu(icerikler: list[HamIcerik], alinamayan: list[dict] | None = None) -> dict:
    alinan = sorted({ic.kaynak for ic in icerikler})
    return {"alinan": alinan, "alinamayan": alinamayan or []}


def topla(cfg: Config, tarih: str) -> tuple[list[HamIcerik], list[dict]]:
    """Kaynaklardan ham içerik toplar (Gmail bültenleri + Hedeffiyat raporları)."""
    icerikler: list[HamIcerik] = []
    alinamayan: list[dict] = []

    g_icerik, g_eksik = fetch_gmail(cfg, tarih)
    icerikler.extend(g_icerik)
    alinamayan.extend(g_eksik)

    h_icerik, h_eksik = fetch_reports(cfg, tarih)
    icerikler.extend(h_icerik)
    alinamayan.extend(h_eksik)

    return icerikler, alinamayan


def _anthropic_client(cfg: Config):
    if not cfg.anthropic_api_key:
        raise SystemExit("ANTHROPIC_API_KEY tanımlı değil (.env). api backend kullanılamaz.")
    import anthropic
    return anthropic.Anthropic(api_key=cfg.anthropic_api_key)


def fetch_only(tarih: str | None = None, *, kok: str | None = None) -> None:
    """Sadece kaynakları çekip raw.json + meta.json yazar (sentez yok).

    Zamanlanmış Claude oturumu bunu çağırır, sonra ham içeriği okuyup bülteni
    kendisi yazar (sentez aboneliğiyle, oturum içinde)."""
    cfg = load_config(kok)
    tarih = tarih or _bugun()
    storage = Storage(cfg.arsiv_dizini)
    icerikler, alinamayan = topla(cfg, tarih)
    storage.save_raw(tarih, icerikler)
    kaynak_durumu = _kaynak_durumu(icerikler, alinamayan)
    storage.save_meta(tarih, {"tarih": tarih, "kaynak_durumu": kaynak_durumu})
    print(f"[fetch] {tarih}: {len(icerikler)} kaynak çekildi -> {storage._gun_dizini(tarih)/'raw.json'}")
    for ic in icerikler:
        print(f"   [{ic.kaynak}] {ic.baslik[:55]} ({len(ic.metin)} kr)")
    if alinamayan:
        print(f"   alinamayan: {alinamayan}")


def yayinla(tarih: str | None = None, *, kok: str | None = None) -> None:
    """Diskteki bulten.md'den panoyu render eder ve tarihli PDF üretir."""
    cfg = load_config(kok)
    tarih = tarih or _bugun()
    storage = Storage(cfg.arsiv_dizini)
    md = storage.load_bulten(tarih)
    if not md:
        raise SystemExit(f"{tarih} için bulten.md yok; önce bülteni yaz.")
    index = render_site(storage, cfg.pano_dizini)
    pdf_yolu = Path(cfg.pdf_dizini) / f"bulten-{tarih}.pdf"
    markdown_to_pdf(md, pdf_yolu)
    print(f"[yayin] {tarih} -> Pano: {index} | PDF: {pdf_yolu}")


def run(
    tarih: str | None = None,
    *,
    dry_run: bool = False,
    resynthesize: bool = False,
    kok: str | None = None,
) -> None:
    """Tam akış (api/cli backend ile sentez dahil). Not: cli backend bu ortamda
    'Not logged in' duvarına takılır; günlük otomasyon zamanlanmış oturumla yapılır
    (fetch_only + oturum-içi sentez + yayinla)."""
    cfg = load_config(kok)
    tarih = tarih or _bugun()
    storage = Storage(cfg.arsiv_dizini)

    if dry_run or resynthesize:
        icerikler = storage.load_raw(tarih)
        if not icerikler and not storage.has_raw(tarih):
            raise SystemExit(f"{tarih} için raw.json yok; --dry-run/--resynthesize çalışamaz.")
        alinamayan: list[dict] = []
    else:
        icerikler, alinamayan = topla(cfg, tarih)
        storage.save_raw(tarih, icerikler)

    kaynak_durumu = _kaynak_durumu(icerikler, alinamayan)
    client = _anthropic_client(cfg) if cfg.backend == "api" and icerikler else None
    bulten = synthesize_bulten(
        icerikler, tarih, kaynak_durumu,
        backend=cfg.backend, cli_model=cfg.cli_model, model=cfg.model, client=client,
    )
    storage.save_bulten(tarih, bulten)
    storage.save_meta(tarih, {"tarih": tarih, "kaynak_durumu": kaynak_durumu,
                              "backend": cfg.backend,
                              "model": cfg.cli_model if cfg.backend == "cli" else cfg.model})
    yayinla(tarih, kok=kok)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Günlük Bülten Sentezi")
    p.add_argument("--tarih", help="YYYY-MM-DD (varsayılan: bugün)")
    p.add_argument("--fetch-only", action="store_true", help="Sadece kaynakları çek (raw.json); sentez yapma")
    p.add_argument("--publish", action="store_true", help="Diskteki bulten.md'den pano + PDF üret")
    p.add_argument("--dry-run", action="store_true", help="Yeniden çekme; diskteki raw.json ile tam akış")
    p.add_argument("--resynthesize", metavar="YYYY-MM-DD", help="O günün raw.json'undan bülteni yeniden üret")
    args = p.parse_args(argv)

    if args.fetch_only:
        fetch_only(args.tarih)
    elif args.publish:
        yayinla(args.tarih)
    elif args.resynthesize:
        run(args.resynthesize, resynthesize=True)
    else:
        run(args.tarih, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
