"""config.yaml ve .env yükleme."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Proje kökü (src/ klasörünün üstü) — göreli yolları cwd'den bağımsız çözmek için.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    senderlar: list[str] = field(default_factory=list)
    adlar: dict[str, str] = field(default_factory=dict)
    gmail_label: str = ""
    kurumlar: list[str] = field(default_factory=list)
    backend: str = "cli"
    cli_model: str = "opus"
    model: str = "claude-opus-4-8"
    calisma_saati: str = "08:00"
    arsiv_dizini: str = "./archive"
    pano_dizini: str = "./site"
    pdf_dizini: str = "./pdf"

    # .env'den
    gmail_user: str = ""
    gmail_app_password: str = ""
    anthropic_api_key: str = ""


def _load_dotenv(path: Path) -> None:
    """Basit .env yükleyici (harici bağımlılık olmadan)."""
    if not path.exists():
        return
    for satir in path.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        anahtar, _, deger = satir.partition("=")
        anahtar = anahtar.strip()
        deger = deger.strip().strip('"').strip("'")
        os.environ.setdefault(anahtar, deger)


def load_config(kok: str | Path | None = None) -> Config:
    kok = Path(kok) if kok is not None else PROJECT_ROOT
    _load_dotenv(kok / ".env")

    def _mutlak(p: str) -> str:
        yol = Path(p)
        return str(yol if yol.is_absolute() else (kok / yol).resolve())

    veri = {}
    cfg_path = kok / "config.yaml"
    if cfg_path.exists():
        veri = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    bultenler = veri.get("bultenler", {}) or {}
    hedeffiyat = veri.get("hedeffiyat", {}) or {}
    sentez = veri.get("sentez", {}) or {}

    return Config(
        senderlar=[s.lower() for s in (bultenler.get("senderlar", []) or [])],
        adlar={k.lower(): v for k, v in (bultenler.get("adlar", {}) or {}).items()},
        gmail_label=bultenler.get("gmail_label", "") or "",
        kurumlar=hedeffiyat.get("kurumlar", []) or [],
        backend=sentez.get("backend", "cli"),
        cli_model=sentez.get("cli_model", "opus"),
        model=sentez.get("model", "claude-opus-4-8"),
        calisma_saati=veri.get("calisma_saati", "08:00"),
        arsiv_dizini=_mutlak(veri.get("arsiv_dizini", "./archive")),
        pano_dizini=_mutlak(veri.get("pano_dizini", "./site")),
        pdf_dizini=_mutlak(veri.get("pdf_dizini", "./pdf")),
        gmail_user=os.environ.get("GMAIL_USER", ""),
        gmail_app_password=os.environ.get("GMAIL_APP_PASSWORD", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
