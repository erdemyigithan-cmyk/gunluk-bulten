"""Orkestratör: topla -> sentezle -> kaydet -> render et.

Faz 1: toplama henüz bağlı değil; diskteki ham içerikten (raw.json) çalışır.
Faz 2-3: fetch_reports / fetch_gmail buraya bağlanacak.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from .config import load_config, Config
from .fetch_gmail import fetch_gmail
from .fetch_reports import fetch_reports
from .render import render_site
from .storage import Storage
from .synthesize import synthesize
from .types import HamIcerik


def _bugun() -> str:
    return date.today().isoformat()


def _kaynak_durumu(icerikler: list[HamIcerik], alinamayan: list[dict] | None = None) -> dict:
    alinan = sorted({ic.kaynak for ic in icerikler})
    return {"alinan": alinan, "alinamayan": alinamayan or []}


def topla(cfg: Config, tarih: str) -> tuple[list[HamIcerik], list[dict]]:
    """Kaynaklardan ham içerik toplar. (Faz 2-3'te doldurulacak.)

    Şimdilik boş döner; gerçek toplama için raw.json'u elle seed'leyin ya da
    --dry-run / mevcut raw.json kullanın.
    """
    icerikler: list[HamIcerik] = []
    alinamayan: list[dict] = []

    # Gmail bültenleri (Faz 3)
    g_icerik, g_eksik = fetch_gmail(cfg, tarih)
    icerikler.extend(g_icerik)
    alinamayan.extend(g_eksik)

    # Hedeffiyat aracı kurum raporları (Faz 2)
    h_icerik, h_eksik = fetch_reports(cfg, tarih)
    icerikler.extend(h_icerik)
    alinamayan.extend(h_eksik)

    return icerikler, alinamayan


def _anthropic_client(cfg: Config):
    if not cfg.anthropic_api_key:
        raise SystemExit("ANTHROPIC_API_KEY tanımlı değil (.env). Sentez yapılamaz.")
    import anthropic
    return anthropic.Anthropic(api_key=cfg.anthropic_api_key)


def run(
    tarih: str | None = None,
    *,
    dry_run: bool = False,
    resynthesize: bool = False,
    kok: str = ".",
) -> None:
    cfg = load_config(kok)
    tarih = tarih or _bugun()
    storage = Storage(cfg.arsiv_dizini)

    # 1) Ham içeriği belirle
    if dry_run or resynthesize:
        icerikler = storage.load_raw(tarih)
        if not icerikler and not storage.has_raw(tarih):
            raise SystemExit(f"{tarih} için raw.json yok; --dry-run/--resynthesize çalışamaz.")
        alinamayan: list[dict] = []
    else:
        icerikler, alinamayan = topla(cfg, tarih)
        storage.save_raw(tarih, icerikler)

    kaynak_durumu = _kaynak_durumu(icerikler, alinamayan)

    # 2) Sentezle
    if icerikler:
        client = _anthropic_client(cfg) if cfg.backend == "api" else None
        sentez = synthesize(
            icerikler, tarih, kaynak_durumu,
            backend=cfg.backend, cli_model=cfg.cli_model, model=cfg.model, client=client,
        )
    else:
        # içerik yoksa hiçbir model çağrısı yapmadan boş ama geçerli sentez
        sentez = synthesize([], tarih, kaynak_durumu, backend=cfg.backend)

    # 3) Kaydet + 4) Render
    storage.save_synthesis(tarih, sentez)
    index = render_site(storage, cfg.pano_dizini)
    print(f"[ok] {tarih} sentezlendi. Pano: {index}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Günlük Bülten Sentezi")
    p.add_argument("--tarih", help="YYYY-MM-DD (varsayılan: bugün)")
    p.add_argument("--dry-run", action="store_true", help="Yeniden çekme; diskteki raw.json kullan")
    p.add_argument("--resynthesize", metavar="YYYY-MM-DD", help="O günün raw.json'undan sentezi yeniden üret")
    args = p.parse_args(argv)

    if args.resynthesize:
        run(args.resynthesize, resynthesize=True)
    else:
        run(args.tarih, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
