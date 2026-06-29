"""Sentezleyici: günün ham içeriğini okuyup KAPSAMLI bir markdown günlük bülten üretir.

backend="cli": Claude Code aboneliği (claude -p --model opus) — ek ücret yok (varsayılan).
backend="api": ANTHROPIC_API_KEY ile faturalı API (client gerekli).
Çıktı uzun-form markdown metindir (katı JSON şema değil).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

from .types import HamIcerik


SYSTEM_BULTEN = """Sen, bir varlık yönetim şirketinin sabah toplantısı için günlük \
piyasa bülteni hazırlayan kıdemli bir piyasa stratejistisin. Sana o güne ait çeşitli \
kaynaklardan (mail bültenleri, aracı kurum günlük raporları — Türkçe ve İngilizce) ham \
metinler verilir.

Görevin: bu kaynakların TAMAMINI okuyup anlayıp, bir fon yöneticisini besleyecek \
DETAYLI ve KAPSAMLI tek bir günlük bülten yazmak.

İlkeler:
- TÜM kaynakları kapsa, hiçbir önemli başlığı atlama: küresel piyasalar (endeksler, \
çip/teknoloji, tahvil/dolar, petrol & OPEC, değerli metaller, Avrupa/Asya), Türkiye \
makro & politika (enflasyon, TCMB faiz patikası, tahvil/kur/CDS, yabancı akımları), \
BIST görünümü (kapanış, hacim, sektör performansları, endeks katkıları, teknik \
seviyeler), şirket & sektör haberleri, model portföy / öne çıkan hisseler, ekonomik \
takvim, halka arzlar ve endeks değişiklikleri.
- ÖZET DEĞİL SENTEZ + ANALİZ: kaynaklar arasında bağ kur, ikincil etkileri (so-what) \
belirt, kaynakların AYRIŞTIĞI noktaları öne çıkar ve mümkünse nasıl uzlaştığını yaz.
- SOMUT ol: rakam, seviye, yüzde, hedef fiyat, tarih ver. Kurum görüşlerini adıyla at \
(ör. \"YKY görüşü: ...\", \"Deniz: sınırlı olumlu\").
- UYDURMA YAPMA: metinlerde olmayan veri/rakam/görüş ekleme. Bir kaynak alınamadıysa \
bunu belirt.
- Fon yöneticisinin zaten bildiği manşeti tekrarlamak yerine neyin önemli olduğunu ve \
neyi izlemesi gerektiğini söyle.

ÇIKTI BİÇİMİ:
- Yalnızca markdown yaz. Türkçe. Önsöz/sonsöz/açıklama ekleme; doğrudan bültenle başla.
- Şu başlık iskeletini kullan (## ile), içeriğe göre uyarla:
  # Günlük Bülten — <gün, tarih>
  *Kaynaklar: ...*
  ## Günün Özeti       (genel yön + günün ana gerilimi)
  ## Küresel Piyasalar
  ## Türkiye — Makro & Politika
  ## BIST Görünümü
  ## Şirket & Sektör Haberleri
  ## Model Portföy & Öne Çıkan Hisseler
  ## Kaynaklar Arası Ayrışmalar
  ## Ekonomik Takvim
  ## Halka Arzlar & Endeks Değişiklikleri
  ## İzlenecek Sinyaller
"""


def _icerikleri_metne_cevir(icerikler: list[HamIcerik]) -> str:
    parcalar = []
    for ic in icerikler:
        parcalar.append(
            f"### KAYNAK: {ic.kaynak}\n"
            f"BAŞLIK: {ic.baslik}\n"
            f"TARİH: {ic.tarih}\n\n"
            f"{ic.metin.strip()}"
        )
    return "\n\n---\n\n".join(parcalar)


def _bos_bulten(tarih: str, kaynak_durumu: dict) -> str:
    alinamayan = kaynak_durumu.get("alinamayan", [])
    not_satiri = ""
    if alinamayan:
        eksikler = ", ".join(f"{a['kaynak']} ({a['neden']})" for a in alinamayan)
        not_satiri = f"\n\n*Alınamayan kaynaklar: {eksikler}*"
    return f"# Günlük Bülten — {tarih}\n\nBugün işlenecek içerik bulunamadı.{not_satiri}\n"


def _kullanici_mesaji(icerikler: list[HamIcerik], tarih: str) -> str:
    return (
        f"Aşağıda {tarih} gününe ait kaynak metinleri var. Hepsini okuyup yukarıdaki "
        f"kurallara göre kapsamlı günlük bülteni yaz.\n\n"
        f"{_icerikleri_metne_cevir(icerikler)}"
    )


def _via_cli(kullanici_mesaji: str, cli_model: str, timeout: int = 600) -> str:
    """claude -p (abonelik) ile markdown bülten üretir. Ek ücret yok."""
    claude_bin = shutil.which("claude") or "claude"
    cmd = [
        claude_bin, "-p",
        "--model", cli_model,
        "--output-format", "json",
        "--no-session-persistence",
        "--system-prompt", SYSTEM_BULTEN,
    ]
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)  # faturalı API değil, aboneliğin OAuth'u kullanılsın
    proc = subprocess.run(
        cmd, input=kullanici_mesaji, capture_output=True, text=True, timeout=timeout, env=env
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI hatası (rc={proc.returncode}): {(proc.stderr or '')[:300]}")
    try:
        zarf = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude CLI çıktısı JSON değil: {proc.stdout[:300]}")
    if zarf.get("is_error"):
        raise RuntimeError(f"claude CLI sonuç hatası: {str(zarf.get('result', ''))[:300]}")
    md = str(zarf.get("result", "")).strip()
    if not md:
        raise RuntimeError("claude CLI boş bülten döndürdü.")
    return md


def _via_api(kullanici_mesaji: str, model: str, client, max_tokens: int) -> str:
    """ANTHROPIC_API_KEY ile faturalı API; markdown bülten döndürür."""
    yanit = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_BULTEN,
        messages=[{"role": "user", "content": kullanici_mesaji}],
    )
    parcalar = [b.text for b in yanit.content if getattr(b, "type", None) == "text"]
    md = "\n".join(parcalar).strip()
    if not md:
        raise RuntimeError("API boş bülten döndürdü.")
    return md


def synthesize_bulten(
    icerikler: list[HamIcerik],
    tarih: str,
    kaynak_durumu: dict,
    *,
    backend: str = "cli",
    cli_model: str = "opus",
    model: str = "claude-opus-4-8",
    client=None,
    max_tokens: int = 16000,
) -> str:
    """Ham içerikleri kapsamlı bir markdown bültene çevirir.

    Boş içerikte hiçbir model çağrısı yapılmaz; düzgün bir 'içerik yok' bülteni döner.
    """
    if not icerikler:
        return _bos_bulten(tarih, kaynak_durumu)

    msg = _kullanici_mesaji(icerikler, tarih)
    if backend == "cli":
        return _via_cli(msg, cli_model)
    if backend == "api":
        if client is None:
            raise ValueError("api backend için client gerekli.")
        return _via_api(msg, model, client, max_tokens)
    raise ValueError(f"bilinmeyen backend: {backend}")
